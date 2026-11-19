"""起動中の MindStella のセッションが使用中のアカウントの利用枠を claude-balancer に問い合わせ、しきい値以上なら起動し直す。"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

import sessions
import state

logger = logging.getLogger("mindstella.usage_watch")

# 見回る間隔の秒数
USAGE_WATCH_INTERVAL_SEC = 60.0

# 見回る間隔を上書きする環境変数
USAGE_WATCH_INTERVAL_ENV = "MINDSTELLA_USAGE_WATCH_INTERVAL"

# claude-balancer へ 1 回問い合わせる上限の秒数
USAGE_QUERY_TIMEOUT_SEC = 5.0

# 貸せない理由のうち、利用枠がしきい値以上を表す値
OVER_THRESHOLD_REASONS = ("five_hour_over_threshold", "seven_day_over_threshold")

# 起動し直しの契機
RESTART_REASON = "usage_threshold"


class BalancerUnavailableError(Exception):
    """claude-balancer につながらないか、応答が読めない。"""


def fetch_accounts(base_url: str) -> list[dict[str, Any]]:
    """claude-balancer の `GET /accounts` の `accounts` を返却する。"""
    url = f"{base_url.rstrip('/')}/accounts"
    try:
        with urllib.request.urlopen(url, timeout=USAGE_QUERY_TIMEOUT_SEC) as response:
            body = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise BalancerUnavailableError(f"{url}: {error}") from error
    accounts = body.get("accounts") if isinstance(body, dict) else None
    if not isinstance(accounts, list):
        raise BalancerUnavailableError(f"{url}: accounts が配列ではありません")
    return accounts


def choose_restarts(
    sessions_by_workspace: dict[str, dict[str, Any]],
    accounts: list[dict[str, Any]],
    release_on_limit: bool,
) -> list[str]:
    """使用中のアカウントがしきい値以上で、切り替え先がある MindStella のセッションのワークスペースの ID を選ぶ。"""
    reasons = {row.get("account"): row.get("unavailableReason") for row in accounts}
    # 貸せるアカウントが 1 つも無い: 切り替え先が無いので今のアカウントで続ける
    if not any(reason is None for reason in reasons.values()):
        return []
    chosen = []
    for workspace_id, session in sessions_by_workspace.items():
        # 使用中のアカウントがしきい値以上でない（一覧に無いものを含む）: 続ける
        if reasons.get(session.get("balancer_account")) not in OVER_THRESHOLD_REASONS:
            continue
        # 指定したアカウントを解除しない設定: 指定したアカウントのまま続ける
        if session.get("specified_account") and not release_on_limit:
            continue
        chosen.append(workspace_id)
    return chosen


def watch_usage_once(
    ctx: Any,
    *,
    fetch: Callable[[str], list[dict[str, Any]]] = fetch_accounts,
    restart: Callable[[str], bool] | None = None,
) -> int | None:
    """見回る対象を 1 回照らして起動し直し、起動し直した数を返却する。問い合わせに失敗したら None。"""
    targets: dict[str, dict[str, Any]] = {}
    for workspace_id in state.read_ids(ctx.state_root):
        current = state.read_session(ctx.state_root, workspace_id)
        # 起動中で、止める予定も書き込みの待ちも無く、貸したアカウントが分かるものだけを見回る
        if (
            current is not None
            and current.status == "running"
            and not current.close_pending
            and not current.pending_write
            and current.balancer_account
        ):
            targets[workspace_id] = {
                "balancer_account": current.balancer_account,
                "specified_account": current.specified_account,
            }
    # 見回る対象が無い: 問い合わせない
    if not targets:
        return 0
    try:
        accounts = fetch(ctx.home.query_url())
    except BalancerUnavailableError:
        return None
    request = restart or (
        lambda workspace_id: sessions.request_restart(workspace_id, RESTART_REASON, ctx)
    )
    reasons = {row.get("account"): row.get("unavailableReason") for row in accounts}
    count = 0
    for workspace_id in choose_restarts(targets, accounts, ctx.home.release_on_limit):
        account = targets[workspace_id]["balancer_account"]
        logger.info(
            "mindstella.usage.over_threshold",
            extra={
                "workspace_id": workspace_id,
                "account": account,
                "unavailable_reason": reasons.get(account),
            },
        )
        if request(workspace_id):
            count += 1
    return count


def start_usage_watch(ctx: Any, stop: threading.Event) -> threading.Thread | None:
    """間隔ごとに watch_usage_once を呼ぶ daemon のスレッドを始める。claude-balancer が無ければ始めない。"""
    if shutil.which("claude-balancer") is None:
        return None
    interval = float(os.environ.get(USAGE_WATCH_INTERVAL_ENV) or USAGE_WATCH_INTERVAL_SEC)

    def loop() -> None:
        """stop が立つまで見回り、問い合わせの失敗は失敗し始めた回だけ記録する。"""
        failing = False
        while not stop.wait(interval):
            try:
                result = watch_usage_once(ctx)
            except Exception:
                logger.exception("mindstella.usage.watch_failed")
                continue
            # 成功から失敗に変わった: 1 回だけ記録する
            if result is None and not failing:
                logger.warning("mindstella.usage.query_failed", extra={"url": ctx.home.query_url()})
            failing = result is None

    thread = threading.Thread(target=loop, name="mindstella-usage-watch", daemon=True)
    thread.start()
    return thread
