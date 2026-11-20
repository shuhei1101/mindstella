"""常駐サーバーの起動時の照合（待ち受けの前の ID の一覧の作り直しと状態の照合、待ち受けの後のエージェントフローの配信元の確認）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from session_fixtures import SessionWorld, wait_until
from workspace_fixtures import REPO_ROOT, UNREACHABLE_PROJECT_INDEX_PORT

from .test_work_done_notify import FakeWebhook

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# エージェントフローの配信元の ID と、起動した常駐サーバーのプラグインの配信の設定
AGENT_FLOWS_SOURCE = "mindstella-agent-flows"
CURRENT_AGENT_FLOWS_CONFIG = str(REPO_ROOT / "plugins" / "mindstella" / "agent-flows" / "dev-docs.yaml")

# 更新の前のプラグインの配信の設定
OLD_AGENT_FLOWS_CONFIG = "/old/plugin/agent-flows/dev-docs.yaml"

# 待ち受けの後のスレッドが要求を出し終えるまで、追加の要求が来ないことを確かめて待つ秒数
SETTLE_SEC = 1.0


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()


def _prepare_workspaces(world: SessionWorld, *names: str) -> list[str]:
    """常駐サーバーを 1 度起動してワークスペースを作り、常駐サーバーを止めて ID を返す。"""
    server = world.start()
    # ID の一覧が無いので、待ち受けの前の作り直しと待ち受けの後の確認の GET が 2 件届いてから作る
    # （後から届く要求を次の起動の分と混ぜない）
    wait_until(lambda: len(_requests(world, "GET")) >= 2)
    ids = [str(world.create_workspace(name)["id"]) for name in names]
    server.stop()
    world.pi.requests.clear()
    return ids


def _webhook_env(world: SessionWorld, webhook: FakeWebhook) -> dict[str, str]:
    """Webhook の URL を記載した設定のファイルを置き、常駐サーバーへ指定する環境変数を返す。"""
    path = world.root / "webhook.ini"
    path.write_text(f"{webhook.url}\n", encoding="utf-8")
    return {WEBHOOK_FILE_ENV: str(path)}


def _ids_file(world: SessionWorld) -> Path:
    """状態のフォルダの workspaces.yaml。"""
    return world.state_root / "workspaces.yaml"


def _status(world: SessionWorld, workspace_id: str) -> str | None:
    """session.json の status。"""
    session = world.read_session(workspace_id)
    return None if session is None else str(session["status"])


def _requests(world: SessionWorld, method: str) -> list[tuple[str, str, Any]]:
    """project-index の Mock が受けた、指定のメソッドの要求。"""
    return [request for request in world.pi.requests if request[0] == method]


def test_normal(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """ID の一覧がある状態で、ペインが無い running の MindStella のセッションを crashed にし、通知を 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    stopped_id, dead_id = _prepare_workspaces(world, "a", "b")
    ids_before = _ids_file(world).read_text(encoding="utf-8")
    world.write_session(stopped_id, status="stopped", pane=None)
    world.write_session(dead_id, status="running")
    # 実行
    server = world.start(_webhook_env(world, webhook))
    # 検証
    assert _status(world, dead_id) == "crashed", server.stderr_text()
    assert _status(world, stopped_id) == "stopped"
    wait_until(lambda: webhook.requests)
    wait_until(lambda: len(_requests(world, "GET")) >= 3)
    time.sleep(SETTLE_SEC)
    assert len(webhook.requests) == 1
    assert "異常終了" in str(webhook.requests[0]["body"]["content"])
    # 停止の通知が B の行を引く 1 件と、待ち受けの後の確認の 1 件と、配り始めの 1 件（作り直しの GET は無い）
    assert len(_requests(world, "GET")) == 3
    assert _requests(world, "PATCH") == []
    assert _ids_file(world).read_text(encoding="utf-8") == ids_before


def test_normal_when_ids_missing(session_world: SessionWorld) -> None:
    """ワークスペースの行の ID で workspaces.yaml を作り、作った ID の一覧で照合する（正常系）。"""
    # 準備
    world = session_world
    first_id, dead_id, closed_id = _prepare_workspaces(world, "a", "b", "c")
    world.pi.rows[closed_id]["outsideRead"] = False
    world.pi.rows["knowledge"] = {
        "id": "knowledge",
        "config": ["/k/dev-docs.yaml"],
        "scope": {"read": ["/k"]},
        "outsideRead": True,
        "status": "served",
    }
    world.pi.save()
    _ids_file(world).unlink()
    world.write_session(dead_id, status="running")
    # 実行
    world.start()
    # 検証
    assert _ids_file(world).read_text(encoding="utf-8") == (
        f"ids:\n- {first_id}\n- {dead_id}\n- {closed_id}\n"
    )
    assert _status(world, dead_id) == "crashed"
    status, body = world.api("GET", "/workspaces")
    assert status == 200
    assert [entry["id"] for entry in body["workspaces"]] == [first_id, dead_id]
    # 待ち受けの前の作り直しと、待ち受けの後の確認と、配り始めの 3 件
    wait_until(lambda: len(_requests(world, "GET")) >= 3)
    time.sleep(SETTLE_SEC)
    assert len(_requests(world, "GET")) == 3


def test_normal_when_plugin_updated(session_world: SessionWorld) -> None:
    """mindstella-agent-flows の行の config を今のプラグインのパスへ書き換える（正常系）。"""
    # 準備
    world = session_world
    _prepare_workspaces(world, "a")
    world.pi.rows[AGENT_FLOWS_SOURCE]["config"] = [OLD_AGENT_FLOWS_CONFIG]
    world.pi.save()
    original_patch = world.pi.patch
    patch_calls: list[int] = []

    def patch_once_conflict(path: str, body: Any) -> tuple[int, Any]:
        """最初の PATCH だけ版が更新前として 409 を返却し、2 回目からは Mock の処理に任せる。"""
        patch_calls.append(1)
        if len(patch_calls) == 1:
            return 409, {"current": str(world.pi.version)}
        return original_patch(path, body)

    world.pi.patch = patch_once_conflict  # type: ignore[method-assign]
    # 実行
    world.start()
    # 検証
    wait_until(lambda: len(_requests(world, "PATCH")) >= 2)
    time.sleep(SETTLE_SEC)
    patches = _requests(world, "PATCH")
    assert len(patches) == 2
    assert patches[0][2]["source"] == {"config": CURRENT_AGENT_FLOWS_CONFIG}
    assert patches[1][2]["source"] == {"config": CURRENT_AGENT_FLOWS_CONFIG}
    assert set(patches[1][2]) == {"expectedVersion", "source"}
    assert patches[1][2]["expectedVersion"] == str(world.pi.version - 1)
    assert world.pi.rows[AGENT_FLOWS_SOURCE]["config"] == [CURRENT_AGENT_FLOWS_CONFIG]


def test_normal_when_agent_flows_missing(session_world: SessionWorld) -> None:
    """mindstella-agent-flows の行が無ければ追加しない（正常系）。"""
    # 準備
    world = session_world
    _prepare_workspaces(world, "a")
    del world.pi.rows[AGENT_FLOWS_SOURCE]
    world.pi.save()
    # 実行
    world.start()
    # 検証
    wait_until(lambda: _requests(world, "GET"))
    time.sleep(SETTLE_SEC)
    assert _requests(world, "POST") == []
    assert _requests(world, "PATCH") == []


def test_error_when_project_index_down(session_world: SessionWorld) -> None:
    """ID の一覧の作り直しとエージェントフローの配信元の確認を飛ばし、照合だけをして待ち受ける（異常系）。"""
    # 準備
    world = session_world
    # 実行
    server = world.start({"PROJECT_INDEX_PORT": UNREACHABLE_PROJECT_INDEX_PORT})
    # 検証
    assert world.api("GET", "/_admin/status")[0] == 200
    assert not _ids_file(world).exists()
    wait_until(lambda: "mindstella.startup.agent_flows_skipped" in server.stderr_text())
    log = server.stderr_text()
    assert log.count("mindstella.startup.rebuild_skipped") == 1
    assert log.count("mindstella.startup.agent_flows_skipped") == 1


def test_error_when_ids_unreadable(session_world: SessionWorld) -> None:
    """読めない workspaces.yaml を書き換えず、照合を飛ばして待ち受ける（異常系）。"""
    # 準備
    world = session_world
    world.state_root.mkdir(parents=True, exist_ok=True)
    _ids_file(world).write_text("ids: [a, b\n", encoding="utf-8")
    # 実行
    server = world.start()
    # 検証
    assert world.api("GET", "/_admin/status")[0] == 200
    assert _ids_file(world).read_text(encoding="utf-8") == "ids: [a, b\n"
    assert "mindstella.startup.ids_unreadable" in server.stderr_text()
