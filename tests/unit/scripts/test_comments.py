"""comments.py（レビュー中のコメントと書きかけの読み書き・まとめて送る）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import comments
import errors
import locations
import store
from errors import (
    CommentConflictError,
    CommentInvalidError,
    CommentNotFoundError,
    ItemNotFoundError,
    MindmapError,
    SchemaMismatchError,
    WriteFailedError,
)
from fixture_types import (
    FailingReplace,
    MakeComment,
    MakeDraft,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    WriteComments,
    WriteDrafts,
    WriteThreads,
)
from workspace_fixtures import RECORD_DIR

# now の代わりに返す日時
FIXED_NOW = "2026-10-05T03:00:00+00:00"

# 項目・コメントに入れる既定の日時
DEFAULT_TIMESTAMP = "2026-10-01T00:00:00+00:00"

# 本文の上限（非機能要件の「送信の本文の長さ」）
MAX_BODY_CHARS = 10000

# 本文の 2 行目を指す箇所（A-1 の本文 `A_BODY` の 2 行目）
LINE2_LOC = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 資料 A-1 の本文
A_BODY = "1 行目\n言い換えたい文\n3 行目"


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _unexpected_now() -> str:
    """今の日時を引かない処理で呼ばれたら失敗させる。"""
    raise AssertionError("now は呼ばれないはず")


def _read_comments(root: Path) -> dict[str, Any]:
    """ワークスペースの comments.yaml を読んで返す。"""
    return yaml.safe_load((root / RECORD_DIR / "comments.yaml").read_text(encoding="utf-8"))


def _read_drafts(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの drafts.yaml の書きかけの並びを返す（ファイルが無ければ空）。"""
    path = root / RECORD_DIR / "drafts.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"]


def _read_threads(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの threads.yaml のスレッドの並びを返す。"""
    data = yaml.safe_load((root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8"))
    return data["items"]


def _reply_comment(comment_id: str, thread: str) -> dict[str, Any]:
    """スレッドへの返信のレビュー中のコメント（target・loc を持たない）を作る。"""
    return {
        "id": comment_id,
        "thread": thread,
        "body": f"{comment_id}の本文",
        "created": DEFAULT_TIMESTAMP,
    }


def _reply_draft(thread: str, body: str = "書きかけ") -> dict[str, Any]:
    """スレッドへの返信の書きかけ（target・loc を持たない）を作る。"""
    return {"thread": thread, "body": body, "updated": DEFAULT_TIMESTAMP}


def test_load_comments(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
) -> None:
    """連番の順に読む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-3"), make_comment("C-1"), seq=3)
    # 実行
    result = comments.load_comments(root)
    # 検証
    assert result.seq == 3
    assert [comment.id for comment in result.items] == ["C-1", "C-3"]


def test_load_comments_when_missing(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ空（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = comments.load_comments(root)
    # 検証
    assert result == comments.CommentFile(seq=0, items=[])


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("items: [", id="unreadable"),
        pytest.param(
            "seq: 1\nitems:\n  - id: C-1\n    target: D-1\n    created: 2026-10-01T00:00:00+00:00\n",
            id="body_removed",
        ),
    ],
)
def test_load_comments_when_invalid(
    make_workspace: MakeWorkspace, make_item: MakeItem, text: str
) -> None:
    """読めない・合わないファイルは読まない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"comments.yaml": text})
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        comments.load_comments(root)
    assert exc_info.value.lines[0].startswith("comments.yaml: ")


@pytest.mark.parametrize(
    ("drafts", "expected_targets"),
    [
        pytest.param(
            [
                {"target": "D-1", "body": "案 A に", "updated": DEFAULT_TIMESTAMP},
                {"body": "全体に", "updated": DEFAULT_TIMESTAMP},
            ],
            ["D-1", None],
            id="with_and_without_target",
        ),
        pytest.param(None, [], id="missing"),
    ],
)
def test_load_drafts(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    write_drafts: WriteDrafts,
    drafts: list[dict[str, Any]] | None,
    expected_targets: list[str | None],
) -> None:
    """書きかけを読む。無ければ空（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    if drafts is not None:
        write_drafts(root, *drafts)
    # 実行
    result = comments.load_drafts(root)
    # 検証
    assert [draft.target for draft in result] == expected_targets


def test_list_review(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_draft: MakeDraft,
    write_comments: WriteComments,
    write_drafts: WriteDrafts,
) -> None:
    """タイトルを付けて書きかけと返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="問い"))
    no_target = make_comment("C-3")
    del no_target["target"]
    write_comments(root, make_comment("C-1"), make_comment("C-2", target="D-9"), no_target)
    write_drafts(root, make_draft(target="D-1", body="案 B も見たい"))
    workspace = store.load_workspace(root)
    # 実行
    result = comments.list_review(workspace)
    # 検証
    assert [(item["id"], item["target_title"]) for item in result["items"]] == [
        ("C-1", "問い"),
        ("C-2", None),
        ("C-3", None),
    ]
    assert result["drafts"] == [
        {"target": "D-1", "loc": None, "thread": None, "body": "案 B も見たい"}
    ]


def test_list_review_when_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    write_comments: WriteComments,
    write_drafts: WriteDrafts,
) -> None:
    """返信と返信の書きかけは返信先を持つ（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, _reply_comment("C-1", "TH-1"))
    write_drafts(root, _reply_draft("TH-1"))
    workspace = store.load_workspace(root)
    # 実行
    result = comments.list_review(workspace)
    # 検証
    reply = result["items"][0]
    assert reply["thread"] == "TH-1"
    assert (reply["target"], reply["target_title"], reply["loc"]) == (None, None, None)
    assert [draft["thread"] for draft in result["drafts"]] == ["TH-1"]


def test_add_comment(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_draft: MakeDraft,
    write_comments: WriteComments,
    write_drafts: WriteDrafts,
) -> None:
    """連番を振って溜め、書きかけを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-2"), seq=2)
    write_drafts(root, make_draft(target="D-1"))
    # 実行
    comment, count = comments.add_comment(
        root, {"target": "D-1", "body": "  案 A にする "}, now=_fixed_now
    )
    # 検証
    assert comment == comments.ReviewComment(
        id="C-3", target="D-1", loc=None, body="案 A にする", created=FIXED_NOW
    )
    assert count == 2
    assert _read_comments(root)["seq"] == 3
    assert _read_drafts(root) == []


@pytest.mark.parametrize(
    ("data", "expected_target", "expected_loc"),
    [
        pytest.param(
            {"target": "A-1", "loc": LINE2_LOC, "body": "ここは言い換える"},
            "A-1",
            LINE2_LOC,
            id="location",
        ),
        pytest.param({"body": "全体に目を通した"}, None, None, id="no_target"),
    ],
)
def test_add_comment_when_location_and_no_target(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    data: dict[str, Any],
    expected_target: str | None,
    expected_loc: dict[str, Any] | None,
) -> None:
    """箇所を持つコメントと項目を指さないコメントを溜める（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": A_BODY})
    # 実行
    comment, _count = comments.add_comment(root, data, now=_fixed_now)
    # 検証
    assert comment.target == expected_target
    assert (
        None if comment.loc is None else locations.location_to_dict(comment.loc)
    ) == expected_loc
    saved = _read_comments(root)["items"][-1]
    assert saved.get("target") == expected_target
    assert saved.get("loc") == expected_loc


def test_add_comment_when_restore(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
) -> None:
    """消したコメントを同じ ID と日時で元の並びに戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"), make_comment("C-3"), seq=3)
    restored = {
        "id": "C-2",
        "created": "2026-10-05T01:00:00+00:00",
        "target": "D-1",
        "body": "戻すコメント",
    }
    # 実行
    comments.add_comment(root, restored, now=_unexpected_now)
    # 検証
    saved = _read_comments(root)
    assert saved["seq"] == 3
    assert [(item["id"], item["created"]) for item in saved["items"]] == [
        ("C-1", DEFAULT_TIMESTAMP),
        ("C-2", "2026-10-05T01:00:00+00:00"),
        ("C-3", DEFAULT_TIMESTAMP),
    ]


@pytest.mark.parametrize(
    ("data", "expected_error"),
    [
        pytest.param({"target": "D-99", "body": "本文"}, ItemNotFoundError, id="target_missing"),
        pytest.param(
            {
                "target": "A-1",
                "loc": {"kind": "body", "start": 1, "end": 1, "text": "本文に無い文"},
                "body": "本文",
            },
            CommentConflictError,
            id="location_stale",
        ),
        pytest.param(
            {"id": "C-1", "created": DEFAULT_TIMESTAMP, "target": "D-1", "body": "本文"},
            CommentConflictError,
            id="restore_existing_id",
        ),
        pytest.param(
            {"id": "C-9", "created": DEFAULT_TIMESTAMP, "target": "D-1", "body": "本文"},
            CommentConflictError,
            id="restore_beyond_seq",
        ),
    ],
)
def test_add_comment_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    data: dict[str, Any],
    expected_error: type[MindmapError],
) -> None:
    """無い項目・合わない箇所・使えない ID は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    write_comments(root, make_comment("C-1"), seq=3)
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(expected_error):
        comments.add_comment(root, data, now=_fixed_now)
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_add_comment_when_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    failing_replace: FailingReplace,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
) -> None:
    """置き換えに失敗したら前のコメントを残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    monkeypatch.setattr(comments.os, "replace", failing_replace("comments.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        comments.add_comment(root, {"target": "D-1", "body": "本文"}, now=_fixed_now)
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before
    assert list(root.rglob("*.tmp")) == []


def test_add_comment_when_reply(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_draft: MakeDraft,
    make_thread: MakeThread,
    write_drafts: WriteDrafts,
    write_threads: WriteThreads,
) -> None:
    """オープンのスレッドへの返信を溜め、そのスレッドの書きかけを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    write_drafts(root, _reply_draft("TH-1"), make_draft(target="D-1"))
    threads_before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 実行
    comment, _count = comments.add_comment(
        root, {"thread": "TH-1", "body": "了解"}, now=_fixed_now
    )
    # 検証
    assert comment.thread == "TH-1"
    saved = _read_comments(root)["items"][-1]
    assert ("target" in saved, "loc" in saved) == (False, False)
    assert [draft.get("target") for draft in _read_drafts(root)] == ["D-1"]
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == threads_before


@pytest.mark.parametrize(
    ("thread_id", "error_name", "message"),
    [
        pytest.param("TH-9", "ThreadNotFoundError", "TH-9", id="not_found"),
        pytest.param("TH-2", "CommentConflictError", "クローズ", id="closed"),
    ],
)
def test_add_comment_when_reply_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    thread_id: str,
    error_name: str,
    message: str,
) -> None:
    """無いスレッド・クローズのスレッドへの返信は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-2", status="closed"))
    # 実行・検証
    with pytest.raises(getattr(errors, error_name), match=message):
        comments.add_comment(root, {"thread": thread_id, "body": "x"}, now=_fixed_now)
    assert not (root / RECORD_DIR / "comments.yaml").exists()


@pytest.mark.parametrize(
    ("comment_id", "data", "expected_items"),
    [
        pytest.param(
            "C-1",
            {"body": " 案 A に決める "},
            [
                {
                    "id": "C-1",
                    "target": "D-1",
                    "body": "案 A に決める",
                    "created": DEFAULT_TIMESTAMP,
                },
                {
                    "id": "C-2",
                    "target": "A-1",
                    "loc": LINE2_LOC,
                    "body": "C-2の本文",
                    "created": DEFAULT_TIMESTAMP,
                },
            ],
            id="body",
        ),
        pytest.param(
            "C-2",
            {"loc": None},
            [
                {
                    "id": "C-1",
                    "target": "D-1",
                    "body": "C-1の本文",
                    "created": DEFAULT_TIMESTAMP,
                },
                {
                    "id": "C-2",
                    "target": "A-1",
                    "body": "C-2の本文",
                    "created": DEFAULT_TIMESTAMP,
                },
            ],
            id="detach_location",
        ),
    ],
)
def test_update_comment(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    comment_id: str,
    data: dict[str, Any],
    expected_items: list[dict[str, Any]],
) -> None:
    """本文を直す・箇所を外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    write_comments(
        root, make_comment("C-1"), make_comment("C-2", target="A-1", loc=LINE2_LOC), seq=2
    )
    # 実行
    result = comments.update_comment(root, comment_id, data)
    # 検証
    assert result.id == comment_id
    saved = _read_comments(root)
    assert saved["seq"] == 2
    assert saved["items"] == expected_items


@pytest.mark.parametrize(
    ("comment_id", "data", "expected_error"),
    [
        pytest.param("C-1", {}, CommentInvalidError, id="empty"),
        pytest.param("C-1", {"body": "  "}, CommentInvalidError, id="blank_body"),
        pytest.param("C-1", {"loc": {"kind": "body"}}, CommentInvalidError, id="loc_not_null"),
        pytest.param("C-9", {"body": "x"}, CommentNotFoundError, id="not_found"),
    ],
)
def test_update_comment_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    comment_id: str,
    data: dict[str, Any],
    expected_error: type[MindmapError],
) -> None:
    """形の誤りと無い ID は直さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(expected_error):
        comments.update_comment(root, comment_id, data)
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_delete_comment(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
) -> None:
    """消して中身と件数を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"), make_comment("C-2"), make_comment("C-3"), seq=3)
    # 実行
    deleted, count = comments.delete_comment(root, "C-2")
    # 検証
    assert deleted.id == "C-2"
    assert count == 2
    saved = _read_comments(root)
    assert saved["seq"] == 3
    assert [item["id"] for item in saved["items"]] == ["C-1", "C-3"]


def test_delete_comment_when_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
) -> None:
    """無い ID は消さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    # 実行・検証
    with pytest.raises(CommentNotFoundError, match="C-9"):
        comments.delete_comment(root, "C-9")


def test_save_draft(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_draft: MakeDraft,
    write_drafts: WriteDrafts,
) -> None:
    """向けた先ごとに上書きする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    located = make_draft(target="D-1", loc=LINE2_LOC, body="箇所の書きかけ")
    write_drafts(root, make_draft(target="D-1", body="案 A に"), located)
    # 実行
    comments.save_draft(root, {"target": "D-1", "body": "案 B も見たい"}, now=_fixed_now)
    # 検証
    assert _read_drafts(root) == [
        located,
        {"target": "D-1", "body": "案 B も見たい", "updated": FIXED_NOW},
    ]


def test_save_draft_when_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_draft: MakeDraft,
    write_drafts: WriteDrafts,
) -> None:
    """空の本文はその向けた先を消す。項目が無くても消せる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_drafts(root, make_draft(target="D-9"))
    # 実行
    comments.save_draft(root, {"target": "D-9", "body": ""}, now=_fixed_now)
    # 検証
    assert _read_drafts(root) == []


@pytest.mark.parametrize(
    ("data", "expected_error"),
    [
        pytest.param({"target": "D-1"}, CommentInvalidError, id="body_missing"),
        pytest.param(
            {"target": "D-1", "body": "あ" * (MAX_BODY_CHARS + 1)},
            CommentInvalidError,
            id="body_too_long",
        ),
        pytest.param({"loc": LINE2_LOC, "body": "x"}, CommentInvalidError, id="loc_without_target"),
        pytest.param({"target": "D-99", "body": "x"}, ItemNotFoundError, id="target_missing"),
    ],
)
def test_save_draft_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    data: dict[str, Any],
    expected_error: type[MindmapError],
) -> None:
    """形の誤りと無い項目への書きかけは保たない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行・検証
    with pytest.raises(expected_error):
        comments.save_draft(root, data, now=_fixed_now)
    assert not (root / RECORD_DIR / "drafts.yaml").exists()


def test_save_draft_when_thread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_drafts: WriteDrafts,
    write_threads: WriteThreads,
) -> None:
    """スレッドごとに保ち、クローズのスレッドへも保つ（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"), make_thread("TH-2", status="closed"))
    write_drafts(root, _reply_draft("TH-1", "了解"))
    # 実行
    comments.save_draft(root, {"thread": "TH-1", "body": "了解した"}, now=_fixed_now)
    comments.save_draft(root, {"thread": "TH-2", "body": "追記"}, now=_fixed_now)
    # 検証
    saved = _read_drafts(root)
    assert {draft["thread"]: draft["body"] for draft in saved} == {
        "TH-1": "了解した",
        "TH-2": "追記",
    }
    assert len(saved) == 2
    assert all("target" not in draft and "loc" not in draft for draft in saved)


@pytest.mark.parametrize(
    ("data", "error_name", "message"),
    [
        pytest.param({"thread": "TH-9", "body": "x"}, "ThreadNotFoundError", "TH-9", id="not_found"),
        pytest.param(
            {"thread": "TH-1", "target": "D-1", "body": "x"},
            "CommentInvalidError",
            "thread",
            id="with_target",
        ),
    ],
)
def test_save_draft_when_thread_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    data: dict[str, Any],
    error_name: str,
    message: str,
) -> None:
    """無いスレッドと、項目と一緒に渡したスレッドは保たない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    # 実行・検証
    with pytest.raises(getattr(errors, error_name), match=message):
        comments.save_draft(root, data, now=_fixed_now)
    assert not (root / RECORD_DIR / "drafts.yaml").exists()


def test_send_comments(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
) -> None:
    """チェックしたものだけを溜めた順に送り、新しいスレッドを立てる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    no_target = make_comment("C-3")
    del no_target["target"]
    write_comments(
        root,
        make_comment("C-1"),
        make_comment("C-2", target="A-1", loc=LINE2_LOC),
        no_target,
    )
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    docs_before = (root / RECORD_DIR / "docs.yaml").read_bytes()
    # 実行
    sent, sent_comments = comments.send_comments(root, {"ids": ["C-2", "C-1"]}, now=_fixed_now)
    # 検証
    assert sent == FIXED_NOW
    assert [(item.comment, item.thread, item.post) for item in sent_comments] == [
        ("C-1", "TH-1", "TH-1-1"),
        ("C-2", "TH-2", "TH-2-1"),
    ]
    saved = _read_threads(root)
    assert [(thread["id"], thread["status"], thread["target"]) for thread in saved] == [
        ("TH-1", "open", "D-1"),
        ("TH-2", "open", "A-1"),
    ]
    assert saved[1]["loc"] == LINE2_LOC
    assert [thread["posts"][0]["comment"] for thread in saved] == ["C-1", "C-2"]
    assert [item["id"] for item in _read_comments(root)["items"]] == ["C-3"]
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before
    assert (root / RECORD_DIR / "docs.yaml").read_bytes() == docs_before


def test_send_comments_when_reply(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_drafts: WriteDrafts,
    write_threads: WriteThreads,
) -> None:
    """返信をスレッドの末尾に足し、そのスレッドの書きかけを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1"), make_post("TH-1-2")))
    write_comments(root, _reply_comment("C-1", "TH-1"))
    write_drafts(root, _reply_draft("TH-1"))
    # 実行
    _sent, sent_comments = comments.send_comments(root, {"ids": ["C-1"]}, now=_fixed_now)
    # 検証
    assert [(item.comment, item.thread, item.post) for item in sent_comments] == [
        ("C-1", "TH-1", "TH-1-3")
    ]
    reply = _read_threads(root)[0]["posts"][2]
    assert (reply["author"], reply["read"], reply["taken"]) == ("user", False, None)
    assert _read_drafts(root) == []


@pytest.mark.parametrize(
    ("data", "expected_error", "expected_message"),
    [
        pytest.param({"ids": []}, CommentInvalidError, "ids", id="empty"),
        pytest.param({"ids": ["C-1", "C-1"]}, CommentInvalidError, "ids", id="duplicated"),
        pytest.param({"ids": ["C-1", "C-9"]}, CommentNotFoundError, "C-9", id="not_found"),
    ],
)
def test_send_comments_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    data: dict[str, Any],
    expected_error: type[MindmapError],
    expected_message: str,
) -> None:
    """形の誤り・無い ID は何も送らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(expected_error, match=expected_message):
        comments.send_comments(root, data, now=_fixed_now)
    assert not (root / RECORD_DIR / "threads.yaml").exists()
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == before


def test_send_comments_when_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
) -> None:
    """送れないコメントを全て返し、何も送らない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("A-1"), bodies={"A-1.md": "1 行目\n2 行目\n3 行目"}
    )
    write_threads(root, make_thread("TH-2", status="closed"))
    out_of_range = {"kind": "body", "start": 5, "end": 5, "text": "5 行目"}
    write_comments(
        root,
        make_comment("C-1"),
        make_comment("C-2", target="A-1", loc=out_of_range),
        make_comment("C-3", target="D-9"),
        _reply_comment("C-4", "TH-2"),
        _reply_comment("C-5", "TH-9"),
    )
    comments_before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    threads_before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(CommentConflictError) as exc_info:
        comments.send_comments(root, {"ids": ["C-1", "C-2", "C-3", "C-4", "C-5"]}, now=_fixed_now)
    stale = exc_info.value.stale
    assert [comment_id for comment_id, _reason in stale] == ["C-2", "C-3", "C-4", "C-5"]
    assert all(reason for _comment_id, reason in stale)
    assert "クローズ" in dict(stale)["C-4"]
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == comments_before
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == threads_before


def test_send_comments_when_already_sent(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
) -> None:
    """既に足してあるコメントは確かめずにレビュー中から外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1", make_post("TH-1-1"), make_post("TH-1-2", comment="C-1"), status="closed"
        ),
    )
    write_comments(root, _reply_comment("C-1", "TH-1"))
    threads_before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 実行
    _sent, sent_comments = comments.send_comments(root, {"ids": ["C-1"]}, now=_fixed_now)
    # 検証
    assert [(item.comment, item.thread, item.post) for item in sent_comments] == [
        ("C-1", "TH-1", "TH-1-2")
    ]
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == threads_before
    assert _read_comments(root)["items"] == []


def test_send_comments_when_comments_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    failing_replace: FailingReplace,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
) -> None:
    """レビュー中を書けなければスレッドを書き戻す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    write_comments(root, make_comment("C-1"))
    threads_before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    comments_before = (root / RECORD_DIR / "comments.yaml").read_bytes()
    monkeypatch.setattr(comments.os, "replace", failing_replace("comments.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        comments.send_comments(root, {"ids": ["C-1"]}, now=_fixed_now)
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == threads_before
    assert (root / RECORD_DIR / "comments.yaml").read_bytes() == comments_before


@pytest.mark.parametrize(
    ("data", "expected_key"),
    [
        pytest.param({"target": "D-1"}, "body", id="body_missing"),
        pytest.param({"body": "  "}, "body", id="body_blank"),
        pytest.param({"body": "あ" * (MAX_BODY_CHARS + 1)}, "body", id="body_too_long"),
        pytest.param({"body": 1}, "body", id="body_not_string"),
        pytest.param({"target": 1, "body": "x"}, "target", id="target_not_string"),
        pytest.param({"loc": LINE2_LOC, "body": "x"}, "target", id="loc_without_target"),
        pytest.param({"id": "C-2", "body": "x"}, "created", id="id_without_created"),
        pytest.param(
            {"id": "X-1", "created": DEFAULT_TIMESTAMP, "body": "x"}, "id", id="id_wrong_form"
        ),
        pytest.param({"thread": 1, "body": "x"}, "thread", id="thread_not_string"),
        pytest.param(
            {"thread": "TH-1", "target": "D-1", "body": "x"}, "thread", id="thread_with_target"
        ),
        pytest.param(
            {"thread": "TH-1", "target": "D-1", "loc": LINE2_LOC, "body": "x"},
            "thread",
            id="thread_with_target_and_loc",
        ),
    ],
)
def test_parse_comment_input_when_invalid(data: dict[str, Any], expected_key: str) -> None:
    """形の誤りを拾う（異常系）。"""
    # 実行・検証
    with pytest.raises(CommentInvalidError) as exc_info:
        comments._parse_comment_input(data)
    assert str(exc_info.value).startswith(expected_key)


def test_parse_comment_input_when_boundary() -> None:
    """ちょうど上限の本文を受ける（正常系）。"""
    # 準備
    body = " " + "あ" * MAX_BODY_CHARS + " "
    # 実行
    result = comments._parse_comment_input({"body": body})
    # 検証
    assert len(result[3]) == MAX_BODY_CHARS
