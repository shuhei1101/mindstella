"""常駐サーバーの待ち受けの `/w/{workspace}` の下で、全てのワークスペースのプレビューを配る。

画面・記録・スレッド・書き換えの知らせを返し、レビュー中のコメント・下書き・まとめて送る・スレッドの状態の書き換え・設定の既定の書き換え・設定の再読み込みを受け付ける。
まとめて送った後は Claude Code へ入力する。
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import logging
import shlex
import subprocess
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, unquote, urlsplit

from starlette.concurrency import iterate_in_threadpool, run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse

from builder import PREVIEW_DIR, read_records
from change_detection import ChangeDetector, detector_of, workspace_id_of
from claude_input import InputTargets, Session
from comments import (
    ReviewComment,
    add_comment,
    delete_comment,
    list_review,
    save_draft,
    send_comments,
    send_now,
    update_comment,
)
from edits import add_edit, delete_edit, list_edits, save_edits
from errors import (
    ConcurrentWriteError,
    ArgumentError,
    CommentConflictError,
    CommentInvalidError,
    CommentNotFoundError,
    EditConflictError,
    EditInvalidError,
    EditNotFoundError,
    EditsBlockedError,
    ItemNotFoundError,
    MindmapError,
    SchemaMismatchError,
    WorkspaceIdConflictError,
    SettingsInvalidError,
    ThreadNotFoundError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from files_serve import (
    FILE_SECURITY_HEADERS,
    FILE_WRITE_CHUNK,
    FILES_DIR,
    FILES_PATH,
    FilePlan,
    plan_file,
    resolve_file,
)
from history import head_until_seq, load_changes, set_confirmed, touch_opened
from kinds import BODY_REF_PREFIX, KINDS, SETTINGS_FILE, body_root, records_root
from locations import location_to_dict
from settings_update import update_display
from store import (
    CHANGES_FILE,
    EDITS_FILE,
    NowFn,
    build_mismatch_error,
    check_settings,
    load_workspace,
    now_utc,
    require_workspace,
    workspace_lock,
)
from transcriber import (
    FAILED_DETAIL,
    UNAVAILABLE_DETAILS,
    Transcriber,
    TranscriberStoppedError,
    TranscriberUnsupportedError,
    TranscriptionFailedError,
    TranscriptionTimeoutError,
    UnavailableReason,
    check_availability,
)
from threads import (
    THREADS_FILE,
    SentPost,
    load_threads,
    mark_seen,
    set_thread_status,
    threads_for_preview,
)

logger = logging.getLogger(__name__)

# 常駐サーバーの待ち受けのアドレス（画面の URL に使う）
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

# POST /api/transcriptions の本文を読む上限（非機能要件「録音の大きさの上限」）
MAX_AUDIO_BYTES = 80_000_000

# 受ける音声の Content-Type の頭
AUDIO_TYPE_PREFIX = "audio/"

# GET で文字起こしの可否を返すパス
TRANSCRIPTION_PATH = "/api/transcription"

# POST で音声を受けて文字起こしするパス
TRANSCRIPTIONS_PATH = "/api/transcriptions"

# POST で書き込み 1 件をすぐスレッドへ送るパス
SEND_NOW_PATH = "/api/comments/send-now"

# config.yaml に transcription.action が無いときの文字起こし後の挙動
DEFAULT_TRANSCRIPTION_ACTION = "review"

# レビュー中のコメント・まとめて送る・下書きのパス
COMMENTS_PATH = "/api/comments"
SEND_PATH = "/api/comments/send"
DRAFTS_PATH = "/api/drafts"

# スレッドの読み取りと、スレッド 1 件の状態の書き換え（`/api/threads/{id}`）のパス
THREADS_PATH = "/api/threads"

# スレッド 1 件の利用者の既読にする口（`/api/threads/{id}/seen`）の、`{id}` の後ろ
SEEN_SUFFIX = "/seen"

# 確認済みの付け外しのパスの頭（PUT `/api/items/{id}/confirmed`）と末尾
ITEMS_PATH = "/api/items"
CONFIRMED_SUFFIX = "/confirmed"

# 保存待ちの編集の読み取り・追加と、1 件の取り消し（`/api/edits/{id}`）のパス
EDITS_PATH = "/api/edits"

# 保存待ちの編集をまとめて保存するパス
EDITS_SAVE_PATH = "/api/edits/save"

# 記録の取得と書き換えの通知のパス
RECORDS_PATH = "/api/records"
EVENTS_PATH = "/api/events"

# 前回開いた日時のパス
OPENED_PATH = "/api/opened"

# 配信が画面を返すパス（ワークスペースのパスの頭より後ろ）。画面の URL はこのパスで終わる
PAGE_PATH = "/"

# 前の画面の URL のパス（`/w/{workspace}` より後ろ）。このパスと、`/spa/` で始まるパスは search を残して `PAGE_PATH` へ再送信する
OLD_PAGE_PATHS = ("/mindstella.html", "/spa")

# 画面のビルドの出力の資産を返すパスの頭
ASSETS_PATH = "/assets"

# 全てのワークスペースの画面と、画面が呼ぶ経路の頭（`/w/{workspace}`）
PREVIEW_PREFIX = "/w"

# プレビューのフォルダの中の、画面のビルドの出力のフォルダの名前
SPA_DIR = "spa"

# 設定の既定の書き換えと、設定の再読み込みのパス
CONFIG_DISPLAY_PATH = "/api/config/display"
CONFIG_RELOAD_PATH = "/api/config/reload"

# JSON・HTML・問題の応答の `Content-Type`
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
PROBLEM_TYPE = "application/problem+json; charset=utf-8"

# SPA の出力のファイルの拡張子ごとの `Content-Type`（表に無い拡張子は `application/octet-stream`）
SPA_TYPES = {
    ".html": HTML_TYPE,
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}

# 書き込む要求が持つべきメディアタイプ
REQUEST_JSON_TYPE = "application/json"

# 書き換えの知らせの応答の `Content-Type`
EVENT_STREAM_TYPE = "text/event-stream"

# 記録の応答の `ETag` に使う、本文の SHA-256 の先頭の文字数
ETAG_DIGEST_LENGTH = 32

# 弱い `ETag` の頭
WEAK_ETAG_PREFIX = "W/"


@dataclass(frozen=True, slots=True, kw_only=True)
class CachedRecords:
    """保持した記録の応答。"""

    # 圧縮する前の本文
    body: bytes
    # gzip で圧縮した本文
    gzip_body: bytes
    # 弱い `ETag`（`W/"{SHA-256 の先頭 32 文字}"`）
    etag: str


class RecordsCache:
    """1 つの配信が持つ、組み立てた記録の応答。常駐サーバーの再起動では持ち越さない。"""

    def __init__(self) -> None:
        """空の保持で始める。"""
        self._cached: CachedRecords | None = None
        # 捨てた回数。組み立てている間に捨てられた応答を保持しないために比べる
        self._generation = 0
        # 要求ごとのスレッドから触るため、触る間だけ取る鍵
        self._guard = threading.Lock()

    def get_or_build(self, build: Callable[[], dict[str, Any]]) -> CachedRecords:
        """保持した応答があれば返却し、無ければ `build` で記録を読んで作り、保持して返却する。"""
        with self._guard:
            cached = self._cached
            generation = self._generation
        # 保持した応答がある: 読まずに返却する
        if cached is not None:
            return cached
        body = json.dumps(build(), ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()[:ETAG_DIGEST_LENGTH]
        built = CachedRecords(body=body, gzip_body=gzip.compress(body), etag=f'{WEAK_ETAG_PREFIX}"{digest}"')
        with self._guard:
            # 組み立てている間に捨てられていない: 保持する（捨てられていれば古い中身のため保持しない）
            if self._generation == generation:
                self._cached = built
        return built

    def discard(self) -> None:
        """保持した応答を捨て、次の要求で作り直させる。"""
        with self._guard:
            self._cached = None
            self._generation += 1


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
    # 常駐サーバーの待ち受けのポート（`check_host`・`check_origin` と画面の URL に使う）
    port: int
    # プロセスの中の書き換えの鍵
    write_lock: threading.Lock
    # 最後に検査に通った設定
    settings: SettingsHolder
    # 雛形のフォルダ
    preview_dir: Path = PREVIEW_DIR
    # 許可するホスト名（`check_host`・`check_origin` に渡す）
    allowed_hosts: frozenset[str] = frozenset()
    # ワークスペースごとの Claude Code への入力の宛先（None ならまとめて送った後に入力しない）
    input_targets: InputTargets | None = None
    # 文字起こしのインターフェース（None なら文字起こしの可否は stopped）
    transcriber: Transcriber | None = None
    # ワークスペースの ID（画面のパスに使う）
    workspace_id: str = ""
    # 組み立てた記録の応答
    records_cache: RecordsCache = field(default_factory=RecordsCache)


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
    # 既定（`Content-Type`・`Cache-Control: no-store`）に加える・上書きするヘッダー
    headers: dict[str, str] = field(default_factory=dict)


class PreviewRegistry:
    """このプロセスが配っているワークスペースを絶対パスごとに 1 つ（配信の文脈）持ち、ワークスペースの ID でも引けるようにする。待ち受けは持たない。"""

    def __init__(
        self,
        write_lock: threading.Lock,
        *,
        port: int,
        external: ExternalAccess | None = None,
        transcriber: Transcriber | None = None,
        input_targets: InputTargets | None = None,
        state_root: Path | None = None,
    ) -> None:
        """ツールと共有する書き換えの鍵と、常駐サーバーのポートと、外から見る設定（無ければ空）と文字起こしと入力の宛先の台帳と状態のフォルダを受け取り、空の台帳を作る。

        状態のフォルダを渡すと、配り始めるたびにそのワークスペースの変更の検知を始める。
        """
        self._servers: dict[Path, ServeContext] = {}
        self._by_id: dict[str, Path] = {}
        self._detectors: dict[Path, ChangeDetector] = {}
        self._state_root = state_root
        self._write_lock = write_lock
        self._port = port
        self._external = ExternalAccess() if external is None else external
        # ワークスペースごとの Claude Code への入力の宛先（配信の文脈へ渡す。配る前に受けたセッションも持つ）
        self._input_targets = InputTargets() if input_targets is None else input_targets
        # 文字起こしのインターフェース（配信の文脈へ渡す）
        self._transcriber = transcriber
        # 台帳を触る間だけ取る鍵（フックの中から同じスレッドで呼び直されても戻れるよう、再入できる鍵）
        self._guard = threading.RLock()

    def start(self, root: Path) -> tuple[str, bool]:
        """そのワークスペースを配り始め、画面の URL と今配り始めたかを返す。配っていればその URL を返す。

        同じ ID の別のフォルダを配っていて、そのフォルダに同じ ID の記録が無ければ（フォルダを移した）、
        前のフォルダの配信をやめてから root を配る。
        """
        key = root.resolve()
        with self._guard:
            moved = self._take_moved(key)
        # 前のフォルダの変更の検知と終了時のフックは、鍵の外で止める・呼ぶ
        if moved is not None:
            self._release(*moved)
        with self._guard:
            existing = self._servers.get(key)
            # 配っている: その URL を返す（検査しない・フックを呼ばない）
            if existing is not None:
                return self._url(existing.workspace_id), False
            workspace_id = workspace_id_of(key)
            served = self._by_id.get(workspace_id)
            # 同じ ID の別のフォルダを配っている: 配らない
            if served is not None:
                raise WorkspaceIdConflictError(
                    f"ワークスペースの ID が配っている別のフォルダと重なります: {workspace_id}（{served}）"
                )
            # 配る前に config.yaml を検査する（合わなければ配らない）
            settings, problems = check_settings(key)
            if problems:
                raise build_mismatch_error(problems)
            context = ServeContext(
                root=key,
                port=self._port,
                write_lock=self._write_lock,
                settings=SettingsHolder(settings),
                allowed_hosts=self._external.allowed_hosts,
                input_targets=self._input_targets,
                transcriber=self._transcriber,
                workspace_id=workspace_id,
            )
            self._servers[key] = context
            self._by_id[workspace_id] = key
            url = self._url(workspace_id)
            logger.info("ワークスペースを配り始めた: %s %s", key, url)
            # そのワークスペースの変更の検知を始める
            if self._state_root is not None:
                detector = ChangeDetector(
                    key,
                    self._state_root,
                    self._write_lock,
                    self._input_targets,
                    on_changed=context.records_cache.discard,
                )
                detector.start()
                self._detectors[key] = detector
            # 配り始めた直後に起動時のフックを呼ぶ
            if self._external.start_hook:
                run_hook(self._external.start_hook, self._port, key.name, page_path(workspace_id))
            return url, True

    def _take_moved(self, key: Path) -> tuple[ServeContext, ChangeDetector | None] | None:
        """key と同じ ID の別のフォルダを配っていて、そのフォルダに同じ ID の記録が無ければ、台帳から外して返す（鍵を取って呼ぶ）。"""
        if key in self._servers:
            return None
        workspace_id = workspace_id_of(key)
        served = self._by_id.get(workspace_id)
        # 同じ ID の記録が前のフォルダに残っている（コピー・クローン）か、配っていない: 外さない
        if served is None or _has_record_of(served, workspace_id):
            return None
        del self._by_id[workspace_id]
        logger.info("移す前のフォルダを配るのをやめる: %s → %s", served, key)
        return self._servers.pop(served), self._detectors.pop(served, None)

    def _release(self, context: ServeContext, detector: ChangeDetector | None) -> None:
        """台帳から外したワークスペースの変更の検知を止め、終了時のフックを呼ぶ（鍵の外で呼ぶ）。"""
        if detector is not None:
            detector.stop()
        if self._external.stop_hook:
            run_hook(
                self._external.stop_hook,
                self._port,
                context.root.name,
                page_path(context.workspace_id),
            )

    def context_of(self, workspace_id: str) -> ServeContext | None:
        """ワークスペースの ID で配信の文脈を引く。配っていなければ None。"""
        with self._guard:
            root = self._by_id.get(workspace_id)
            return None if root is None else self._servers.get(root)

    def url_of(self, root: Path) -> str | None:
        """そのワークスペースを配っていれば画面の URL を、配っていなければ None を返す（配り始めない）。"""
        with self._guard:
            context = self._servers.get(root.resolve())
        return None if context is None else self._url(context.workspace_id)

    def listing(self) -> list[dict[str, Any]]:
        """配っているワークスペースと画面の URL を、ワークスペースの絶対パスの昇順で返す。"""
        with self._guard:
            servers = sorted(self._servers.items())
        return [{"workspace": str(root), "url": self._url(context.workspace_id)} for root, context in servers]

    def discard_records(self, root: Path) -> None:
        """そのワークスペースを配っていれば、保持した記録の応答を捨てる（配っていなければ何もしない）。"""
        with self._guard:
            context = self._servers.get(root.resolve())
        if context is not None:
            context.records_cache.discard()

    def remember_session(self, root: Path, session: Session) -> None:
        """そのワークスペースの Claude Code への入力の宛先を、ツールを呼んだセッションにする。"""
        self._input_targets.remember(root, session)

    def stop_workspace(self, workspace_id: str) -> None:
        """ワークスペースの ID が一致するワークスペースを配るのをやめ、変更の検知を止める。無ければ何もしない。"""
        # 鍵の中では台帳から外して手元に取るだけにし、フックと停止は鍵の外で呼ぶ
        with self._guard:
            root = self._by_id.pop(workspace_id, None)
            context = None if root is None else self._servers.pop(root, None)
            detector = None if root is None else self._detectors.pop(root, None)
        if detector is not None:
            detector.stop()
        if context is not None and self._external.stop_hook:
            run_hook(self._external.stop_hook, self._port, context.root.name, page_path(workspace_id))

    def stop_all(self) -> None:
        """配っているワークスペースごとに終了時のフックを呼び、台帳を空にする。2 回呼んでも 2 回目は何もしない。"""
        # 鍵の中では台帳を空にして手元に取るだけにし、フックと停止は鍵の外で呼ぶ
        with self._guard:
            taken = list(self._servers.values())
            self._servers = {}
            self._by_id = {}
            detectors = list(self._detectors.values())
            self._detectors = {}
        for detector in detectors:
            detector.stop()
        if self._external.stop_hook:
            for context in taken:
                run_hook(
                    self._external.stop_hook,
                    self._port,
                    context.root.name,
                    page_path(context.workspace_id),
                )

    def _url(self, workspace_id: str) -> str:
        """ワークスペースの画面の URL を組み立てる。"""
        return f"http://{LISTEN_HOST}:{self._port}{page_path(workspace_id)}"


def _has_record_of(folder: Path, workspace_id: str) -> bool:
    """folder に workspace_id の記録（`.mindstella/config.yaml`）が残っていれば真を返す。"""
    return (records_root(folder) / SETTINGS_FILE).is_file() and workspace_id_of(folder) == workspace_id


def page_path(workspace_id: str) -> str:
    """ワークスペースの画面のパス（`/w/{パーセントエンコードした ID}/`）を返す。"""
    return f"{PREVIEW_PREFIX}/{quote(workspace_id, safe='')}{PAGE_PATH}"


class PreviewEndpoint:
    """常駐サーバーの経路 `/w/{workspace}` と `/w/{workspace}/{rest:path}` に登録する Starlette のエンドポイント。

    ワークスペースの ID で配信の文脈を引き、メソッドとパスで処理の関数へ振り分け、返った応答を Starlette の応答にする。
    同期の処理の関数はスレッドで呼ぶ。
    """

    def __init__(self, registry: PreviewRegistry) -> None:
        """配信の台帳を受け取る。"""
        self._registry = registry

    async def __call__(self, request: Request) -> StarletteResponse:
        """配信の文脈を引き、`Host` を確かめ、メソッドとパスで処理の関数へ振り分ける。"""
        workspace = str(request.path_params["workspace"])
        context = self._registry.context_of(workspace)
        # 配っていないワークスペース
        if context is None:
            return _to_starlette(problem_response(HTTPStatus.NOT_FOUND, "配っていないワークスペースです"))
        # 接続先が合わない
        if not check_host(request.headers.get("host"), context.port, allowed_hosts=context.allowed_hosts):
            return _to_starlette(problem_response(HTTPStatus.FORBIDDEN, "接続先が合いません"))
        base = f"{PREVIEW_PREFIX}/{quote(workspace, safe='')}"
        rest = request.path_params.get("rest")
        # `/w/{workspace}`: 末尾に `/` を付けて送り直す
        if rest is None:
            return _to_starlette(redirect_response(_with_search(f"{base}{PAGE_PATH}", request)))
        path = f"/{rest}"
        handlers = {
            "GET": self._get,
            "POST": self._post,
            "PUT": self._put,
            "PATCH": self._patch,
            "DELETE": self._delete,
        }
        handler = handlers.get(request.method)
        if handler is None:
            return _to_starlette(problem_response(HTTPStatus.METHOD_NOT_ALLOWED, f"メソッドを受けません: {request.method}"))
        response = await handler(request, context, path, base)
        # 画面の保存・書き込み: 書いたファイルを次の記録の取得で読み直させる
        if request.method != "GET":
            context.records_cache.discard()
        return response

    async def _get(self, request: Request, context: ServeContext, path: str, base: str) -> StarletteResponse:
        """画面・資産・ファイル・記録・書き換えの通知・コメント・スレッド・編集・文字起こしの可否へ振り分ける。"""
        origin = request.headers.get("origin")
        if path == PAGE_PATH or path.startswith(f"{ASSETS_PATH}/"):
            return await _call(lambda: spa_response(context.preview_dir / SPA_DIR, path))
        # 前の画面の URL: search を残して画面へ送り直す
        if path in OLD_PAGE_PATHS or path.startswith(f"{OLD_PAGE_PATHS[1]}/"):
            return _to_starlette(redirect_response(_with_search(f"{base}{PAGE_PATH}", request)))
        if path.startswith(FILES_PATH):
            return await self._send_file(context, path.removeprefix(FILES_PATH), request.headers.get("range"))
        if path == EVENTS_PATH:
            return self._stream(request, context)
        simple = {
            RECORDS_PATH: lambda: records_response(
                context,
                if_none_match=request.headers.get("if-none-match"),
                accept_encoding=request.headers.get("accept-encoding"),
            ),
            COMMENTS_PATH: lambda: comments_response(context.root),
            THREADS_PATH: lambda: threads_response(context.root),
            EDITS_PATH: lambda: edits_response(context.root),
            TRANSCRIPTION_PATH: lambda: transcription_response(context, origin=origin),
        }
        call = simple.get(path)
        if call is None:
            return _to_starlette(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))
        return await _call(call)

    async def _post(self, request: Request, context: ServeContext, path: str, base: str) -> StarletteResponse:
        """前回開いた日時・設定の再読み込み・保存待ちの編集・既読・コメント・まとめて送信する・すぐ送信する・文字起こしへ振り分ける。"""
        origin = request.headers.get("origin")
        seen_thread_id = _seen_thread_id_of(path)
        if path == OPENED_PATH:
            return await _call(lambda: opened_response(context))
        if path == CONFIG_RELOAD_PATH:
            return await _call(lambda: reload_response(context, origin=origin))
        if path == EDITS_SAVE_PATH:
            return await _call(lambda: edits_save_response(context, origin=origin))
        if path == EDITS_PATH:
            return await _write(request, context, lambda root, data: _edit_added(*add_edit(root, data)), HTTPStatus.CREATED)
        if seen_thread_id is not None:
            return await _call(lambda: seen_response(context, seen_thread_id, origin=origin))
        if path == COMMENTS_PATH:
            return await _write(
                request, context, lambda root, data: _added_body(*add_comment(root, data)), HTTPStatus.CREATED
            )
        if path == SEND_PATH:
            # 書き換えの鍵を外した後に、足した書き込みを Claude Code へ入力する
            return await _write(
                request,
                context,
                lambda root, data: _sent_body(*send_comments(root, data)),
                HTTPStatus.CREATED,
                after=lambda body: _entered_body(context, body),
            )
        if path == SEND_NOW_PATH:
            # まとめて送信するのと同じく、鍵を外した後に Claude Code へ入力する（件数は 1）
            return await _write(
                request,
                context,
                lambda root, data: _sent_now_body(*send_now(root, data)),
                HTTPStatus.CREATED,
                after=lambda body: _entered_body(context, body),
            )
        if path == TRANSCRIPTIONS_PATH:
            return await self._transcribe(request, context)
        return _to_starlette(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    async def _put(self, request: Request, context: ServeContext, path: str, base: str) -> StarletteResponse:
        """下書き・設定の既定・確認済みへ振り分ける。"""
        if path == DRAFTS_PATH:
            return await _write(request, context, _saved_draft, HTTPStatus.NO_CONTENT)
        if path == CONFIG_DISPLAY_PATH:
            return await _write(request, context, update_display, HTTPStatus.OK)
        item_id = _confirmed_item_id_of(path)
        if item_id is not None:
            return await _write(
                request, context, lambda root, data: set_confirmed(root, item_id, data), HTTPStatus.OK
            )
        return _to_starlette(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    async def _patch(self, request: Request, context: ServeContext, path: str, base: str) -> StarletteResponse:
        """レビュー中のコメント 1 件の書き換えとスレッド 1 件の状態の書き換えへ振り分ける。"""
        comment_id = _comment_id_of(path)
        thread_id = _thread_id_of(path)
        if comment_id is not None:
            return await _write(
                request,
                context,
                lambda root, data: _updated_body(update_comment(root, comment_id, data)),
                HTTPStatus.OK,
            )
        if thread_id is not None:
            return await _write(
                request, context, lambda root, data: patch_thread_status(root, thread_id, data), HTTPStatus.OK
            )
        return _to_starlette(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    async def _delete(self, request: Request, context: ServeContext, path: str, base: str) -> StarletteResponse:
        """レビュー中のコメント 1 件と保存待ちの編集 1 件の削除へ振り分ける。"""
        origin = request.headers.get("origin")
        comment_id = _comment_id_of(path)
        edit_id = _edit_id_of(path)
        if comment_id is not None:
            return await _call(lambda: delete_response(context, origin=origin, comment_id=comment_id))
        if edit_id is not None:
            return await _call(lambda: edit_delete_response(context, origin=origin, edit_id=edit_id))
        return _to_starlette(problem_response(HTTPStatus.NOT_FOUND, f"パスがありません: {path}"))

    async def _send_file(self, context: ServeContext, sub_path: str, range_header: str | None) -> StarletteResponse:
        """ワークスペースのファイルを解決し、200・206・416 で本文を分けて返す。解決できなければ 404。"""
        path = resolve_file(context.root / FILES_DIR, sub_path)
        # フォルダの外部・無い・フォルダは、パスを含めずに 404 にする
        if path is None:
            return _to_starlette(
                problem_response(HTTPStatus.NOT_FOUND, "ファイルがありません"), FILE_SECURITY_HEADERS
            )
        try:
            plan = plan_file(path, range_header)
        except OSError:
            # 解決した後に消された
            return _to_starlette(
                problem_response(HTTPStatus.NOT_FOUND, "ファイルがありません"), FILE_SECURITY_HEADERS
            )
        headers = {"Content-Type": plan.content_type, "Content-Length": str(plan.length)}
        headers.update(dict(plan.headers))
        return StreamingResponse(iterate_in_threadpool(_file_chunks(plan)), status_code=plan.status, headers=headers)

    def _stream(self, request: Request, context: ServeContext) -> StreamingResponse:
        """`text/event-stream` で、画面が閉じるまで書き換えを知らせ続ける。知らせの見張りは別のスレッドで動かす。"""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes] = asyncio.Queue()
        closed = threading.Event()

        def _write(chunk: bytes) -> None:
            """画面が閉じていれば書き出しをやめさせ、閉じていなければキューへ渡す。"""
            if closed.is_set():
                raise BrokenPipeError("画面が閉じました")
            loop.call_soon_threadsafe(queue.put_nowait, chunk)

        def _sleep(seconds: float) -> None:
            """次の見張りまで待つ。待つ間に画面が閉じたら書き出しをやめさせる。"""
            if closed.wait(seconds):
                raise BrokenPipeError("画面が閉じました")

        def _watch() -> None:
            """画面が閉じるまで書き換えを見張る。"""
            try:
                stream_events(
                    context.root,
                    _write,
                    sleep=_sleep,
                    # 再読み込みはファイルが変わらなくても知らせるため、回数を印に混ぜる
                    signature=lambda root: (
                        f"{workspace_signature(root)}|settings:{context.settings.revision()}"
                    ),
                    on_changed=context.records_cache.discard,
                )
            except (BrokenPipeError, ConnectionResetError):
                return

        watcher = threading.Thread(target=_watch, name=f"mindstella-events-{context.workspace_id}", daemon=True)
        watcher.start()

        async def _chunks() -> AsyncIterator[bytes]:
            """キューの片を順に返し、画面が閉じたら見張りを終わらせる。"""
            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(queue.get(), timeout=POLL_INTERVAL_SEC)
                    except TimeoutError:
                        if await request.is_disconnected():
                            return
                        continue
                    yield chunk
            finally:
                closed.set()

        # media_type で渡すと charset が付くため、ヘッダーで渡す
        return StreamingResponse(
            _chunks(), headers={"Content-Type": EVENT_STREAM_TYPE, "Cache-Control": "no-store"}
        )

    async def _transcribe(self, request: Request, context: ServeContext) -> StarletteResponse:
        """音声の本文を上限まで数えながら読み、文字起こしの受け付けへ渡す。上限を超えたら 413。"""
        too_large = problem_response(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"録音が大きすぎます（{MAX_AUDIO_BYTES} バイトまで）"
        )
        length = _content_length(request)
        # 長さが分かる: 読む前に上限と比べる
        if length is not None and length > MAX_AUDIO_BYTES:
            return _to_starlette(too_large)
        chunks: list[bytes] = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > MAX_AUDIO_BYTES:
                return _to_starlette(too_large)
            chunks.append(chunk)
        body = b"".join(chunks)
        return await _call(
            lambda: transcribe_response(
                context,
                content_type=request.headers.get("content-type"),
                origin=request.headers.get("origin"),
                body=body,
            )
        )


def _file_chunks(plan: FilePlan) -> Iterator[bytes]:
    """計画の範囲のファイルの中身を、書き出しの単位ごとに読んでは返す（全体を読み込まない。接続が切れたら読むのをやめる）。"""
    remaining = plan.length
    if remaining == 0:
        return
    # 先読みのバッファを持たず、書き出しの単位だけを読む
    with plan.path.open("rb", buffering=0) as stream:
        stream.seek(plan.start)
        while remaining > 0:
            chunk = stream.read(min(FILE_WRITE_CHUNK, remaining))
            # 書き出す途中でファイルが縮んだ
            if not chunk:
                return
            remaining -= len(chunk)
            yield chunk


def _content_length(request: Request) -> int | None:
    """`Content-Length` を整数で返す（無い・整数でない・負のときは None）。"""
    text = request.headers.get("content-length")
    if text is None:
        return None
    try:
        length = int(text)
    except ValueError:
        return None
    return length if length >= 0 else None


async def _call(make: Callable[[], Response]) -> StarletteResponse:
    """同期の処理の関数をスレッドで呼び、返った応答を Starlette の応答にする。"""
    return _to_starlette(await run_in_threadpool(make))


async def _write(
    request: Request,
    context: ServeContext,
    handle: Callable[[Path, dict[str, Any]], Any],
    status: int,
    *,
    after: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> StarletteResponse:
    """本文の長さを確かめて読み、書き込む受け付けの関数へ渡して応答にする。after は鍵を外した後に呼ぶ処理。"""
    length = _content_length(request)
    # 長さが無いか、上限を超える: 本文を読まずに断る
    if length is None or length > MAX_REQUEST_BYTES:
        return _to_starlette(
            problem_response(HTTPStatus.BAD_REQUEST, f"本文の長さが要ります（{MAX_REQUEST_BYTES} バイトまで）")
        )
    body = await request.body()
    return await _call(
        lambda: write_response(
            context,
            content_type=request.headers.get("content-type"),
            origin=request.headers.get("origin"),
            body=body,
            handle=handle,
            status=status,
            after=after,
        )
    )


def _to_starlette(response: Response, extra_headers: tuple[tuple[str, str], ...] = ()) -> StarletteResponse:
    """処理の関数が返した応答を、控えさせない Starlette の応答にする（extra_headers を加える）。"""
    headers = {"Content-Type": response.content_type, "Cache-Control": "no-store"}
    headers.update(response.headers)
    headers.update(dict(extra_headers))
    # 送り直す応答は宛先を持つ
    if response.location is not None:
        headers["Location"] = response.location
    # 204・304 は本文を持たない
    body = b"" if response.status in (HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED) else response.body
    return StarletteResponse(content=body, status_code=response.status, headers=headers)


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


def run_hook(command: tuple[str, ...], port: int, name: str, path: str) -> bool:
    """フックのコマンドの末尾に常駐サーバーのポート・ワークスペースの名前・画面のパスを足し、新しいセッションで起動して終わりを待たずに返す。"""
    try:
        subprocess.Popen(
            [*command, str(port), name, path],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        logger.warning("フックを起動できない: %s（%s）", command, error)
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


def _with_search(location: str, request: Request) -> str:
    """要求に search があれば `?{search}` を付けた location を返す。"""
    query = request.url.query
    return f"{location}?{query}" if query else location


def redirect_response(location: str) -> Response:
    """本文を持たない 302 で、location へ送り直す応答を作る。"""
    return Response(status=HTTPStatus.FOUND, content_type=HTML_TYPE, body=b"", location=location)


def spa_response(spa_dir: Path, sub_path: str) -> Response:
    """画面のビルドの出力のファイルを返す。`/` は `index.html`、出力に無いパスと出力の外を指すパスは 404。"""
    base = spa_dir.resolve()
    if sub_path == PAGE_PATH:
        target = base / "index.html"
        if not target.is_file():
            logger.error("画面のビルドの出力がありません: %s", spa_dir)
            return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"画面のビルドの出力がありません（{spa_dir}）")
    else:
        target = (base / unquote(sub_path).lstrip("/")).resolve()
        if not target.is_relative_to(base) or not target.is_file():
            return problem_response(HTTPStatus.NOT_FOUND, f"ファイルがありません: {sub_path}")
    content_type = SPA_TYPES.get(target.suffix, "application/octet-stream")
    return Response(status=HTTPStatus.OK, content_type=content_type, body=target.read_bytes())


def records_response(
    context: ServeContext,
    read: Callable[..., dict[str, Any]] = read_records,
    *,
    if_none_match: str | None = None,
    accept_encoding: str | None = None,
) -> Response:
    """記録の JSON を返却する。保持した応答があれば読まずに使い、`If-None-Match` が合えば 304、`gzip` を受けるなら圧縮して返却する。"""

    def _build() -> dict[str, Any]:
        """ワークスペースを読み、config.yaml が検査に通れば最後に通った設定を差し替える。"""
        data = read(context.root, last_settings=context.settings.current())
        # config.yaml が検査に通った: 最後に通った設定として控える
        if data.get("settings_problem") is None:
            context.settings.accept(data["settings"])
        return data

    try:
        cached = context.records_cache.get_or_build(_build)
    except SchemaMismatchError as error:
        # 読めない・スキーマに合わない: 合わない箇所の行を detail にする
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join(error.lines))
    except WorkspaceNotFoundError as error:
        # 配っている間に config.yaml が無くなった
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
    headers = {"ETag": cached.etag, "Cache-Control": "no-cache", "Vary": "Accept-Encoding"}
    # 画面が持つ応答と同じ: 本文の無い 304
    if if_none_match is not None and _etag_matches(if_none_match, cached.etag):
        return Response(status=HTTPStatus.NOT_MODIFIED, content_type=JSON_TYPE, body=b"", headers=headers)
    # gzip を受ける: 圧縮した本文を返却する
    if _accepts_gzip(accept_encoding):
        return Response(
            status=HTTPStatus.OK,
            content_type=JSON_TYPE,
            body=cached.gzip_body,
            headers={**headers, "Content-Encoding": "gzip"},
        )
    return Response(status=HTTPStatus.OK, content_type=JSON_TYPE, body=cached.body, headers=headers)


def _etag_matches(if_none_match: str, etag: str) -> bool:
    """`If-None-Match` のどれかが `ETag` と弱い比較（両方の `W/` を除いて比べる）で一致するかを返却する。"""
    current = etag.removeprefix(WEAK_ETAG_PREFIX)
    candidates = [value.strip() for value in if_none_match.split(",")]
    return any(value == "*" or value.removeprefix(WEAK_ETAG_PREFIX) == current for value in candidates)


def _accepts_gzip(accept_encoding: str | None) -> bool:
    """`Accept-Encoding` が `q=0` でない `gzip` を含むかを返却する。"""
    if accept_encoding is None:
        return False
    for part in accept_encoding.split(","):
        coding, _, params = part.strip().partition(";")
        # q=0 は受けない意味
        if coding.strip().lower() == "gzip" and params.replace(" ", "") not in ("q=0", "q=0.0"):
            return True
    return False


def opened_response(context: ServeContext, now: NowFn = now_utc) -> Response:
    """前回開いた時点を返し、今の時点に書き換える（記録のロックは取らない）。"""
    try:
        seq = head_until_seq(load_changes(context.root))
    except SchemaMismatchError as error:
        # changes.yaml が読めない: 前回開いた時点を書き換えず、画面はタブを開いた時点を範囲の始まりにする
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join(error.lines))
    opened = {"at": now(), "seq": seq}
    try:
        previous = touch_opened(context.root, opened)
    except WriteFailedError as error:
        # 前回開いた時点を書けない: 画面はタブを開いた時点を範囲の始まりにする
        return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps({"previous": previous, "opened": opened}, ensure_ascii=False).encode(
            "utf-8"
        ),
    )


def seen_response(context: ServeContext, thread_id: str, *, origin: str | None) -> Response:
    """送り元を確かめ、そのスレッドの利用者の未読の書き込みを全て既読にして、既読にした ID を返す。"""
    # 別のサイトからの書き込み
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        require_workspace(context.root)
        thread = next((item for item in load_threads(context.root) if item.id == thread_id), None)
        # 無いスレッド
        if thread is None:
            raise ThreadNotFoundError(f"スレッドがありません: {thread_id}")
        # 未読が無い: 鍵を取らず、書かずに空を返す
        if all(post.seen for post in thread.posts):
            seen: list[str] = []
        else:
            # 鍵を取るまでに足された書き込みも既読にする（画面は書き換えの知らせでその書き込みを描く）
            with workspace_lock(context.root, context.write_lock):
                seen = mark_seen(context.root, thread_id)
    except MindmapError as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps({"id": thread_id, "seen": seen}, ensure_ascii=False).encode("utf-8"),
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
    context.records_cache.discard()
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps({"settings": settings}, ensure_ascii=False).encode("utf-8"),
    )


def workspace_signature(root: Path) -> str:
    """見ているファイルの名前・更新日時（ナノ秒）・大きさをつないだ、書き換えの印を返す。"""
    # 前回開いた日時（`.mindstella-opened`）は、タブが開くたびに書き換わるので見ない
    names = [
        SETTINGS_FILE,
        *(spec.file for spec in KINDS.values()),
        THREADS_FILE,
        CHANGES_FILE,
        EDITS_FILE,
    ]
    # 本文の Markdown と HTML（直下の `docs/` の直下）も、記録のフォルダからの名前で見る
    records = records_root(root)
    body_dir = body_root(root)
    if body_dir.is_dir():
        names.extend(
            f"{BODY_REF_PREFIX}{path.name}"
            for pattern in ("*.md", "*.html")
            for path in body_dir.glob(pattern)
        )
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
    duplicates: Callable[[Path], tuple[str, ...]] | None = None,
    on_changed: Callable[[], None] | None = None,
) -> None:
    """書き換えの印が変わったら（知らせる前に on_changed を呼び） `changed` を、重なった ID の集まりが変わったら `duplicate_ids` を、知らせが無いまま一定時間過ぎたら保つ行を書き続ける。"""
    last_signature = signature(root)
    last_written = clock()
    last_duplicates: tuple[str, ...] = ()
    read_duplicates = duplicates or _detected_duplicates
    while True:
        sleep(POLL_INTERVAL_SEC)
        current = signature(root)
        found = read_duplicates(root)
        try:
            # 重なった ID の集まりが前に書いたものと違う: その集まりを知らせる
            if found != last_duplicates:
                write(f"event: duplicate_ids\ndata: {json.dumps(list(found))}\n\n".encode())
                last_duplicates = found
                last_written = clock()
            if current != last_signature:
                # 印が変わった: 保持した記録の応答を捨ててから、変わったことだけを知らせる（画面が記録を読み直す）
                if on_changed is not None:
                    on_changed()
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


def _detected_duplicates(root: Path) -> tuple[str, ...]:
    """そのワークスペースの変更の検知が最後に求めた重なった ID を返す（検知が動いていなければ空）。"""
    detector = detector_of(root)
    return () if detector is None else detector.duplicate_ids()


def comments_response(root: Path) -> Response:
    """レビュー中のコメントと下書きをその場で読んだ JSON を返す。"""
    try:
        data = list_review(load_workspace(root))
    except (SchemaMismatchError, WorkspaceNotFoundError) as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )


def threads_response(root: Path) -> Response:
    """全てのスレッドをその場で読んだ JSON を返す。"""
    try:
        data = threads_for_preview(load_workspace(root))
    except (SchemaMismatchError, WorkspaceNotFoundError) as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )


def edits_response(root: Path) -> Response:
    """保存待ちの編集をその場で読んだ JSON を返す。"""
    try:
        data = list_edits(root)
    except MindmapError as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
    )


def edit_delete_response(context: ServeContext, *, origin: str | None, edit_id: str) -> Response:
    """送り元を確かめ、書き換えの鍵を取って保存待ちの編集 1 件を取り消す。"""
    # 別のサイトからの書き込み
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        with workspace_lock(context.root, context.write_lock):
            body = delete_edit(context.root, edit_id)
    except MindmapError as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
    )


def edits_save_response(context: ServeContext, *, origin: str | None) -> Response:
    """送り元を確かめ、書き換えの鍵を取って保存待ちの編集をまとめて保存する。"""
    # 別のサイトからの書き込み
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    try:
        with workspace_lock(context.root, context.write_lock):
            body = save_edits(context.root)
    except MindmapError as error:
        return error_response(error)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
    )


def patch_thread_status(root: Path, thread_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """画面からのクローズ・オープンへの戻しを、書き手を利用者にして書く。"""
    require_workspace(root)
    status = data.get("status")
    changed = set_thread_status(
        root, thread_id, status=cast("str", status), reason=data.get("reason"), author="user"
    )
    return {"id": thread_id, "status": status, "changed": changed}


def write_response(
    context: ServeContext,
    *,
    content_type: str | None,
    origin: str | None,
    body: bytes,
    handle: Callable[[Path, dict[str, Any]], Any],
    status: int,
    after: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> Response:
    """本文の形と送り元を確かめ、書き換えの鍵を取って渡した処理を呼び、結果の応答を返す。after があれば、鍵を外した後に結果を渡して呼び、返った値を応答の本文にする。"""
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
    # 結果で成功のステータスコードが変わる処理は、本文とステータスコードの組を返す
    if isinstance(result, tuple):
        result, status = result
    # 鍵を外した後の処理がある: 結果を渡して、返った値を応答の本文にする
    if after is not None and result is not None:
        result = after(result)
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
        "thread": deleted.thread,
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
    if isinstance(
        error, (CommentInvalidError, SettingsInvalidError, ArgumentError, EditInvalidError)
    ):
        return problem_response(HTTPStatus.BAD_REQUEST, detail)
    if isinstance(
        error, (ItemNotFoundError, CommentNotFoundError, ThreadNotFoundError, EditNotFoundError)
    ):
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
    if isinstance(error, (EditConflictError, ConcurrentWriteError)):
        return problem_response(HTTPStatus.CONFLICT, detail)
    # 書き込めない編集は、全てを返す
    if isinstance(error, EditsBlockedError):
        problem = json.loads(problem_response(HTTPStatus.CONFLICT, detail).body)
        problem["blocked"] = [
            {"id": entry.id, "reason": entry.reason, "detail": entry.detail, "refs": entry.refs}
            for entry in error.blocked
        ]
        return Response(
            status=HTTPStatus.CONFLICT,
            content_type=PROBLEM_TYPE,
            body=json.dumps(problem, ensure_ascii=False).encode("utf-8"),
        )
    if isinstance(error, (WorkspaceNotFoundError, SchemaMismatchError)):
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, "\n".join([detail, *error.lines]))
    # 書き込めなかった・渡された種類のないエラー
    if not isinstance(error, WriteFailedError):
        logger.error("渡された種類のないエラー: %s %s", type(error).__name__, detail)
    return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, detail)


def _edit_added(body: dict[str, Any], created: bool) -> tuple[dict[str, Any], HTTPStatus]:
    """保存待ちの編集の追加の本文と、新しく溜めたとき 201・同じ編集の書き換えと外したとき 200 のステータスコードの組を返す。"""
    return body, HTTPStatus.CREATED if created else HTTPStatus.OK


def _added_body(comment: ReviewComment, count: int) -> dict[str, Any]:
    """溜めたコメントの応答の本文を作る。"""
    return {"id": comment.id, "created": comment.created, "count": count}


def _sent_body(sent: str, items: list[SentPost]) -> dict[str, Any]:
    """まとめて送った応答の本文を作る。"""
    return {"sent": sent, "items": [asdict(item) for item in items]}


def _entered_body(context: ServeContext, body: dict[str, Any]) -> dict[str, Any]:
    """まとめて送った応答の本文に、Claude Code へ入力したか（`entered`）と起動し直したか（`restarted`）を足す。"""
    targets = context.input_targets
    # まとめて送るは送った件数、すぐ送るは 1 件
    count = len(body["items"]) if "items" in body else 1
    # 宛先の台帳が無い: 入力しない
    if targets is None:
        return {**body, "entered": False, "restarted": False}
    entered, restarted = targets.enter_or_restart(context.root, count)
    return {**body, "entered": entered, "restarted": restarted}


def _sent_now_body(sent: str, post: SentPost) -> dict[str, Any]:
    """すぐ送った応答の本文を作る。"""
    return {"sent": sent, "thread": post.thread, "post": post.post}


def _updated_body(comment: ReviewComment) -> dict[str, Any]:
    """書き換えたコメントの応答の本文を作る。"""
    return {
        "id": comment.id,
        "body": comment.body,
        "loc": None if comment.loc is None else location_to_dict(comment.loc),
    }


def _saved_draft(root: Path, data: dict[str, Any]) -> None:
    """下書きを保つ（応答の本文は持たない）。"""
    save_draft(root, data)


def _comment_id_of(path: str | None) -> str | None:
    """`/api/comments/{id}` のパスからコメントの ID を取り出す（送る口の `send` は ID でない）。"""
    prefix = f"{COMMENTS_PATH}/"
    # 別のパス
    if path is None or not path.startswith(prefix) or path in (SEND_PATH, SEND_NOW_PATH):
        return None
    return unquote(path.removeprefix(prefix))


def _thread_id_of(path: str | None) -> str | None:
    """`/api/threads/{id}` のパスからスレッドの ID を取り出す（`id` は `/` を含まない）。"""
    prefix = f"{THREADS_PATH}/"
    # 別のパス
    if path is None or not path.startswith(prefix):
        return None
    thread_id = unquote(path.removeprefix(prefix))
    return thread_id if thread_id and "/" not in thread_id else None


def _edit_id_of(path: str | None) -> str | None:
    """`/api/edits/{id}` のパスから編集の ID を取り出す（`id` は `/` を含まない）。"""
    prefix = f"{EDITS_PATH}/"
    # 別のパス
    if path is None or not path.startswith(prefix):
        return None
    edit_id = unquote(path.removeprefix(prefix))
    return edit_id if edit_id and "/" not in edit_id else None


def _confirmed_item_id_of(path: str | None) -> str | None:
    """`/api/items/{id}/confirmed` のパスから項目の ID を取り出す（`id` は `/` を含まない）。"""
    prefix = f"{ITEMS_PATH}/"
    # 別のパス
    if path is None or not path.startswith(prefix) or not path.endswith(CONFIRMED_SUFFIX):
        return None
    item_id = unquote(path.removeprefix(prefix).removesuffix(CONFIRMED_SUFFIX))
    return item_id if item_id and "/" not in item_id else None


def _seen_thread_id_of(path: str | None) -> str | None:
    """`/api/threads/{id}/seen` のパスからスレッドの ID を取り出す（`id` は `/` を含まない）。"""
    prefix = f"{THREADS_PATH}/"
    # 別のパス
    if path is None or not path.startswith(prefix) or not path.endswith(SEEN_SUFFIX):
        return None
    thread_id = unquote(path.removeprefix(prefix).removesuffix(SEEN_SUFFIX))
    return thread_id if thread_id and "/" not in thread_id else None


def transcription_response(context: ServeContext, *, origin: str | None) -> Response:
    """文字起こしを使えるかと理由・プリセットの候補・ワークスペースの文字起こしの設定を返す。"""
    # 別のサイトからの読み取り
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    settings_or_error = _transcription_settings(context.root)
    if isinstance(settings_or_error, Response):
        return settings_or_error
    availability = check_availability(context.transcriber)
    payload = {
        "available": availability.available,
        "reason": availability.reason,
        "detail": availability.detail,
        "presets": availability.presets,
        "action": settings_or_error.get("action", DEFAULT_TRANSCRIPTION_ACTION),
        "preset": settings_or_error.get("preset"),
    }
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )


def transcribe_response(
    context: ServeContext, *, content_type: str | None, origin: str | None, body: bytes
) -> Response:
    """受けた音声を文字起こしのインターフェースへ渡し、起こした文字を返す（ワークスペースを書き換えないので鍵を取らない）。"""
    media_type = (content_type or "").split(";")[0].strip().lower()
    # 音声でない（別のサイトのフォームから送れる形を受けない）
    if not media_type.startswith(AUDIO_TYPE_PREFIX):
        return problem_response(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "録音した音声で送ってください")
    # 別のサイトからの送信
    if not check_origin(origin, context.port, allowed_hosts=context.allowed_hosts):
        return problem_response(HTTPStatus.FORBIDDEN, "送り元が合いません")
    if not body:
        return problem_response(HTTPStatus.BAD_REQUEST, "録音が空です")
    settings_or_error = _transcription_settings(context.root)
    if isinstance(settings_or_error, Response):
        return settings_or_error
    # 配信が文字起こしを持たない: 届かないと同じに扱う
    if context.transcriber is None:
        return _unavailable_response("stopped")
    try:
        text = context.transcriber.transcribe(
            body, content_type or media_type, preset=settings_or_error.get("preset")
        )
    except TranscriberStoppedError as error:
        logger.warning("文字起こしできなかった: %s %s", type(error).__name__, error)
        return _unavailable_response("stopped")
    except TranscriberUnsupportedError as error:
        logger.warning("文字起こしできなかった: %s %s", type(error).__name__, error)
        return _unavailable_response("unsupported")
    except TranscriptionFailedError as error:
        logger.warning("文字起こしできなかった: %s %s", type(error).__name__, error)
        return problem_response(HTTPStatus.BAD_GATEWAY, FAILED_DETAIL)
    except TranscriptionTimeoutError as error:
        logger.warning("文字起こしできなかった: %s %s", type(error).__name__, error)
        return problem_response(HTTPStatus.GATEWAY_TIMEOUT, FAILED_DETAIL)
    return Response(
        status=HTTPStatus.OK,
        content_type=JSON_TYPE,
        body=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
    )


def _transcription_settings(root: Path) -> dict[str, Any] | Response:
    """config.yaml を検査して transcription を返す。読めない・スキーマに合わなければ 422 の応答を返す。"""
    try:
        settings, problems = check_settings(root)
    except WorkspaceNotFoundError as error:
        return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
    if problems:
        return error_response(build_mismatch_error(problems))
    transcription = settings.get("transcription")
    return transcription if isinstance(transcription, dict) else {}


def _unavailable_response(reason: UnavailableReason) -> Response:
    """使えない理由を本文の reason に足した 503 の応答を作る。"""
    problem = json.loads(
        problem_response(HTTPStatus.SERVICE_UNAVAILABLE, UNAVAILABLE_DETAILS[reason]).body
    )
    problem["reason"] = reason
    return Response(
        status=HTTPStatus.SERVICE_UNAVAILABLE,
        content_type=PROBLEM_TYPE,
        body=json.dumps(problem, ensure_ascii=False).encode("utf-8"),
    )
