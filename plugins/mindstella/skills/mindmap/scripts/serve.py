"""ワークスペースごとに `127.0.0.1` の空きポートでプレビューを配る。

画面・記録・書き換えの知らせを返し、レビュー中のコメント・書きかけ・まとめて送る・設定の既定の書き換え・設定の再読み込みを受け付ける。
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit

from builder import PREVIEW_DIR, assemble_template, read_records
from comments import (
    ReviewComment,
    SentComment,
    add_comment,
    delete_comment,
    list_review,
    save_draft,
    send_comments,
    update_comment,
)
from errors import (
    CommentConflictError,
    CommentInvalidError,
    CommentNotFoundError,
    ItemNotFoundError,
    MindmapError,
    SchemaMismatchError,
    ServeFailedError,
    SettingsInvalidError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from history import touch_opened
from kinds import BODY_DIR, KINDS, SETTINGS_FILE, records_root
from locations import location_to_dict
from settings_update import update_display
from store import (
    CHANGES_FILE,
    NowFn,
    build_mismatch_error,
    check_settings,
    load_workspace,
    now_utc,
    workspace_lock,
)
from submissions import SUBMISSIONS_FILE

logger = logging.getLogger(__name__)

# 待ち受けのアドレス（ポートは `config.yaml` の `preview.port` があればそれ、無ければ 0 で OS に選ばせる）
LISTEN_HOST = "127.0.0.1"

# 許可するホスト名・起動時のフック・終了時のフックを読む環境変数の名前
ALLOWED_HOSTS_ENV = "MINDSTELLA_ALLOWED_HOSTS"
START_HOOK_ENV = "MINDSTELLA_PREVIEW_START_HOOK"
STOP_HOOK_ENV = "MINDSTELLA_PREVIEW_STOP_HOOK"

# `Origin` で許可するホスト名を受けるスキーム
ORIGIN_SCHEMES = ("https", "http")

# 書き換えの印を作り直す間隔（秒）
POLL_INTERVAL_SEC = 0.25

# 知らせが無いままこの秒数が過ぎたら保つための行を送る
KEEPALIVE_SEC = 15

# 書き込む要求の本文を読む上限（バイト）。`Content-Length` がこれを超えたら読まずに 400 にする
MAX_REQUEST_BYTES = 131072

# レビュー中のコメント・まとめて送る・書きかけのパス
COMMENTS_PATH = "/api/comments"
SEND_PATH = "/api/comments/send"
DRAFTS_PATH = "/api/drafts"

# 前回開いた日時のパス
OPENED_PATH = "/api/opened"

# 配信が画面を返すパス。`/` はここへ送り直し、`PreviewServer.url` はこのパスで終わる
PAGE_PATH = "/mindstella.html"

# 設定の既定の書き換えと、設定の再読み込みのパス
CONFIG_DISPLAY_PATH = "/api/config/display"
CONFIG_RELOAD_PATH = "/api/config/reload"

# JSON・HTML・問題の応答の `Content-Type`
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
PROBLEM_TYPE = "application/problem+json; charset=utf-8"

# 書き込む要求が持つべきメディアタイプ
REQUEST_JSON_TYPE = "application/json"

# 書き換えの知らせの応答の `Content-Type`
EVENT_STREAM_TYPE = "text/event-stream"


class SettingsHolder:
    """1 つの配信が持つ、最後に検査に通った `config.yaml` の中身と、再読み込みの回数。"""

    def __init__(self, settings: dict[str, Any]) -> None:
        """初めの設定を受け取り、回数を 0 にする。"""
        self._settings = settings
        # 再読み込みで差し替えた回数。書き換えの印に混ぜ、ファイルが変わらない再読み込みでも知らせる
        self._revision = 0
        # 要求ごとのスレッドから触るため、触る間だけ取る鍵
        self._guard = threading.Lock()

    def current(self) -> dict[str, Any]:
        """最後に検査に通った設定を返す。"""
        with self._guard:
            return self._settings

    def accept(self, settings: dict[str, Any]) -> None:
        """記録の取得が検査に通した設定に差し替える（回数は進めない）。"""
        with self._guard:
            self._settings = settings

    def reload(self, settings: dict[str, Any]) -> None:
        """再読み込みで設定を差し替え、回数を 1 進める。"""
        with self._guard:
            self._settings = settings
            self._revision += 1

    def revision(self) -> int:
        """再読み込みの回数を返す。"""
        with self._guard:
            return self._revision


@dataclass(frozen=True, slots=True, kw_only=True)
class ServeContext:
    """要求の受け口が使う、配っているワークスペースと待ち受けの値。"""

    root: Path
    port: int
    # プロセスの中の書き換えの鍵
    write_lock: threading.Lock
    # 最後に検査に通った設定
    settings: SettingsHolder
    # 雛形のフォルダ
    preview_dir: Path = PREVIEW_DIR
    # 許可するホスト名（`check_host`・`check_origin` に渡す）
    allowed_hosts: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalAccess:
    """環境変数から読んだ、許可するホスト名と起動時・終了時のフック。どれも無ければ今と同じ動きになる。"""

    # 許可するホスト名（小文字）
    allowed_hosts: frozenset[str] = frozenset()
    # 起動時のフックのコマンドと引数（空なら呼ばない）
    start_hook: tuple[str, ...] = ()
    # 終了時のフックのコマンドと引数（空なら呼ばない）
    stop_hook: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Response:
    """処理の関数が返す、書く前の応答。"""

    status: int
    content_type: str
    body: bytes
    # 送り直しの宛先（送り直す応答だけが持つ）
    location: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PreviewServer:
    """1 つのワークスペースの待ち受けと、それを動かすスレッド。"""

    root: Path
    # `http://127.0.0.1:{ポート}/mindstella.html`
    url: str
    httpd: ThreadingHTTPServer
    thread: threading.Thread
    # 待ち受けのポート（フックへ渡す）
    port: int

    def stop(self) -> None:
        """待ち受けを止めて閉じる（つながっている書き換えの知らせは、書き込みが失敗して終わる）。"""
        self.httpd.shutdown()
        self.httpd.server_close()


class PreviewRegistry:
    """このプロセスが立てた配信をワークスペースの絶対パスごとに 1 つ持ち、終わるときに全て止める。"""

    def __init__(self, write_lock: threading.Lock, *, external: ExternalAccess | None = None) -> None:
        """ツールと共有する書き換えの鍵と外から見る設定（無ければ空）を受け取り、空の台帳を作る。"""
        self._servers: dict[Path, PreviewServer] = {}
        self._write_lock = write_lock
        self._external = ExternalAccess() if external is None else external
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
            # 立てる前に config.yaml を検査する（合わなければ配信を立てない）
            settings, problems = check_settings(key)
            if problems:
                raise build_mismatch_error(problems)
            preview = start_preview_server(
                key,
                write_lock=self._write_lock,
                settings=settings,
                port=settings.get("preview", {}).get("port", 0),
                allowed_hosts=self._external.allowed_hosts,
            )
            self._servers[key] = preview
            logger.info("配信を立てた: %s %s", key, preview.url)
            # 立てた直後に起動時のフックを呼ぶ
            if self._external.start_hook:
                run_hook(self._external.start_hook, preview.port, key.name)
            return preview.url, True

    def url_of(self, root: Path) -> str | None:
        """そのワークスペースを配っていれば画面の URL を、配っていなければ None を返す（配信は立てない）。"""
        with self._guard:
            preview = self._servers.get(root.resolve())
        return None if preview is None else preview.url

    def stop_all(self) -> None:
        """立てた配信ごとに終了時のフックを呼んでから全て止め、台帳を空にする。2 回呼んでも 2 回目は何もしない。"""
        with self._guard:
            # 配信を止める前に、終了時のフックを全て立てる
            if self._external.stop_hook:
                for preview in self._servers.values():
                    run_hook(self._external.stop_hook, preview.port, preview.root.name)
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
        """`Host` を確かめ、`/`・`/mindstella.html`・`/api/records`・`/api/events`・`/api/comments` を処理の関数へ振り分ける。"""
        context = self.context
        # 接続先が合わない
        if not check_host(
            self.headers.get("Host"), context.port, allowed_hosts=context.allowed_hosts
        ):
            self._reply(problem_response(HTTPStatus.FORBIDDEN, "接続先が合いません"))
            return
        path = urlsplit(self.path).path
        if path == "/":
            # 画面のパスへ送り直す
            self._reply(redirect_response(PAGE_PATH))
        elif path == PAGE_PATH:
            self._reply(index_response(context.preview_dir))
        elif path == "/api/records":
            self._reply(records_response(context))
        elif path == "/api/events":
            self._stream(context)
        elif path == COMMENTS_PATH:
            self._reply(comments_response(context.root))
        else:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    def do_POST(self) -> None:
        """前回開いた日時を返す・レビュー中のコメントを溜める・まとめて送る・設定の再読み込みを処理の関数へ渡す。"""
        path = self._checked_path()
        if path == OPENED_PATH:
            # 本文を読まずに、前回開いた日時を返して書き換える
            self._reply(opened_response(self.context))
        elif path == CONFIG_RELOAD_PATH:
            # 本文を読まずに、設定を読み直す
            self._reply(reload_response(self.context, origin=self.headers.get("Origin")))
        elif path == COMMENTS_PATH:
            self._write(
                lambda root, data: _added_body(*add_comment(root, data)), HTTPStatus.CREATED
            )
        elif path == SEND_PATH:
            self._write(
                lambda root, data: _sent_body(*send_comments(root, data)), HTTPStatus.CREATED
            )
        elif path is not None:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    def do_PUT(self) -> None:
        """書きかけを保つ・設定の既定を書き換える要求を受け付けの関数へ渡す。"""
        path = self._checked_path()
        if path == DRAFTS_PATH:
            self._write(_saved_draft, HTTPStatus.NO_CONTENT)
        elif path == CONFIG_DISPLAY_PATH:
            self._write(update_display, HTTPStatus.OK)
        elif path is not None:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    def do_PATCH(self) -> None:
        """レビュー中のコメント 1 件を書き換える要求を受け付けの関数へ渡す。"""
        path = self._checked_path()
        comment_id = _comment_id_of(path)
        if comment_id is not None:
            self._write(
                lambda root, data: _updated_body(update_comment(root, comment_id, data)),
                HTTPStatus.OK,
            )
        elif path is not None:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    def do_DELETE(self) -> None:
        """レビュー中のコメント 1 件を消す要求を受け付けの関数へ渡す。"""
        path = self._checked_path()
        comment_id = _comment_id_of(path)
        if comment_id is not None:
            self._reply(
                delete_response(
                    self.context, origin=self.headers.get("Origin"), comment_id=comment_id
                )
            )
        elif path is not None:
            self._reply(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """標準の要求の記録を `logging` の `DEBUG` に回す（標準エラーへの直接の書き込みをやめる）。"""
        logger.debug("受けた要求: %s", format % args)

    def _checked_path(self) -> str | None:
        """`Host` を確かめて要求のパスを返す。接続先が合わなければ 403 を書いて None を返す。"""
        # 接続先が合わない
        if not check_host(
            self.headers.get("Host"), self.context.port, allowed_hosts=self.context.allowed_hosts
        ):
            self._reply(problem_response(HTTPStatus.FORBIDDEN, "接続先が合いません"))
            return None
        return urlsplit(self.path).path

    def _write(
        self, handle: Callable[[Path, dict[str, Any]], dict[str, Any] | None], status: int
    ) -> None:
        """本文の長さを確かめて読み、書き込む受け付けの関数へ渡して応答を書く。"""
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
        self._reply(
            write_response(
                self.context,
                content_type=self.headers.get("Content-Type"),
                origin=self.headers.get("Origin"),
                body=self.rfile.read(length),
                handle=handle,
                status=status,
            )
        )

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
        # 送り直す応答は宛先を持つ
        if response.location is not None:
            self.send_header("Location", response.location)
        self.end_headers()
        # 204 は本文を持たない
        if response.status != HTTPStatus.NO_CONTENT:
            self.wfile.write(response.body)

    def _stream(self, context: ServeContext) -> None:
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
            stream_events(
                context.root,
                _write,
                # 再読み込みはファイルが変わらなくても知らせるため、回数を印に混ぜる
                signature=lambda root: (
                    f"{workspace_signature(root)}|settings:{context.settings.revision()}"
                ),
            )
        except (BrokenPipeError, ConnectionResetError):
            # 見出しを送る前に画面が閉じた
            return


def start_preview_server(
    root: Path,
    *,
    write_lock: threading.Lock,
    settings: dict[str, Any],
    port: int = 0,
    allowed_hosts: frozenset[str] = frozenset(),
) -> PreviewServer:
    """`LISTEN_HOST` の port（0 なら空きポート）で待ち受け、デーモンのスレッドで動かし始める。settings は立てる前に検査に通った設定。"""
    try:
        httpd = ThreadingHTTPServer((LISTEN_HOST, port), PreviewHandler)
    except OSError as error:
        raise ServeFailedError(
            f"プレビューの配信を立てられません（ポート {port}）: {error}"
        ) from error
    httpd.daemon_threads = True
    bound_port = httpd.server_address[1]
    # 要求の受け口が `self.server.context` で引けるように、待ち受けに持たせる
    context = ServeContext(
        root=root,
        port=bound_port,
        write_lock=write_lock,
        settings=SettingsHolder(settings),
        allowed_hosts=allowed_hosts,
    )
    setattr(httpd, "context", context)  # noqa: B010
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return PreviewServer(
        root=root,
        url=f"http://{LISTEN_HOST}:{bound_port}{PAGE_PATH}",
        httpd=httpd,
        thread=thread,
        port=bound_port,
    )


def host_part(value: str) -> str:
    """`Host` か `Origin` の `netloc` から、末尾の `:{数字}` を外して小文字にしたホスト名を返す。"""
    head, separator, tail = value.rpartition(":")
    # 最後の `:` より後ろが全て数字: ポートを外す
    if separator and tail.isdigit():
        value = head
    return value.lower()


def check_host(host: str | None, port: int, *, allowed_hosts: frozenset[str]) -> bool:
    """`Host` が `127.0.0.1:{ポート}`・`localhost:{ポート}` か、ポートを外したホスト名が許可するホスト名かを返す。"""
    # 無い: 合わない
    if host is None:
        return False
    if host.lower() in {f"{LISTEN_HOST}:{port}", f"localhost:{port}"}:
        return True
    return host_part(host) in allowed_hosts


def check_origin(origin: str | None, port: int, *, allowed_hosts: frozenset[str]) -> bool:
    """`Origin` が無いか、配信の URL と同じか、許可するホスト名の https / http かを返す。"""
    # 無い（同じ送り元からの要求など）: 通す
    if origin is None:
        return True
    if origin in {f"http://{LISTEN_HOST}:{port}", f"http://localhost:{port}"}:
        return True
    try:
        parts = urlsplit(origin)
    except ValueError:
        # URL として分けられない送り元は合わない
        return False
    return parts.scheme in ORIGIN_SCHEMES and host_part(parts.netloc) in allowed_hosts


def load_external_access(environ: Mapping[str, str]) -> ExternalAccess:
    """環境変数から許可するホスト名とフックを読み、`ExternalAccess` を返す。"""
    allowed: set[str] = set()
    for element in environ.get(ALLOWED_HOSTS_ENV, "").split(","):
        name = element.strip().lower()
        # 空の要素は捨てる
        if not name:
            continue
        # スキーム・ポート・パスを含む要素は、ホスト名として使えない
        if ":" in name or "/" in name:
            logger.warning("許可するホスト名に使えない値を外した: %s", name)
            continue
        allowed.add(name)
    return ExternalAccess(
        allowed_hosts=frozenset(allowed),
        start_hook=_split_hook(environ, START_HOOK_ENV),
        stop_hook=_split_hook(environ, STOP_HOOK_ENV),
    )


def _split_hook(environ: Mapping[str, str], key: str) -> tuple[str, ...]:
    """環境変数 key のフックのコマンドをシェルの書き方で分ける。分けられなければ空にする。"""
    try:
        return tuple(shlex.split(environ.get(key, "")))
    except ValueError as error:
        logger.warning("フックのコマンドを分けられない: %s（%s）", key, error)
        return ()


def run_hook(command: tuple[str, ...], port: int, name: str) -> bool:
    """フックのコマンドの末尾にポートとワークスペースの名前を足し、新しいセッションで立てて終わりを待たずに返す。"""
    try:
        subprocess.Popen(
            [*command, str(port), name],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        logger.warning("フックを立てられない: %s（%s）", command, error)
        return False
    return True


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


def redirect_response(location: str) -> Response:
    """本文を持たない 302 で、location へ送り直す応答を作る。"""
    return Response(status=HTTPStatus.FOUND, content_type=HTML_TYPE, body=b"", location=location)


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
    context: ServeContext, read: Callable[..., dict[str, Any]] = read_records
) -> Response:
    """ワークスペースをその場で読んだ記録の JSON を返す。config.yaml が検査に通れば最後に通った設定を差し替え、通らなければ最後に通った設定で返す。"""
    try:
        data = read(context.root, last_settings=context.settings.current())
    except SchemaMismatchError as error:
        # 読めない・スキーマに合わない: 合わない箇所の行を detail にする
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join(error.lines))
    except WorkspaceNotFoundError as error:
        # 配っている間に config.yaml が無くなった
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
    # config.yaml が検査に通った: 最後に通った設定として控える
    if data.get("settings_problem") is None:
        context.settings.accept(data["settings"])
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )


def opened_response(context: ServeContext, now: NowFn = now_utc) -> Response:
    """前回開いた日時を返し、今の日時に書き換える（記録のロックは取らない）。"""
    opened = now()
    try:
        previous = touch_opened(context.root, opened)
    except WriteFailedError as error:
        # 前回開いた日時を書けない: 画面はタブを開いた日時を範囲の始まりにする
        return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps({"previous": previous, "opened": opened}, ensure_ascii=False).encode(
            "utf-8"
        ),
    )


def reload_response(context: ServeContext, *, origin: str | None) -> Response:
    """config.yaml を検査し、通れば最後に検査に通った設定を差し替えて知らせ、通らなければ違う箇所を返す。"""
    # 別のサイトからの要求
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        settings, problems = check_settings(context.root)
    except WorkspaceNotFoundError as error:
        return error_response(error)
    # 検査に通らない: 最後に通った設定のまま、合わない箇所を返す
    if problems:
        lines = [f"{problem.file}: {problem.key}: {problem.detail}" for problem in problems]
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join(lines))
    # 通った: 差し替えて回数を進める（書き換えの印が変わり、開いている画面へ知らせが届く）
    context.settings.reload(settings)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps({"settings": settings}, ensure_ascii=False).encode("utf-8"),
    )


def workspace_signature(root: Path) -> str:
    """見ているファイルの名前・更新日時（ナノ秒）・大きさをつないだ、書き換えの印を返す。"""
    # 前回開いた日時（`.mindstella-opened`）は、タブが開くたびに書き換わるので見ない
    names = [SETTINGS_FILE, *(spec.file for spec in KINDS.values()), SUBMISSIONS_FILE, CHANGES_FILE]
    # 本文の Markdown（`.mindstella/docs/` の直下）も見る
    records = records_root(root)
    body_dir = records / BODY_DIR
    if body_dir.is_dir():
        names.extend(f"{BODY_DIR}/{path.name}" for path in body_dir.glob("*.md"))
    parts: list[str] = []
    for name in sorted(names):
        try:
            stat = (records / name).stat()
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


def comments_response(root: Path) -> Response:
    """レビュー中のコメントと書きかけをその場で読んだ JSON を返す。"""
    try:
        data = list_review(load_workspace(root))
    except (SchemaMismatchError, WorkspaceNotFoundError) as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )


def write_response(
    context: ServeContext,
    *,
    content_type: str | None,
    origin: str | None,
    body: bytes,
    handle: Callable[[Path, dict[str, Any]], dict[str, Any] | None],
    status: int,
) -> Response:
    """本文の形と送り元を確かめ、書き換えの鍵を取って渡した処理を呼び、結果の応答を返す。"""
    media_type = (content_type or "").split(";")[0].strip().lower()
    # JSON でない
    if media_type != REQUEST_JSON_TYPE:
        return problem_response(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE, f"{REQUEST_JSON_TYPE} で送ってください"
        )
    # 別のサイトからの書き込み
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        data = None
    # JSON として読めないか、オブジェクトでない
    if not isinstance(data, dict):
        return problem_response(
            HTTPStatus.BAD_REQUEST, "本文は JSON のオブジェクトで送ってください"
        )
    try:
        with workspace_lock(context.root, context.write_lock):
            result = handle(context.root, data)
    except MindmapError as error:
        return error_response(error)
    return Response(
        status=status,
        content_type=JSON_TYPE,
        body=b""
        if status == HTTPStatus.NO_CONTENT
        else json.dumps(result, ensure_ascii=False).encode("utf-8"),
    )


def delete_response(context: ServeContext, *, origin: str | None, comment_id: str) -> Response:
    """送り元を確かめ、書き換えの鍵を取ってコメントを消し、消した中身を返す。"""
    # 別のサイトからの書き込み
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        with workspace_lock(context.root, context.write_lock):
            deleted, count = delete_comment(context.root, comment_id)
    except MindmapError as error:
        return error_response(error)
    body = {
        "id": deleted.id,
        "target": deleted.target,
        "loc": None if deleted.loc is None else location_to_dict(deleted.loc),
        "body": deleted.body,
        "created": deleted.created,
        "count": count,
    }
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
    )


def error_response(error: MindmapError) -> Response:
    """ツールのエラーの種類からステータスコードを決めて問題の応答にする。"""
    detail = str(error)
    if isinstance(error, (CommentInvalidError, SettingsInvalidError)):
        return problem_response(HTTPStatus.BAD_REQUEST, detail)
    if isinstance(error, (ItemNotFoundError, CommentNotFoundError)):
        return problem_response(HTTPStatus.NOT_FOUND, detail)
    if isinstance(error, CommentConflictError):
        response = problem_response(HTTPStatus.CONFLICT, detail)
        # まとめて送るでは、合わないコメントを全て返す
        if error.stale:
            problem = json.loads(response.body)
            problem["stale"] = [{"id": item, "reason": reason} for item, reason in error.stale]
            return Response(
                status=response.status,
                content_type=PROBLEM_TYPE,
                body=json.dumps(problem, ensure_ascii=False).encode("utf-8"),
            )
        return response
    if isinstance(error, (WorkspaceNotFoundError, SchemaMismatchError)):
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join([detail, *error.lines]))
    # 書き込めなかった・渡された種類のないエラー
    if not isinstance(error, WriteFailedError):
        logger.error("渡された種類のないエラー: %s %s", type(error).__name__, detail)  # noqa: TRY400
    return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, detail)


def _added_body(comment: ReviewComment, count: int) -> dict[str, Any]:
    """溜めたコメントの応答の本文を作る。"""
    return {"id": comment.id, "created": comment.created, "count": count}


def _sent_body(sent: str, items: list[SentComment]) -> dict[str, Any]:
    """まとめて送った応答の本文を作る。"""
    return {"sent": sent, "items": [asdict(item) for item in items]}


def _updated_body(comment: ReviewComment) -> dict[str, Any]:
    """書き換えたコメントの応答の本文を作る。"""
    return {
        "id": comment.id,
        "body": comment.body,
        "loc": None if comment.loc is None else location_to_dict(comment.loc),
    }


def _saved_draft(root: Path, data: dict[str, Any]) -> None:
    """書きかけを保つ（応答の本文は持たない）。"""
    save_draft(root, data)


def _comment_id_of(path: str | None) -> str | None:
    """`/api/comments/{id}` のパスからコメントの ID を取り出す（送る口の `send` は ID でない）。"""
    prefix = f"{COMMENTS_PATH}/"
    # 別のパス
    if path is None or not path.startswith(prefix) or path == SEND_PATH:
        return None
    return unquote(path.removeprefix(prefix))
