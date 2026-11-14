"""workspaces.py（ワークスペースの作成とクローズ）の単体テスト。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

import project_index
import sessions
import state
import workspaces
from errors import ApiError
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

    def url_of(self, root: Path) -> str:
        """配っている URL を返す。"""
        return PREVIEW_URL


class FakeProjectIndex:
    """配信元の行を持ち、project_index の関数の代わりに答える。"""

    def __init__(self, settings_path: Path) -> None:
        """空の行で始める。"""
        self.settings_path = settings_path
        self.rows: dict[str, dict[str, Any]] = {}
        self.added: list[dict[str, Any]] = []
        self.patched: list[tuple[str, dict[str, Any]]] = []
        self.add_error: ProjectIndexError | None = None

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
        self.patched.append((source_id, changes))
        if "outside_read" in changes:
            self.rows[source_id]["outsideRead"] = changes["outside_read"]


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
    monkeypatch.setattr(workspaces, "check_flow", lambda *_args: None)
    monkeypatch.setattr(sessions, "is_alive", lambda *_args: False)
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


def test_create_workspace_rollback(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """配信元の登録に失敗したら、作った記録を消す。"""
    folder = allowed / "家計簿"
    fake_pi.add_error = ProjectIndexError(None, "つながりません")
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert (caught.value.status, caught.value.stage) == (502, "source")
    workspace_id = workspaces.workspace_id_for(folder)
    assert not (folder / ".mindstella").exists()
    assert state.read_launch(ctx.state_root, workspace_id) is None
    assert workspace_id not in state.read_ids(ctx.state_root)


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


def test_create_workspace_unmigrated(
    allowed: Path, fake_pi: FakeProjectIndex, ctx: SimpleNamespace
) -> None:
    """直下に移す前の設定ファイルがあれば 409。"""
    folder = allowed / "家計簿"
    folder.mkdir()
    (folder / "mindmap.yaml").write_text("summary: x\n", encoding="utf-8")
    with pytest.raises(ApiError) as caught:
        workspaces.create_workspace(_request(folder), ctx)
    assert caught.value.status == 409
    assert fake_pi.added == []


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
    monkeypatch.setattr(sessions, "is_alive", lambda *_args: True)
    with pytest.raises(ApiError) as caught:
        workspaces.close_workspace(created["id"], ctx)
    assert (caught.value.status, caught.value.stage) == (409, "session")
    assert fake_pi.patched == []


def test_close_workspace_unknown(ctx: SimpleNamespace) -> None:
    """ID の一覧に無いワークスペースは 404。"""
    with pytest.raises(ApiError) as caught:
        workspaces.close_workspace("mindstella-x-000000", ctx)
    assert caught.value.status == 404
