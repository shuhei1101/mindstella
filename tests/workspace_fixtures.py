"""単体・結合・E2E のテストが共有する、ワークスペースと MCP サーバーの起動の fixture。

fixture は `tests/conftest.py` が読み込み、`tests/` の下の全てのテストが使える。
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

# このファイルから見たリポジトリの直下（tests の 1 つ上）
REPO_ROOT_PARENT_DEPTH = 1
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# MCP サーバーの入口（起動スクリプトが MCP の設定に書くスクリプト）
SERVER_SCRIPT = (
    REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts" / "server.py"
)

# 子プロセス 1 回を待つ上限秒数
COMMAND_TIMEOUT_SEC = 120

# MCP のクライアントが名乗る版（サーバーが受け入れる通信の版）
MCP_PROTOCOL_VERSION = "2025-06-18"

# サーバーが標準入力を閉じられてから終わるまで待つ上限秒数
SERVER_EXIT_TIMEOUT_SEC = 5

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
type MakeComment = Callable[..., dict[str, Any]]
type WriteComments = Callable[..., None]
type MakeDraft = Callable[..., dict[str, Any]]
type WriteDrafts = Callable[..., None]
type MakeWorkspace = Callable[..., Path]
type MakeLegacyItem = Callable[[str, bool], dict[str, Any]]
type MakeLegacyWorkspace = Callable[..., Path]
type SnapshotTree = Callable[[Path], dict[str, bytes]]
type MakeVenv = Callable[..., Path]


@dataclass(frozen=True)
class ToolResult:
    """MCP のツールの結果。`data` は構造化の結果（JSON のオブジェクト）で、エラーのときは None。"""

    is_error: bool
    text: str
    data: dict[str, Any] | None


class McpServer:
    """MCP サーバーを子プロセスとして立て、標準入出力の JSON-RPC でツールを呼ぶ同期のクライアント。"""

    def __init__(
        self, *, python: str, env: dict[str, str], cwd: Path | None, script: Path = SERVER_SCRIPT
    ) -> None:
        """サーバーを立てて初期化を済ませ、サーバーの名前を控える。"""
        self._next_id = 0
        self.process = subprocess.Popen(
            [python, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=cwd,
        )
        initialized = self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "integration-test", "version": "0"},
            },
        )
        self.server_name: str = initialized["serverInfo"]["name"]
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, message: dict[str, Any]) -> None:
        """JSON-RPC の 1 通を、標準入力へ 1 行で書く。"""
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """リクエストを送り、同じ id の応答の `result` を返す。"""
        assert self.process.stdout is not None
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params})
        line = self.process.stdout.readline()
        assert line, (
            f"サーバーが応答せずに終わりました: {self.process.stderr.read() if self.process.stderr else ''}"
        )
        response = json.loads(line)
        assert response["id"] == self._next_id
        return response["result"]

    def list_tools(self) -> list[dict[str, Any]]:
        """ツールの一覧（名前・入力のスキーマ）を返す。"""
        return self._request("tools/list", {})["tools"]

    def call(self, name: str, **arguments: Any) -> ToolResult:
        """ツールを呼び、結果の本文・エラーかどうか・構造化の結果を返す。"""
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        text = "".join(part["text"] for part in result["content"] if part["type"] == "text")
        return ToolResult(
            is_error=bool(result.get("isError")),
            text=text,
            data=result.get("structuredContent"),
        )

    def close_stdin(self) -> None:
        """標準入力を閉じる（Claude Code を閉じたのと同じ）。"""
        assert self.process.stdin is not None
        self.process.stdin.close()

    def wait_exit(self, timeout: float = SERVER_EXIT_TIMEOUT_SEC) -> int:
        """プロセスが終わるのを待ち、終了コードを返す。"""
        return self.process.wait(timeout=timeout)

    def stop(self) -> None:
        """まだ動いていれば標準入力を閉じて終わらせ、動いたままなら止める。"""
        if self.process.poll() is None:
            if self.process.stdin is not None and not self.process.stdin.closed:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=SERVER_EXIT_TIMEOUT_SEC)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()


@pytest.fixture
def start_server(tmp_path: Path) -> Iterator[StartServer]:
    """MCP サーバーを子プロセスとして立てる関数を返し、テストの後で全て止める。"""
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
        """サーバーを立てて初期化を済ませる。cwd が相対パスの workspace の基準になる。"""
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
    """テスト全体で共有する MCP サーバーを 1 つ立てて返す（立ち上げに数秒かかるため）。"""
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
