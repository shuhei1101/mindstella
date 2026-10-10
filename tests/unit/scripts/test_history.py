"""history.py（変更履歴・書き換えのまとまり・前回開いた日時）の単体テスト。"""

from __future__ import annotations

import time
from typing import Any

import pytest

import history
import store
from errors import SchemaMismatchError
from fixture_types import MakeItem, MakeWorkspace
from workspace_fixtures import RECORD_DIR

# まとめた日時・書き換えた日時
NOW = "2026-10-02T08:00:00+00:00"

# 前回開いた日時として 1 回目・2 回目に渡す日時
FIRST_OPENED = "2026-10-04T13:05:00+00:00"
SECOND_OPENED = "2026-10-04T14:45:00+00:00"

# 大きな本文の行数と、空行を挟む間隔（3 行に 1 行が空行）
LARGE_LINE_COUNT = 5000
BLANK_LINE_PERIOD = 4

# 大きな書き換えの差分を作る時間の上限（秒）
LARGE_DIFF_LIMIT_SEC = 1.0

# 3 行の本文の 2 行目を書き換え、4 行目を足す前後
BEFORE_BODY = "# 見出し\n元の段落\n末尾の段落\n"
AFTER_BODY = "# 見出し\n書き換えた段落\n末尾の段落\n足した段落\n"


def _empty_changes() -> dict[str, Any]:
    """まとまりも、まだまとめていない変更も持たない記録を作る。"""
    return {"last_seq": 0, "sets": [], "pending": {"added": [], "changed": []}}


def _removed(item_id: str, seq: int, added_seq: int, title: str = "重複したメモ") -> dict[str, Any]:
    """消した項目の記録（changes.yaml の removed の 1 要素）を作る。種類は ID の頭の文字から決める。"""
    kinds = {
        "D": "decision",
        "T": "task",
        "R": "research",
        "A": "doc",
        "G": "term",
        "N": "note",
        "L": "log",
    }
    return {
        "id": item_id,
        "kind": kinds[item_id[0]],
        "title": title,
        "seq": seq,
        "added_seq": added_seq,
    }


def _markdown_of(prefix: str) -> str:
    """3 行に 1 行が空行の 5000 行の Markdown を作る（空行でない行は prefix で始まる）。"""
    lines = [
        "" if index % BLANK_LINE_PERIOD == BLANK_LINE_PERIOD - 1 else f"{prefix} {index}"
        for index in range(LARGE_LINE_COUNT)
    ]
    return "\n".join(lines) + "\n"


def test_load_changes_when_missing(make_workspace: MakeWorkspace) -> None:
    """ファイルが無ければ空の記録を返す（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    changes = history.load_changes(root)
    # 検証
    assert changes == _empty_changes()


def test_load_changes_when_schema_mismatch(make_workspace: MakeWorkspace) -> None:
    """崩れたファイルは読まず、合わない箇所を返す（異常系）。"""
    # 準備
    broken = "last_seq: 0\nsets: []\npending:\n  changed: []\n"
    root = make_workspace(raw_files={"changes.yaml": broken})
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        history.load_changes(root)
    assert exc_info.value.lines[0].startswith("changes.yaml: pending")


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        pytest.param({}, 5, id="missing"),
        pytest.param({"history_limit": 0}, 0, id="zero"),
        pytest.param({"history_limit": 3}, 3, id="three"),
    ],
)
def test_history_limit(settings: dict[str, Any], expected: int) -> None:
    """設定が無ければ既定の 5 を返し、あればその回数を返す（正常系）。"""
    # 実行
    limit = history.history_limit(settings)
    # 検証
    assert limit == expected


def test_diff_body() -> None:
    """変えた行だけを持ち、当てると前の本文になる（正常系）。"""
    # 実行
    hunks = history.diff_body(BEFORE_BODY, AFTER_BODY)
    # 検証
    assert hunks == [
        {"line": 2, "now": ["書き換えた段落"], "before": ["元の段落"]},
        {"line": 4, "now": ["足した段落"], "before": []},
    ]
    assert history.apply_body_diff(AFTER_BODY, hunks) == BEFORE_BODY


def test_diff_body_when_large_rewrite() -> None:
    """空行を挟む大きな本文を丸ごと書き換えても速く、戻せる（正常系）。"""
    # 準備
    before = _markdown_of("前の段落")
    after = _markdown_of("後の段落")
    # 実行
    started = time.perf_counter()
    hunks = history.diff_body(before, after)
    elapsed = time.perf_counter() - started
    # 検証
    assert elapsed < LARGE_DIFF_LIMIT_SEC
    assert history.apply_body_diff(after, hunks) == before


def test_apply_body_diff_when_text_rewritten() -> None:
    """手で書き換えた本文には当たらない（正常系）。"""
    # 準備
    hunks = history.diff_body(BEFORE_BODY, AFTER_BODY)
    rewritten = "手で書いた 1\n手で書いた 2\n手で書いた 3\n手で書いた 4\n"
    # 実行
    result = history.apply_body_diff(rewritten, hunks)
    # 検証
    assert result is None


def test_make_entry() -> None:
    """変わった・消えた・足したキーを前の値で持つ（正常系）。"""
    # 準備
    before_item = {
        "id": "D-1",
        "title": "問い",
        "status": "未決定",
        "weight": "大",
        "updated": "2026-10-01T00:00:00+00:00",
    }
    after_item = {
        "id": "D-1",
        "title": "問い",
        "status": "決定済み",
        "answer": "a",
        "updated": NOW,
    }
    # 実行
    entry = history.make_entry(
        before_item, after_item, before_body="本文\n", after_body="本文\n", seq=1, at=NOW, by="ai"
    )
    # 検証
    assert entry is not None
    assert entry["seq"] == 1
    assert entry["at"] == NOW
    assert entry["before"] == {"answer": None, "status": "未決定", "weight": "大"}
    assert "body_diff" not in entry


def test_make_entry_when_nothing_changed() -> None:
    """変わったものが無ければ作らない（正常系）。"""
    # 準備
    before_item = {"id": "D-1", "title": "問い", "updated": "2026-10-01T00:00:00+00:00"}
    after_item = {"id": "D-1", "title": "問い", "updated": NOW}
    # 実行
    entry = history.make_entry(
        before_item, after_item, before_body="本文\n", after_body="本文\n", seq=1, at=NOW, by="ai"
    )
    # 検証
    assert entry is None


@pytest.mark.parametrize(
    ("before_item", "after_item", "expected"),
    [
        pytest.param(
            {"id": "D-1", "title": "問い", "updated": "2026-10-01T00:00:00+00:00"},
            {"id": "D-1", "title": "問い", "answer": "a", "updated": NOW, "updated_by": "ai"},
            {"seq": 1, "at": NOW, "by": "ai", "before": {"answer": None}},
            id="value_changed",
        ),
        pytest.param(
            {"id": "D-1", "title": "問い", "updated_by": "user"},
            {"id": "D-1", "title": "問い", "updated": NOW, "updated_by": "ai"},
            None,
            id="only_editor_changed",
        ),
    ],
)
def test_make_entry_records_editor(
    before_item: dict[str, Any], after_item: dict[str, Any], expected: dict[str, Any] | None
) -> None:
    """書き換えた人を持ち、updated_by の違いだけでは作らない（正常系）。"""
    # 実行
    entry = history.make_entry(
        before_item, after_item, before_body="本文\n", after_body="本文\n", seq=1, at=NOW, by="ai"
    )
    # 検証
    assert entry == expected


def test_make_entry_when_body_format_changed() -> None:
    """本文の形式を替えた回は前の body を before に入れる（正常系）。"""
    # 準備
    before_item = {"id": "A-1", "title": "モック", "body": "A-1.md"}
    after_item = {"id": "A-1", "title": "モック", "body": "A-1.html"}
    # 実行
    entry = history.make_entry(
        before_item,
        after_item,
        before_body="a\n",
        after_body="<p>a</p>\n",
        seq=1,
        at=NOW,
        by="ai",
    )
    # 検証
    assert entry is not None
    assert entry["before"] == {"body": "A-1.md"}
    assert history.apply_body_diff("<p>a</p>\n", entry["body_diff"]) == "a\n"


def test_stack_history() -> None:
    """保持する回数を超えた古いものを消し、消した回の seq を残す（正常系）。"""
    # 準備
    old_entry = {"seq": 5, "at": "2026-10-01T00:00:00+00:00", "before": {"answer": None}}
    new_entry = {"seq": 9, "at": NOW, "before": {"status": "未決定"}}
    item = {"id": "D-1", "title": "問い", "history": [old_entry], "history_dropped_seq": 3}
    # 実行
    stacked = history.stack_history(item, new_entry, 1, read_seq=None)
    # 検証
    assert stacked["history"] == [new_entry]
    assert stacked["history_dropped_seq"] == 5
    assert item["history"] == [old_entry]
    assert item["history_dropped_seq"] == 3


def test_stack_history_when_not_dropped() -> None:
    """消さなければ消した回の seq を付けない（正常系）。"""
    # 準備
    new_entry = {"seq": 1, "at": NOW, "before": {"status": "未決定"}}
    item = {"id": "D-1", "title": "問い"}
    # 実行
    stacked = history.stack_history(item, new_entry, 1, read_seq=None)
    # 検証
    assert stacked["history"] == [new_entry]
    assert "history_dropped_seq" not in stacked


def test_stack_history_when_limit_zero() -> None:
    """回数が 0 なら変更履歴と消した回の seq を消す（正常系）。"""
    # 準備
    old_entry = {"seq": 1, "at": "2026-10-01T00:00:00+00:00", "before": {"answer": None}}
    new_entry = {"seq": 2, "at": NOW, "before": {"status": "未決定"}}
    item = {"id": "D-1", "title": "問い", "history": [old_entry], "history_dropped_seq": 1}
    # 実行
    stacked = history.stack_history(item, new_entry, 0, read_seq=None)
    # 検証
    assert "history" not in stacked
    assert "history_dropped_seq" not in stacked


def test_stack_history_keeps_unread() -> None:
    """読んでいない回は保持する回数を超えても残す（正常系）。"""
    # 準備
    entry_4 = {"seq": 4, "at": "2026-10-01T00:00:00+00:00", "before": {"answer": None}}
    entry_2 = {"seq": 2, "at": "2026-10-01T00:00:00+00:00", "before": {"weight": "大"}}
    new_entry = {"seq": 6, "at": NOW, "before": {"status": "未決定"}}
    item = {"id": "D-1", "title": "問い", "history": [entry_4, entry_2]}
    # 実行
    stacked = history.stack_history(item, new_entry, 1, read_seq=3)
    # 検証
    assert stacked["history"] == [new_entry, entry_4]
    assert stacked["history_dropped_seq"] == 2


def test_note_pending() -> None:
    """足した項目は変えても changed に入らず、通し番号は進めない（正常系）。"""
    # 準備
    added = history.note_pending(_empty_changes(), "D-1", "added")
    # 実行
    noted = history.note_pending(added, "D-1", "changed")
    # 検証
    assert noted["pending"] == {"added": ["D-1"], "changed": []}
    assert noted["last_seq"] == 0


def test_commit_pending() -> None:
    """まだまとめていない変更をまとまりにする（正常系）。"""
    # 準備
    changes = {
        "last_seq": 3,
        "sets": [
            {
                "id": "V-1",
                "at": "2026-10-01T00:00:00+00:00",
                "summary": "最初",
                "until_seq": 1,
                "added": [],
                "changed": ["D-1"],
            }
        ],
        "pending": {"added": ["T-1"], "changed": ["D-1"]},
    }
    # 実行
    committed, change_set = history.commit_pending(changes, "決める", NOW)
    # 検証
    assert change_set == {
        "id": "V-2",
        "at": NOW,
        "summary": "決める",
        "until_seq": 3,
        "added": ["T-1"],
        "changed": ["D-1"],
    }
    assert committed["sets"][0] == change_set
    assert committed["sets"][1]["id"] == "V-1"
    assert committed["pending"] == {"added": [], "changed": []}


def test_commit_pending_when_empty() -> None:
    """まとめるものが無ければ何もしない（正常系）。"""
    # 準備
    changes = _empty_changes()
    # 実行
    committed, change_set = history.commit_pending(changes, "決める", NOW)
    # 検証
    assert change_set is None
    assert committed == changes


def test_commit_pending_when_only_removed() -> None:
    """消した項目だけでもまとまりにする（正常系）。"""
    # 準備
    removed = _removed("N-2", seq=3, added_seq=2)
    changes = {
        "last_seq": 3,
        "sets": [],
        "pending": {"added": [], "changed": [], "removed": [removed]},
    }
    # 実行
    committed, change_set = history.commit_pending(changes, "重複した N-2 を消す", NOW)
    # 検証
    assert change_set is not None
    assert change_set["removed"] == [removed]
    assert committed["sets"][0] == change_set
    assert committed["pending"]["added"] == []
    assert committed["pending"]["changed"] == []
    assert committed["pending"].get("removed", []) == []


def test_pending_view(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """変えたキーをまとめて返す（正常系）。"""
    # 準備
    entries = [
        {"seq": 3, "at": NOW, "before": {"answer": None}},
        {
            "seq": 2,
            "at": NOW,
            "before": {"status": "未決定"},
            "body_diff": [{"line": 1, "now": ["新しい行"], "before": ["元の行"]}],
        },
    ]
    root = make_workspace(make_item("D-1", history=entries), make_item("T-1"))
    workspace = store.load_workspace(root)
    changes = {
        "last_seq": 3,
        "sets": [
            {
                "id": "V-1",
                "at": "2026-10-01T00:00:00+00:00",
                "summary": "最初",
                "until_seq": 1,
                "added": [],
                "changed": [],
            }
        ],
        "pending": {"added": ["T-1"], "changed": ["D-1"]},
    }
    # 実行
    view = history.pending_view(workspace, changes)
    # 検証
    assert view["added"] == [{"id": "T-1", "title": "T-1の題"}]
    assert len(view["changed"]) == 1
    assert view["changed"][0]["id"] == "D-1"
    assert view["changed"][0]["title"] == "D-1の題"
    assert sorted(view["changed"][0]["keys"]) == ["answer", "body_markdown", "status"]


def test_pending_view_when_removed(make_workspace: MakeWorkspace) -> None:
    """消した項目を removed で返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace())
    changes = {
        "last_seq": 3,
        "sets": [],
        "pending": {"added": [], "changed": [], "removed": [_removed("N-2", seq=3, added_seq=2)]},
    }
    # 実行
    view = history.pending_view(workspace, changes)
    # 検証
    assert view["removed"] == [{"id": "N-2", "kind": "note", "title": "重複したメモ"}]
    assert view["added"] == []
    assert view["changed"] == []


def test_touch_opened(make_workspace: MakeWorkspace) -> None:
    """前の日時を返して書き換える（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    first = history.touch_opened(root, FIRST_OPENED)
    second = history.touch_opened(root, SECOND_OPENED)
    # 検証
    assert first is None
    assert second == FIRST_OPENED
    opened_text = (root / RECORD_DIR / ".mindstella-opened").read_text(encoding="utf-8")
    assert opened_text.splitlines()[0] == SECOND_OPENED


def test_advance_seq() -> None:
    """番号を 1 進め、渡した記録は書き換えない（正常系）。"""
    # 準備
    changes = {"last_seq": 3, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    advanced, seq = history.advance_seq(changes)
    # 検証
    assert advanced["last_seq"] == 4
    assert seq == 4
    assert changes["last_seq"] == 3


def test_values_at_read(make_item: MakeItem) -> None:
    """読んだ時点の値と本文の差分を組み立てる（正常系）。"""
    # 準備
    entries = [
        {
            "seq": 5,
            "at": NOW,
            "before": {"title": "問い B"},
            "body_diff": [{"line": 2, "now": ["書き換えた段落"], "before": ["元の段落"]}],
        },
        {"seq": 4, "at": NOW, "before": {"title": "問い A"}},
    ]
    item = make_item("D-1", title="問い C", history=entries)
    body = "# 見出し\n書き換えた段落\n末尾の段落\n"
    # 実行
    before, hunks = history.values_at_read(item, body, 3)
    # 検証
    assert before == {"title": "問い A"}
    assert hunks == [{"line": 2, "now": ["書き換えた段落"], "before": ["元の段落"]}]
    assert history.apply_body_diff(body, hunks) == "# 見出し\n元の段落\n末尾の段落\n"


def test_values_at_read_when_changed_back(make_item: MakeItem) -> None:
    """元の値に戻したキーは返さない（正常系）。"""
    # 準備
    entries = [
        {"seq": 5, "at": NOW, "before": {"answer": "b"}},
        {"seq": 4, "at": NOW, "before": {"answer": "a"}},
    ]
    item = make_item("D-1", answer="a", history=entries)
    # 実行
    before, hunks = history.values_at_read(item, None, 3)
    # 検証
    assert before == {}
    assert hunks is None


def test_changes_since(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """読んだ時点より後の追加と変更を分けて返す（正常系）。"""
    # 準備
    entry = {"seq": 5, "at": NOW, "before": {"answer": None}}
    root = make_workspace(
        make_item("D-1", answer="新しい答え", added_seq=1, seq=5, history=[entry]),
        make_item("D-2", added_seq=2, seq=2),
        make_item("T-1", added_seq=4, seq=4),
    )
    workspace = store.load_workspace(root)
    changes = {"last_seq": 5, "read_seq": 3, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    result = history.changes_since(workspace, changes)
    # 検証
    assert result["had_read_point"] is True
    assert result["read_seq"] == 3
    assert result["until_seq"] == 5
    assert result["added"] == [
        {"id": "T-1", "kind": "task", "title": "T-1の題", "updated_by": None}
    ]
    assert result["changed"] == [
        {
            "id": "D-1",
            "kind": "decision",
            "title": "D-1の題",
            "updated_by": None,
            "by": [],
            "before": {"answer": None},
            "body_diff": None,
        }
    ]


def test_changes_since_when_no_read_point(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """読んだ時点が無ければ差分を返さない（正常系）。"""
    # 準備
    entry = {"seq": 2, "at": NOW, "before": {"answer": None}}
    root = make_workspace(make_item("D-1", answer="答え", added_seq=1, seq=2, history=[entry]))
    workspace = store.load_workspace(root)
    changes = {"last_seq": 2, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    result = history.changes_since(workspace, changes)
    # 検証
    assert result == {
        "had_read_point": False,
        "read_seq": None,
        "until_seq": 2,
        "added": [],
        "changed": [],
        "removed": [],
    }


def test_changes_since_when_limit_zero(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """保持する回数が 0 なら前の値を組み立てない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", added_seq=1, seq=5),
        settings={**valid_settings, "history_limit": 0},
    )
    workspace = store.load_workspace(root)
    changes = {"last_seq": 5, "read_seq": 3, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    result = history.changes_since(workspace, changes)
    # 検証
    assert result["added"] == []
    assert result["changed"] == [
        {
            "id": "D-1",
            "kind": "decision",
            "title": "D-1の題",
            "updated_by": None,
            "by": [],
            "before": None,
            "body_diff": None,
        }
    ]


def test_changes_since_reports_editors(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """読んだ後に利用者と AI が直した項目で、両方を返す（正常系）。"""
    # 準備
    entries = [
        {"seq": 5, "at": NOW, "by": "ai", "before": {"answer": "b"}},
        {"seq": 4, "at": NOW, "by": "user", "before": {"answer": "a"}},
        {"seq": 2, "at": NOW, "by": "user", "before": {"answer": None}},
    ]
    root = make_workspace(
        make_item("D-1", answer="c", added_seq=1, seq=5, updated_by="ai", history=entries)
    )
    workspace = store.load_workspace(root)
    changes = {"last_seq": 5, "read_seq": 3, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    result = history.changes_since(workspace, changes)
    # 検証
    assert len(result["changed"]) == 1
    assert result["changed"][0]["id"] == "D-1"
    assert result["changed"][0]["updated_by"] == "ai"
    # seq 2 の回は読んだ時点より前なので数えない
    assert result["changed"][0]["by"] == ["user", "ai"]


def test_changes_since_when_removed(make_workspace: MakeWorkspace) -> None:
    """読んだ時点に有って後で消した項目だけを返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace())
    changes = {
        "last_seq": 6,
        "read_seq": 3,
        "sets": [
            {
                "id": "V-1",
                "at": NOW,
                "summary": "最初",
                "until_seq": 2,
                "added": [],
                "changed": [],
                "removed": [_removed("N-1", seq=2, added_seq=1)],
            }
        ],
        "pending": {
            "added": [],
            "changed": [],
            "removed": [_removed("N-2", seq=4, added_seq=2), _removed("N-3", seq=6, added_seq=5)],
        },
    }
    # 実行
    result = history.changes_since(workspace, changes)
    # 検証
    # N-1 は読む前に消した、N-3 は読んだ後に足して消したので返さない
    assert result["removed"] == [{"id": "N-2", "kind": "note", "title": "重複したメモ"}]


def test_note_removed() -> None:
    """変えた項目を消すと changed から除き removed に足す（正常系）。"""
    # 準備
    changes = {
        "last_seq": 5,
        "sets": [],
        "pending": {"added": [], "changed": ["D-1", "D-2"]},
    }
    removed = _removed("D-1", seq=5, added_seq=1, title="D-1の題")
    # 実行
    noted = history.note_removed(changes, removed)
    # 検証
    assert noted["pending"]["changed"] == ["D-2"]
    assert noted["pending"]["removed"] == [removed]
    # 渡した記録は書き換えない
    assert changes["pending"] == {"added": [], "changed": ["D-1", "D-2"]}


def test_note_removed_when_added_since_commit() -> None:
    """まとめる前に足した項目も removed に記録する（正常系）。"""
    # 準備
    changes = {"last_seq": 1, "sets": [], "pending": {"added": ["N-1"], "changed": []}}
    removed = _removed("N-1", seq=2, added_seq=1)
    # 実行
    noted = history.note_removed(changes, removed)
    # 検証
    assert noted["pending"]["added"] == []
    assert noted["pending"]["removed"] == [removed]


def test_removed_items() -> None:
    """まとまりとまだまとめていない変更の記録を消した順に返す（正常系）。"""
    # 準備
    first = _removed("N-1", seq=3, added_seq=1)
    second = _removed("N-2", seq=5, added_seq=2)
    changes = {
        "last_seq": 5,
        "sets": [
            {
                "id": "V-2",
                "at": NOW,
                "summary": "消す",
                "until_seq": 4,
                "added": [],
                "changed": [],
                "removed": [first],
            },
            {"id": "V-1", "at": NOW, "summary": "最初", "until_seq": 2, "added": [], "changed": []},
        ],
        "pending": {"added": [], "changed": [], "removed": [second]},
    }
    # 実行
    items = history.removed_items(changes)
    # 検証
    assert items == [first, second]


def test_mark_read() -> None:
    """読んだ時点を最後の通し番号にする（正常系）。"""
    # 準備
    changes = {"last_seq": 7, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    marked = history.mark_read(changes)
    # 検証
    assert marked["read_seq"] == 7
    assert "read_seq" not in changes
