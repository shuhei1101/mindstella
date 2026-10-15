"""コメントをまとめて送る（POST /api/comments/send）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import yaml
from claude_pane_fixtures import StartClaudePane

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteThreads,
)
from .http_helpers import http_request, post_json
from .thread_helpers import read_threads, threads_path
from workspace_fixtures import RECORD_DIR, StartServer

# まとめて送るのパス
SEND_PATH = "/api/comments/send"

# 資料 A-1 の本文
A_BODY = "1 行目\n言い換えたい文\n3 行目"

# 入力が入ったと確かめて返るまでの上限秒数（確かめの上限 0.5 秒）と、入らないと分かって返るまでの上限秒数
ENTERED_RESPONSE_SEC = 0.5
NOT_ENTERED_RESPONSE_SEC = 1.0

# 偽のコマンドが書き足した行を待つ上限秒数と、確かめる間隔
TRANSCRIPT_WAIT_SEC = 5
POLL_INTERVAL_SEC = 0.05


def _read(root: Path, name: str) -> dict[str, object]:
    """ワークスペースの YAML を読む。"""
    return yaml.safe_load((root / RECORD_DIR / name).read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """チェックしたコメントだけをスレッドへ移し、残りはレビュー中に残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    loc = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}
    no_target = make_comment("C-3", body="全体に目を通した")
    del no_target["target"]
    write_comments(
        root,
        make_comment("C-1", body="案 A にする"),
        make_comment("C-2", target="A-1", loc=loc, body="ここは言い換える"),
        no_target,
    )
    url = serve_preview(root)
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    docs_before = (root / RECORD_DIR / "docs.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-2", "C-1"]})
    # 検証
    assert result.status == 201
    assert result.json()["items"] == [
        {"comment": "C-1", "thread": "TH-1", "post": "TH-1-1"},
        {"comment": "C-2", "thread": "TH-2", "post": "TH-2-1"},
    ]
    # tmux の外で立てたサーバーなので、入力しない
    assert result.json()["entered"] is False
    threads = read_threads(root)
    assert [(item["id"], item["status"], item["target"], item["summary"]) for item in threads] == [
        ("TH-1", "open", "D-1", None),
        ("TH-2", "open", "A-1", None),
    ]
    assert "loc" not in threads[0]
    assert threads[1]["loc"] == loc
    first_post = threads[0]["posts"][0]
    assert (first_post["author"], first_post["read"], first_post["taken"], first_post["comment"]) == (
        "user",
        False,
        None,
        "C-1",
    )
    # 利用者が書いたものは利用者の既読
    assert [thread["posts"][0]["seen"] for thread in threads] == [True, True]
    assert [item["id"] for item in _read(root, "comments.yaml")["items"]] == ["C-3"]
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before
    assert (root / RECORD_DIR / "docs.yaml").read_bytes() == docs_before


def test_normal_when_reply(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """返信は向けたスレッドの末尾に足し、新しいスレッドは作らない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1", make_post("TH-1-1", author="ai", body="D-1 を起票してよいですか"), summary="起票の確認"
        ),
    )
    reply = make_comment("C-1", body="起票してよい", thread="TH-1")
    del reply["target"]
    write_comments(root, reply)
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1"]})
    # 検証
    assert result.status == 201
    assert result.json()["items"] == [{"comment": "C-1", "thread": "TH-1", "post": "TH-1-2"}]
    threads = read_threads(root)
    assert [item["id"] for item in threads] == ["TH-1"]
    ai_post, user_post = threads[0]["posts"]
    assert ai_post["author"] == "ai"
    assert (user_post["author"], user_post["body"], user_post["read"], user_post["taken"]) == (
        "user",
        "起票してよい",
        False,
        None,
    )
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data is not None
    assert [item["id"] for item in awaiting.data["items"]] == ["TH-1"]


def test_error_when_ids_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """チェックが 0 件の送信は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_PATH, {"ids": []})
    # 検証
    assert result.status == 400
    assert "ids" in result.json()["detail"]
    assert not threads_path(root).exists()


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの送信は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行
    result = post_json(
        url, SEND_PATH, {"ids": ["C-1"]}, headers={"Origin": "https://attacker.example"}
    )
    # 検証
    assert result.status == 403
    assert not threads_path(root).exists()
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_error_when_comment_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """消えたコメントを含むと、どれも送らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1", "C-9"]})
    # 検証
    assert result.status == 404
    assert "C-9" in result.json()["detail"]
    assert not threads_path(root).exists()
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_error_when_location_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """本文が書き換わって箇所が合わないコメントがあれば、どれも送らない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("A-1"), bodies={"A-1.md": "1 行目\n2 行目\n3 行目"}
    )
    stale_loc = {"kind": "body", "start": 5, "end": 5, "text": "5 行目"}
    write_comments(root, make_comment("C-1"), make_comment("C-2", target="A-1", loc=stale_loc))
    url = serve_preview(root)
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1", "C-2"]})
    # 検証
    assert result.status == 409
    stale = result.json()["stale"]
    assert [item["id"] for item in stale] == ["C-2"]
    assert stale[0]["reason"] != ""
    assert not threads_path(root).exists()
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_error_when_html_body_location_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """HTML の本文が書き換わって選んだ文が無くなったコメントがあれば、どれも送らない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", body="A-1.html"),
        bodies={"A-1.html": "<style>p { color: red; }</style>\n\n\n<p>書き直した文</p>\n"},
    )
    loc = {"kind": "body", "start": 4, "end": 4, "text": "言い換えたい文"}
    write_comments(root, make_comment("C-1", target="A-1", loc=loc))
    url = serve_preview(root)
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1"]})
    # 検証
    assert result.status == 409
    assert [item["id"] for item in result.json()["stale"]] == ["C-1"]
    assert not threads_path(root).exists()
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_error_when_thread_closed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """送る前にクローズになったスレッドへの返信があれば、どれも送らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", status="closed"))
    reply = make_comment("C-1", body="了解", thread="TH-1")
    del reply["target"]
    free = make_comment("C-2", body="全体に目を通した")
    del free["target"]
    write_comments(root, reply, free)
    url = serve_preview(root)
    comments_before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    threads_before = threads_path(root).read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1", "C-2"]})
    # 検証
    assert result.status == 409
    stale = result.json()["stale"]
    assert [item["id"] for item in stale] == ["C-1"]
    assert "クローズ" in stale[0]["reason"]
    assert threads_path(root).read_bytes() == threads_before
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == comments_before


def test_error_when_not_json(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """フォームの形の本文は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(
        url,
        SEND_PATH,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="ids=C-1",
    )
    # 検証
    assert result.status == 415
    assert not threads_path(root).exists()


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、スレッドもレビュー中も前のままにする（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1"]})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert snapshot_tree(root) == before


def test_normal_when_entered_to_claude_code(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    start_server: StartServer,
    start_claude_pane: StartClaudePane,
) -> None:
    """tmux の中で立てたとき、届いた件数を Claude Code のペインへ 1 回の入力として貼り、会話の記録で確かめる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    loc = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}
    no_target = make_comment("C-3", body="全体に目を通した\n2 行目")
    del no_target["target"]
    write_comments(
        root,
        make_comment("C-1", body="案 A にする"),
        make_comment("C-2", target="A-1", loc=loc, body="ここは言い換える"),
        no_target,
    )
    pane = start_claude_pane(mode="user", cwd=root)
    server = start_server(extra_env=pane.env, cwd=root)
    opened = server.call("preview_url", workspace=str(root))
    assert opened.data is not None
    started = time.monotonic()
    # 実行
    result = post_json(str(opened.data["url"]), SEND_PATH, {"ids": ["C-1", "C-2", "C-3"]})
    elapsed = time.monotonic() - started
    # 検証
    assert result.status == 201
    assert result.json()["entered"] is True
    assert len(pane.lines()) == 1
    assert (
        '"content": "[mindstella] ユーザーからのコメントが 3 件届きました。読み直してください。"'
        in pane.lines()[0]
    )
    threads = read_threads(root)
    assert [(item["id"], item["posts"][0]["taken"]) for item in threads] == [
        ("TH-1", None),
        ("TH-2", None),
        ("TH-3", None),
    ]
    assert elapsed <= ENTERED_RESPONSE_SEC


def test_normal_when_queued(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    start_server: StartServer,
    start_claude_pane: StartClaudePane,
) -> None:
    """Claude Code が処理中で入力が待ち行列に入ったときも、入力したと返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1", body="案 A にする"))
    pane = start_claude_pane(mode="queue", cwd=root)
    server = start_server(extra_env=pane.env, cwd=root)
    opened = server.call("preview_url", workspace=str(root))
    assert opened.data is not None
    # 実行
    result = post_json(str(opened.data["url"]), SEND_PATH, {"ids": ["C-1"]})
    # 検証
    assert result.status == 201
    assert result.json()["entered"] is True
    threads = read_threads(root)
    assert [(item["id"], item["posts"][0]["taken"]) for item in threads] == [("TH-1", None)]


def test_normal_when_not_entered(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    start_server: StartServer,
    start_claude_pane: StartClaudePane,
) -> None:
    """上限までに会話の記録に入らなければ、スレッドを残したまま入力できなかったと返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1", body="案 A にする"))
    pane = start_claude_pane(mode="silent", cwd=root)
    server = start_server(extra_env=pane.env, cwd=root)
    opened = server.call("preview_url", workspace=str(root))
    assert opened.data is not None
    started = time.monotonic()
    # 実行
    result = post_json(str(opened.data["url"]), SEND_PATH, {"ids": ["C-1"]})
    elapsed = time.monotonic() - started
    # 検証
    assert result.status == 201
    assert result.json()["entered"] is False
    threads = read_threads(root)
    assert [(item["id"], item["posts"][0]["taken"]) for item in threads] == [("TH-1", None)]
    assert _read(root, "comments.yaml")["items"] == []
    assert elapsed <= NOT_ENTERED_RESPONSE_SEC
    # 標準エラーの読み取りは別のスレッドなので、理由の行が届くまで少し待つ
    deadline = time.monotonic() + TRANSCRIPT_WAIT_SEC
    while "WARNING" not in server.stderr_text() and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SEC)
    assert "Claude Code" in server.stderr_text()
    assert "WARNING" in server.stderr_text()
