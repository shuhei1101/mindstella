"""常駐サーバーの起動時の照合。待ち受けの前に ID の一覧を作り直して状態を照合し、待ち受けと並行してエージェントフローの配信元の行を確かめ、ID の一覧のワークスペースを配り始める。"""

from __future__ import annotations

import logging
import threading
from typing import Any

import yaml

import project_index
import sessions
import state
from errors import MindmapError, WriteFailedError
from project_index import ProjectIndexError
from readme import write_readme
from workspaces import AGENT_FLOWS_CONFIG, AGENT_FLOWS_SOURCE, PLUGIN_DIR, workspace_folder

logger = logging.getLogger("mindstella.startup")

# 待ち受けの前に ID の一覧を作り直すときの GET /settings/sources を打ち切る秒数
# （常駐サーバーの起動の確認が待ち受けを待つ上限 10 秒に、待ち受けるまでの約 1 秒と余裕 50% を収める）
STARTUP_GET_TIMEOUT_SEC = 5.0

# 配信元の行をワークスペースの行と見分ける config の末尾
WORKSPACE_CONFIG_SUFFIX = "/.mindstella/dev-docs.yaml"

# エージェントフローの配信元の行を確かめるスレッドの名前
AGENT_FLOWS_THREAD_NAME = "mindstella-agent-flows-check"

# ID の一覧のワークスペースを配り始めるスレッドの名前
SERVE_REGISTERED_THREAD_NAME = "mindstella-serve-registered"


def reconcile_before_listen(ctx: Any) -> None:
    """ID の一覧が無ければ作り直し、状態の照合を 1 回して戻る。どれに失敗しても例外を送らない。"""
    # 1. ID の一覧の作り直し（失敗しても照合へ進む）
    try:
        rebuild_ids_if_missing(ctx)
    except Exception as error:
        logger.exception(
            "mindstella.startup.rebuild_failed",
            extra={"error_type": type(error).__name__, "reason": str(error)},
        )
    # 2. 状態の照合（落ちた MindStella のセッションを crashed にして通知する）
    try:
        count = sessions.watch_crashes_once(ctx)
    except (yaml.YAMLError, ValueError) as error:
        # ID の一覧が読めない: 照合を飛ばす
        logger.exception("mindstella.startup.ids_unreadable", extra={"reason": str(error)})
        return
    except Exception as error:
        # そのほかの失敗（workspaces.yaml を読めない など）: 照合を飛ばす
        logger.exception(
            "mindstella.startup.reconcile_failed",
            extra={"error_type": type(error).__name__, "reason": str(error)},
        )
        return
    logger.info("mindstella.startup.reconciled", extra={"crashed": count})


def rebuild_ids_if_missing(ctx: Any) -> int | None:
    """`workspaces.yaml` が無いときだけ、project-index の配信元の行のうちワークスペースの行の ID で作る。"""
    # 一覧がある: 突き合わせず、project-index も呼ばない
    if state.ids_exist(ctx.state_root):
        return None
    try:
        settings = project_index.get_settings(ctx.pi_port, timeout=STARTUP_GET_TIMEOUT_SEC)
    except ProjectIndexError as error:
        logger.warning(
            "mindstella.startup.rebuild_skipped",
            extra={"status": error.status, "reason": error.detail},
        )
        return None
    # 応答に配信元の行の並びが無い（本文が JSON でない など）: 空の一覧を作らない
    if not isinstance(settings.get("sources"), list):
        logger.warning(
            "mindstella.startup.rebuild_skipped",
            extra={"status": None, "reason": "応答に sources の並びがありません"},
        )
        return None
    ids = workspace_ids(settings)
    # 取得している間に『ワークスペースの作成』が一覧を作った: 書き換えない
    if not state.create_ids_if_missing(ctx.state_root, ids):
        return None
    logger.info("mindstella.startup.ids_rebuilt", extra={"count": len(ids)})
    return len(ids)


def workspace_ids(settings: dict[str, Any]) -> list[str]:
    """応答の行のうち、config の末尾が WORKSPACE_CONFIG_SUFFIX の行の id を応答の並び順で返す。"""
    ids: list[str] = []
    for row in settings.get("sources") or []:
        # 辞書でない行・id が文字列でない行・config が文字列でない行: ワークスペースの行でない
        if not isinstance(row, dict):
            continue
        source_id = row.get("id")
        config = _row_config(row)
        if not isinstance(source_id, str) or config is None:
            continue
        # ワークスペースの記録を配る設定を指す行だけを、重ならないように並べる（クローズ済みも含める）
        if config.endswith(WORKSPACE_CONFIG_SUFFIX) and source_id not in ids:
            ids.append(source_id)
    return ids


def check_agent_flows_source(ctx: Any) -> bool:
    """エージェントフローの配信元の行が今のプラグインを指していなければ config を書き換え、書き換えたかを返す。"""
    current = str(PLUGIN_DIR / AGENT_FLOWS_CONFIG)
    try:
        settings = project_index.get_settings(ctx.pi_port)
        row = _find_row(settings, AGENT_FLOWS_SOURCE)
        # 行が無い: 足すのは『ワークスペースの作成』なので何もしない
        if row is None:
            return False
        before = _row_config(row)
        # 今のプラグインを指している: 書き換えない
        if before == current:
            return False
        # config だけを書き換える（409 のときの 1 回の取得し直しは patch_source が行う）
        project_index.patch_source(ctx.pi_port, AGENT_FLOWS_SOURCE, {"config": current})
    except ProjectIndexError as error:
        logger.warning(
            "mindstella.startup.agent_flows_skipped",
            extra={"status": error.status, "reason": error.detail},
        )
        return False
    logger.info(
        "mindstella.startup.agent_flows_updated", extra={"before": before, "after": current}
    )
    return True


def start_agent_flows_check(ctx: Any) -> threading.Thread:
    """check_agent_flows_source を 1 回だけ呼ぶ daemon のスレッドを始めて返す。"""
    thread = threading.Thread(
        target=check_agent_flows_source, args=(ctx,), name=AGENT_FLOWS_THREAD_NAME, daemon=True
    )
    thread.start()
    return thread


def serve_registered(ctx: Any) -> int | None:
    """状態の ID の一覧のワークスペースを配信の台帳で配り始め、直下の README を書き直す。配り始めた数を返す。

    project-index に問い合わせられなければ None を返す。どれに失敗しても例外を送出しない。
    """
    ids = state.read_ids(ctx.state_root)
    try:
        settings = project_index.get_settings(ctx.pi_port)
    except ProjectIndexError as error:
        logger.warning(
            "mindstella.startup.serve_registered_skipped",
            extra={"status": error.status, "reason": f"{error.detail}（preview_url で配れる）"},
        )
        return None
    started_count = 0
    for workspace_id in ids:
        row = _find_row(settings, workspace_id)
        # 配信元の行が無い ID は飛ばす
        if row is None:
            continue
        root = workspace_folder(row)
        try:
            url, started = ctx.previews.start(root)
        except (MindmapError, OSError) as error:
            logger.warning(
                "ワークスペースを配れない: %s %s（%s）", workspace_id, root, error
            )
            continue
        if not started:
            continue
        started_count += 1
        # 配り始めたときは、run_preview_url と同じく README のプレビューの節をその URL にする
        try:
            write_readme(root, preview_url=url)
        except WriteFailedError as error:
            logger.warning("README を書けなかった: %s（%s）", root, error)
    logger.info("mindstella.startup.serve_registered", extra={"count": started_count})
    return started_count


def start_serve_registered(ctx: Any) -> threading.Thread:
    """serve_registered を 1 回だけ呼ぶ daemon のスレッドを始めて返す（待ち受けを始めるのを待たせない）。"""
    thread = threading.Thread(
        target=serve_registered, args=(ctx,), name=SERVE_REGISTERED_THREAD_NAME, daemon=True
    )
    thread.start()
    return thread


def _find_row(settings: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    """応答の行のうち、ID の行を返す。"""
    for row in settings.get("sources") or []:
        if isinstance(row, dict) and row.get("id") == source_id:
            return row
    return None


def _row_config(row: dict[str, Any]) -> str | None:
    """行の config を返す。並びなら先頭の要素、文字列でなければ None。"""
    config = row.get("config")
    # 複数の配信の設定を並べた行: 先頭の要素を行の config とする
    first = (config[0] if config else None) if isinstance(config, list) else config
    return first if isinstance(first, str) else None
