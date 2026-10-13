"""threads.py（スレッドの読み書き）の単体テスト。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

import store
import threads
from errors import (
    ArgumentError,
    ItemNotFoundError,
    SchemaMismatchError,
    ThreadClosedError,
    ThreadNotFoundError,
    WriteFailedError,
)
from fixture_types import (
    FailingReplace,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    WriteThreads,
)
from workspace_fixtures import RECORD_DIR

# now の代わりに返す日時
FIXED_NOW = "2026-10-13T03:00:00+00:00"

# 本文の 2 行目を指す箇所（資料 A-1 の本文 `A_BODY` の 2 行目）
LINE2_LOC = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 資料 A-1 の本文
A_BODY = "1 行目\n言い換えたい文\n3 行目"

# 一覧の head の文字数（設計書の定数 HEAD_CHARS）
HEAD_CHARS = 80

# 本文の上限・要約と理由の上限（設計書の定数 MAX_BODY_CHARS・MAX_SUMMARY_CHARS）
MAX_BODY_CHARS = 10000
MAX_SUMMARY_CHARS = 400

# 時刻の違う書き込みに使う日時
T_0030 = "2026-10-12T00:30:00+00:00"
T_0100 = "2026-10-12T01:00:00+00:00"
T_0200 = "2026-10-12T02:00:00+00:00"

# 古い更新日時（書き換えたかを更新日時で確かめるため、先にファイルをこの時刻へ戻す）
OLD_MTIME_SEC = 1_000_000_000


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _unexpected_now() -> str:
    """呼ばれてはいけない now の代わり。呼ばれたら失敗させる。"""
    raise AssertionError("now は呼ばれないはず")


def _read_threads(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの threads.yaml を読んで、スレッドの並びを返す。"""
    data = yaml.safe_load((root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8"))
    return data["items"]


def _find(raw: list[dict[str, Any]], thread_id: str) -> dict[str, Any]:
    """スレッドの並びから、ID のスレッドを返す。"""
    return next(thread for thread in raw if thread["id"] == thread_id)


def _post(post_id: str, *, author: str = "user", **overrides: Any) -> threads.Post:
    """書き込みを作る（取り込んでいない利用者の未読の書き込みが既定）。"""
    return threads.Post(
        id=post_id,
        author=author,
        body=f"{post_id}の本文",
        created=T_0100,
        read=author == "ai",
        **overrides,
    )


def _mtime(path: Path) -> int | None:
    """ファイルの更新日時を返す。ファイルが無ければ None。"""
    return path.stat().st_mtime_ns if path.exists() else None


def _age(path: Path) -> int | None:
    """ファイルがあれば更新日時を古い時刻へ戻し、その更新日時を返す。ファイルが無ければ None。"""
    # ファイルが無い場合は戻すものが無い
    if path.exists():
        os.utime(path, (OLD_MTIME_SEC, OLD_MTIME_SEC))
    return _mtime(path)


def test_load_threads(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """並びの順に読む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1"),
            make_post("TH-1-2", author="ai"),
            target="D-1",
            loc=LINE2_LOC,
            events=[
                {"kind": "closed", "author": "ai", "reason": None, "created": T_0100},
            ],
        ),
        make_thread("TH-2"),
    )
    # 実行
    result = threads.load_threads(root)
    # 検証
    assert [thread.id for thread in result] == ["TH-1", "TH-2"]
    assert (len(result[0].posts), len(result[0].events)) == (2, 1)
    assert (result[1].target, result[1].loc) == (None, None)


def test_load_threads_when_missing(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ空（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = threads.load_threads(root)
    # 検証
    assert result == []


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("items: [", id="unreadable"),
        pytest.param(
            "items:\n  - id: TH-1\n    status: open\n    tags: []\n    summary: null\n    events: []\n",
            id="posts_removed",
        ),
        pytest.param(
            "items:\n  - id: TH-1\n    status: done\n    tags: []\n    summary: null\n"
            "    posts:\n      - id: TH-1-1\n        author: user\n        body: 本文\n"
            "        created: 2026-10-12T00:00:00+00:00\n        read: false\n        taken: null\n"
            "    events: []\n",
            id="status_done",
        ),
    ],
)
def test_load_threads_when_invalid(
    make_workspace: MakeWorkspace, make_item: MakeItem, text: str
) -> None:
    """読めない・合わないファイルは読まない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"threads.yaml": text})
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        threads.load_threads(root)
    assert exc_info.value.lines[0].startswith("threads.yaml: ")


def test_write_threads(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """持たないキーを書かず、読み直すと同じになる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    written = [
        threads.Thread(
            id="TH-1",
            status="open",
            tags=[],
            summary=None,
            posts=[_post("TH-1-1"), _post("TH-1-2", author="ai")],
            events=[],
        )
    ]
    # 実行
    threads._write_threads(root, written)
    # 検証
    assert threads.load_threads(root) == written
    raw = _find(_read_threads(root), "TH-1")
    assert ("target" in raw, "loc" in raw, raw["summary"]) == (False, False, None)
    user_post, ai_post = raw["posts"]
    assert user_post["taken"] is None
    assert "taken" not in ai_post
    assert ("comment" in user_post, "comment" in ai_post) == (False, False)


def test_write_threads_when_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    failing_replace: FailingReplace,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """置き換えに失敗したら前のスレッドを残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    monkeypatch.setattr(threads.os, "replace", failing_replace("threads.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        threads._write_threads(root, threads.load_threads(root))
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == before
    assert list(root.rglob("*.tmp")) == []


RAW_THREADS = (
    "items:\n"
    "  - id: TH-1\n    status: waiting\n    target: D-9\n"
    "    posts:\n      - {author: user, taken: null}\n"
    "  - id: TH-2\n    status: closed\n    target: D-1\n"
    "    posts:\n      - {author: user, taken: '2026-10-12T00:30:00+00:00'}\n"
    "  - id: TH-3\n    status: open\n"
    "  - id: 4\n    target: D-1\n"
    "  - id: TH-5\n    target: 7\n"
)


def test_raw_thread_targets(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """合わないファイルから、ID と向けた項目が文字列のスレッドだけを、取り込み待ちかを添えて拾う（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"threads.yaml": RAW_THREADS})
    # 実行
    result = threads.raw_thread_targets(root)
    # 検証
    assert result == [("TH-1", "D-9", True), ("TH-2", "D-1", False)]


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(": : :\n  - [", id="not_yaml"),
        pytest.param("items: 3\n", id="items_not_list"),
        pytest.param("- id: TH-1\n", id="not_mapping"),
    ],
)
def test_raw_thread_targets_when_unreadable(
    make_workspace: MakeWorkspace, make_item: MakeItem, text: str
) -> None:
    """読めない・スレッドの並びでないファイルは、拾えるものが無い（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"threads.yaml": text})
    # 実行
    result = threads.raw_thread_targets(root)
    # 検証
    assert result == []


def test_awaiting_posts() -> None:
    """取り込んでいない利用者の書き込みだけを返す（正常系）。"""
    # 準備
    with_awaiting = threads.Thread(
        id="TH-1",
        status="open",
        tags=[],
        summary=None,
        posts=[
            _post("TH-1-1", taken=T_0100),
            _post("TH-1-2", author="ai"),
            _post("TH-1-3"),
        ],
        events=[],
    )
    only_ai = threads.Thread(
        id="TH-2",
        status="open",
        tags=[],
        summary=None,
        posts=[_post("TH-2-1", author="ai")],
        events=[],
    )
    # 実行
    result = (threads.awaiting_posts(with_awaiting), threads.awaiting_posts(only_ai))
    # 検証
    assert [post.id for post in result[0]] == ["TH-1-3"]
    assert result[1] == []


def test_list_threads(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """既定はオープンだけを最後の書き込みの新しい順に返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="写しの取り方"))
    two_lines = "a" * 49 + "\n" + "b" * 50
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", created=T_0030),
            make_post("TH-1-2", author="ai", created=T_0100),
            target="D-1",
            summary="写しの話",
        ),
        make_thread("TH-2", status="closed"),
        make_thread(
            "TH-3",
            make_post("TH-3-1", body=two_lines, created=T_0200),
        ),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = threads.list_threads(workspace)
    # 検証
    assert [row["id"] for row in result] == ["TH-3", "TH-1"]
    by_id = {row["id"]: row for row in result}
    assert (by_id["TH-1"]["target_title"], by_id["TH-1"]["last_author"]) == ("写しの取り方", "ai")
    assert by_id["TH-3"]["summary"] is None
    assert by_id["TH-3"]["head"] == "a" * 49 + " " + "b" * (HEAD_CHARS - 50)


@pytest.mark.parametrize(
    ("kwargs", "expected_ids"),
    [
        pytest.param({"awaiting": True}, ["TH-1", "TH-2"], id="status_omitted"),
        pytest.param({"awaiting": True, "status": "open"}, ["TH-1"], id="status_open"),
    ],
)
def test_list_threads_when_awaiting(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    kwargs: dict[str, Any],
    expected_ids: list[str],
) -> None:
    """取り込み待ちは状態を渡さなければクローズも返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1", created=T_0100)),
        make_thread("TH-2", make_post("TH-2-1", created=T_0030), status="closed"),
        make_thread("TH-3", make_post("TH-3-1", taken=T_0100)),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = threads.list_threads(workspace, **kwargs)
    # 検証
    assert sorted(row["id"] for row in result) == expected_ids
    assert all(row["awaiting"] >= 1 for row in result)


def test_list_threads_when_tag_and_unread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """タグと未読を両方満たすものだけ返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True),
            make_post("TH-1-2", read=False),
            tags=["画面"],
        ),
        make_thread("TH-2", make_post("TH-2-1", read=True), tags=["画面"]),
        make_thread("TH-3", make_post("TH-3-1", read=False), tags=["起票"]),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = threads.list_threads(workspace, tag="画面", unread=True)
    # 検証
    assert [(row["id"], row["unread"]) for row in result] == [("TH-1", 1)]


@pytest.mark.parametrize(
    ("raw_files", "expected"),
    [
        pytest.param(
            {
                "threads.yaml": (
                    "items:\n"
                    "  - {id: TH-2, status: open, tags: [], summary: null, events: [],\n"
                    "     posts: [{id: TH-2-1, author: user, body: 本文, created: '2026-10-12T01:00:00+00:00', read: false, taken: null}]}\n"
                    "  - {id: TH-10, status: open, tags: [], summary: null, events: [],\n"
                    "     posts: [{id: TH-10-1, author: user, body: 本文, created: '2026-10-12T01:00:00+00:00', read: false, taken: null}]}\n"
                )
            },
            [("TH-10", None, None), ("TH-2", None, None)],
            id="same_time",
        ),
        pytest.param({}, [], id="missing_file"),
        pytest.param(
            {
                "threads.yaml": (
                    "items:\n"
                    "  - {id: TH-1, status: open, tags: [], summary: null, events: [], target: D-9,\n"
                    "     posts: [{id: TH-1-1, author: user, body: 本文, created: '2026-10-12T01:00:00+00:00', read: false, taken: null}]}\n"
                )
            },
            [("TH-1", "D-9", None)],
            id="removed_target",
        ),
    ],
)
def test_list_threads_when_same_time_or_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    raw_files: dict[str, str],
    expected: list[tuple[str, str | None, str | None]],
) -> None:
    """同じ日時は連番の大きい順。ファイルが無ければ空。消えた項目はタイトルを None にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files=raw_files)
    workspace = store.load_workspace(root)
    # 実行
    result = threads.list_threads(workspace)
    # 検証
    assert [(row["id"], row["target"], row["target_title"]) for row in result] == expected


@pytest.mark.parametrize(
    ("kwargs", "expected_post_ids"),
    [
        pytest.param({}, ["TH-1-3"], id="unread_only"),
        pytest.param({"unread_only": False}, ["TH-1-1", "TH-1-2", "TH-1-3"], id="all"),
    ],
)
def test_view_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    kwargs: dict[str, Any],
    expected_post_ids: list[str],
) -> None:
    """未読だけか全部かを選ぶ（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True, taken=T_0100),
            make_post("TH-1-2", author="ai"),
            make_post("TH-1-3", read=False),
            events=[{"kind": "closed", "author": "ai", "reason": None, "created": T_0200}],
        ),
    )
    workspace = store.load_workspace(root)
    # 実行
    view, unread_ids = threads.view_thread(workspace, "TH-1", **kwargs)
    # 検証
    assert [post["id"] for post in view["posts"]] == expected_post_ids
    assert unread_ids == ["TH-1-3"]
    assert len(view["events"]) == 1
    assert next(post for post in view["posts"] if post["id"] == "TH-1-3")["read"] is False


def test_view_thread_when_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """無い ID は読まない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    workspace = store.load_workspace(root)
    # 実行・検証
    with pytest.raises(ThreadNotFoundError, match="TH-9"):
        threads.view_thread(workspace, "TH-9")


def test_mark_read(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """渡した書き込みだけを既読にし、取り込み済みは変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root, make_thread("TH-1", make_post("TH-1-1"), make_post("TH-1-2"))
    )
    # 実行
    threads.mark_read(root, "TH-1", ["TH-1-1"])
    # 検証
    first, second = _find(_read_threads(root), "TH-1")["posts"]
    assert (first["read"], second["read"]) == (True, False)
    assert (first["taken"], second["taken"]) == (None, None)


def test_mark_read_when_nothing_changes(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """既に既読なら書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", read=True)))
    mtime_before = _age(root / RECORD_DIR / "threads.yaml")
    # 実行
    threads.mark_read(root, "TH-1", ["TH-1-1"])
    # 検証
    assert (root / RECORD_DIR / "threads.yaml").stat().st_mtime_ns == mtime_before


def test_create_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """連番を振って AI の既読の書き込みで立てる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"), make_thread("TH-3"))
    workspace = store.load_workspace(root)
    # 実行
    result = threads.create_thread(
        workspace,
        body=" 起票してよいですか ",
        summary="起票の確認",
        tags=["起票"],
        target="D-1",
        now=_fixed_now,
    )
    # 検証
    assert result == ("TH-4", "TH-4-1", FIXED_NOW)
    created = _find(_read_threads(root), "TH-4")
    assert (created["status"], created["tags"], created["events"]) == ("open", ["起票"], [])
    assert (created["summary"], created["target"]) == ("起票の確認", "D-1")
    post = created["posts"][0]
    assert (post["author"], post["read"], post["body"]) == ("ai", True, "起票してよいですか")
    assert "taken" not in post


def test_create_thread_when_first(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ作って TH-1。項目を指さないスレッドは target を書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    # 実行
    thread_id, _, _ = threads.create_thread(
        workspace, body="お知らせ", summary="知らせ", now=_fixed_now
    )
    # 検証
    assert thread_id == "TH-1"
    assert "target" not in _find(_read_threads(root), "TH-1")


@pytest.mark.parametrize(
    ("params", "exception", "argument"),
    [
        pytest.param({"body": "  "}, ArgumentError, "body", id="blank_body"),
        pytest.param(
            {"summary": "あ" * (MAX_SUMMARY_CHARS + 1)}, ArgumentError, "summary", id="long_summary"
        ),
        pytest.param({"tags": ["a", "a"]}, ArgumentError, "tags", id="duplicated_tags"),
        pytest.param({"tags": [""]}, ArgumentError, "tags", id="empty_tag"),
        pytest.param({"target": "D-99"}, ItemNotFoundError, None, id="missing_target"),
    ],
)
def test_create_thread_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    params: dict[str, Any],
    exception: type[Exception],
    argument: str | None,
) -> None:
    """形の誤りと無い項目は立てない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    kwargs = {"body": "本文", "summary": "要約", **params}
    # 実行・検証
    with pytest.raises(exception) as exc_info:
        threads.create_thread(workspace, now=_fixed_now, **kwargs)
    assert getattr(exc_info.value, "argument", None) == argument
    assert not (root / RECORD_DIR / "threads.yaml").exists()


def test_create_thread_when_boundary(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ちょうど上限の本文と要約を受ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    # 実行
    threads.create_thread(
        workspace,
        body="あ" * MAX_BODY_CHARS,
        summary="い" * MAX_SUMMARY_CHARS,
        now=_fixed_now,
    )
    # 検証
    created = _find(_read_threads(root), "TH-1")
    assert len(created["posts"][0]["body"]) == MAX_BODY_CHARS
    assert len(created["summary"]) == MAX_SUMMARY_CHARS


def test_reply_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """返信を足し、要約を書き直し、既読の書き込みだけを取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True),
            make_post("TH-1-2", read=False),
        ),
    )
    # 実行
    result = threads.reply_thread(
        root, "TH-1", body="返信です", summary="書き直した要約", now=_fixed_now
    )
    # 検証
    assert result == ("TH-1-3", FIXED_NOW, ["TH-1-1"])
    raw = _find(_read_threads(root), "TH-1")
    assert raw["summary"] == "書き直した要約"
    first, second, reply = raw["posts"]
    assert (first["taken"], second["taken"]) == (FIXED_NOW, None)
    assert (reply["author"], reply["read"]) == ("ai", True)


def test_reply_thread_when_no_take(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """take が偽なら取り込み済みにしない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", read=True)))
    # 実行
    _, _, taken = threads.reply_thread(
        root, "TH-1", body="返信です", summary="要約", take=False, now=_fixed_now
    )
    # 検証
    assert taken == []
    assert _find(_read_threads(root), "TH-1")["posts"][0]["taken"] is None


@pytest.mark.parametrize(
    ("thread_id", "body", "summary", "exception", "message"),
    [
        pytest.param("TH-2", "返信", "要約", ThreadClosedError, "set_thread_status", id="closed"),
        pytest.param("TH-9", "返信", "要約", ThreadNotFoundError, "TH-9", id="not_found"),
        pytest.param("TH-1", "", "要約", ArgumentError, "body", id="empty_body"),
        pytest.param(
            "TH-1", "返信", "あ" * (MAX_SUMMARY_CHARS + 1), ArgumentError, "summary", id="long_summary"
        ),
    ],
)
def test_reply_thread_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    thread_id: str,
    body: str,
    summary: str,
    exception: type[Exception],
    message: str,
) -> None:
    """クローズ・無い ID・形の誤りは書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"), make_thread("TH-2", status="closed"))
    before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(exception, match=message):
        threads.reply_thread(root, thread_id, body=body, summary=summary, now=_fixed_now)
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == before


def test_set_thread_status(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """クローズにして記録を足し、取り込み待ちは変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    # 実行
    changed = threads.set_thread_status(
        root, "TH-1", status="closed", reason=" 案 A で決着 ", author="ai", now=_fixed_now
    )
    # 検証
    assert changed is True
    raw = _find(_read_threads(root), "TH-1")
    assert raw["status"] == "closed"
    assert raw["events"][-1] == {
        "kind": "closed",
        "author": "ai",
        "reason": "案 A で決着",
        "created": FIXED_NOW,
    }
    assert raw["posts"][0]["taken"] is None


def test_set_thread_status_when_reopen(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """オープンに戻す。空白だけの理由は持たない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", status="closed"))
    # 実行
    changed = threads.set_thread_status(
        root, "TH-1", status="open", reason="  ", author="user", now=_fixed_now
    )
    # 検証
    assert changed is True
    last = _find(_read_threads(root), "TH-1")["events"][-1]
    assert (last["kind"], last["author"], last["reason"]) == ("reopened", "user", None)


def test_set_thread_status_when_same(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """既にその状態なら書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    mtime_before = _age(root / RECORD_DIR / "threads.yaml")
    # 実行
    changed = threads.set_thread_status(
        root, "TH-1", status="open", author="ai", now=_unexpected_now
    )
    # 検証
    assert changed is False
    assert (root / RECORD_DIR / "threads.yaml").stat().st_mtime_ns == mtime_before


@pytest.mark.parametrize(
    ("thread_id", "status", "reason", "exception", "argument"),
    [
        pytest.param("TH-1", "done", None, ArgumentError, "status", id="bad_status"),
        pytest.param(
            "TH-1", "closed", "あ" * (MAX_SUMMARY_CHARS + 1), ArgumentError, "reason", id="long_reason"
        ),
        pytest.param("TH-9", "closed", None, ThreadNotFoundError, None, id="not_found"),
    ],
)
def test_set_thread_status_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    thread_id: str,
    status: str,
    reason: str | None,
    exception: type[Exception],
    argument: str | None,
) -> None:
    """形の誤りと無い ID は書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(exception) as exc_info:
        threads.set_thread_status(
            root, thread_id, status=status, reason=reason, author="ai", now=_fixed_now
        )
    assert getattr(exc_info.value, "argument", None) == argument
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == before


def test_update_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """クローズのスレッドの既読の書き込みを取り込み済みにし、要約を書き直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", author="ai"),
            make_post("TH-1-2", read=True),
            status="closed",
            tags=["画面"],
            events=[{"kind": "closed", "author": "user", "reason": None, "created": T_0100}],
        ),
    )
    # 実行
    taken = threads.update_thread(root, "TH-1", summary="書き直した要約", take=True, now=_fixed_now)
    # 検証
    assert taken == ["TH-1-2"]
    raw = _find(_read_threads(root), "TH-1")
    assert (raw["summary"], raw["posts"][1]["taken"]) == ("書き直した要約", FIXED_NOW)
    assert (raw["tags"], raw["status"], len(raw["events"])) == (["画面"], "closed", 1)


@pytest.mark.parametrize(
    "tags",
    [
        pytest.param(["起票", "資料"], id="replace"),
        pytest.param([], id="clear"),
    ],
)
def test_update_thread_when_tags(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    tags: list[str],
) -> None:
    """タグを置き換える・外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", tags=["画面"], summary="前の要約"))
    # 実行
    taken = threads.update_thread(root, "TH-1", tags=tags, now=_fixed_now)
    # 検証
    assert taken == []
    raw = _find(_read_threads(root), "TH-1")
    assert (raw["tags"], raw["summary"]) == (tags, "前の要約")


@pytest.mark.parametrize(
    ("thread_id", "kwargs", "exception", "argument"),
    [
        pytest.param("TH-1", {}, ArgumentError, "summary", id="nothing"),
        pytest.param("TH-1", {"summary": " "}, ArgumentError, "summary", id="blank_summary"),
        pytest.param("TH-1", {"tags": ["a", "a"]}, ArgumentError, "tags", id="duplicated_tags"),
        pytest.param("TH-9", {"take": True}, ThreadNotFoundError, None, id="not_found"),
    ],
)
def test_update_thread_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    thread_id: str,
    kwargs: dict[str, Any],
    exception: type[Exception],
    argument: str | None,
) -> None:
    """変えるものが無い・形の誤り・無い ID は書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(exception) as exc_info:
        threads.update_thread(root, thread_id, now=_fixed_now, **kwargs)
    assert getattr(exc_info.value, "argument", None) == argument
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == before


def _input(comment: str, **overrides: Any) -> threads.UserPostInput:
    """足す利用者の書き込みを作る（新しいスレッドの最初の書き込みで項目 D-1 を指すのが既定）。"""
    values: dict[str, Any] = {
        "comment": comment,
        "thread": None,
        "target": "D-1",
        "loc": None,
        "body": f"{comment}の本文",
    }
    values.update(overrides)
    return threads.UserPostInput(**values)


def test_append_user_posts(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """新しいスレッドを立て、返信を末尾に足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1"), make_post("TH-1-2")),
        make_thread("TH-3", make_post("TH-3-1"), make_post("TH-3-2")),
    )
    posts = [
        _input("C-1"),
        _input("C-2", target="A-1", loc=LINE2_LOC),
        _input("C-3", target=None),
        _input("C-4", thread="TH-1", target=None),
    ]
    # 実行
    sent_at, sent = threads.append_user_posts(root, posts, now=_fixed_now)
    # 検証
    assert sent_at == FIXED_NOW
    assert [(item.comment, item.thread, item.post) for item in sent] == [
        ("C-1", "TH-4", "TH-4-1"),
        ("C-2", "TH-5", "TH-5-1"),
        ("C-3", "TH-6", "TH-6-1"),
        ("C-4", "TH-1", "TH-1-3"),
    ]
    raw = _read_threads(root)
    new_thread = _find(raw, "TH-4")
    assert (new_thread["status"], new_thread["tags"], new_thread["summary"]) == ("open", [], None)
    assert new_thread["target"] == "D-1"
    assert _find(raw, "TH-5")["loc"] == LINE2_LOC
    assert ("target" in _find(raw, "TH-6"), "loc" in _find(raw, "TH-6")) == (False, False)
    reply = _find(raw, "TH-1")["posts"][2]
    assert (reply["author"], reply["read"], reply["taken"], reply["comment"]) == (
        "user",
        False,
        None,
        "C-4",
    )
    assert (reply["created"], reply["body"]) == (FIXED_NOW, "C-4の本文")


def test_append_user_posts_when_first(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ作って TH-1（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    _, sent = threads.append_user_posts(root, [_input("C-1")], now=_fixed_now)
    # 検証
    assert [(item.comment, item.thread, item.post) for item in sent] == [
        ("C-1", "TH-1", "TH-1-1")
    ]
    assert (root / RECORD_DIR / "threads.yaml").exists()


def test_append_user_posts_when_already_sent(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """既に送ったコメントは足さずにその書き込みを返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", comment="C-1")))
    # 実行
    _, sent = threads.append_user_posts(root, [_input("C-1"), _input("C-2")], now=_fixed_now)
    # 検証
    assert [(item.comment, item.thread, item.post) for item in sent] == [
        ("C-1", "TH-1", "TH-1-1"),
        ("C-2", "TH-2", "TH-2-1"),
    ]
    raw = _read_threads(root)
    assert (len(raw), len(_find(raw, "TH-1")["posts"])) == (2, 1)


def test_append_user_posts_when_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    failing_replace: FailingReplace,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """置き換えに失敗したら前のスレッドを残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    monkeypatch.setattr(threads.os, "replace", failing_replace("threads.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        threads.append_user_posts(root, [_input("C-1")], now=_fixed_now)
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == before


def test_threads_for_preview(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """クローズも含めて返し、既読と取り込み済みを含めない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="写しの取り方"))
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1", created=T_0100), target="D-1"),
        make_thread(
            "TH-2",
            make_post("TH-2-1", created=T_0200, comment="C-1"),
            status="closed",
            target="D-9",
            events=[{"kind": "closed", "author": "user", "reason": None, "created": T_0200}],
        ),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = threads.threads_for_preview(workspace)
    # 検証
    assert [thread["id"] for thread in result["threads"]] == ["TH-2", "TH-1"]
    second, first = result["threads"]
    assert (first["target_title"], second["target_title"]) == ("写しの取り方", None)
    assert len(second["events"]) == 1
    for post in first["posts"] + second["posts"]:
        assert {"read", "taken", "comment"}.isdisjoint(post)


def test_threads_for_preview_when_missing(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """ファイルが無ければ空（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    # 実行
    result = threads.threads_for_preview(workspace)
    # 検証
    assert result == {"threads": []}


def test_reset_unread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """既読を全て未読に戻し、ほかは変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    events = [{"kind": "closed", "author": "ai", "reason": None, "created": T_0200}]
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True, taken=T_0100),
            make_post("TH-1-2", author="ai"),
            make_post("TH-1-3", read=True),
            make_post("TH-1-4", read=False),
            status="closed",
            summary="要約",
            tags=["画面"],
            events=events,
        ),
    )
    # 実行
    count = threads.reset_unread(root)
    # 検証
    assert count == 3
    raw = _find(_read_threads(root), "TH-1")
    assert [post["read"] for post in raw["posts"]] == [False, False, False, False]
    assert raw["posts"][0]["taken"] == T_0100
    assert (raw["status"], raw["summary"], raw["tags"], raw["events"]) == (
        "closed",
        "要約",
        ["画面"],
        events,
    )


@pytest.mark.parametrize(
    "raw_files",
    [
        pytest.param(
            {
                "threads.yaml": (
                    "items:\n"
                    "  - {id: TH-1, status: open, tags: [], summary: null, events: [],\n"
                    "     posts: [{id: TH-1-1, author: user, body: 本文, created: '2026-10-12T01:00:00+00:00', read: false, taken: null}]}\n"
                )
            },
            id="all_unread",
        ),
        pytest.param({}, id="missing_file"),
    ],
)
def test_reset_unread_when_nothing(
    make_workspace: MakeWorkspace, make_item: MakeItem, raw_files: dict[str, str]
) -> None:
    """全て未読かファイルが無ければ書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files=raw_files)
    state_before = _age(root / RECORD_DIR / "threads.yaml")
    # 実行
    count = threads.reset_unread(root)
    # 検証
    assert count == 0
    assert _mtime(root / RECORD_DIR / "threads.yaml") == state_before
