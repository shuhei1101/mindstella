"""workspaces.py（ワークスペースの作成とクローズ）の単体テスト。"""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

import migrator
import project_index
import read_point
import sessions
import settings_update
import state
import workspaces
from errors import ApiError, StepFailedError
from fixture_types import PatchPluginVersion, SnapshotTree
from project_index import ProjectIndexError
from state import LaunchOptions, SessionState
from workspaces import WorkspaceLocks

# 進め方の文書
FLOW = {"source": "aituber", "doc": "flow-1"}

# 追加の MCP の定義
MCP_CONFIG = {"mcpServers": {"aituber": {"command": "aituber-mcp"}}}

# 配信の URL
PREVIEW_URL = "http://127.0.0.1:9100/mindstella.html"


class FakePreviews:
    """配信を立てたことにして URL を返す配信の台帳。"""

    def start(self, root: Path) -> tuple[str, bool]:
        """立てたことにする。"""
        return PREVIEW_URL, True

    def __init__(self) -> None:
        """止めた配信の ID を空で始める。"""
        self.stopped: list[str] = []

    def url_of(self, root: Path) -> str:
        """配っている URL を返す。"""
        return PREVIEW_URL

    def stop_workspace(self, workspace_id: str) -> None:
        """止めたワークスペースの ID を記録する。"""
        self.stopped.append(workspace_id)


class FakeProjectIndex:
    """配信元の行を持ち、project_index の関数の代わりに答える。"""

    def __init__(self, settings_path: Path) -> None:
        """空の行で始める。"""
        self.settings_path = settings_path
        self.rows: dict[str, dict[str, Any]] = {}
        self.added: list[dict[str, Any]] = []
        self.patched: list[tuple[str, dict[str, Any]]] = []
        self.add_error: ProjectIndexError | None = None
        self.reloads = 0
        self.reload_error: ProjectIndexError | None = None
        self.patch_error: ProjectIndexError | None = None
        self.deleted: list[str] = []
        self.delete_error: ProjectIndexError | None = None

    def get_settings(self, port: int) -> dict[str, Any]:
        """設定のファイルのパスと行を返す。"""
        return {
            "settingsPath": str(self.settings_path),
            "version": "v1",
            "sources": list(self.rows.values()),
        }

    def add_source(self, port: int, row: dict[str, Any]) -> str:
        """行を足す。同じ ID があれば足さない。"""
        if self.add_error is not None:
            raise self.add_error
        self.added.append(row)
        if row["id"] in self.rows:
            return "exists_same"
        self.rows[row["id"]] = {
            "id": row["id"],
            "config": [row["config"]],
            "scope": row["scope"],
            "outsideRead": row.get("outside_read", True),
        }
        return "added"

    def patch_source(self, port: int, source_id: str, changes: dict[str, Any]) -> None:
        """行のキーを変える。"""
        if self.patch_error is not None:
            raise self.patch_error
        self.patched.append((source_id, changes))
        if "outside_read" in changes:
            self.rows[source_id]["outsideRead"] = changes["outside_read"]

    def delete_source(self, port: int, source_id: str) -> bool:
        """行を削除する。行が無ければ偽を返す。"""
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted.append(source_id)
        return self.rows.pop(source_id, None) is not None

    def reload_sources(self, port: int) -> None:
        """全ての配信元を読み直させたことを数える。"""
        if self.reload_error is not None:
            raise self.reload_error
        self.reloads += 1


@pytest.fixture
def allowed(tmp_path: Path) -> Path:
    """許可するフォルダ。"""
    folder = tmp_path / "allowed"
    folder.mkdir()
    return folder


@pytest.fixture
def fake_pi(tmp_path: Path, allowed: Path, monkeypatch: pytest.MonkeyPatch) -> FakeProjectIndex:
    """許可するフォルダを書いた設定のファイルと、偽の project-index の関数。"""
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        yaml.safe_dump({"mindstella": {"allowed_dirs": [str(allowed)]}, "sources": []}),
        encoding="utf-8",
    )
    fake = FakeProjectIndex(settings_path)
    monkeypatch.setattr(project_index, "get_settings", fake.get_settings)
    monkeypatch.setattr(project_index, "add_source", fake.add_source)
    monkeypatch.setattr(project_index, "patch_source", fake.patch_source)
    monkeypatch.setattr(project_index, "reload_sources", fake.reload_sources, raising=False)
    monkeypatch.setattr(project_index, "delete_source", fake.delete_source, raising=False)
    monkeypatch.setattr(workspaces, "check_flow", lambda *_args: None)
    monkeypatch.setattr(sessions, "is_alive", lambda *_args, **_kwargs: False)
    return fake


@pytest.fixture
def ctx(tmp_path: Path) -> SimpleNamespace:
    """入口が渡す値。"""
    return SimpleNamespace(
        port=8784,
        pi_port=8786,
        state_root=tmp_path / "state",
        locks=WorkspaceLocks(),
        previews=FakePreviews(),
        plugin_root=tmp_path / "plugin",
        tmux=None,
        proc=None,
    )


def _request(folder: Path, **changes: object) -> dict[str, Any]:
    """作成の本文を作る。"""
    body: dict[str, Any] = {
        "folder": str(folder),
        "flow": FLOW,
        "mcp_config": MCP_CONFIG,
        "plugin_dirs": [],
    }
    body.update(changes)
    return body


def _write_session(ctx: SimpleNamespace, workspace_id: str, **changes: object) -> None:
    """MindStella のセッションの状態を書く。"""
    values: dict[str, Any] = {
        "session": "S-0123456789ab",
        "status": "stopped",
        "started_at": "2026-11-15T00:00:00+00:00",
    }
    values.update(changes)
    state.update_session(ctx.state_root, workspace_id, lambda _current: SessionState(**values))


def test_workspace_id_for(tmp_path: Path) -> None:
    """同じフォルダは同じ ID、別の場所の同じ名前は別の ID。"""
    first = tmp_path / "a" / "家計簿.app"
    second = tmp_path / "b" / "家計簿.app"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(first)
    workspace_id = workspaces.workspace_id_for(first)
    assert re.fullmatch(r"mindstella-家計簿-app-[0-9a-f]{6}", workspace_id)
    assert workspaces.workspace_id_for(link) == workspace_id
    assert workspaces.workspace_id_for(second) != workspace_id


def test_validate_options(tmp_path: Path) -> None:
    """形が合えば LaunchOptions を返す。"""
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "aituber"}', encoding="utf-8")
    assert workspaces.validate_options(MCP_CONFIG, [str(plugin)]) == LaunchOptions(
        mcp_config=MCP_CONFIG, plugin_dirs=[str(plugin)]
    )


@pytest.mark.parametrize(
    ("mcp_config", "plugin_json", "stage"),
    [
        pytest.param(
            {"mcpServers": {"mindstella": {"command": "x"}}},
            '{"name": "p"}',
            "mcp_config",
            id="reserved",
        ),
        pytest.param({"servers": {}}, '{"name": "p"}', "mcp_config", id="no-mcp-servers"),
        pytest.param(None, None, "plugin_dirs", id="no-plugin-json"),
        pytest.param(None, "{broken", "plugin_dirs", id="broken-plugin-json"),
    ],
)
def test_validate_options_error(
    mcp_config: dict[str, Any] | None, plugin_json: str | None, stage: str, tmp_path: Path
) -> None:
    """読めない指定は ApiError 422。"""
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    if plugin_json is not None:
        (plugin / ".claude-plugin" / "plugin.json").write_text(plugin_json, encoding="utf-8")
    with pytest.raises(ApiError) as caught:
        workspaces.validate_options(mcp_config, [str(plugin)])
    assert caught.value.status == 422
    assert caught.value.stage == stage


def _flow_settings(folder: Path) -> dict[str, Any]:
    """進め方の文書の配信元の行を持つ設定。"""
    return {
        "version": "v1",
        "sources": [{"id": "aituber", "scope": {"read": [str(folder), f"{folder}/**"]}}],
    }


def test_check_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """3 段とも通れば例外を送らない。"""
    monkeypatch.setattr(project_index, "get_settings", lambda _port: _flow_settings(tmp_path))
    monkeypatch.setattr(project_index, "find_doc_path", lambda *_args: "docs/flow.yaml")
    monkeypatch.setattr(project_index, "doc_exists", lambda *_args: True)
    workspaces.check_flow(8786, FLOW, tmp_path / "w")


@pytest.mark.parametrize(
    ("scope_folder", "doc_path", "exists"),
    [
        pytest.param("/elsewhere", "docs/flow.yaml", True, id="scope"),
        pytest.param(None, None, True, id="not-listed"),
        pytest.param(None, "docs/flow.yaml", False, id="not-found"),
    ],
)
def test_check_flow_error(
    scope_folder: str | None,
    doc_path: str | None,
    exists: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """どこかで止まれば ApiError 422（stage: flow）。"""
    folder = Path(scope_folder) if scope_folder else tmp_path
    monkeypatch.setattr(project_index, "get_settings", lambda _port: _flow_settings(folder))
    monkeypatch.setattr(project_index, "find_doc_path", lambda *_args: doc_path)
    monkeypatch.setattr(project_index, "doc_exists", lambda *_args: exists)
    with pytest.raises(ApiError) as caught:
        workspaces.check_flow(8786, FLOW, tmp_path / "w")
    assert caught.value.status == 422
    assert caught.value.stage == "flow"


def test_create_workspace(allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """記録の無いフォルダに作る。"""
    folder = allowed / "家計簿"
    status, body = workspaces.create_workspace(_request(folder), ctx)
    assert status == 201
    assert body["result"] == "created"
    assert body["launch_options_recorded"] is True
    assert body["url"] == PREVIEW_URL
    config = yaml.safe_load((folder / ".mindstella" / "config.yaml").read_text(encoding="utf-8"))
    assert config["id"] == body["id"]
    assert config["flow"] == FLOW
    assert config["summary"] == "家計簿"
    assert state.read_launch(ctx.state_root, body["id"]) == LaunchOptions(
        mcp_config=MCP_CONFIG, plugin_dirs=[]
    )
    assert state.read_ids(ctx.state_root) == [body["id"]]
    row = fake_pi.added[0]
    assert row["config"] == f"{folder.resolve()}/.mindstella/dev-docs.yaml"
    assert row["scope"]["read"] == [str(folder.resolve()), f"{folder.resolve()}/**"]


def test_create_workspace_opened(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """記録があり launch.json が無ければ、今回の指定を記録して opened。"""
    folder = allowed / "家計簿"
    _status, created = workspaces.create_workspace(_request(folder), ctx)
    state.delete_launch(ctx.state_root, created["id"])
    fake_pi.rows.clear()
    config_before = (folder / ".mindstella" / "config.yaml").read_bytes()
    status, body = workspaces.create_workspace(_request(folder, flow=None), ctx)
    assert (status, body["result"], body["launch_options_recorded"]) == (200, "opened", True)
    assert (folder / ".mindstella" / "config.yaml").read_bytes() == config_before


def test_create_workspace_already_open(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """既に開いていれば何も変えない。"""
    folder = allowed / "家計簿"
    _status, created = workspaces.create_workspace(_request(folder), ctx)
    status, body = workspaces.create_workspace(_request(folder, mcp_config=None), ctx)
    assert (status, body["result"], body["launch_options_recorded"]) == (200, "already_open", False)
    assert state.read_launch(ctx.state_root, created["id"]) == LaunchOptions(
        mcp_config=MCP_CONFIG, plugin_dirs=[]
    )


def test_create_workspace_reopened(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """クローズ済みなら outside_read を戻し、クローズ待ちを解く。"""
    folder = allowed / "家計簿"
    _status, created = workspaces.create_workspace(_request(folder), ctx)
    fake_pi.rows[created["id"]]["outsideRead"] = False
    _write_session(ctx, created["id"], close_pending=True)
    status, body = workspaces.create_workspace(_request(folder), ctx)
    assert (status, body["result"]) == (200, "reopened")
    assert fake_pi.patched == [(created["id"], {"outside_read": True})]
    session = state.read_session(ctx.state_root, created["id"])
    assert session is not None
    assert session.close_pending is False


def _moved(allowed: Path, ctx: SimpleNamespace) -> tuple[str, Path, Path]:
    """前のフォルダに作ったワークスペースを移した先のフォルダへ移し、ID と 2 つのフォルダを返す。"""
    before = allowed / "家計簿"
    after = allowed / "家計簿-移動後"
    _status, created = workspaces.create_workspace(_request(before), ctx)
    before.rename(after)
    return created["id"], before.resolve(), after.resolve()


def _moved_changes(folder: Path) -> dict[str, Any]:
    """移した先のフォルダへ変える配信元の行のキー。"""
    paths = [str(folder), f"{folder}/**"]
    return {
        "config": f"{folder}/.mindstella/dev-docs.yaml",
        "scope": {"read": paths, "write": list(paths)},
    }


def test_create_workspace_moved(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """配信元の行が記録の無い前のフォルダを指せば、行を移した先へ変える。"""
    # 準備
    workspace_id, before, after = _moved(allowed, ctx)
    assert workspace_id == workspaces.workspace_id_for(before)
    # 実行
    status, body = workspaces.create_workspace(_request(after), ctx)
    # 検証
    assert (status, body["id"], body["result"]) == (200, workspace_id, "opened")
    assert fake_pi.patched == [(workspace_id, _moved_changes(after))]
    assert [row["id"] for row in fake_pi.added] == [workspace_id, workspaces.AGENT_FLOWS_SOURCE]


def test_create_workspace_moved_closed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """移した先でクローズ済みの行は同じ依頼で outside_read も戻す。"""
    # 準備
    workspace_id, _before, after = _moved(allowed, ctx)
    fake_pi.rows[workspace_id]["outsideRead"] = False
    _write_session(ctx, workspace_id, close_pending=True)
    # 実行
    status, body = workspaces.create_workspace(_request(after), ctx)
    # 検証
    assert (status, body["result"]) == (200, "reopened")
    assert fake_pi.patched == [
        (workspace_id, {**_moved_changes(after), "outside_read": True})
    ]
    session = state.read_session(ctx.state_root, workspace_id)
    assert session is not None
    assert session.close_pending is False


def test_create_workspace_duplicate(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """行が指す別のフォルダに同じ ID の記録があれば 409。"""
    # 準備
    original = allowed / "家計簿"
    copied = allowed / "家計簿-コピー"
    workspaces.create_workspace(_request(original), ctx)
    copied.mkdir()
    shutil.copytree(original / ".mindstella", copied / ".mindstella")
    # 実行
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(copied), ctx)
    # 検証
    assert (caught.value.status, caught.value.stage) == (409, "duplicate")
    assert str(original.resolve()) in caught.value.detail
    assert fake_pi.patched == []
    assert [row["id"] for row in fake_pi.added] == [
        workspaces.workspace_id_for(original.resolve()),
        workspaces.AGENT_FLOWS_SOURCE,
    ]


def test_create_workspace_moved_patch_failed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """行の変更が失敗すれば 502 で記録は消さない。"""
    # 準備
    workspace_id, _before, after = _moved(allowed, ctx)

    def failing_patch(_port: int, _source_id: str, _changes: dict[str, Any]) -> None:
        raise ProjectIndexError(None, "つながりません")

    monkeypatch.setattr(project_index, "patch_source", failing_patch)
    # 実行
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(after), ctx)
    # 検証
    assert (caught.value.status, caught.value.stage) == (502, "source")
    assert (after / ".mindstella" / "config.yaml").is_file()
    assert state.read_launch(ctx.state_root, workspace_id) is not None


def test_create_workspace_rollback(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """配信元の登録に失敗したら、作った記録とこの依頼で書いた README を消す。"""
    folder = allowed / "家計簿"
    fake_pi.add_error = ProjectIndexError(None, "つながりません")
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (502, "source")
    workspace_id = workspaces.workspace_id_for(folder)
    assert not (folder / ".mindstella").exists()
    assert not (folder / "README.md").exists()
    assert state.read_launch(ctx.state_root, workspace_id) is None
    assert workspace_id not in state.read_ids(ctx.state_root)


def test_create_workspace_rollback_keeps_user_readme(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """作成の前からあった利用者の README は、巻き戻しで消さない。"""
    folder = allowed / "家計簿"
    folder.mkdir()
    (folder / "README.md").write_text("利用者のメモ\n", encoding="utf-8")
    fake_pi.add_error = ProjectIndexError(None, "つながりません")
    with pytest.raises(ApiError):
        workspaces.create_workspace(_request(folder), ctx)
    assert (folder / "README.md").read_text(encoding="utf-8") == "利用者のメモ\n"


@pytest.mark.parametrize(
    "has_key", [pytest.param(True, id="other-folder"), pytest.param(False, id="no-key")]
)
def test_create_workspace_folder_not_allowed(
    has_key: bool, tmp_path: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """許可するフォルダの外は 403 で、何も書かない。"""
    other = tmp_path / "other"
    other.mkdir()
    content: dict[str, Any] = {"sources": []}
    if has_key:
        content["mindstella"] = {"allowed_dirs": [str(other)]}
    fake_pi.settings_path.write_text(yaml.safe_dump(content), encoding="utf-8")
    folder = tmp_path / "allowed" / "家計簿"
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (403, "folder")
    assert not folder.exists()
    assert not ctx.state_root.exists()


@pytest.mark.parametrize(
    ("folder_name", "file_name"),
    [pytest.param("docs", "memo.md", id="docs"), pytest.param("files", "memo.png", id="files")],
)
def test_create_workspace_root_folder_exists(
    folder_name: str,
    file_name: str,
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
) -> None:
    """記録が無く直下に docs/ か files/ があれば 409 で、何も書かない（異常系）。"""
    # 準備
    folder = allowed / "家計簿"
    (folder / folder_name).mkdir(parents=True)
    (folder / folder_name / file_name).write_text("利用者のファイル\n", encoding="utf-8")
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (409, "root_folder")
    assert f"{folder_name}/" in caught.value.detail
    assert not (folder / ".mindstella").exists()
    assert not (folder / "README.md").exists()
    assert (folder / folder_name / file_name).read_text(encoding="utf-8") == "利用者のファイル\n"
    assert fake_pi.added == []
    assert not ctx.state_root.exists()


def _legacy_folder(allowed: Path, version: str) -> Path:
    """版 version の記録を持ち、設定に削除したキー playbooks を持つワークスペースのフォルダを作る。"""
    folder = allowed / "家計簿"
    records = folder / ".mindstella"
    (records / "docs").mkdir(parents=True)
    (records / "config.yaml").write_text(
        "summary: 家計簿\nplaybooks: [システム開発]\nlinks: []\n", encoding="utf-8"
    )
    (records / "mindstella-version.ini").write_text(f"{version}\n", encoding="utf-8")
    return folder


def test_create_workspace_migrated(
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    patch_plugin_version: PatchPluginVersion,
) -> None:
    """前の版の記録は移し替えて開き、報告を残す（正常系）。"""
    # 準備
    patch_plugin_version("v0.14.0")
    folder = _legacy_folder(allowed, "v0.13.0")
    # 実行
    status, body = workspaces.create_workspace(_request(folder), ctx)
    # 検証
    assert (status, body["result"]) == (200, "opened")
    assert body["migration"]["from_version"] == "v0.13.0"
    config = yaml.safe_load((folder / ".mindstella" / "config.yaml").read_text(encoding="utf-8"))
    assert "playbooks" not in config
    assert read_point.load_migration_report(folder, state_root=ctx.state_root) is not None
    # 配信の検知を立てない台帳でも、移し替えた後に前回の中身（rebase_snapshot の書き出し）がある
    assert (ctx.state_root / "workspaces" / body["id"] / "snapshot" / "docs").is_dir()


def test_create_workspace_newer(
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    patch_plugin_version: PatchPluginVersion,
    snapshot_tree: SnapshotTree,
) -> None:
    """記録の版が新しければ 409（異常系）。"""
    # 準備
    patch_plugin_version("v0.14.0")
    folder = _legacy_folder(allowed, "v9.0.0")
    before = snapshot_tree(folder)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (409, "version")
    assert snapshot_tree(folder) == before
    assert fake_pi.added == []


def test_create_workspace_migration_failed(
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    patch_plugin_version: PatchPluginVersion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """移し替えが失敗したら 422（異常系）。"""
    # 準備
    patch_plugin_version("v0.14.0")
    folder = _legacy_folder(allowed, "v0.13.0")

    def _fail(*_args: object, **_kwargs: object) -> None:
        """手順の失敗を送る。"""
        raise StepFailedError("v0.14.0 の手順 1（call）: 手順が失敗しました")

    monkeypatch.setattr(migrator, "migrate", _fail)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (422, "migration")
    assert fake_pi.added == []


def test_ensure_agent_flows_source(fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """行が無ければ足す（正常系）。"""
    # 実行
    workspaces.ensure_agent_flows_source(ctx, [Path("/w")])
    # 検証
    assert len(fake_pi.added) == 1
    row = fake_pi.added[0]
    assert row["id"] == "mindstella-agent-flows"
    assert row["config"].endswith("/agent-flows/dev-docs.yaml")
    assert row["scope"]["read"] == ["/w", "/w/**"]
    assert "write" not in row["scope"]


def test_ensure_agent_flows_source_when_exists(fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """行があれば何も送らない（正常系）。"""
    # 準備
    fake_pi.rows["mindstella-agent-flows"] = {"id": "mindstella-agent-flows", "config": [], "scope": {}}
    # 実行
    workspaces.ensure_agent_flows_source(ctx, [Path("/w")])
    # 検証
    assert fake_pi.added == []


def test_ensure_agent_flows_source_when_failed(
    fake_pi: FakeProjectIndex, ctx: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    """足せなくても止めずに記録する（正常系）。"""
    # 準備
    fake_pi.add_error = ProjectIndexError(None, "つながりません")
    # 実行
    with caplog.at_level(logging.WARNING):
        workspaces.ensure_agent_flows_source(ctx, [Path("/w")])
    # 検証
    assert "mindstella.agent_flows.register_failed" in caplog.text


def test_create_workspace_rollback_failed(
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """巻き戻しの削除に失敗しても 502 を返し、記録する。"""
    folder = allowed / "家計簿"
    fake_pi.add_error = ProjectIndexError(500, "壊れています")

    def fail(*_args: object, **_kwargs: object) -> None:
        """消せない。"""
        raise OSError("busy")

    monkeypatch.setattr(workspaces.shutil, "rmtree", fail)
    with caplog.at_level(logging.ERROR), pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert caught.value.status == 502
    assert str(folder.resolve() / ".mindstella") in caught.value.detail
    assert "mindstella.workspace.rollback_failed" in caplog.messages


def test_close_workspace(allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """配信元の行を outside_read: false にし、クローズ待ちにする。"""
    _status, created = workspaces.create_workspace(_request(allowed / "家計簿"), ctx)
    _write_session(ctx, created["id"])
    assert workspaces.close_workspace(created["id"], ctx) == {"id": created["id"], "closed": True}
    assert fake_pi.patched == [(created["id"], {"outside_read": False})]
    session = state.read_session(ctx.state_root, created["id"])
    assert session is not None
    assert session.close_pending is True
    assert state.read_launch(ctx.state_root, created["id"]) is not None


def test_close_workspace_session_running(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MindStella のセッションが生きていれば 409 で、行を変えない。"""
    _status, created = workspaces.create_workspace(_request(allowed / "家計簿"), ctx)
    _write_session(ctx, created["id"], status="running", pane=f"{created['id']}:0.0")
    monkeypatch.setattr(sessions, "is_alive", lambda *_args, **_kwargs: True)
    with pytest.raises(ApiError) as caught:
        workspaces.close_workspace(created["id"], ctx)
    assert (caught.value.status, caught.value.stage) == (409, "session")
    assert fake_pi.patched == []


def test_close_workspace_unknown(ctx: SimpleNamespace) -> None:
    """ID の一覧に無いワークスペースは 404。"""
    with pytest.raises(ApiError) as caught:
        workspaces.close_workspace("mindstella-x-000000", ctx)
    assert caught.value.status == 404


def _closed(allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> str:
    """クローズしたワークスペースを作り、ID を返す。"""
    _status, created = workspaces.create_workspace(_request(allowed / "家計簿"), ctx)
    fake_pi.rows[created["id"]]["outsideRead"] = False
    _write_session(ctx, created["id"], close_pending=True)
    return created["id"]


def test_reopen_workspace(allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """クローズ済みなら行を戻してクローズ待ちを解く（正常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    # 実行
    result = workspaces.reopen_workspace(workspace_id, ctx)
    # 検証
    assert result == {"id": workspace_id, "reopened": True, "closed": False}
    assert fake_pi.patched == [(workspace_id, {"outside_read": True})]
    session = state.read_session(ctx.state_root, workspace_id)
    assert session is not None
    assert session.close_pending is False


def test_reopen_workspace_not_closed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """クローズしていなければクローズ待ちだけ解く（正常系）。"""
    # 準備
    _status, created = workspaces.create_workspace(_request(allowed / "家計簿"), ctx)
    _write_session(ctx, created["id"], close_pending=True)
    # 実行
    result = workspaces.reopen_workspace(created["id"], ctx)
    # 検証
    assert result == {"id": created["id"], "reopened": False, "closed": False}
    assert fake_pi.patched == []
    session = state.read_session(ctx.state_root, created["id"])
    assert session is not None
    assert session.close_pending is False


def test_reopen_workspace_error_when_unknown(fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """ID の一覧に無いワークスペースは 404（異常系）。"""
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.reopen_workspace("mindstella-x-000000", ctx)
    assert (caught.value.status, caught.value.stage) == (404, "workspace")


def test_reopen_workspace_error_when_row_missing(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """配信元の行が無いワークスペースは 404（異常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    del fake_pi.rows[workspace_id]
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.reopen_workspace(workspace_id, ctx)
    assert (caught.value.status, caught.value.stage) == (404, "workspace")


def test_reopen_workspace_error_when_patch_failed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """project-index の失敗は 502 で、クローズ待ちを解かない（異常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    fake_pi.patch_error = ProjectIndexError(500, "壊れた")
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.reopen_workspace(workspace_id, ctx)
    assert (caught.value.status, caught.value.stage) == (502, "source")
    session = state.read_session(ctx.state_root, workspace_id)
    assert session is not None
    assert session.close_pending is True


def test_delete_workspace(allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """クローズ済みなら行・状態・ID の一覧の行を削除する（正常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    # 実行
    result = workspaces.delete_workspace(workspace_id, ctx)
    # 検証
    assert result == {"id": workspace_id, "deleted": True}
    assert fake_pi.deleted == [workspace_id]
    assert ctx.previews.stopped == [workspace_id]
    assert not state.workspace_dir(ctx.state_root, workspace_id).exists()
    assert workspace_id not in state.read_ids(ctx.state_root)
    assert (allowed / "家計簿" / ".mindstella" / "config.yaml").is_file()


def test_delete_workspace_source_row_missing(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """行が無ければ残りだけ削除する（正常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    del fake_pi.rows[workspace_id]
    # 実行
    result = workspaces.delete_workspace(workspace_id, ctx)
    # 検証
    assert result == {"id": workspace_id, "deleted": True}
    assert fake_pi.deleted == []
    assert not state.workspace_dir(ctx.state_root, workspace_id).exists()
    assert workspace_id not in state.read_ids(ctx.state_root)


def test_delete_workspace_error_when_unknown(fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """ID の一覧に無いワークスペースは 404（異常系）。"""
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.delete_workspace("mindstella-x-000000", ctx)
    assert (caught.value.status, caught.value.stage) == (404, "workspace")


def test_delete_workspace_error_when_not_closed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """クローズしていなければ 409 で、何も変えない（異常系）。"""
    # 準備
    _status, created = workspaces.create_workspace(_request(allowed / "家計簿"), ctx)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.delete_workspace(created["id"], ctx)
    assert (caught.value.status, caught.value.stage) == (409, "not_closed")
    assert fake_pi.deleted == []
    assert created["id"] in state.read_ids(ctx.state_root)


def test_delete_workspace_error_when_source_failed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """project-index の失敗は 502 で、状態のフォルダを変えない（異常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    fake_pi.delete_error = ProjectIndexError(500, "壊れた")
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.delete_workspace(workspace_id, ctx)
    assert (caught.value.status, caught.value.stage) == (502, "source")
    assert state.workspace_dir(ctx.state_root, workspace_id).exists()
    assert workspace_id in state.read_ids(ctx.state_root)


def test_delete_workspace_error_when_state_failed(
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """状態のフォルダを削除できなければ 500 で、ID の一覧の行を残す（異常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)

    def fail(*_args: object) -> None:
        raise OSError("消せない")

    monkeypatch.setattr(state, "delete_workspace_state", fail, raising=False)
    caplog.set_level(logging.ERROR)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.delete_workspace(workspace_id, ctx)
    assert (caught.value.status, caught.value.stage) == (500, "state")
    assert workspace_id in state.read_ids(ctx.state_root)
    assert "mindstella.workspace.delete_failed" in caplog.messages


def test_delete_workspace_concurrent(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """鍵を取った時点で ID の一覧に無ければ 404（異常系）。"""
    # 準備
    workspace_id = _closed(allowed, fake_pi, ctx)
    results: list[object] = []

    def delete() -> None:
        try:
            results.append(workspaces.delete_workspace(workspace_id, ctx))
        except ApiError as error:
            results.append((error.status, error.stage))

    threads = [threading.Thread(target=delete) for _ in range(2)]
    # 実行
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # 検証
    assert sorted(results, key=str) == sorted(
        [{"id": workspace_id, "deleted": True}, (404, "workspace")], key=str
    )
    assert fake_pi.deleted == [workspace_id]


def _plugin_dir(base: Path, name: str) -> str:
    """プラグインの定義を持つフォルダを作り、絶対パスを返す。"""
    folder = base / name
    manifest = folder / workspaces.PLUGIN_MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": name}), encoding="utf-8")
    return str(folder)


def _updatable(
    allowed: Path, ctx: SimpleNamespace, *, plugin_dirs: list[str] | None = None
) -> tuple[str, Path]:
    """書き換えられるワークスペースを作り、ID と記録のフォルダを返す。"""
    ctx.write_lock = threading.Lock()
    body = _request(allowed / "家計簿", plugin_dirs=plugin_dirs or [])
    _status, created = workspaces.create_workspace(body, ctx)
    return created["id"], allowed / "家計簿"


def _config(folder: Path) -> dict[str, Any]:
    """記録のフォルダの config.yaml を読む。"""
    return yaml.safe_load((folder / ".mindstella" / "config.yaml").read_text(encoding="utf-8"))


def _launch_text(ctx: SimpleNamespace, workspace_id: str) -> str | None:
    """launch.json の中身を読む。無ければ None。"""
    path = state.workspace_dir(ctx.state_root, workspace_id) / state.LAUNCH_FILE
    return path.read_text(encoding="utf-8") if path.exists() else None


def test_update_workspace(
    tmp_path: Path, allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """4 つの指定を書き換え、変わったキーを返す（正常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    plugin = _plugin_dir(tmp_path, "aituber")
    new_flow = {"source": "aituber", "doc": "flow-2"}
    new_mcp = {"mcpServers": {"voice": {"command": "voice-mcp"}}}
    # 実行
    result = workspaces.update_workspace(
        workspace_id,
        {
            "settings": {"summary": "台本の作成"},
            "flow": new_flow,
            "mcp_config": new_mcp,
            "plugin_dirs": [plugin],
        },
        ctx,
    )
    # 検証
    assert result == {
        "id": workspace_id,
        "changed": ["summary", "flow", "mcp_config", "plugin_dirs"],
    }
    config = _config(folder)
    assert config["summary"] == "台本の作成"
    assert config["flow"] == new_flow
    assert state.read_launch(ctx.state_root, workspace_id) == LaunchOptions(
        mcp_config=new_mcp, plugin_dirs=[plugin]
    )


def test_update_workspace_keeps_other_launch_key(
    tmp_path: Path, allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """プラグインだけを渡すと、追加の MCP の記録を残す（正常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    before = (folder / ".mindstella" / "config.yaml").read_text(encoding="utf-8")
    plugin = _plugin_dir(tmp_path, "aituber")
    # 実行
    result = workspaces.update_workspace(workspace_id, {"plugin_dirs": [plugin]}, ctx)
    # 検証
    assert result["changed"] == ["plugin_dirs"]
    assert state.read_launch(ctx.state_root, workspace_id) == LaunchOptions(
        mcp_config=MCP_CONFIG, plugin_dirs=[plugin]
    )
    assert (folder / ".mindstella" / "config.yaml").read_text(encoding="utf-8") == before


def test_update_workspace_launch_record_missing(
    tmp_path: Path, allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """launch.json が無ければ、指定しなかった方を空にして作る（正常系）。"""
    # 準備
    workspace_id, _folder = _updatable(allowed, ctx)
    state.delete_launch(ctx.state_root, workspace_id)
    plugin = _plugin_dir(tmp_path, "aituber")
    # 実行
    result = workspaces.update_workspace(workspace_id, {"plugin_dirs": [plugin]}, ctx)
    # 検証
    assert result["changed"] == ["plugin_dirs"]
    assert state.read_launch(ctx.state_root, workspace_id) == LaunchOptions(
        mcp_config={"mcpServers": {}}, plugin_dirs=[plugin]
    )


def test_update_workspace_flow_removed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """flow: null は確かめずに flow を外す（正常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    called: list[object] = []
    monkeypatch.setattr(workspaces, "check_flow", lambda *args: called.append(args))
    # 実行
    result = workspaces.update_workspace(workspace_id, {"flow": None}, ctx)
    # 検証
    assert result["changed"] == ["flow"]
    assert called == []
    assert "flow" not in _config(folder)


def test_update_workspace_unchanged(
    tmp_path: Path, allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """同じ値は書かず、changed が空（正常系）。"""
    # 準備
    plugin = _plugin_dir(tmp_path, "aituber")
    workspace_id, folder = _updatable(allowed, ctx, plugin_dirs=[plugin])
    config_path = folder / ".mindstella" / "config.yaml"
    launch_path = state.workspace_dir(ctx.state_root, workspace_id) / state.LAUNCH_FILE
    summary = _config(folder)["summary"]
    times = (config_path.stat().st_mtime_ns, launch_path.stat().st_mtime_ns)
    # 実行
    result = workspaces.update_workspace(
        workspace_id, {"settings": {"summary": summary}, "plugin_dirs": [plugin]}, ctx
    )
    # 検証
    assert result == {"id": workspace_id, "changed": []}
    assert (config_path.stat().st_mtime_ns, launch_path.stat().st_mtime_ns) == times


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="empty"),
        pytest.param({"title": "x"}, id="unknown_key"),
        pytest.param({"settings": {}}, id="empty_settings"),
        pytest.param({"flow": "x"}, id="flow_not_object"),
        pytest.param({"mcp_config": []}, id="mcp_config_not_object"),
        pytest.param({"plugin_dirs": "x"}, id="plugin_dirs_not_list"),
    ],
)
def test_update_workspace_error_when_body_invalid(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace, body: dict[str, Any]
) -> None:
    """指定が無い・知らないキー・空の settings・形の違う値は 400（異常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    before = _config(folder)
    launch = _launch_text(ctx, workspace_id)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.update_workspace(workspace_id, body, ctx)
    assert (caught.value.status, caught.value.stage) == (400, "body")
    assert _config(folder) == before
    assert _launch_text(ctx, workspace_id) == launch


def test_update_workspace_error_when_unknown(fake_pi: FakeProjectIndex, ctx: SimpleNamespace) -> None:
    """ID の一覧に無いワークスペースは 404（異常系）。"""
    # 準備
    ctx.write_lock = threading.Lock()
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.update_workspace("mindstella-x-000000", {"flow": None}, ctx)
    assert (caught.value.status, caught.value.stage) == (404, "workspace")


def test_update_workspace_error_when_records_missing(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """配信元の行のフォルダに記録が無ければ 409（異常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    (folder / ".mindstella" / "config.yaml").unlink()
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.update_workspace(workspace_id, {"flow": None}, ctx)
    assert (caught.value.status, caught.value.stage) == (409, "records")


def test_update_workspace_error_when_plugin_dir_unreadable(
    tmp_path: Path, allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """読めないプラグインのフォルダは 422 で、ほかの指定も書かない（異常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    before = _config(folder)
    launch = _launch_text(ctx, workspace_id)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.update_workspace(
            workspace_id,
            {"settings": {"summary": "台本の作成"}, "plugin_dirs": [str(tmp_path / "無い")]},
            ctx,
        )
    assert (caught.value.status, caught.value.stage) == (422, "plugin_dirs")
    assert _config(folder) == before
    assert _launch_text(ctx, workspace_id) == launch


def test_update_workspace_error_when_settings_invalid(
    tmp_path: Path, allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """スキーマに合わない設定は 422 で、何も書かない（異常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    before = _config(folder)
    launch = _launch_text(ctx, workspace_id)
    plugin = _plugin_dir(tmp_path, "aituber")
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.update_workspace(
            workspace_id, {"settings": {"summary": ""}, "plugin_dirs": [plugin]}, ctx
        )
    assert (caught.value.status, caught.value.stage) == (422, "settings")
    assert re.search(r"^config\.yaml: summary", caught.value.detail, re.MULTILINE)
    assert _config(folder) == before
    assert _launch_text(ctx, workspace_id) == launch


def test_update_workspace_error_when_flow_unreadable(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """参照できない進め方の文書は 422 で、何も書かない（異常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    before = _config(folder)

    def _unreadable(*_args: object) -> None:
        raise ApiError(422, "flow", "進め方の文書を参照できません")

    monkeypatch.setattr(workspaces, "check_flow", _unreadable)
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.update_workspace(
            workspace_id, {"flow": {"source": "aituber", "doc": "無い"}}, ctx
        )
    assert (caught.value.status, caught.value.stage) == (422, "flow")
    assert _config(folder) == before


def test_update_workspace_error_when_launch_write_failed(
    tmp_path: Path,
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """launch.json を書けなければ config.yaml を戻して 500（異常系）。"""
    # 準備
    workspace_id, folder = _updatable(allowed, ctx)
    before = _config(folder)
    plugin = _plugin_dir(tmp_path, "aituber")

    def _broken(*_args: object) -> None:
        raise OSError("書けません")

    monkeypatch.setattr(state, "write_launch", _broken)
    # 実行・検証
    with caplog.at_level(logging.ERROR), pytest.raises(ApiError) as caught:
        workspaces.update_workspace(
            workspace_id, {"settings": {"summary": "台本の作成"}, "plugin_dirs": [plugin]}, ctx
        )
    assert (caught.value.status, caught.value.stage) == (500, "write")
    assert _config(folder) == before
    assert any(record.message == "mindstella.workspace.update_failed" for record in caplog.records)


def test_update_workspace_error_when_config_write_failed(
    tmp_path: Path,
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """config.yaml を書けなければ 500 で、launch.json を書かない（異常系）。"""
    # 準備
    workspace_id, _folder = _updatable(allowed, ctx)
    launch = _launch_text(ctx, workspace_id)
    plugin = _plugin_dir(tmp_path, "aituber")

    def _broken(*_args: object) -> list[str]:
        raise OSError("書けません")

    monkeypatch.setattr(settings_update, "save_settings", _broken)
    # 実行・検証
    with caplog.at_level(logging.ERROR), pytest.raises(ApiError) as caught:
        workspaces.update_workspace(
            workspace_id, {"settings": {"summary": "台本の作成"}, "plugin_dirs": [plugin]}, ctx
        )
    assert (caught.value.status, caught.value.stage) == (500, "write")
    assert _launch_text(ctx, workspace_id) == launch
    assert any(record.message == "mindstella.workspace.update_failed" for record in caplog.records)


def test_update_workspace_error_when_rollback_failed(
    tmp_path: Path,
    allowed: Path,
    fake_pi: FakeProjectIndex,
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """戻しも失敗したら、戻したかを偽にして 500（異常系）。"""
    # 準備
    workspace_id, _folder = _updatable(allowed, ctx)
    plugin = _plugin_dir(tmp_path, "aituber")
    real_save = settings_update.save_settings
    calls: list[int] = []

    def _first_only(*args: Any) -> list[str]:
        calls.append(1)
        # 1 回目（書き換え）は通し、2 回目（戻し）で失敗する
        if len(calls) == 1:
            return real_save(*args)
        raise OSError("戻せません")

    def _broken(*_args: object) -> None:
        raise OSError("書けません")

    monkeypatch.setattr(settings_update, "save_settings", _first_only)
    monkeypatch.setattr(state, "write_launch", _broken)
    # 実行・検証
    with caplog.at_level(logging.ERROR), pytest.raises(ApiError) as caught:
        workspaces.update_workspace(
            workspace_id, {"settings": {"summary": "台本の作成"}, "plugin_dirs": [plugin]}, ctx
        )
    assert (caught.value.status, caught.value.stage) == (500, "write")
    failed = [r for r in caplog.records if r.message == "mindstella.workspace.update_failed"]
    assert failed
    assert getattr(failed[-1], "config_restored", None) is False


def _stale_schema(folder: Path) -> None:
    """スキーマの複製の docs.schema.json を別の中身にする。"""
    (folder / ".mindstella" / "schemas" / "docs.schema.json").write_text("{}\n", encoding="utf-8")


def test_create_workspace_schema_reloaded(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """スキーマの複製を書き直し、行を送らないときは全ての配信元を読み直させる（正常系）。"""
    # 準備
    folder = allowed / "家計簿"
    workspaces.create_workspace(_request(folder), ctx)
    _stale_schema(folder)
    fake_pi.added.clear()
    # 実行
    status, body = workspaces.create_workspace(_request(folder), ctx)
    # 検証
    assert (status, body["result"], body["migration"]) == (200, "already_open", None)
    assert fake_pi.reloads == 1
    assert (fake_pi.added, fake_pi.patched) == ([], [])


def test_create_workspace_schema_rewritten_row_added(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """行を追加するときは読み直しを重ねて送らない（正常系）。"""
    # 準備
    folder = allowed / "家計簿"
    _status, created = workspaces.create_workspace(_request(folder), ctx)
    _stale_schema(folder)
    del fake_pi.rows[created["id"]]
    fake_pi.added.clear()
    # 実行
    status, body = workspaces.create_workspace(_request(folder), ctx)
    # 検証
    assert (status, body["result"]) == (200, "opened")
    assert len(fake_pi.added) == 1
    assert fake_pi.reloads == 0


def test_create_workspace_schema_reload_failed(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """読み直しに失敗したら 502（異常系）。"""
    # 準備
    folder = allowed / "家計簿"
    workspaces.create_workspace(_request(folder), ctx)
    _stale_schema(folder)
    fake_pi.reload_error = ProjectIndexError(500, "読み直せません")
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (502, "source")
    assert (folder / ".mindstella" / "config.yaml").is_file()


# 状態の取得のテストのワークスペースの ID
STATUS_ID = "mindstella-家計簿-3f2a9c"

# セッションの管理が返す MindStella のセッション
RUNNING_SESSION = {
    "id": "S-0123456789ab",
    "status": "running",
    "responding": False,
    "pending_write": False,
    "pane": f"{STATUS_ID}:0.0",
    "last_error": None,
}


def _status_folder(tmp_path: Path, name: str, workspace_id: str) -> Path:
    """題名を持つ記録のフォルダを作る。"""
    folder = tmp_path / name
    (folder / ".mindstella").mkdir(parents=True)
    (folder / ".mindstella" / "config.yaml").write_text(
        yaml.safe_dump(
            {"id": workspace_id, "title": f"{name}の題名", "summary": name}, allow_unicode=True
        ),
        encoding="utf-8",
    )
    return folder


def _write_rows(settings_path: Path, rows: list[tuple[str, Path, bool]]) -> None:
    """グローバルの設定のファイルに配信元の行（ID・フォルダ・outside_read）を書く。"""
    settings_path.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "id": workspace_id,
                        "config": [f"{folder}/.mindstella/dev-docs.yaml"],
                        "outside_read": outside_read,
                    }
                    for workspace_id, folder, outside_read in rows
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _snapshot(*roots: Path) -> dict[str, bytes]:
    """フォルダの下の全てのファイルの中身。"""
    return {
        str(path): path.read_bytes()
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def status_ctx(tmp_path: Path) -> SimpleNamespace:
    """グローバルの設定のファイルの場所を持つ、入口が渡す値。"""
    return SimpleNamespace(
        port=8784,
        pi_port=8786,
        state_root=tmp_path / "state",
        settings_file=tmp_path / "settings.yaml",
        locks=WorkspaceLocks(),
        previews=FakePreviews(),
        plugin_root=tmp_path / "plugin",
        tmux=None,
        proc=None,
    )


@pytest.fixture
def listed_sessions(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """セッションの管理の一覧の代わりに返す値（テストが close_pending を書き換える）。"""
    body: dict[str, Any] = {"sessions": [RUNNING_SESSION], "close_pending": False}
    monkeypatch.setattr(sessions, "list_sessions", lambda _workspace_id, _ctx: dict(body))
    return body


@pytest.fixture
def status_workspace(tmp_path: Path, status_ctx: SimpleNamespace) -> Path:
    """ID の一覧・開いている配信元の行・記録・launch.json がそろったワークスペースのフォルダ。"""
    folder = _status_folder(tmp_path, "家計簿", STATUS_ID)
    state.add_id(status_ctx.state_root, STATUS_ID)
    state.write_launch(
        status_ctx.state_root, STATUS_ID, LaunchOptions(mcp_config=None, plugin_dirs=[])
    )
    _write_rows(status_ctx.settings_file, [(STATUS_ID, folder, True)])
    return folder


def test_workspace_status(
    status_workspace: Path,
    status_ctx: SimpleNamespace,
    listed_sessions: dict[str, Any],
    tmp_path: Path,
) -> None:
    """ワークスペースとセッションの状態をまとめて書き換えない（正常系）。"""
    # 準備
    before = _snapshot(tmp_path)
    # 実行
    body = workspaces.workspace_status(STATUS_ID, status_ctx)
    # 検証
    assert body["id"] == STATUS_ID
    assert body["status"] == "active"
    assert body["closed"] is False
    assert body["title"] == "家計簿の題名"
    assert body["url"] == PREVIEW_URL
    assert body["sessions"] == [RUNNING_SESSION]
    assert body["close_pending"] is False
    assert body["launch_options_recorded"] is True
    assert body["warnings"] == []
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("outside_read", "close_pending", "expected"),
    [
        pytest.param(False, False, "closed", id="closed"),
        pytest.param(True, True, "stopped", id="stopped"),
        pytest.param(True, False, "active", id="active"),
    ],
)
def test_workspace_status_by_state(
    outside_read: bool,
    close_pending: bool,
    expected: str,
    status_workspace: Path,
    status_ctx: SimpleNamespace,
    listed_sessions: dict[str, Any],
) -> None:
    """closed と close_pending からワークスペースの状態を決める（正常系）。"""
    # 準備
    _write_rows(status_ctx.settings_file, [(STATUS_ID, status_workspace, outside_read)])
    listed_sessions["close_pending"] = close_pending
    # 実行
    body = workspaces.workspace_status(STATUS_ID, status_ctx)
    # 検証
    assert body["status"] == expected


def test_workspace_status_without_launch(
    status_workspace: Path, status_ctx: SimpleNamespace, listed_sessions: dict[str, Any]
) -> None:
    """launch.json が無ければ偽で、中身を返さない（正常系）。"""
    # 準備
    state.delete_launch(status_ctx.state_root, STATUS_ID)
    # 実行
    body = workspaces.workspace_status(STATUS_ID, status_ctx)
    # 検証
    assert body["launch_options_recorded"] is False
    assert "mcp_config" not in body
    assert "plugin_dirs" not in body
    assert state.read_launch(status_ctx.state_root, STATUS_ID) is None


def _break_records(folder: Path, settings_file: Path, case: str) -> None:
    """記録・グローバルの設定のファイル・変更履歴のどれかを参照できなくする。"""
    if case == "records-missing":
        shutil.rmtree(folder / ".mindstella")
    elif case == "settings-broken":
        settings_file.write_text("sources: [", encoding="utf-8")
    elif case == "config-broken":
        (folder / ".mindstella" / "config.yaml").write_text("title: [", encoding="utf-8")
    else:
        (folder / ".mindstella" / "history.yaml").write_text("items: []\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("case", "stage", "detail_part", "expected"),
    [
        pytest.param(
            "records-missing",
            "records",
            "家計簿",
            {
                "status": "active",
                "closed": False,
                "unseen_ai_posts": None,
                "awaiting_user_posts": None,
                "updated": None,
            },
            id="records-missing",
        ),
        pytest.param(
            "settings-broken",
            "settings",
            "settings.yaml",
            {
                "status": None,
                "closed": None,
                "unseen_ai_posts": None,
                "awaiting_user_posts": None,
                "updated": None,
            },
            id="settings-broken",
        ),
        pytest.param(
            "history-mismatch",
            "records",
            "history.yaml",
            {
                "status": "active",
                "closed": False,
                "unseen_ai_posts": None,
                "awaiting_user_posts": None,
                "updated": None,
            },
            id="history-mismatch",
        ),
        pytest.param(
            "config-broken",
            "records",
            "config.yaml",
            {"status": "active", "title": None, "unseen_ai_posts": 0, "awaiting_user_posts": 0},
            id="config-broken",
        ),
    ],
)
def test_workspace_status_warnings(
    case: str,
    stage: str,
    detail_part: str,
    expected: dict[str, Any],
    status_workspace: Path,
    status_ctx: SimpleNamespace,
    listed_sessions: dict[str, Any],
) -> None:
    """記録か設定を参照できなければ警告を付ける（異常系）。"""
    # 準備
    _break_records(status_workspace, status_ctx.settings_file, case)
    # 実行
    body = workspaces.workspace_status(STATUS_ID, status_ctx)
    # 検証
    assert [warning["stage"] for warning in body["warnings"]] == [stage]
    assert detail_part in body["warnings"][0]["detail"]
    assert {key: body[key] for key in expected} == expected
    assert body["sessions"] == [RUNNING_SESSION]


def test_workspace_status_unknown(status_ctx: SimpleNamespace) -> None:
    """ID の一覧に無ければ 404（異常系）。"""
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        workspaces.workspace_status("mindstella-無い-000000", status_ctx)
    assert (caught.value.status, caught.value.stage) == (404, "workspace")


@pytest.fixture
def listed_workspaces(tmp_path: Path, status_ctx: SimpleNamespace) -> None:
    """ID の一覧に 4 つ（開いている 2 つ・クローズ済み 1 つ・配信元の行が無い 1 つ）を書く。"""
    folders = {
        name: _status_folder(tmp_path, name, f"mindstella-{name}-000000")
        for name in ("a", "b", "c", "d")
    }
    for name in ("a", "b", "c", "d"):
        state.add_id(status_ctx.state_root, f"mindstella-{name}-000000")
    _write_rows(
        status_ctx.settings_file,
        [
            ("mindstella-a-000000", folders["a"], True),
            ("mindstella-b-000000", folders["b"], False),
            ("mindstella-c-000000", folders["c"], True),
        ],
    )


@pytest.mark.parametrize(
    ("include_closed", "expected"),
    [
        pytest.param(
            False,
            [("mindstella-a-000000", False), ("mindstella-c-000000", False)],
            id="open-only",
        ),
        pytest.param(
            True,
            [
                ("mindstella-a-000000", False),
                ("mindstella-b-000000", True),
                ("mindstella-c-000000", False),
            ],
            id="include-closed",
        ),
    ],
)
def test_list_workspaces(
    include_closed: bool,
    expected: list[tuple[str, bool]],
    listed_workspaces: None,
    status_ctx: SimpleNamespace,
) -> None:
    """クローズ済みを除くか含める（正常系）。"""
    # 実行
    body = workspaces.list_workspaces(include_closed, status_ctx)
    # 検証
    assert [(entry["id"], entry["closed"]) for entry in body["workspaces"]] == expected
    assert body["workspaces"][0]["title"] == "aの題名"
    assert body["workspaces"][0]["url"] == PREVIEW_URL
    assert body["warnings"] == []


def test_list_workspaces_settings_unreadable(status_ctx: SimpleNamespace) -> None:
    """設定を参照できなければ空と警告（異常系）。"""
    # 準備
    state.add_id(status_ctx.state_root, STATUS_ID)
    # 実行
    body = workspaces.list_workspaces(False, status_ctx)
    # 検証
    assert body["workspaces"] == []
    assert [warning["stage"] for warning in body["warnings"]] == ["settings"]
