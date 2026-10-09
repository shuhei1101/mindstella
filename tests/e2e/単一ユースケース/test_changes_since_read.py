"""前回読んだ時点からの変更を読む（スキルが準備で、前回読んだ後に足された・変わった項目を読む）の E2E テスト。

MCP サーバーを立て、MCP のクライアントで書き込みのツールと前回読んだ時点からの変更を読むツールを呼んで、結果とワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from workspace_fixtures import RECORD_DIR, MakeWorkspace, SnapshotTree

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 本文（3 行）と、2 行目だけを書き換えた本文
BODY_BEFORE = "1 行目\n2 行目\n3 行目\n"
BODY_AFTER = "1 行目\n書き換えた 2 行目\n3 行目\n"

# 足す検討事項の中身
DECISION: dict[str, Any] = {
    "title": "問い A",
    "status": "未決定",
    "options": [{"key": "A", "content": "案 A"}],
    "body_markdown": BODY_BEFORE,
}

# 足すタスクの中身
TASK: dict[str, Any] = {"title": "調べる", "kind": "調査", "status": "未着手"}


def _set_history_limit(root: Path, limit: int) -> None:
    """`config.yaml` に保持する回数を書く。"""
    path = root / RECORD_DIR / "config.yaml"
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    settings["history_limit"] = limit
    path.write_text(yaml.safe_dump(settings, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_normal(
    make_workspace: MakeWorkspace,
    replay: Replay,
    snapshot_tree: SnapshotTree,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """前回読んだ後に足した・変えた項目を、変わったキーと前の値つきで読み、読んだ時点を進める（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    replay("add", **ws, kind="decision", item=DECISION)
    # 前回読んだ時点を記録する
    replay("changes_since_read", **ws)
    # 読んだ後の書き換え: タイトルを 2 回直し、2 回目は本文の 2 行目も直し、タスクを足す
    replay("update", **ws, id="D-1", item={"title": "問い B"})
    replay("update", **ws, id="D-1", item={"title": "問い C", "body_markdown": BODY_AFTER})
    replay("add", **ws, kind="task", item=TASK)
    before = snapshot_tree(root)
    # 実行
    first = replay("changes_since_read", **ws)
    second = replay("changes_since_read", **ws)
    # 検証
    # 足した項目が T-1 の 1 件である
    assert first["added"] == [{"id": "T-1", "kind": "task", "title": "調べる", "updated_by": "ai"}]
    # 変えた項目が D-1 の 1 件で、変わったキーが title と本文である
    assert [entry["id"] for entry in first["changed"]] == ["D-1"]
    changed = first["changed"][0]
    # D-1 の title の前の値が、読んだ時点の 問い A である
    assert changed["before"] == {"title": "問い A"}
    # 足した T-1 と変えた D-1 に、最後に編集した人 ai が載っている
    assert changed["updated_by"] == "ai"
    # D-1 の本文が 2 行目だけの行の差分で返り、本文の全文を含まない
    assert changed["body_diff"] == [{"line": 2, "now": ["書き換えた 2 行目"], "before": ["2 行目"]}]
    # 読んだ後、AI が最後に読んだ時点が changes.yaml の last_seq と同じである
    changes = read_yaml(root, "changes.yaml")
    assert changes["read_seq"] == changes["last_seq"]
    # 2 回目の読み取りが、足した項目・変えた項目を 0 件で返す
    assert second["added"] == []
    assert second["changed"] == []
    # 項目の YAML の中身が、読む前と同じである
    after = snapshot_tree(root)
    assert {name: text for name, text in after.items() if name != ".mindstella/changes.yaml"} == {
        name: text for name, text in before.items() if name != ".mindstella/changes.yaml"
    }


def test_normal_when_no_read_point(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """読んだ時点の記録が無ければ差分を返さず、今の時点を記録する（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    replay("add", **ws, kind="decision", item=DECISION)
    replay("update", **ws, id="D-1", item={"answer": "答え"})
    # 実行
    first = replay("changes_since_read", **ws)
    second = replay("changes_since_read", **ws)
    # 検証
    # 1 回目の結果が、記録が無かったことを示し、足した項目・変えた項目を 0 件で返す
    assert first["had_read_point"] is False
    assert first["added"] == []
    assert first["changed"] == []
    # 1 回目の後、AI が最後に読んだ時点が changes.yaml の last_seq と同じである
    changes = read_yaml(root, "changes.yaml")
    assert changes["read_seq"] == changes["last_seq"]
    # 2 回目の結果が、記録が無かったことを示さず、足した項目・変えた項目を 0 件で返す
    assert second["had_read_point"] is True
    assert second["added"] == []
    assert second["changed"] == []


def test_normal_when_history_limit_zero(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """保持する回数が 0 のときは、変えた項目を ID だけで返す（正常系）。"""
    # 準備
    root = make_workspace()
    _set_history_limit(root, 0)
    ws = {"workspace": str(root)}
    replay("add", **ws, kind="decision", item=DECISION)
    replay("changes_since_read", **ws)
    replay("update", **ws, id="D-1", item={"answer": "答え"})
    replay("add", **ws, kind="task", item=TASK)
    # 実行
    result = replay("changes_since_read", **ws)
    # 検証
    # 足した項目が T-1、変えた項目が D-1 である
    assert [entry["id"] for entry in result["added"]] == ["T-1"]
    assert [entry["id"] for entry in result["changed"]] == ["D-1"]
    # D-1 が変わったキーと前の値を持たず、ID だけで返る
    assert result["changed"][0]["before"] is None
    assert result["changed"][0]["body_diff"] is None
    # D-1 が変更履歴を持たない
    assert "history" not in read_yaml(root, "decisions.yaml")["items"][0]


def test_normal_when_item_removed(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """読んだ時点に有って後で消した項目だけを、消した項目として読む（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    replay("add", **ws, kind="note", item={"title": "メモ", "content": "中身"})
    replay("add", **ws, kind="note", item={"title": "重複したメモ", "content": "中身"})
    # 前回読んだ時点を記録する
    replay("changes_since_read", **ws)
    # 読んだ後の書き換え: N-2 を消し、メモ N-3 を足してから消す
    replay("remove", **ws, id="N-2")
    replay("add", **ws, kind="note", item={"title": "読んだ後に足すメモ", "content": "中身"})
    replay("remove", **ws, id="N-3")
    # 実行
    result = replay("changes_since_read", **ws)
    # 検証
    # 消した項目が N-2 の 1 件で、種類 note と消したときのタイトルを持つ
    assert result["removed"] == [{"id": "N-2", "kind": "note", "title": "重複したメモ"}]
    # 足した項目・変えた項目・消した項目のどれにも N-3 が無い
    returned = [entry["id"] for key in ("added", "changed", "removed") for entry in result[key]]
    assert "N-3" not in returned
    # 足した項目・変えた項目が 0 件である
    assert result["added"] == []
    assert result["changed"] == []
    # 読んだ後、AI が最後に読んだ時点が changes.yaml の last_seq と同じである
    changes = read_yaml(root, "changes.yaml")
    assert changes["read_seq"] == changes["last_seq"]
