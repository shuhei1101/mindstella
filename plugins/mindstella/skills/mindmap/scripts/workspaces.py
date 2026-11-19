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
import history
import migrator
import project_index
import read_point
import sessions
import state
import threads
from errors import ApiError, SchemaMismatchError, StepFailedError, WorkspaceNewerError
from kinds import LEGACY_SETTINGS_FILE, SETTINGS_FILE, records_root
from migration_ops import describe_step
from project_index import ProjectIndexError
from readme import PLUGIN_DIR, README_FILE
from state import LaunchOptions
from store import workspace_lock

logger = logging.getLogger("mindstella.workspaces")

# project-index に登録するエージェントフローの配信元の ID
AGENT_FLOWS_SOURCE = "mindstella-agent-flows"

# エージェントフローの配信元の設定（プラグインのフォルダから）
AGENT_FLOWS_CONFIG = Path("agent-flows") / "dev-docs.yaml"

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

# グローバルの設定のファイルの行の作業範囲の外のキー（API の応答の OUTSIDE_READ_KEY は camelCase）
FILE_OUTSIDE_READ_KEY = "outside_read"


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
    options = validate_options(mcp_config, plugin_dirs)
    migration: dict[str, Any] | None = None
    source_files: list[str] = []

    with ctx.locks.for_folder(folder):
        legacy = (folder / SETTINGS_FILE).exists() or (folder / LEGACY_SETTINGS_FILE).exists()
        exists = (records / SETTINGS_FILE).is_file() or legacy
        workspace_id = workspace_id_of(folder)
        with ctx.locks.for_workspace(workspace_id):
            # 記録がある: 開く前に今の形式へ移し替える
            if exists:
                migration, source_files = _migrate(ctx, folder)
            # 記録が無いときだけ、進め方の文書を確かめてから記録を作る
            if not exists:
                if flow is not None:
                    check_flow(ctx.pi_port, flow, folder)
                readme_existed = (folder / README_FILE).exists()
                commands.run_init(folder, _default_settings(workspace_id, folder, flow))
            recorded = state.read_launch(ctx.state_root, workspace_id) is None
            if recorded:
                state.write_launch(ctx.state_root, workspace_id, options)
            try:
                result, row_sent = _register_source(
                    ctx, workspace_id, folder, created=not exists, recorded=recorded
                )
                # スキーマの複製か配信の設定を書き直したが行を送っていない: project-index に読み直させる
                if source_files and not row_sent:
                    project_index.reload_sources(ctx.pi_port)
            except ProjectIndexError as error:
                remaining = _rollback(
                    ctx,
                    workspace_id,
                    folder,
                    created=not exists,
                    recorded=recorded,
                    readme_written=not exists and not readme_existed,
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
            ensure_agent_flows_source(ctx, allowed)
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
    body = {
        "id": workspace_id,
        "url": url,
        "result": result,
        "launch_options_recorded": recorded,
        "migration": migration,
    }
    return (201 if result == "created" else 200), body


def ensure_agent_flows_source(ctx: Any, allowed_dirs: list[Path]) -> None:
    """project-index に配信元 `mindstella-agent-flows` の行が無ければ足す（失敗してもワークスペースの作成は止めない）。"""
    try:
        # 行がある: 何もしない
        if _find_row(project_index.get_settings(ctx.pi_port), AGENT_FLOWS_SOURCE) is not None:
            return
        read = [path for base in allowed_dirs for path in (str(base), f"{base}/**")]
        project_index.add_source(
            ctx.pi_port,
            {
                "id": AGENT_FLOWS_SOURCE,
                "config": str(PLUGIN_DIR / AGENT_FLOWS_CONFIG),
                "scope": {"read": read},
                "outside_read": True,
            },
        )
    except ProjectIndexError as error:
        logger.warning(
            "mindstella.agent_flows.register_failed",
            extra={"status": error.status, "reason": error.detail},
        )


def _migrate(ctx: Any, folder: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """記録を今の形式へ移し替え、移し替えたら報告を状態のフォルダに残し、応答の形と書き直したスキーマの複製・配信の設定を返す。"""
    try:
        with workspace_lock(folder, threading.Lock(), require=migrator.require_migratable):
            report = migrator.migrate(folder)
    except WorkspaceNewerError as error:
        raise ApiError(409, "version", str(error)) from error
    except (StepFailedError, SchemaMismatchError) as error:
        detail = "\n".join([str(error), *error.lines])
        raise ApiError(422, "migration", detail) from error
    # 当てる手順が無かった: 移し替えていない
    if not report.steps:
        return None, report.source_files
    read_point.save_migration_report(
        folder,
        {"not_carried": report.not_carried, "provisional": report.provisional},
        state_root=ctx.state_root,
    )
    response = {
        "from_version": None if report.workspace_version is None else str(report.workspace_version),
        "to_version": str(report.recorded or report.plugin_version),
        "steps": [f"{step.version} #{step.index}: {describe_step(step)}" for step in report.steps],
        "not_carried": report.not_carried,
    }
    return response, report.source_files


def close_workspace(workspace_id: str, ctx: Any) -> dict[str, Any]:
    """MindStella のセッションが無いワークスペースの配信元の行を outside_read: false にし、クローズ待ちにする。"""
    if workspace_id not in state.read_ids(ctx.state_root):
        raise ApiError(404, "workspace", f"ワークスペースがありません: {workspace_id}")
    with ctx.locks.for_workspace(workspace_id):
        # MindStella のセッションが起動中・停止の途中: 行を変えない
        if sessions.is_alive(
            ctx.state_root,
            workspace_id,
            ctx.tmux,
            ctx.proc,
            on_crashed=lambda: sessions.notify_stopped(ctx, workspace_id, "crashed"),
        ):
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


def reopen_workspace(workspace_id: str, ctx: Any) -> dict[str, Any]:
    """クローズ済みなら配信元の行を outside_read: true に戻し、どちらもクローズ待ちを解く。"""
    with ctx.locks.for_workspace(workspace_id):
        # 鍵を取ってから ID の一覧を確かめる（同時の削除の後なら 404）
        if workspace_id not in state.read_ids(ctx.state_root):
            raise ApiError(404, "workspace", f"ワークスペースがありません: {workspace_id}")
        try:
            row = find_workspace_row(ctx.pi_port, workspace_id)
            # 配信元の行が無い: 開き直す先が無い
            if row is None:
                raise ApiError(404, "workspace", f"配信元の行がありません: {workspace_id}")
            reopened = is_closed(row)
            # クローズ済み: 行を戻す（失敗したらクローズ待ちを解かない）
            if reopened:
                project_index.patch_source(ctx.pi_port, workspace_id, {"outside_read": True})
        except ProjectIndexError as error:
            raise ApiError(502, "source", error.detail) from error
        _clear_close_pending(ctx, workspace_id)
    logger.info(
        "mindstella.workspace.reopened",
        extra={"workspace_id": workspace_id, "reopened": reopened},
    )
    return {"id": workspace_id, "reopened": reopened, "closed": False}


def delete_workspace(workspace_id: str, ctx: Any) -> dict[str, Any]:
    """クローズしたワークスペースの配信元の行・配信・状態の記録・ID の一覧の行をこの順に消す。記録のフォルダは残す。"""
    with ctx.locks.for_workspace(workspace_id):
        # 鍵を取ってから ID の一覧を確かめる（同時の削除の 2 つ目は 404）
        if workspace_id not in state.read_ids(ctx.state_root):
            raise ApiError(404, "workspace", f"ワークスペースがありません: {workspace_id}")
        try:
            row = find_workspace_row(ctx.pi_port, workspace_id)
            # 行があるがクローズしていない: 何も変えない
            if row is not None and not is_closed(row):
                raise ApiError(
                    409, "not_closed", "クローズしていないワークスペースは削除できません。先にクローズしてください"
                )
            # 行がありクローズ済み: 行を消す（行が無ければ前の削除で消えたものとして続ける）
            if row is not None:
                project_index.delete_source(ctx.pi_port, workspace_id)
        except ProjectIndexError as error:
            raise ApiError(502, "source", error.detail) from error
        # 状態のフォルダを消す前に、書き直さないよう配信と変更の検知を止める
        ctx.previews.stop_workspace(workspace_id)
        try:
            state.delete_workspace_state(ctx.state_root, workspace_id)
        except OSError as error:
            logger.exception(
                "mindstella.workspace.delete_failed", extra={"workspace_id": workspace_id}
            )
            raise ApiError(500, "state", f"状態のフォルダを消せません: {error}") from error
        # ID の一覧の行は最後に消す（途中で失敗したら同じ削除をもう一度受けられる）
        state.remove_id(ctx.state_root, workspace_id)
    logger.info("mindstella.workspace.deleted", extra={"workspace_id": workspace_id})
    return {"id": workspace_id, "deleted": True}


def _clear_close_pending(ctx: Any, workspace_id: str) -> None:
    """MindStella のセッションの状態があれば、クローズ待ちを解く。"""
    state.update_session(
        ctx.state_root,
        workspace_id,
        lambda current: None if current is None else current.replace(close_pending=False),
    )


def workspace_status(workspace_id: str, ctx: Any) -> dict[str, Any]:
    """ワークスペースと MindStella のセッションの状態をまとめて返す。何も書かず、鍵も取らない。"""
    # 1. ID の一覧に無い: 知らないワークスペース
    if workspace_id not in state.read_ids(ctx.state_root):
        raise ApiError(404, "workspace", f"ワークスペースがありません: {workspace_id}")
    warnings: list[dict[str, str]] = []
    body: dict[str, Any] = {
        "id": workspace_id,
        "status": None,
        "title": None,
        "url": None,
        "closed": None,
        "unseen_ai_posts": None,
        "awaiting_user_posts": None,
        "updated": None,
    }
    # 2. グローバルの設定のファイルから配信元の行を引く
    row, settings_warning = _file_row(ctx.settings_file, workspace_id)
    if settings_warning is not None:
        warnings.append(settings_warning)
    # 3〜5. 行があれば、クローズ済みか・記録の中身・画面の URL を集める
    if row is not None:
        folder = workspace_folder(row)
        body["closed"] = row.get(FILE_OUTSIDE_READ_KEY) is False
        body["url"] = ctx.previews.url_of(folder)
        body.update(_records_status(folder, warnings))
    # 6. MindStella のセッションの状態と、追加の MCP・プラグインの記録があるか
    listed = sessions.list_sessions(workspace_id, ctx)
    body["sessions"] = listed["sessions"]
    body["close_pending"] = listed["close_pending"]
    body["launch_options_recorded"] = state.read_launch(ctx.state_root, workspace_id) is not None
    # 7. ワークスペースの状態（行を参照できなければ分からない）
    if body["closed"] is True:
        body["status"] = "closed"
    elif body["closed"] is False:
        body["status"] = "stopped" if body["close_pending"] else "active"
    body["warnings"] = warnings
    return body


def list_workspaces(include_closed: bool, ctx: Any) -> dict[str, Any]:
    """ID の一覧の順に、配信元の行があるワークスペースの ID・題名・画面の URL・クローズ済みかを返す。何も書かない。"""
    try:
        rows = project_index.read_source_rows(ctx.settings_file)
    except ProjectIndexError as error:
        # グローバルの設定のファイルを参照できない: 空の並びと警告
        return {"workspaces": [], "warnings": [{"stage": "settings", "detail": error.detail}]}
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    listed: list[dict[str, Any]] = []
    for workspace_id in state.read_ids(ctx.state_root):
        row = by_id.get(workspace_id)
        # 配信元の行が無い: 一覧に含めない
        if row is None:
            continue
        closed = row.get(FILE_OUTSIDE_READ_KEY) is False
        # クローズ済みで、含める指定が無い: 除く
        if closed and not include_closed:
            continue
        folder = workspace_folder(row)
        listed.append(
            {
                "id": workspace_id,
                "title": _load_title(folder)[0],
                "url": ctx.previews.url_of(folder),
                "closed": closed,
            }
        )
    return {"workspaces": listed, "warnings": []}


def _file_row(
    settings_file: Path, workspace_id: str
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """グローバルの設定のファイルからワークスペースの行を返す。参照できなければ行の代わりに settings の警告を返す。"""
    try:
        rows = project_index.read_source_rows(settings_file)
    except ProjectIndexError as error:
        return None, {"stage": "settings", "detail": error.detail}
    for row in rows:
        if isinstance(row, dict) and row.get("id") == workspace_id:
            return row, None
    return None, {
        "stage": "settings",
        "detail": f"グローバルの設定のファイルに配信元の行がありません: {settings_file}（{workspace_id}）",
    }


def _records_status(folder: Path, warnings: list[dict[str, str]]) -> dict[str, Any]:
    """記録から題名・未読の 2 つの数・最後の更新の日時を集める。参照できない分は None にして warnings に足す。"""
    # 記録のフォルダが無い: 記録の項目は全て分からない
    if not (records_root(folder) / SETTINGS_FILE).is_file():
        warnings.append({"stage": "records", "detail": f"記録のフォルダがありません: {folder}"})
        return {}
    title, title_error = _load_title(folder)
    collected: dict[str, Any] = {"title": title}
    # 記録の設定が読めない: 題名は分からないが、スレッドと変更履歴は続けて数える
    if title_error is not None:
        warnings.append({"stage": "records", "detail": title_error})
    try:
        unseen_ai, awaiting, last_post = threads.status_counts(folder)
        last_item = history.last_updated(folder)
    except SchemaMismatchError as error:
        # スレッドか変更履歴が読めない: 題名だけを返す
        reason = "、".join(error.lines) or str(error)
        warnings.append({"stage": "records", "detail": f"{error}: {reason}"})
        return collected
    collected["unseen_ai_posts"] = unseen_ai
    collected["awaiting_user_posts"] = awaiting
    # 日時は UTC のタイムゾーン付き ISO 8601 で揃っているので、文字列の大小で新しい方を選ぶ
    collected["updated"] = max(
        (stamp for stamp in (last_item, last_post) if stamp is not None), default=None
    )
    return collected


def _load_title(folder: Path) -> tuple[str | None, str | None]:
    """記録の設定の title と、読めなかった理由を返す。記録か title が無ければ title は None。"""
    path = records_root(folder) / SETTINGS_FILE
    if not path.is_file():
        return None, None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        # 読めないか YAML として壊れている: 題名を None にして理由を返す
        reason = " ".join(str(error).split())
        return None, f"記録の設定を読めません: {path}（{reason}）"
    title = data.get("title") if isinstance(data, dict) else None
    return (title if isinstance(title, str) else None), None


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
        }
    )
    return settings


def workspace_id_of(folder: Path) -> str:
    """記録の設定の id を返す。記録か id が無ければフォルダから振る。"""
    return _recorded_id(folder) or workspace_id_for(folder)


def _recorded_id(folder: Path) -> str | None:
    """記録の設定の id を返す。記録か id が無ければ `None`。"""
    path = records_root(folder) / SETTINGS_FILE
    if not path.is_file():
        return None
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    value = loaded.get("id") if isinstance(loaded, dict) else None
    return str(value) if value else None


def _register_source(
    ctx: Any, workspace_id: str, folder: Path, *, created: bool, recorded: bool
) -> tuple[str, bool]:
    """配信元の行を追加するか戻し、作成の結果（created・opened・reopened・already_open）と、行を書き換えて配信元を読み直させたかを返す。"""
    existing = find_workspace_row(ctx.pi_port, workspace_id)
    # 行が無い: 追加する（同じ内容の行が同時に足されていれば、追加済みとして続ける）
    if existing is None:
        added = project_index.add_source(ctx.pi_port, _source_row(workspace_id, folder))
        # 同じ ID で中身の違う行がある: 別のフォルダの行とみなして止める
        if added == "exists_different":
            raise ProjectIndexError(409, f"配信元 {workspace_id} の行が別の内容で登録されています")
        # 追加したときだけ、project-index がその配信元を読み込む
        return ("created" if created else "opened"), added == "added"
    changes: dict[str, Any] = {}
    row_folder = workspace_folder(existing).resolve()
    # 行が別のフォルダを指す: 移したなら行を今回のフォルダへ変え、コピーしたなら止める
    if row_folder != folder:
        if _recorded_id(row_folder) == workspace_id:
            raise ApiError(
                409, "duplicate", f"同じ ID のワークスペースの記録が別のフォルダにあります: {row_folder}"
            )
        source_row = _source_row(workspace_id, folder)
        changes = {"config": source_row["config"], "scope": source_row["scope"]}
    # クローズ済みの行: outside_read を戻してクローズ待ちを解く
    if is_closed(existing):
        project_index.patch_source(ctx.pi_port, workspace_id, {**changes, "outside_read": True})
        _clear_close_pending(ctx, workspace_id)
        return "reopened", True
    if changes:
        project_index.patch_source(ctx.pi_port, workspace_id, changes)
        return "opened", True
    # 行はあるが、今回の指定を記録したか ID の一覧に無い: 開き直した
    if recorded or workspace_id not in state.read_ids(ctx.state_root):
        return "opened", False
    return "already_open", False


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
    ctx: Any,
    workspace_id: str,
    folder: Path,
    *,
    created: bool,
    recorded: bool,
    readme_written: bool,
) -> list[str]:
    """この依頼で作った記録・直下の README・状態の記録を消し、消せなかったパスを返す。"""
    targets: list[Path] = []
    if created:
        targets.append(records_root(folder))
    # 作成の前に README が無かった: この依頼で書いた README も消す
    if readme_written:
        targets.append(folder / README_FILE)
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
