"""単体・結合・E2E のテストが共有する、ワークスペースと MCP サーバーの起動の fixture。

fixture は `tests/conftest.py` が読み込み、`tests/` の下の全てのテストが使える。
"""

from __future__ import annotations

import asyncio
import itertools
import copy
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque
from collections.abc import Callable, Iterator
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# このファイルから見たリポジトリの直下（tests の 1 つ上）
REPO_ROOT_PARENT_DEPTH = 1
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# MCP サーバーの入口（起動スクリプトが MCP の設定に書くスクリプト）
SERVER_SCRIPT = (
    REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts" / "server.py"
)

# 子プロセス 1 回を待つ上限秒数
COMMAND_TIMEOUT_SEC = 120

# 常駐サーバーが待ち受けるホストと、待ち受けのポートを読む環境変数の名前
LISTEN_HOST = "127.0.0.1"
PORT_ENV = "MINDSTELLA_PORT"


# テストの常駐サーバーに渡すポートの範囲（OS の一時ポートの範囲より下）の始まりと、xdist のワーカー 1 つ分の個数
TEST_PORT_BASE = 20000
TEST_PORTS_PER_WORKER = 500

# ワーカーの範囲の中で次に試す位置
_port_counter = itertools.count()
# 常駐サーバーの MCP の入口と、状態を返す GET のパス
MCP_PATH = "/mcp"
STATUS_PATH = "/_admin/status"

# 状態の GET 1 回を打ち切る秒数
STATUS_TIMEOUT_SEC = 1

# 常駐サーバーが待ち受けるまで待つ上限秒数と、確かめる間隔
SERVER_START_TIMEOUT_SEC = 20
START_POLL_SEC = 0.1

# MCP のクライアントがつなぐ・1 回のリクエストを待つ上限秒数
CLIENT_TIMEOUT_SEC = 60

# 常駐サーバーが終わり始めてから終わるまで待つ上限秒数
SERVER_EXIT_TIMEOUT_SEC = 5

# サーバーの出力のうち、失敗の報告に残す直近の行数（残りは読み捨てる）
STDERR_KEEP_LINES = 200

# 標準エラーを読み切るのを待つ上限秒数
STDERR_JOIN_TIMEOUT_SEC = 1

# 書き換えるツールが置く排他ロックのファイル（中身は空）。書き込みの前後の比べからは外す
LOCK_FILE_NAME = ".mindstella.lock"

# ワークスペースの直下に置く、記録を全てまとめるフォルダ（ER 図『ワークスペース』）
RECORD_DIR = ".mindstella"

# 項目に入れる既定の日時（UTC のタイムゾーン付き ISO 8601）
DEFAULT_TIMESTAMP = "2026-10-01T00:00:00+00:00"

# ID の頭の文字 → 書き込む YAML のファイル名（並びは D・T・R・A・G・N・L）
KIND_FILES = {
    "D": "decisions.yaml",
    "T": "tasks.yaml",
    "R": "research.yaml",
    "A": "docs.yaml",
    "G": "terms.yaml",
    "N": "notes.yaml",
    "L": "logs.yaml",
}

# 決定済みの検討事項に付ける、案 A を採用した案
ADOPTED_OPTIONS: list[dict[str, Any]] = [{"key": "A", "content": "案 A", "adopted": True}]

# ID の頭の文字 → スキーマが必須にしているキーの既定値
KIND_DEFAULTS: dict[str, dict[str, Any]] = {
    "D": {"status": "未決定", "options": [{"key": "A", "content": "案 A"}]},
    "T": {"kind": "作業", "status": "未着手"},
    "R": {"question": "何を調べたか"},
    "A": {"kind": "図", "deliverable": False, "status": "下書き"},
    "G": {"meaning": "用語の意味"},
    "N": {"content": "メモの中身"},
    "L": {"date": "2026-10-01"},
}

type StartServer = Callable[..., McpServer]
type CallTool = Callable[..., ToolResult]
type MakeItem = Callable[..., dict[str, Any]]
type MakeSubmission = Callable[..., dict[str, Any]]
type WriteSubmissions = Callable[..., None]
type MakePost = Callable[..., dict[str, Any]]
type MakeThread = Callable[..., dict[str, Any]]
type WriteThreads = Callable[..., None]
type MakeComment = Callable[..., dict[str, Any]]
type WriteComments = Callable[..., None]
type MakeDraft = Callable[..., dict[str, Any]]
type WriteDrafts = Callable[..., None]
type MakeEdit = Callable[..., dict[str, Any]]
type WriteEdits = Callable[..., None]
type MakeWorkspace = Callable[..., Path]
type MakeLegacyItem = Callable[[str, bool], dict[str, Any]]
type MakeLegacyWorkspace = Callable[..., Path]
type SnapshotTree = Callable[[Path], dict[str, bytes]]
type MakeVenv = Callable[..., Path]


def free_port() -> int:
    """`127.0.0.1` の空きポートを、OS の一時ポートの範囲（プレビューの配信が使う）の外の、xdist のワーカーごとの範囲から 1 つ選んで返す。"""
    worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0").removeprefix("gw")
    start = TEST_PORT_BASE + int(worker if worker.isdigit() else 0) * TEST_PORTS_PER_WORKER
    for offset in range(TEST_PORTS_PER_WORKER):
        port = start + (next(_port_counter) + offset) % TEST_PORTS_PER_WORKER
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((LISTEN_HOST, port))
            except OSError:
                continue
        return port
    raise AssertionError(f"{start} からの {TEST_PORTS_PER_WORKER} 個のポートに空きが無い")


def is_listening(port: int) -> bool:
    """`127.0.0.1` のそのポートへつながるかを返す。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((LISTEN_HOST, port)) == 0


def read_server_status(port: int) -> dict[str, Any] | None:
    """`GET /_admin/status` の JSON を返す。つながらなければ None。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://{LISTEN_HOST}:{port}{STATUS_PATH}", timeout=STATUS_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except OSError:
        return None


@dataclass(frozen=True)
class ToolResult:
    """MCP のツールの結果。`data` は構造化の結果（JSON のオブジェクト）で、エラーのときは None。"""

    is_error: bool
    text: str
    data: dict[str, Any] | None


class McpClient:
    """常駐サーバーの `/mcp` へ MCP の SDK のクライアントでつなぎ、ツールを同期で呼ぶ。

    SDK のクライアントは非同期で、つないだタスクの中で使い続ける必要があるため、専用のスレッドのイベントループの 1 つのタスクで動かす。
    """

    def __init__(self, url: str) -> None:
        """つないで初期化を済ませ、サーバーの名前を控える。"""
        self._loop = asyncio.new_event_loop()
        self._requests: asyncio.Queue[tuple[Callable[[ClientSession], Any], Future[Any]] | None]
        ready: Future[str] = Future()
        self._thread = threading.Thread(target=self._run, args=(url, ready), daemon=True)
        self._thread.start()
        self.server_name = ready.result(timeout=CLIENT_TIMEOUT_SEC)

    def _run(self, url: str, ready: Future[str]) -> None:
        """イベントループを動かし、つないだクライアントでリクエストを待つ。"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve(url, ready))

    async def _serve(self, url: str, ready: Future[str]) -> None:
        """つないで初期化し、閉じるまで届いたリクエストを順に呼ぶ。"""
        self._requests = asyncio.Queue()
        try:
            async with (
                streamable_http_client(url) as (read_stream, write_stream, *_),
                ClientSession(read_stream, write_stream) as session,
            ):
                initialized = await session.initialize()
                ready.set_result(initialized.server_info.name)
                while (request := await self._requests.get()) is not None:
                    run, result = request
                    try:
                        result.set_result(await run(session))
                    except Exception as error:  # noqa: BLE001 - 呼び出し元のスレッドで送り直す
                        result.set_exception(error)
        except BaseException as error:
            # つなぐ前に失敗した: 呼び出し元へ知らせる
            if not ready.done():
                ready.set_exception(error)
            raise

    def _request(self, run: Callable[[ClientSession], Any]) -> Any:
        """クライアントのスレッドで run を呼び、結果を返す。"""
        result: Future[Any] = Future()
        self._loop.call_soon_threadsafe(self._requests.put_nowait, (run, result))
        return result.result(timeout=CLIENT_TIMEOUT_SEC)

    def list_tools(self) -> list[dict[str, Any]]:
        """ツールの一覧（名前・入力のスキーマ）を返す。"""
        listed = self._request(lambda session: session.list_tools())
        return [{"name": tool.name, "inputSchema": tool.input_schema} for tool in listed.tools]

    def call(self, name: str, **arguments: Any) -> ToolResult:
        """ツールを呼び、結果の本文・エラーかどうか・構造化の結果を返す。"""
        result = self._request(lambda session: session.call_tool(name, arguments))
        text = "".join(part.text for part in result.content if part.type == "text")
        return ToolResult(
            is_error=bool(result.is_error), text=text, data=result.structured_content
        )

    def close(self) -> None:
        """セッションを閉じて、クライアントのスレッドを終える（既に閉じていれば何もしない）。"""
        if not self._thread.is_alive():
            return
        self._loop.call_soon_threadsafe(self._requests.put_nowait, None)
        self._thread.join(timeout=CLIENT_TIMEOUT_SEC)


class McpServer:
    """常駐サーバーを空きポートで子プロセスとして起動し、MCP のクライアントでつないでツールを呼ぶ。"""

    def __init__(
        self, *, python: str, env: dict[str, str], cwd: Path | None, script: Path = SERVER_SCRIPT
    ) -> None:
        """常駐サーバーを起動して待ち受けを待ち、クライアントを 1 つつなぐ。"""
        self.port = int(env.get(PORT_ENV) or free_port())
        self.url = f"http://{LISTEN_HOST}:{self.port}{MCP_PATH}"
        self.process = subprocess.Popen(
            [python, str(script)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env={**env, PORT_ENV: str(self.port)},
            cwd=cwd,
        )
        # 出力のパイプは満杯になるとサーバーの書き込みが止まるので、別のスレッドで読み続ける
        self._output_lines: deque[str] = deque(maxlen=STDERR_KEEP_LINES)
        self._output_reader = threading.Thread(target=self._drain_output, daemon=True)
        self._output_reader.start()
        self._wait_listening()
        self._clients: list[McpClient] = []
        self.client = self.connect()
        self.server_name = self.client.server_name

    def _drain_output(self) -> None:
        """サーバーの標準出力と標準エラーを終わりまで読み、直近の行だけを残す。"""
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._output_lines.append(line)

    def _wait_listening(self) -> None:
        """`GET /_admin/status` が返るまで待つ。先に終わるか上限を過ぎたらテストを止める。"""
        deadline = time.monotonic() + SERVER_START_TIMEOUT_SEC
        while read_server_status(self.port) is None:
            assert self.process.poll() is None, f"常駐サーバーが終わりました: {self.stderr_text()}"
            assert time.monotonic() < deadline, f"常駐サーバーが待ち受けません: {self.stderr_text()}"
            time.sleep(START_POLL_SEC)

    def stderr_text(self) -> str:
        """サーバーが標準エラーへ書いた直近の行を返す（サーバーが終わっていれば読み切ってから）。"""
        if self.process.poll() is not None:
            self._output_reader.join(timeout=STDERR_JOIN_TIMEOUT_SEC)
        return "".join(self._output_lines)

    def connect(self) -> McpClient:
        """同じ常駐サーバーへ、もう 1 つのクライアントをつなぐ。"""
        client = McpClient(self.url)
        self._clients.append(client)
        return client

    def list_tools(self) -> list[dict[str, Any]]:
        """最初につないだクライアントでツールの一覧を返す。"""
        return self.client.list_tools()

    def call(self, name: str, **arguments: Any) -> ToolResult:
        """最初につないだクライアントでツールを呼ぶ。"""
        return self.client.call(name, **arguments)

    def wait_exit(self, timeout: float = SERVER_EXIT_TIMEOUT_SEC) -> int:
        """プロセスが終わるのを待ち、終了コードを返す。"""
        return self.process.wait(timeout=timeout)

    def stop(self) -> None:
        """クライアントを閉じ、まだ動いていれば SIGTERM で終わらせ、動いたままなら止める。"""
        for client in self._clients:
            client.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=SERVER_EXIT_TIMEOUT_SEC)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        # 出力は読むスレッドが終わりまで読むので、読み切ってから閉じる
        self._output_reader.join(timeout=STDERR_JOIN_TIMEOUT_SEC)
        if self.process.stdout is not None:
            self.process.stdout.close()


@pytest.fixture
def start_server(tmp_path: Path) -> Iterator[StartServer]:
    """常駐サーバーを空きポートで子プロセスとして起動する関数を返し、テストの後で全て止める。"""
    # 子プロセスの入出力を UTF-8 に揃える（既定の文字コードに左右されないため）
    base_env = {**os.environ, "PYTHONUTF8": "1"}
    started: list[McpServer] = []

    def _start(
        *,
        python: str = sys.executable,
        extra_env: dict[str, str] | None = None,
        cwd: Path | None = None,
        script: Path = SERVER_SCRIPT,
    ) -> McpServer:
        """常駐サーバーを起動してクライアントをつなぐ。cwd は常駐サーバーの作業フォルダ。"""
        server = McpServer(
            python=python, env={**base_env, **(extra_env or {})}, cwd=cwd or tmp_path, script=script
        )
        started.append(server)
        return server

    yield _start
    for server in started:
        server.stop()


@pytest.fixture(scope="session")
def mcp_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[McpServer]:
    """テスト全体で共有する常駐サーバーを 1 つ起動して返す（立ち上げに数秒かかるため）。"""
    server = McpServer(
        python=sys.executable,
        env={**os.environ, "PYTHONUTF8": "1"},
        cwd=tmp_path_factory.mktemp("mcp-server-cwd"),
    )
    yield server
    server.stop()


@pytest.fixture
def call_tool(mcp_server: McpServer) -> CallTool:
    """立てた MCP サーバーでツールを呼ぶ関数を返す。"""
    return mcp_server.call


@pytest.fixture
def valid_settings() -> dict[str, Any]:
    """設定のスキーマに合う設定（config.yaml の中身）を返す。"""
    return {
        "summary": "要件出しのスキル mindmap を設計する",
        "playbooks": ["システム開発"],
        "target_label": "システム",
        "phases": ["目的", "要件", "構成"],
        "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
        "categories": [{"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}],
        "goal": {
            "phase": "構成",
            "summary": "作り始められる",
            "deliverables": [{"title": "YAML のスキーマ"}],
        },
        "links": [],
    }


@pytest.fixture
def make_item() -> MakeItem:
    """ID の頭の文字に合う必須のキーを持つ項目を作る関数を返す。"""

    def _make(item_id: str, **overrides: Any) -> dict[str, Any]:
        """ID・題・種類ごとの必須のキーに、渡したキーを重ねて日時を足した項目を返す。"""
        item: dict[str, Any] = {"id": item_id, "title": f"{item_id}の題"}
        # 案の配列などの入れ子は、項目どうしで共有しないよう写してから入れる
        item.update(copy.deepcopy(KIND_DEFAULTS[item_id[0]]))
        # 資料は本文が必須なので、ID に揃えたファイル名を既定にする
        if item_id[0] == "A":
            item["body"] = f"{item_id}.md"
        item.update(overrides)
        item.setdefault("created", DEFAULT_TIMESTAMP)
        item.setdefault("updated", DEFAULT_TIMESTAMP)
        return item

    return _make


@pytest.fixture
def make_submission() -> MakeSubmission:
    """送信（submissions.yaml の 1 件）を作る関数を返す。"""

    def _make(submission_id: str, **overrides: Any) -> dict[str, Any]:
        """ID・向けた項目・本文・送った日時・取り込んだ日時（未取り込み）に、渡したキーを重ねた送信を返す。"""
        submission: dict[str, Any] = {
            "id": submission_id,
            "target": "D-1",
            "body": f"{submission_id}の本文",
            "sent": DEFAULT_TIMESTAMP,
            "taken": None,
        }
        submission.update(overrides)
        return submission

    return _make


@pytest.fixture
def write_submissions() -> WriteSubmissions:
    """ワークスペースに submissions.yaml を書く関数を返す。"""

    def _write(root: Path, *submissions: dict[str, Any]) -> None:
        """渡した送信を並びのまま items に入れて、root の記録のフォルダの submissions.yaml に書く。"""
        write_yaml(root / RECORD_DIR / "submissions.yaml", {"items": list(submissions)})

    return _write


@pytest.fixture
def make_post() -> MakePost:
    """スレッドの書き込み（threads.yaml の posts の 1 件）を作る関数を返す。"""

    def _make(post_id: str, **overrides: Any) -> dict[str, Any]:
        """ID・書き手・本文・書いた日時・AI の既読・利用者の既読・取り込んだ日時に、渡したキーを重ねた書き込みを返す。

        既定は AI が読んでいない、取り込んでいない利用者の書き込み。AI の書き込みは、渡さない限り AI の既読で、
        取り込んだ日時のキーを持たない。どちらも利用者の既読が既定で、利用者の未読にするときは `seen=False` を渡す。
        """
        post: dict[str, Any] = {
            "id": post_id,
            "author": "user",
            "body": f"{post_id}の本文",
            "created": DEFAULT_TIMESTAMP,
            "read": False,
            "seen": True,
            "taken": None,
        }
        # AI の書き込みは取り込みの対象ではないので、既読にして taken を持たせない
        if overrides.get("author") == "ai":
            post["read"] = True
            del post["taken"]
        post.update(overrides)
        return post

    return _make


@pytest.fixture
def make_thread(make_post: MakePost) -> MakeThread:
    """スレッド（threads.yaml の 1 件）を作る関数を返す。"""

    def _make(thread_id: str, *posts: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        """ID・オープン・タグなし・要約なし・渡した書き込み（無ければ 1 件）・状態の記録なしに、渡したキーを重ねたスレッドを返す。"""
        thread: dict[str, Any] = {
            "id": thread_id,
            "status": "open",
            "tags": [],
            "summary": None,
            "posts": list(posts) if posts else [make_post(f"{thread_id}-1")],
            "events": [],
        }
        thread.update(overrides)
        return thread

    return _make


@pytest.fixture
def write_threads() -> WriteThreads:
    """ワークスペースに threads.yaml を書く関数を返す。"""

    def _write(root: Path, *threads: dict[str, Any]) -> None:
        """渡したスレッドを並びのまま items に入れて、root の記録のフォルダの threads.yaml に書く。"""
        write_yaml(root / RECORD_DIR / "threads.yaml", {"items": list(threads)})

    return _write


@pytest.fixture
def make_comment() -> MakeComment:
    """レビュー中のコメント（comments.yaml の 1 件）を作る関数を返す。"""

    def _make(comment_id: str, **overrides: Any) -> dict[str, Any]:
        """ID・向けた項目・本文・溜めた日時に、渡したキーを重ねたコメントを返す。"""
        comment: dict[str, Any] = {
            "id": comment_id,
            "target": "D-1",
            "body": f"{comment_id}の本文",
            "created": DEFAULT_TIMESTAMP,
        }
        comment.update(overrides)
        return comment

    return _make


@pytest.fixture
def write_comments() -> WriteComments:
    """ワークスペースに comments.yaml を書く関数を返す。"""

    def _write(root: Path, *comments: dict[str, Any], seq: int | None = None) -> None:
        """seq と渡したコメントを並びのまま書く。seq を渡さなければコメントの ID の連番の最大にする。"""
        last = max((int(comment["id"].split("-")[1]) for comment in comments), default=0)
        write_yaml(
            root / RECORD_DIR / "comments.yaml",
            {"seq": last if seq is None else seq, "items": list(comments)},
        )

    return _write


@pytest.fixture
def make_draft() -> MakeDraft:
    """書きかけ（drafts.yaml の 1 件）を作る関数を返す。"""

    def _make(**overrides: Any) -> dict[str, Any]:
        """向けた項目・本文・書いた日時に、渡したキーを重ねた書きかけを返す。"""
        draft: dict[str, Any] = {"target": "D-1", "body": "書きかけ", "updated": DEFAULT_TIMESTAMP}
        draft.update(overrides)
        return draft

    return _make


@pytest.fixture
def write_drafts() -> WriteDrafts:
    """ワークスペースに drafts.yaml を書く関数を返す。"""

    def _write(root: Path, *drafts: dict[str, Any]) -> None:
        """渡した書きかけを並びのまま items に入れて、root の記録のフォルダの drafts.yaml に書く。"""
        write_yaml(root / RECORD_DIR / "drafts.yaml", {"items": list(drafts)})

    return _write


@pytest.fixture
def make_edit() -> MakeEdit:
    """保存待ちの編集（edits.yaml の 1 件）を作る関数を返す。"""

    def _make(edit_id: str, **overrides: Any) -> dict[str, Any]:
        """ID・向け先・編集の種類・キー・後の値・元の値・溜めたときの更新日時・溜めた日時に、渡したキーを重ねた編集を返す。

        既定は D-1 の `answer` を書き換える `set`。付け替えの対応 `map` は、渡したときだけ持つ。
        """
        edit: dict[str, Any] = {
            "id": edit_id,
            "target": "D-1",
            "op": "set",
            "key": "answer",
            "value": "答え",
            "before": None,
            "base": DEFAULT_TIMESTAMP,
            "created": DEFAULT_TIMESTAMP,
        }
        edit.update(overrides)
        return edit

    return _make


@pytest.fixture
def write_edits() -> WriteEdits:
    """ワークスペースに edits.yaml を書く関数を返す。"""

    def _write(
        root: Path, *edits: dict[str, Any], seq: int | None = None, new_seq: int | None = None
    ) -> None:
        """seq・new_seq と渡した編集を並びのまま書く。

        seq を渡さなければ編集の ID の連番の最大、new_seq を渡さなければ仮の ID の連番の最大にする。
        """
        last = max((int(edit["id"].split("-")[1]) for edit in edits), default=0)
        last_new = max(
            (
                int(edit["target"].split("-")[1])
                for edit in edits
                if str(edit["target"]).startswith("new-")
            ),
            default=0,
        )
        write_yaml(
            root / RECORD_DIR / "edits.yaml",
            {
                "seq": last if seq is None else seq,
                "new_seq": last_new if new_seq is None else new_seq,
                "items": list(edits),
            },
        )

    return _write


@pytest.fixture
def make_workspace(tmp_path: Path, valid_settings: dict[str, Any]) -> MakeWorkspace:
    """一時フォルダにワークスペースを書く関数を返す。項目は ID の頭の文字で YAML に振り分ける。"""

    def _make(
        *items: dict[str, Any],
        settings: dict[str, Any] | None = None,
        raw_files: dict[str, str] | None = None,
        bodies: dict[str, str] | None = None,
        name: str = "workspace",
        settings_file: str = "config.yaml",
        top: bool = False,
    ) -> Path:
        """項目のある種類の YAML だけを置いたワークスペースを作り、そのフォルダを返す。

        記録は直下の `.mindstella/` の下に置く。top を真にすると、v0.6.0 より前の形式として
        記録を直下に置く。設定のファイル名は settings_file で決める（v0.6.0 より前は mindmap.yaml）。
        raw_files と bodies のキーは、記録を置くフォルダからの相対パス。
        """
        root = tmp_path / name
        base = root if top else root / RECORD_DIR
        (base / "docs").mkdir(parents=True)
        (base / "release").mkdir()
        write_yaml(base / settings_file, valid_settings if settings is None else settings)
        # 項目のある種類だけ、渡した並びのまま 1 つの YAML にまとめる
        for prefix, file_name in KIND_FILES.items():
            kind_items = [item for item in items if item["id"][0] == prefix]
            if kind_items:
                write_yaml(base / file_name, {"items": kind_items})
        # 壊れた YAML や一番上が配列のファイルなど、そのまま書きたいファイルは上書きする
        for file_name, text in (raw_files or {}).items():
            (base / file_name).write_text(text, encoding="utf-8")
        for body_name, text in (bodies or {}).items():
            (base / "docs" / body_name).write_text(text, encoding="utf-8")
        return root

    return _make


@pytest.fixture
def make_legacy_item(make_item: MakeItem) -> MakeLegacyItem:
    """前の版の形式（状態の代わりに done を持つ）の資料を作る関数を返す。"""

    def _make(item_id: str, done: bool) -> dict[str, Any]:
        """status の位置に done を置いた資料を返す（キーの並びは今の形式のまま）。"""
        item = make_item(item_id)
        return {
            ("done" if key == "status" else key): (done if key == "status" else value)
            for key, value in item.items()
        }

    return _make


@pytest.fixture
def make_legacy_workspace(
    tmp_path: Path, make_workspace: MakeWorkspace, make_legacy_item: MakeLegacyItem
) -> MakeLegacyWorkspace:
    """前の版の形式（資料の done・題名の無い設定）で書いたワークスペースを作る関数を返す。"""

    def _make(
        *items: dict[str, Any],
        legacy_docs: dict[str, bool] | None = None,
        without_summary: bool = False,
        settings_file: str = "config.yaml",
        top: bool = False,
    ) -> Path:
        """items は今の形式の項目、legacy_docs は資料の ID → done。設定の題名は without_summary で外す。

        記録を置く場所と設定のファイル名は make_workspace の top・settings_file と同じ。
        """
        legacy_items = [
            make_legacy_item(doc_id, done) for doc_id, done in (legacy_docs or {}).items()
        ]
        root = make_workspace(
            *items,
            bodies={f"{item['id']}.md": "資料の本文\n" for item in legacy_items},
            settings_file=settings_file,
            top=top,
        )
        base = root if top else root / RECORD_DIR
        # 前の形式の資料を docs.yaml に直接書く（今の形式の資料の後ろに並べる）
        if legacy_items:
            docs_path = base / "docs.yaml"
            current = (
                yaml.safe_load(docs_path.read_text(encoding="utf-8"))["items"]
                if docs_path.exists()
                else []
            )
            write_yaml(docs_path, {"items": [*current, *legacy_items]})
        # 題名を持たない設定にする
        if without_summary:
            settings = yaml.safe_load((base / settings_file).read_text(encoding="utf-8"))
            del settings["summary"]
            write_yaml(base / settings_file, settings)
        return root

    return _make


@pytest.fixture
def snapshot_tree() -> SnapshotTree:
    """フォルダの下の全てのファイルを、相対パス → 中身にして返す関数を返す。"""

    def _snapshot(root: Path) -> dict[str, bytes]:
        """書き込みの前後で何も変わっていないことを比べるための写しを作る（排他ロックのファイルは除く）。"""
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.name != LOCK_FILE_NAME
        }

    return _snapshot


@pytest.fixture
def make_venv(tmp_path: Path) -> MakeVenv:
    """一時フォルダに仮想環境を作る関数を返す。ライブラリはテストを動かす Python のものを見せる。"""

    def _make(name: str, *, python: str = sys.executable, with_libraries: bool = True) -> Path:
        """pip の無い仮想環境を作る。with_libraries なら PyYAML・jsonschema を見せる（通信しない）。"""
        venv_dir = tmp_path / name
        subprocess.run([python, "-m", "venv", "--without-pip", str(venv_dir)], check=True)
        # 仮想環境の Python の場所
        python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if with_libraries:
            site_packages = subprocess.run(
                [
                    str(python_path),
                    "-c",
                    "import sysconfig; print(sysconfig.get_paths()['purelib'])",
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            # テストを動かす Python のライブラリの置き場所を、`.pth` で仮想環境に足す
            library_dirs = [
                entry for entry in sys.path if entry.endswith(("site-packages", "dist-packages"))
            ]
            (Path(site_packages) / "mindmap_test.pth").write_text(
                "\n".join(library_dirs) + "\n", encoding="utf-8"
            )
        return venv_dir

    return _make


def write_yaml(path: Path, data: Any) -> None:
    """日本語をそのままにして、キーの並びを保って YAML を書く。"""
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def plugin_version() -> str:
    """プラグインの版（`plugins/mindstella/version.ini` の 1 行目）を返す。"""
    path = REPO_ROOT / "plugins" / "mindstella" / "version.ini"
    return path.read_text(encoding="utf-8").splitlines()[0]


# 移し替えの手順の版のフォルダの名前（`v{major}.{minor}.{patch}`）
STEP_VERSION_PATTERN = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def _version_key(version: str) -> tuple[int, ...]:
    """`v0.5.0` の形の版を、大小を比べられる数の並びにする。"""
    return tuple(int(part) for part in version.removeprefix("v").split("."))


def step_versions_after(version: str | None) -> set[str]:
    """`version` より新しく、プラグインの版までの移し替えの手順の版の集まりを返す。`None` は全ての版。"""
    migrations = REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "migrations"
    plugin = _version_key(plugin_version())
    return {
        folder.name
        for folder in migrations.iterdir()
        if folder.is_dir()
        and STEP_VERSION_PATTERN.fullmatch(folder.name)
        and (version is None or _version_key(version) < _version_key(folder.name))
        and _version_key(folder.name) <= plugin
    }
