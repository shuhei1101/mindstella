"""送信の取り込み（`session` が話し合いの最初と、話し合いの途中にサーバーが入力した 1 行を受けたときに、取り込み待ちのスレッドを拾って記録し、返信するか返信せずにクローズにするかを決めて取り込み済みにする）の E2E テスト。

モデルを呼ばず、手順が連ねる取り込み待ちのスレッドの一覧・スレッドを読む・`adopt`・`add`（会話ログ）・スレッドへの返信・クローズ・オープンへの戻し・取り込み済みにする・要約の書き直しを、決めた引数で順に再生する。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from conftest import Replay
from workspace_fixtures import (
    RECORD_DIR,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)

# 取り込む書き込みの本文
POST_BODY = "案 A にする"

# 話し合いの途中にサーバーが会話へ入力する 1 行（中身は記録に使わず、取り込み待ちのスレッドの一覧で読み直す）
ENTERED_LINE = "[mindstella] ユーザーからのコメントが 1 件届きました。読み直してください。"

# 資料 A-1 の本文と、2 行目を指す箇所（選んだ文は「言い換えたい文」）
BODY = "最初の文\n言い換えたい文\n最後の文\n"
SECOND_LINE = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 決める検討事項の案
OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]

# 案 A を採用した決定済みの検討事項の案
ADOPTED_A = [{"key": "A", "content": "表で見せる", "adopted": True}]

# 取り込んだ日時と、書き込みの日時
TAKEN_AT = "2026-10-12T00:30:00+00:00"
T_0100 = "2026-10-12T01:00:00+00:00"
T_0200 = "2026-10-12T02:00:00+00:00"
T_0300 = "2026-10-12T03:00:00+00:00"

# 利用者がクローズにした記録（理由なし）
USER_CLOSED = {"kind": "closed", "author": "user", "reason": None, "created": T_0300}

# AI がクローズにした記録
AI_CLOSED = {"kind": "closed", "author": "ai", "reason": "了解を受けた", "created": T_0200}


def _thread_of(root: Path, read_yaml: Callable[[Path, str], Any], thread_id: str) -> dict[str, Any]:
    """threads.yaml から、指定した ID のスレッドを返す。"""
    items = read_yaml(root, "threads.yaml")["items"]
    return next(item for item in items if item["id"] == thread_id)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """取り込み待ちのスレッドを拾い、未読の書き込みを記録して返信し、取り込み済みにして要約を書き直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    write_threads(root, make_thread("TH-1", target="D-1"))
    ws = {"workspace": str(root)}
    # 実行
    # 準備のステップ: 取り込み待ちのスレッドを読む
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    posts = replay("thread", **ws, id="TH-1")["posts"]
    # 取り込みのステップ: 書き込みの本文を記録する（案 A を採用して決定済みにし、会話ログに本文を残す）
    replay("adopt", **ws, id="D-1", key="A")
    replay("update", **ws, id="D-1", item={"status": "決定済み", "answer": "表で見せる"})
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた回答",
            "date": "2026-10-04",
            "related": ["D-1"],
            "body_markdown": POST_BODY,
        },
    )
    # 記録した後に、返信して取り込み済みにし、要約を書き直す
    replay(
        "reply",
        **ws,
        id="TH-1",
        body="D-1 を案 A で決定にしました",
        summary="D-1 の案の相談。案 A で決定",
    )
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert [item["id"] for item in awaiting] == ["TH-1"]
    assert [post["body"] for post in posts] == ["TH-1-1の本文"]
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["A"]
    assert decision["status"] == "決定済み"
    assert POST_BODY in (root / RECORD_DIR / "docs" / "L-1.md").read_text(encoding="utf-8")
    thread = _thread_of(root, read_yaml, "TH-1")
    last = thread["posts"][-1]
    assert (last["author"], "D-1" in last["body"]) == ("ai", True)
    # AI の返信は利用者の未読
    assert last["seen"] is False
    assert (thread["status"], thread["summary"]) == ("open", "D-1 の案の相談。案 A で決定")
    assert (thread["posts"][0]["read"], thread["posts"][0]["taken"] is not None) == (True, True)
    assert after == {"items": []}


def test_normal_when_nothing_awaiting(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    snapshot_tree: SnapshotTree,
) -> None:
    """取り込み待ちが無ければ、一覧が 0 件を返し、ワークスペースは何も変わらない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=False, taken=TAKEN_AT, created=T_0100),
            status="closed",
            events=[USER_CLOSED],
        ),
        make_thread(
            "TH-2",
            make_post("TH-2-1", read=False, taken=TAKEN_AT, created=T_0100),
            make_post("TH-2-2", author="ai", read=False, created=T_0200),
        ),
        make_thread(
            "TH-3",
            make_post("TH-3-1", read=False, taken=TAKEN_AT, created=T_0100),
            status="closed",
            events=[AI_CLOSED],
        ),
    )
    before = snapshot_tree(root)
    # 実行
    awaiting = replay("threads", workspace=str(root), awaiting=True)
    # 検証
    assert awaiting == {"items": []}
    assert snapshot_tree(root) == before


def test_normal_when_location_and_no_target(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """箇所を持つ書き込みと、項目を指さない書き込みを、箇所と項目なしを添えて拾い、1 件目へ返信し、2 件目は返信せずにクローズにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": BODY})
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="ここは言い換える", created=T_0100),
            target="A-1",
            loc=SECOND_LINE,
        ),
        make_thread("TH-2", make_post("TH-2-1", body="全体に目を通した", created=T_0200)),
    )
    ws = {"workspace": str(root)}
    # 実行
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    first = replay("thread", **ws, id="TH-1")
    # 箇所の書き込みは本文の行の範囲と選んだ文を添えて会話ログに残し、返信して取り込み済みにする
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた意見（A-1 の箇所）",
            "date": "2026-10-04",
            "related": ["A-1"],
            "body_markdown": "A-1 の本文の 2 行目「言い換えたい文」へ: ここは言い換える",
        },
    )
    replay("reply", **ws, id="TH-1", body="A-1 の 2 行目を直します", summary="A-1 の 2 行目の言い換え")
    # 項目を指さない書き込みは、発言と同じく会話ログに残し、返信せずにクローズにして取り込み済みにする
    second = replay("thread", **ws, id="TH-2")
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた意見（項目を指さない）",
            "date": "2026-10-04",
            "body_markdown": "全体に目を通した",
        },
    )
    replay("set_thread_status", **ws, id="TH-2", status="closed", reason="受け取った")
    replay("update_thread", **ws, id="TH-2", summary="全体に目を通したという知らせ", take=True)
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert len(awaiting) == 2
    assert (first["target"], first["target_title"], first["loc"], first["posts"][0]["body"]) == (
        "A-1",
        "A-1の題",
        SECOND_LINE,
        "ここは言い換える",
    )
    assert (second["target"], second["loc"], second["posts"][0]["body"]) == (
        None,
        None,
        "全体に目を通した",
    )
    first_log = (root / RECORD_DIR / "docs" / "L-1.md").read_text(encoding="utf-8")
    assert "2 行目「言い換えたい文」" in first_log
    assert "ここは言い換える" in first_log
    assert "全体に目を通した" in (root / RECORD_DIR / "docs" / "L-2.md").read_text(encoding="utf-8")
    first_thread = _thread_of(root, read_yaml, "TH-1")
    second_thread = _thread_of(root, read_yaml, "TH-2")
    assert (first_thread["posts"][-1]["author"], first_thread["status"]) == ("ai", "open")
    assert [post["author"] for post in second_thread["posts"]] == ["user"]
    closed = second_thread["events"][-1]
    assert (second_thread["status"], closed["author"], closed["reason"]) == (
        "closed",
        "ai",
        "受け取った",
    )
    assert first_thread["summary"] is not None
    assert second_thread["summary"] is not None
    assert all(
        post["taken"] is not None
        for thread in (first_thread, second_thread)
        for post in thread["posts"]
        if post["author"] == "user"
    )
    assert after == {"items": []}


def test_normal_when_entered_during_session(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """話し合いの途中に入力された 1 行を受けたら、一覧のスレッドだけを記録して返信し、取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    write_threads(root, make_thread("TH-1", target="D-1"))
    ws = {"workspace": str(root)}
    # 実行
    # 入力された 1 行の中身は記録に使わず、取り込み待ちのスレッドの一覧で読み直す
    assert ENTERED_LINE.startswith("[mindstella]")
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    replay("thread", **ws, id=awaiting[0]["id"])
    # 一覧にあるスレッドだけを、案 A を採用して決定済みにし、会話ログに本文を残して記録する
    replay("adopt", **ws, id="D-1", key="A")
    replay("update", **ws, id="D-1", item={"status": "決定済み", "answer": "表で見せる"})
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた回答",
            "date": "2026-10-04",
            "related": ["D-1"],
            "body_markdown": POST_BODY,
        },
    )
    # 記録した後に、返信して取り込み済みにする
    replay(
        "reply",
        **ws,
        id="TH-1",
        body="D-1 を案 A で決定にしました",
        summary="D-1 の案の相談。案 A で決定",
    )
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert [item["id"] for item in awaiting] == ["TH-1"]
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["A"]
    assert decision["status"] == "決定済み"
    assert POST_BODY in (root / RECORD_DIR / "docs" / "L-1.md").read_text(encoding="utf-8")
    last = _thread_of(root, read_yaml, "TH-1")["posts"][-1]
    assert (last["author"], "D-1" in last["body"]) == ("ai", True)
    assert after == {"items": []}


def test_normal_when_reply_to_ai_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """AI が立てたスレッドへの利用者の返信を読み、メモを足して、メモの ID を書いた返信で取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post(
                "TH-1-1",
                author="ai",
                body="D-1 の比べた結果を Issue に起票してよいですか",
                created=T_0100,
            ),
            make_post("TH-1-2", body="起票してよい", created=T_0200),
            summary="D-1 の比べた結果を Issue に起票してよいかの確認。返事待ち",
            tags=["起票"],
            target="D-1",
        ),
    )
    ws = {"workspace": str(root)}
    # 実行
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    unread = replay("thread", **ws, id="TH-1")["posts"]
    replay(
        "add",
        **ws,
        kind="note",
        item={"title": "D-1 の比べた結果を起票した", "content": "Issue に起票した"},
    )
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた返信",
            "date": "2026-10-04",
            "related": ["D-1"],
            "body_markdown": "起票してよい",
        },
    )
    replay(
        "reply",
        **ws,
        id="TH-1",
        body="起票しました。経緯は N-1 に書きました",
        summary="D-1 の比べた結果を Issue に起票した。N-1 に記録",
    )
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert [item["id"] for item in awaiting] == ["TH-1"]
    assert [(post["author"], post["body"]) for post in unread] == [("user", "起票してよい")]
    assert read_yaml(root, "notes.yaml")["items"][0]["id"] == "N-1"
    thread = _thread_of(root, read_yaml, "TH-1")
    assert [post["author"] for post in thread["posts"]] == ["ai", "user", "ai"]
    assert "N-1" in thread["posts"][-1]["body"]
    assert thread["summary"] == "D-1 の比べた結果を Issue に起票した。N-1 に記録"
    assert after == {"items": []}


def test_normal_when_no_reply_needed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """返事の要らない書き込み「了解」は、返信せずにクローズにして取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=ADOPTED_A, status="決定済み"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="案 A にする", read=True, taken=TAKEN_AT, created=T_0100),
            make_post("TH-1-2", author="ai", body="D-1 を案 A で決定にしました", created=T_0200),
            make_post("TH-1-3", body="了解", created=T_0300),
            summary="D-1 の案の相談。案 A で決定",
            target="D-1",
        ),
    )
    ws = {"workspace": str(root)}
    # 実行
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    unread = replay("thread", **ws, id="TH-1")["posts"]
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた返信",
            "date": "2026-10-04",
            "related": ["D-1"],
            "body_markdown": "了解",
        },
    )
    replay("set_thread_status", **ws, id="TH-1", status="closed", reason="了解を受けた")
    replay(
        "update_thread",
        **ws,
        id="TH-1",
        summary="D-1 の案の相談。案 A で決定し、了解を受けた",
        take=True,
    )
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert [item["id"] for item in awaiting] == ["TH-1"]
    assert [post["body"] for post in unread] == ["了解"]
    thread = _thread_of(root, read_yaml, "TH-1")
    assert [post["author"] for post in thread["posts"]] == ["user", "ai", "user"]
    closed = thread["events"][-1]
    assert (thread["status"], closed["author"], closed["reason"], bool(closed["created"])) == (
        "closed",
        "ai",
        "了解を受けた",
        True,
    )
    assert thread["posts"][2]["taken"] is not None
    assert after == {"items": []}


def test_normal_when_closed_by_user(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """利用者が返信を送ってからクローズにしたスレッドも、状態を渡さずに拾い、返信を記録して取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", author="ai", body="D-1 は案 B で進めてよいですか", created=T_0100),
            make_post("TH-1-2", body="それでよい", created=T_0200),
            status="closed",
            summary="D-1 を案 B で進めてよいかの確認。返事待ち",
            target="D-1",
            events=[USER_CLOSED],
        ),
    )
    ws = {"workspace": str(root)}
    # 実行
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    unread = replay("thread", **ws, id="TH-1")["posts"]
    replay("adopt", **ws, id="D-1", key="B")
    replay("update", **ws, id="D-1", item={"status": "決定済み", "answer": "カードで見せる"})
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた返信",
            "date": "2026-10-04",
            "related": ["D-1"],
            "body_markdown": "それでよい",
        },
    )
    replay(
        "update_thread",
        **ws,
        id="TH-1",
        summary="D-1 を案 B で進めてよいかの確認。それでよいと回答",
        take=True,
    )
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert [(item["id"], item["status"]) for item in awaiting] == [("TH-1", "closed")]
    assert [post["body"] for post in unread] == ["それでよい"]
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["B"]
    assert decision["status"] == "決定済み"
    thread = _thread_of(root, read_yaml, "TH-1")
    assert (thread["status"], len(thread["posts"])) == ("closed", 2)
    assert thread["posts"][1]["taken"] is not None
    assert after == {"items": []}


def test_normal_when_reopen_to_reply(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """クローズのスレッドに返信が要るときは、理由つきでオープンに戻してから返信して取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-2", options=ADOPTED_A, status="決定済み"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="版はどこに書く？", created=T_0100),
            status="closed",
            target="D-2",
            events=[USER_CLOSED],
        ),
    )
    ws = {"workspace": str(root)}
    # 実行
    awaiting = replay("threads", **ws, awaiting=True)["items"]
    unread = replay("thread", **ws, id="TH-1")["posts"]
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた質問",
            "date": "2026-10-04",
            "related": ["D-2"],
            "body_markdown": "版はどこに書く？",
        },
    )
    replay("set_thread_status", **ws, id="TH-1", status="open", reason="質問に答える")
    replay(
        "reply",
        **ws,
        id="TH-1",
        body="D-2 の版は config.yaml に書きます",
        summary="D-2 の版の置き場所の質問。config.yaml に書くと回答",
    )
    after = replay("threads", **ws, awaiting=True)
    # 検証
    assert [(item["id"], item["status"]) for item in awaiting] == [("TH-1", "closed")]
    assert [post["body"] for post in unread] == ["版はどこに書く？"]
    thread = _thread_of(root, read_yaml, "TH-1")
    reopened = thread["events"][-1]
    assert (thread["status"], reopened["kind"], reopened["author"], reopened["reason"]) == (
        "open",
        "reopened",
        "ai",
        "質問に答える",
    )
    assert bool(reopened["created"]) is True
    last = thread["posts"][-1]
    assert (last["author"], "D-2" in last["body"]) == ("ai", True)
    assert thread["posts"][0]["taken"] is not None
    assert after == {"items": []}
