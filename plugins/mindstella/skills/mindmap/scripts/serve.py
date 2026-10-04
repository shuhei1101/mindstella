"""ワークスペースごとに `127.0.0.1` の空きポートでプレビューを配る。

画面・記録・書き換えの知らせを返し、回答・意見の送信を受け付ける。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from builder import PREVIEW_DIR, assemble_template, read_records
from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    ServeFailedError,
    SubmissionInvalidError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from kinds import BODY_DIR, KINDS, SETTINGS_FILE
from store import workspace_lock
from submissions import SUBMISSIONS_FILE, Submission, add_submission

logger = logging.getLogger(__name__)

# 待ち受けのアドレス（ポートは 0 で OS に選ばせる）
LISTEN_HOST = "127.0.0.1"

# 書き換えの印を作り直す間隔（秒）
POLL_INTERVAL_SEC = 0.25

# 知らせが無いままこの秒数が過ぎたら保つための行を送る
KEEPALIVE_SEC = 15

# 送信の要求の本文を読む上限（バイト）。`Content-Length` がこれを超えたら読まずに 400 にする
MAX_REQUEST_BYTES = 65536

# 送信を受け付けるパス
SUBMISSIONS_PATH = "/api/submissions"

# JSON・HTML・問題の応答の `Content-Type`
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
PROBLEM_TYPE = "application/problem+json; charset=utf-8"

# 送信の要求が持つべきメディアタイプ
REQUEST_JSON_TYPE = "application/json"

# 書き換えの知らせの応答の `Content-Type`
EVENT_STREAM_TYPE = "text/event-stream"


@dataclass(frozen=True, slots=True, kw_only=True)
class ServeContext:
    """要求の受け口が使う、配っているワークスペースと待ち受けの値。"""

    root: Path
    port: int
    # プロセスの中の書き換えの鍵
    write_lock: threading.Lock
    # 雛形のフォルダ
    preview_dir: Path = PREVIEW_DIR


@dataclass(frozen=True, slots=True, kw_only=True)
class Response:
    """処理の関数が返す、書く前の応答。"""

    status: int
    content_type: str
    body: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class PreviewServer:
    """1 つのワークスペースの待ち受けと、それを動かすスレッド。"""

    root: Path
    # `http://127.0.0.1:{ポート}/`
    url: str
    httpd: ThreadingHTTPServer
    thread: threading.Thread

    def stop(self) -> None:
        """待ち受けを止めて閉じる（つながっている書き換えの知らせは、書き込みが失敗して終わる）。"""
        self.httpd.shutdown()
        self.httpd.server_close()


class PreviewRegistry:
    """このプロセスが立てた配信をワークスペースの絶対パスごとに 1 つ持ち、終わるときに全て止める。"""

    def __init__(self, write_lock: threading.Lock) -> None:
        """ツールと共有する書き換えの鍵を受け取り、空の台帳を作る。"""
        self._servers: dict[Path, PreviewServer] = {}
        self._write_lock = write_lock
        # `_servers` を触る間だけ取る鍵
        self._guard = threading.Lock()

    def start(self, root: Path) -> tuple[str, bool]:
        """そのワークスペースの配信を立て、URL と今立てたかを返す。立っていればその URL を返す。"""
        key = root.resolve()
        with self._guard:
            existing = self._servers.get(key)
            # 立っている: その URL を返す
            if existing is not None:
                return existing.url, False
            preview = start_preview_server(key, write_lock=self._write_lock)
            self._servers[key] = preview
            logger.info("配信を立てた: %s %s", key, preview.url)
            return preview.url, True

    def stop_all(self) -> None:
        """立てた配信を全て止め、台帳を空にする。"""
        with self._guard:
            for preview in self._servers.values():
                preview.stop()
            self._servers.clear()


class PreviewHandler(BaseHTTPRequestHandler):
    """パスごとに処理の関数へ振り分け、返った応答を書く。要求と応答の読み書きだけを持つ。"""

    @property
    def context(self) -> ServeContext:
        """待ち受けに持たせた、配信の文脈を返す。"""
        return cast("ServeContext", getattr(self.server, "context"))  # noqa: B009

    def do_GET(self) -> None:
        """`Host` を確かめ、`/`・`/api/records`・`/api/events` を処理の関数へ振り分ける。"""
        context = self.context
        # 接続先が合わない
        if not check_host(self.headers.get("Host"), context.port):
            self._reply(problem_response(HTTPStatus.FORBIDDEN, "接続先が合いません"))
            return
        path = urlsplit(self.path).path
        if path == "/":
            self._reply(index_response(context.preview_dir))
        elif path == "/api/records":
            self._reply(records_response(context.root))
        elif path == "/api/events":
            self._stream(context.root)
        else:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    def do_POST(self) -> None:
        """`Host` を確かめ、`/api/submissions` を受け付けの関数へ渡す。"""
        context = self.context
        # 接続先が合わない
        if not check_host(self.headers.get("Host"), context.port):
            self._reply(problem_response(HTTPStatus.FORBIDDEN, "接続先が合いません"))
            return
        path = urlsplit(self.path).path
        if path != SUBMISSIONS_PATH:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))
            return
        length = self._content_length()
        # 長さが無いか、上限を超える: 本文を読まずに断る
        if length is None or length > MAX_REQUEST_BYTES:
            self._reply(
                problem_response(
                    HTTPStatus.BAD_REQUEST,
                    f"本文の長さが要ります（{MAX_REQUEST_BYTES} バイトまで）",
                )
            )
            return
        body = self.rfile.read(length)
        self._reply(
            submission_response(
                context,
                content_type=self.headers.get("Content-Type"),
                origin=self.headers.get("Origin"),
                body=body,
            )
        )

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """標準の要求の記録を `logging` の `DEBUG` に回す（標準エラーへの直接の書き込みをやめる）。"""
        logger.debug("受けた要求: %s", format % args)

    def _content_length(self) -> int | None:
        """`Content-Length` を整数で返す（無い・整数でない・負のときは None）。"""
        text = self.headers.get("Content-Length")
        if text is None:
            return None
        try:
            length = int(text)
        except ValueError:
            return None
        return length if length >= 0 else None

    def _reply(self, response: Response) -> None:
        """ステータスコード・ヘッダー・本文を書く（常に控えさせない）。"""
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response.body)

    def _stream(self, root: Path) -> None:
        """`200` と `text/event-stream` を書き、画面が閉じるまで書き換えを知らせ続ける。"""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", EVENT_STREAM_TYPE)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        def _write(chunk: bytes) -> None:
            """書いてすぐ送り出す。"""
            self.wfile.write(chunk)
            self.wfile.flush()

        try:
            self.wfile.flush()
            stream_events(root, _write)
        except (BrokenPipeError, ConnectionResetError):
            # 見出しを送る前に画面が閉じた
            return


def start_preview_server(root: Path, *, write_lock: threading.Lock) -> PreviewServer:
    """`LISTEN_HOST` の空きポートで待ち受け、デーモンのスレッドで動かし始める。"""
    try:
        httpd = ThreadingHTTPServer((LISTEN_HOST, 0), PreviewHandler)
    except OSError as error:
        raise ServeFailedError(f"プレビューの配信を立てられません: {error}") from error
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    # 要求の受け口が `self.server.context` で引けるように、待ち受けに持たせる
    setattr(httpd, "context", ServeContext(root=root, port=port, write_lock=write_lock))  # noqa: B010
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return PreviewServer(root=root, url=f"http://{LISTEN_HOST}:{port}/", httpd=httpd, thread=thread)


def check_host(host: str | None, port: int) -> bool:
    """`Host` が `127.0.0.1:{ポート}` か `localhost:{ポート}` かを返す。"""
    # 無い: 合わない
    if host is None:
        return False
    return host.lower() in {f"{LISTEN_HOST}:{port}", f"localhost:{port}"}


def check_origin(origin: str | None, port: int) -> bool:
    """`Origin` が無いか、配信の URL と同じかを返す。"""
    # 無い（同じ送り元からの要求など）: 通す
    if origin is None:
        return True
    return origin in {f"http://{LISTEN_HOST}:{port}", f"http://localhost:{port}"}


def problem_response(status: int, detail: str) -> Response:
    """RFC 9457 の `application/problem+json` の応答を作る。"""
    problem = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": int(status),
        "detail": detail,
    }
    return Response(
        status=int(status),
        content_type=PROBLEM_TYPE,
        body=json.dumps(problem, ensure_ascii=False).encode("utf-8"),
    )


def index_response(preview_dir: Path) -> Response:
    """雛形に CSS と JavaScript を差し込んだ画面を返す（記録は埋め込まない）。"""
    try:
        html = assemble_template(preview_dir=preview_dir)
    except (ValueError, OSError) as error:
        # 同梱の雛形の誤り（差し込み口の数・閉じタグ・欠けたファイル）
        logger.error("同梱の雛形の誤り: %s", error)  # noqa: TRY400
        return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"同梱の雛形の誤り: {error}")
    return Response(status=HTTPStatus.OK, content_type=HTML_TYPE, body=html.encode("utf-8"))


def records_response(
    root: Path, read: Callable[[Path], dict[str, Any]] = read_records
) -> Response:
    """ワークスペースをその場で読んだ記録の JSON を返す。"""
    try:
        data = read(root)
    except SchemaMismatchError as error:
        # 読めない・スキーマに合わない: 合わない箇所の行を detail にする
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join(error.lines))
    except WorkspaceNotFoundError as error:
        # 配っている間に mindmap.yaml が無くなった
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )


def workspace_signature(root: Path) -> str:
    """見ているファイルの名前・更新日時（ナノ秒）・大きさをつないだ、書き換えの印を返す。"""
    names = [SETTINGS_FILE, *(spec.file for spec in KINDS.values()), SUBMISSIONS_FILE]
    # 本文の Markdown（`docs/` の直下）も見る
    body_dir = root / BODY_DIR
    if body_dir.is_dir():
        names.extend(f"{BODY_DIR}/{path.name}" for path in body_dir.glob("*.md"))
    parts: list[str] = []
    for name in sorted(names):
        try:
            stat = (root / name).stat()
        except OSError:
            # 無い（足される・消されると印が変わる）
            parts.append(f"{name}:-")
            continue
        parts.append(f"{name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def stream_events(
    root: Path,
    write: Callable[[bytes], None],
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    signature: Callable[[Path], str] = workspace_signature,
) -> None:
    """書き換えの印が変わったら `changed` を、知らせが無いまま一定時間過ぎたら保つ行を書き続ける。"""
    last_signature = signature(root)
    last_written = clock()
    while True:
        sleep(POLL_INTERVAL_SEC)
        current = signature(root)
        try:
            if current != last_signature:
                # 印が変わった: 変わったことだけを知らせる（画面が記録を読み直す）
                write(f"event: changed\ndata: {current}\n\n".encode())
                last_signature = current
                last_written = clock()
            elif clock() - last_written >= KEEPALIVE_SEC:
                # 変わらないまま長く経った: つながりを保つ
                write(b": keepalive\n\n")
                last_written = clock()
        except (BrokenPipeError, ConnectionResetError):
            # 画面が閉じた
            return


def submission_response(
    context: ServeContext,
    *,
    content_type: str | None,
    origin: str | None,
    body: bytes,
    add: Callable[..., Submission] = add_submission,
) -> Response:
    """送り元と本文の形を確かめ、書き換えの鍵を取って送信を足し、結果の応答を返す。"""
    media_type = (content_type or "").split(";")[0].strip().lower()
    # JSON でない
    if media_type != REQUEST_JSON_TYPE:
        return problem_response(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE, f"{REQUEST_JSON_TYPE} で送ってください"
        )
    # 別のサイトからの書き込み
    if not check_origin(origin, context.port):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        data = None
    # JSON として読めないか、オブジェクトでない
    if not isinstance(data, dict):
        return problem_response(HTTPStatus.BAD_REQUEST, "本文は JSON のオブジェクトで送ってください")
    try:
        with workspace_lock(context.root, context.write_lock):
            submission = add(context.root, data)
    except SubmissionInvalidError as error:
        return problem_response(HTTPStatus.BAD_REQUEST, str(error))
    except ItemNotFoundError as error:
        return problem_response(HTTPStatus.NOT_FOUND, str(error))
    except (WorkspaceNotFoundError, SchemaMismatchError) as error:
        return problem_response(
            HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join(error.lines) or str(error)
        )
    except WriteFailedError as error:
        return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))
    logger.info("送信を受けた: %s %s", submission.id, submission.target)
    return Response(
        status=HTTPStatus.CREATED,
        content_type=JSON_TYPE,
        body=json.dumps({"id": submission.id, "sent": submission.sent}, ensure_ascii=False).encode(
            "utf-8"
        ),
    )
