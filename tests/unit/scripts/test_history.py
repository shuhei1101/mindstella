"""history.py（変更履歴・書き換えのまとまり・前回開いた日時）の単体テスト。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

import history
import store
from errors import SchemaMismatchError
from fixture_types import MakeItem, MakeWorkspace

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
        before_item, after_item, before_body="本文\n", after_body="本文\n", seq=1, at=NOW
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
        before_item, after_item, before_body="本文\n", after_body="本文\n", seq=1, at=NOW
    )
    # 検証
    assert entry is None


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


def test_touch_opened(tmp_path: Path) -> None:
    """前の日時を返して書き換える（正常系）。"""
    # 実行
    first = history.touch_opened(tmp_path, FIRST_OPENED)
    second = history.touch_opened(tmp_path, SECOND_OPENED)
    # 検証
    assert first is None
    assert second == FIRST_OPENED
    opened_text = (tmp_path / ".mindstella-opened").read_text(encoding="utf-8")
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
    assert result["added"] == [{"id": "T-1", "kind": "task", "title": "T-1の題"}]
    assert result["changed"] == [
        {
            "id": "D-1",
            "kind": "decision",
            "title": "D-1の題",
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
        {"id": "D-1", "kind": "decision", "title": "D-1の題", "before": None, "body_diff": None}
    ]


def test_mark_read() -> None:
    """読んだ時点を最後の通し番号にする（正常系）。"""
    # 準備
    changes = {"last_seq": 7, "sets": [], "pending": {"added": [], "changed": []}}
    # 実行
    marked = history.mark_read(changes)
    # 検証
    assert marked["read_seq"] == 7
    assert "read_seq" not in changes
