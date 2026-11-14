"""ワークスペースを作る・開き、project-index の配信元に登録し、クローズにする。"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import threading
from pathlib import Path
from typing import Any

import yaml

import commands
import project_index
import sessions
import state
from errors import ApiError
from kinds import LEGACY_SETTINGS_FILE, SETTINGS_FILE, records_root
from project_index import ProjectIndexError
from state import LaunchOptions
from store import UPGRADE_HINT

logger = logging.getLogger("mindstella.workspaces")

# 記録の無いフォルダの config.yaml の playbooks
DEFAULT_PLAYBOOK = "壁打ち"

# プレイブック『壁打ち』のフェーズ
DEFAULT_PHASES = ["問い", "発散", "整理", "絞り込み", "結論"]

# target_label の既定
DEFAULT_TARGET_LABEL = "対象"

# ユーザー配下のプラグインの MCP と重なるため、追加の MCP に使えない名前
RESERVED_MCP_NAMES = {"mindstella", "project-index"}

# ワークスペースの ID の頭
ID_PREFIX = "mindstella"

# ワークスペースの ID に入れる、パスのハッシュの桁数
HASH_DIGITS = 6

# フォルダ名のうち、tmux のセッションの名前に使えないため `-` に置き換える文字
UNSAFE_NAME_CHARS = ".:"

# 配信元の行の config（記録を配信元として配る設定）のファイル名
SOURCE_CONFIG_FILE = "dev-docs.yaml"

# プラグインのフォルダが持つ定義のファイル
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"

# project-index の配信元の行の、外から参照できるかのキー（GET の応答）
OUTSIDE_READ_KEY = "outsideRead"


class WorkspaceLocks:
    """ワークスペースごと・フォルダごとの依頼の順番の鍵。ワークスペースの管理とセッションの管理が 1 つを共有する。"""

    def __init__(self) -> None:
        """空の鍵の表で始める。"""
        self._guard = threading.Lock()
        self._workspaces: dict[str, threading.Lock] = {}
        self._folders: dict[str, threading.Lock] = {}

    def for_workspace(self, workspace_id: str) -> threading.Lock:
        """ワークスペースの ID の鍵を返す（無ければ作る）。"""
        with self._guard:
            return self._workspaces.setdefault(workspace_id, threading.Lock())

    def for_folder(self, folder: Path) -> threading.Lock:
        """フォルダの鍵を返す（無ければ作る）。"""
        with self._guard:
            return self._folders.setdefault(str(folder), threading.Lock())


def workspace_id_for(folder: Path) -> str:
    """`mindstella-{フォルダ名}-{ハッシュ}` を返す。"""
    resolved = folder.resolve()
    name = resolved.name
    for char in UNSAFE_NAME_CHARS:
        name = name.replace(char, "-")
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:HASH_DIGITS]
    return f"{ID_PREFIX}-{name}-{digest}"


def validate_options(mcp_config: dict[str, Any] | None, plugin_dirs: list[str]) -> LaunchOptions:
    """追加の MCP の形と予約の名前、プラグインのフォルダの定義を確かめる。"""
    # 追加の MCP がある: mcpServers のオブジェクトで、予約の名前を持たない
    if mcp_config is not None:
        servers = mcp_config.get("mcpServers") if isinstance(mcp_config, dict) else None
        if not isinstance(servers, dict):
            raise ApiError(
                422,
                "mcp_config",
                "mcp_config は mcpServers のオブジェクトを持つ JSON にしてください",
            )
        reserved = sorted(RESERVED_MCP_NAMES & set(servers))
        if reserved:
            raise ApiError(
                422,
                "mcp_config",
                f"mcp_config に使えない MCP の名前があります: {', '.join(reserved)}",
            )
    if not isinstance(plugin_dirs, list) or not all(
        isinstance(value, str) for value in plugin_dirs
    ):
        raise ApiError(422, "plugin_dirs", "plugin_dirs は文字列の並びにしてください")
    # 各プラグインのフォルダ: 定義のファイルを JSON のオブジェクトとして読める
    for value in plugin_dirs:
        manifest = Path(value) / PLUGIN_MANIFEST
        try:
            loaded = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ApiError(422, "plugin_dirs", f"{manifest} を読めません: {error}") from error
        if not isinstance(loaded, dict):
            raise ApiError(422, "plugin_dirs", f"{manifest} が JSON のオブジェクトではありません")
    return LaunchOptions(mcp_config=mcp_config, plugin_dirs=list(plugin_dirs))


def check_flow(pi_port: int, flow: dict[str, str], folder: Path) -> None:
    """進め方の文書を、配信元の scope・文書の一覧・文書の取得の 3 段で確かめる。"""
    source_id = flow["source"]
    doc_id = flow["doc"]
    row = _find_row(_settings(pi_port), source_id)
    patterns = list(((row or {}).get("scope") or {}).get("read") or [])
    # 1. 配信元の scope.read にワークスペースのフォルダが含まれない: 参照できない
    if row is None or not project_index.scope_includes(patterns, folder.resolve()):
        raise ApiError(
            422,
            "flow",
            f"配信元 {source_id} の scope に {folder} が含まれないため、進め方の文書を参照できません",
        )
    try:
        path = project_index.find_doc_path(pi_port, source_id, doc_id)
        # 2. 文書の一覧に ID が無い
        if path is None:
            raise ApiError(
                422, "flow", f"配信元 {source_id} に文書 {doc_id} がありません（missing）"
            )
        # 3. 文書を取得できない
        if not project_index.doc_exists(pi_port, source_id, path, doc_id):
            raise ApiError(
                422,
                "flow",
                f"配信元 {source_id} の文書 {doc_id}（{path}）を取得できません（missing）",
            )
    except ProjectIndexError as error:
        raise ApiError(502, "source", error.detail) from error


def create_workspace(request: dict[str, Any], ctx: Any) -> tuple[int, dict[str, Any]]:
    """記録を作るか開き、配信元の行と ID の一覧を揃えて、ワークスペースの ID と画面の URL を返す。"""
    folder, flow, mcp_config, plugin_dirs = _parse_request(request)
    # 許可するフォルダの下か（何も書く前に確かめる）
    settings = _settings(ctx.pi_port)
    allowed = project_index.read_allowed_dirs(Path(str(settings.get("settingsPath"))))
    if not any(folder == base or folder.is_relative_to(base) for base in allowed):
        raise ApiError(
            403,
            "folder",
            f"許可するフォルダの外です: {folder}（端末の設定の mindstella.allowed_dirs に親のフォルダを書いてください）",
        )
    records = records_root(folder)
    # 移す前の形のワークスペース: 移し替えを案内する
    if not records.is_dir() and (
        (folder / SETTINGS_FILE).exists() or (folder / LEGACY_SETTINGS_FILE).exists()
    ):
        raise ApiError(409, "unmigrated", UPGRADE_HINT.replace("{root}", str(folder)))
    options = validate_options(mcp_config, plugin_dirs)

    with ctx.locks.for_folder(folder):
        exists = (records / SETTINGS_FILE).is_file()
        workspace_id = workspace_id_of(folder)
        with ctx.locks.for_workspace(workspace_id):
            # 記録が無いときだけ、進め方の文書を確かめてから記録を作る
            if not exists:
                if flow is not None:
                    check_flow(ctx.pi_port, flow, folder)
                commands.run_init(folder, _default_settings(workspace_id, folder, flow))
            recorded = state.read_launch(ctx.state_root, workspace_id) is None
            if recorded:
                state.write_launch(ctx.state_root, workspace_id, options)
            try:
                result = _register_source(
                    ctx, workspace_id, folder, created=not exists, recorded=recorded
                )
            except ProjectIndexError as error:
                remaining = _rollback(
                    ctx, workspace_id, folder, created=not exists, recorded=recorded
                )
                logger.error(  # noqa: TRY400
                    "mindstella.workspace.create_failed",
                    extra={
                        "workspace_id": workspace_id,
                        "stage": "source",
                        "status": error.status,
                        "reason": error.detail,
                    },
                )
                detail = (
                    error.detail
                    if not remaining
                    else f"{error.detail}（消せなかったもの: {', '.join(remaining)}）"
                )
                raise ApiError(502, "source", detail) from error
            state.add_id(ctx.state_root, workspace_id)
    url = commands.run_preview_url(folder, ctx.previews)["url"]
    if result != "already_open":
        logger.info(
            "mindstella.workspace.created",
            extra={
                "workspace_id": workspace_id,
                "result": result,
                "launch_options_recorded": recorded,
            },
        )
    body = {"id": workspace_id, "url": url, "result": result, "launch_options_recorded": recorded}
    return (201 if result == "created" else 200), body


def close_workspace(workspace_id: str, ctx: Any) -> dict[str, Any]:
    """MindStella のセッションが無いワークスペースの配信元の行を outside_read: false にし、クローズ待ちにする。"""
    if workspace_id not in state.read_ids(ctx.state_root):
        raise ApiError(404, "workspace", f"ワークスペースがありません: {workspace_id}")
    with ctx.locks.for_workspace(workspace_id):
        # MindStella のセッションが起動中・停止の途中: 行を変えない
        if sessions.is_alive(ctx.state_root, workspace_id, ctx.tmux, ctx.proc):
            raise ApiError(
                409, "session", "MindStella のセッションが動いているため、クローズにできません"
            )
        try:
            project_index.patch_source(ctx.pi_port, workspace_id, {"outside_read": False})
        except ProjectIndexError as error:
            logger.error(  # noqa: TRY400
                "mindstella.workspace.close_failed",
                extra={
                    "workspace_id": workspace_id,
                    "status": error.status,
                    "reason": error.detail,
                },
            )
            raise ApiError(502, "source", error.detail) from error
        state.update_session(
            ctx.state_root,
            workspace_id,
            lambda current: None if current is None else current.replace(close_pending=True),
        )
    logger.info("mindstella.workspace.closed", extra={"workspace_id": workspace_id})
    return {"id": workspace_id, "closed": True}


def find_workspace_row(pi_port: int, workspace_id: str) -> dict[str, Any] | None:
    """project-index の配信元の行のうち、ワークスペースの ID の行を返す。"""
    return _find_row(_settings(pi_port), workspace_id)


def workspace_folder(row: dict[str, Any]) -> Path:
    """配信元の行の config（`{フォルダ}/.mindstella/dev-docs.yaml`）からワークスペースのフォルダを返す。"""
    config = row.get("config")
    first = config[0] if isinstance(config, list) else config
    return Path(str(first)).parent.parent


def is_closed(row: dict[str, Any]) -> bool:
    """配信元の行がクローズ済み（outside_read が偽）かを返す。"""
    return row.get(OUTSIDE_READ_KEY) is False


def _parse_request(
    request: Any,
) -> tuple[Path, dict[str, str] | None, dict[str, Any] | None, list[str]]:
    """本文から folder・flow・mcp_config・plugin_dirs を取り出す。形が違えば 400。"""
    if not isinstance(request, dict):
        raise ApiError(400, "body", "本文は JSON のオブジェクトにしてください")
    raw_folder = request.get("folder")
    if not isinstance(raw_folder, str) or not Path(raw_folder).is_absolute():
        raise ApiError(400, "body", "folder は絶対パスにしてください")
    flow = request.get("flow")
    if flow is not None and not (
        isinstance(flow, dict)
        and isinstance(flow.get("source"), str)
        and isinstance(flow.get("doc"), str)
    ):
        raise ApiError(400, "body", "flow は {source, doc} の文字列のオブジェクトにしてください")
    plugin_dirs = request.get("plugin_dirs")
    return (
        Path(raw_folder).resolve(),
        flow,
        request.get("mcp_config"),
        [] if plugin_dirs is None else plugin_dirs,
    )


def _default_settings(
    workspace_id: str, folder: Path, flow: dict[str, str] | None
) -> dict[str, Any]:
    """記録の無いフォルダに書く既定の設定を返す。"""
    settings: dict[str, Any] = {"id": workspace_id}
    if flow is not None:
        settings["flow"] = {"source": flow["source"], "doc": flow["doc"]}
    settings.update(
        {
            "summary": folder.name,
            "playbooks": [DEFAULT_PLAYBOOK],
            "target_label": DEFAULT_TARGET_LABEL,
            "phases": list(DEFAULT_PHASES),
            "targets": [],
            "categories": [],
        }
    )
    return settings


def workspace_id_of(folder: Path) -> str:
    """記録の設定の id を返す。記録か id が無ければフォルダから振る。"""
    path = records_root(folder) / SETTINGS_FILE
    if not path.is_file():
        return workspace_id_for(folder)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    value = loaded.get("id") if isinstance(loaded, dict) else None
    return str(value) if value else workspace_id_for(folder)


def _register_source(
    ctx: Any, workspace_id: str, folder: Path, *, created: bool, recorded: bool
) -> str:
    """配信元の行を追加するか戻し、作成の結果（created・opened・reopened・already_open）を返す。"""
    existing = find_workspace_row(ctx.pi_port, workspace_id)
    added = project_index.add_source(ctx.pi_port, _source_row(workspace_id, folder))
    # 行を追加した: 作ったか、残っている記録を開いた
    if added == "added":
        return "created" if created else "opened"
    # 同じ ID で中身の違う行がある: 別のフォルダの行とみなして止める
    if added == "exists_different":
        raise ProjectIndexError(409, f"配信元 {workspace_id} の行が別の内容で登録されています")
    # クローズ済みの行: outside_read を戻してクローズ待ちを解く
    if existing is not None and is_closed(existing):
        project_index.patch_source(ctx.pi_port, workspace_id, {"outside_read": True})
        state.update_session(
            ctx.state_root,
            workspace_id,
            lambda current: None if current is None else current.replace(close_pending=False),
        )
        return "reopened"
    # 行はあるが、今回の指定を記録したか ID の一覧に無い: 開き直した
    if recorded or workspace_id not in state.read_ids(ctx.state_root):
        return "opened"
    return "already_open"


def _source_row(workspace_id: str, folder: Path) -> dict[str, Any]:
    """配信元の行を作る。"""
    paths = [str(folder), f"{folder}/**"]
    return {
        "id": workspace_id,
        "config": f"{folder}/{records_root(folder).name}/{SOURCE_CONFIG_FILE}",
        "scope": {"read": paths, "write": list(paths)},
        "outside_read": True,
    }


def _rollback(
    ctx: Any, workspace_id: str, folder: Path, *, created: bool, recorded: bool
) -> list[str]:
    """この依頼で作った記録と状態の記録を消し、消せなかったパスを返す。"""
    targets: list[Path] = []
    if created:
        targets.append(records_root(folder))
    if recorded:
        targets.append(state.workspace_dir(ctx.state_root, workspace_id) / state.LAUNCH_FILE)
    remaining: list[str] = []
    for target in targets:
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
        except OSError:
            logger.exception(
                "mindstella.workspace.rollback_failed",
                extra={"workspace_id": workspace_id, "path": str(target)},
            )
            remaining.append(str(target))
    return remaining


def _settings(pi_port: int) -> dict[str, Any]:
    """project-index の端末の設定を読む。つながらなければ 502。"""
    try:
        return project_index.get_settings(pi_port)
    except ProjectIndexError as error:
        raise ApiError(502, "source", error.detail) from error


def _find_row(settings: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    """端末の設定の行のうち、ID の行を返す。"""
    for row in settings.get("sources") or []:
        if isinstance(row, dict) and row.get("id") == source_id:
            return row
    return None
