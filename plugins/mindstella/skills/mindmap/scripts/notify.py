"""MindStella のセッションごとの書き込みのマーカーを持ち、応答の終わりに Discord の Webhook へ作業の完了を送信する。"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger("mindstella.notify")

# 成功したら書き込みのマーカーを付ける MCP のツール
MARKING_TOOLS = ("commit", "new_thread", "reply")

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# Webhook の送信を待つ上限の秒数（非機能要件『Webhook の送信を待つ上限』）
SEND_TIMEOUT_SEC = 10.0

# Webhook へ送信するときの User-Agent（標準ライブラリの既定の値では Discord が 403 を返却する）
USER_AGENT = "DiscordBot (https://github.com/shuhei1101/mindstella, 1.0)"

# Discord の content の上限の文字数
CONTENT_LIMIT = 2000

# 本文の 1 行目の名前の後ろの文言
DONE_TEXT = "作業が完了しました"

# 名前を切り詰めたときに末尾へ付ける文字
ELLIPSIS = "…"


class WriteMarkers:
    """この応答で書き込んだワークスペースの ID を、常駐サーバーのメモリに持つ。"""

    def __init__(self) -> None:
        self._marked: set[str] = set()
        # _marked を触る間だけ取る鍵（MCP のツールと出来事の受け取りが別のスレッドで触る）
        self._guard = threading.Lock()

    def mark(self, workspace_id: str) -> None:
        """マーカーを付ける。"""
        with self._guard:
            self._marked.add(workspace_id)

    def clear(self, workspace_id: str) -> None:
        """マーカーを解除する（無ければ何もしない）。"""
        with self._guard:
            self._marked.discard(workspace_id)

    def take(self, workspace_id: str) -> bool:
        """マーカーがあったかを返却し、同じ鍵の中で解除する。"""
        with self._guard:
            if workspace_id in self._marked:
                self._marked.remove(workspace_id)
                return True
            return False


# 常駐サーバーのプロセスに 1 つの書き込みのマーカー（起動し直すと空になる）
MARKERS = WriteMarkers()


def read_webhook_url(environ: Mapping[str, str]) -> str | None:
    """WEBHOOK_FILE_ENV が指すファイルの 1 行目を Webhook の URL として返却する。使用できないときは None。"""
    path = environ.get(WEBHOOK_FILE_ENV, "")
    # 指定が無い・空: 通知を使用しない
    if not path:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        # 参照できない: パスと中身は秘匿のため記録しない
        logger.warning("Webhook の設定を参照できない: %s", type(error).__name__)
        return None
    lines = text.splitlines()
    first = lines[0].strip() if lines else ""
    # 1 行目が http:// か https:// で始まるか
    if first.startswith(("http://", "https://")):
        return first
    return None


def build_content(name: str, url: str | None) -> str:
    """`{名前}: 作業が完了しました` と画面の URL の 2 行を、CONTENT_LIMIT 文字以内で組み立てる。"""
    tail = f": {DONE_TEXT}"
    # 画面の配信があれば 2 行目に URL を配置する
    if url:
        tail = f"{tail}\n{url}"
    if len(name) + len(tail) <= CONTENT_LIMIT:
        return f"{name}{tail}"
    # 上限を超える: 名前の末尾を切り詰めて ELLIPSIS を付ける
    keep = max(CONTENT_LIMIT - len(tail) - len(ELLIPSIS), 0)
    return f"{name[:keep]}{ELLIPSIS}{tail}"


def send_webhook(
    url: str,
    content: str,
    *,
    timeout: float = SEND_TIMEOUT_SEC,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> bool:
    """`POST {url}?wait=true` に `{"content": 本文}` を送信し、結果を URL を含めずに記録する。例外を送出しない。"""
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}wait=true",
        data=json.dumps({"content": content}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    started = time.monotonic()
    try:
        with opener(request, timeout=timeout) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        # 4xx・5xx の応答: ステータスコードだけを記録する
        logger.warning("Webhook への送信が失敗した: %s", error.code)
        return False
    except OSError as error:
        # 接続できない・上限を過ぎた: 例外の文字列は URL を含むため種類だけを記録する
        logger.warning("Webhook への送信が失敗した: %s", type(error).__name__)
        return False
    # 200 だけを成功とする（wait=true は投稿したメッセージを 200 で返却する）
    if status != 200:  # noqa: PLR2004
        logger.warning("Webhook への送信が失敗した: %s", status)
        return False
    logger.info("Webhook への送信が成功した: %s（%.2f 秒）", status, time.monotonic() - started)
    return True


def mark_written(tool: str, workspace_id: str, payload: dict[str, Any]) -> None:
    """ツールの名前が MARKING_TOOLS で、結果が書き込んだことを示すときだけ MARKERS に付ける。"""
    # 対象外のツール
    if tool not in MARKING_TOOLS:
        return
    # まとめる変更が無かった commit
    if tool == "commit" and payload.get("id") is None:
        return
    MARKERS.mark(workspace_id)


def clear_written(workspace_id: str) -> None:
    """書き込みのマーカーを解除する。"""
    MARKERS.clear(workspace_id)


def notify_if_written(
    workspace_id: str,
    describe: Callable[[], tuple[str, str | None] | None],
    *,
    environ: Mapping[str, str] = os.environ,
    send: Callable[[str, str], bool] = send_webhook,
) -> threading.Thread | None:
    """マーカーを確認して解除し、あったときだけ daemon のスレッドで本文を組み立てて送信する。"""
    # この応答で書き込んでいない
    if not MARKERS.take(workspace_id):
        return None
    url = read_webhook_url(environ)
    # Webhook の設定が無い
    if url is None:
        return None

    def run() -> None:
        """名前と画面の URL を参照して送信する。"""
        try:
            described = describe()
            # ワークスペースが見つからない: 送信しない
            if described is None:
                return
            name, page_url = described
            send(url, build_content(name, page_url))
        except Exception as error:  # noqa: BLE001
            # 想定していない例外: 応答の受け取りに影響させず、種類だけを記録する
            logger.error("通知の予期しないエラー: %s", type(error).__name__)  # noqa: TRY400

    thread = threading.Thread(target=run, name="mindstella-notify", daemon=True)
    thread.start()
    return thread
