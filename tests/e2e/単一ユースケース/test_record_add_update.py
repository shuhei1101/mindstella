"""記録の追加と更新（スキルが検討事項などを足し、後から直す）の E2E テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree

# 本文（3 行）と、2 行目を書き換えた本文
BODY_BEFORE = "1 行目\n2 行目\n3 行目\n"
BODY_AFTER = "1 行目\n書き換えた 2 行目\n3 行目\n"

# スキルが足す検討事項の中身
NEW_DECISION: dict[str, Any] = {
    "title": "YAML のキーをどう分けるか",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "lead": "種類ごとにキーを分けるかを決める。",
    "weight": "大",
}


def _read_decisions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの検討事項の並びを読む。"""
    return yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]


def _stdin(data: dict[str, Any]) -> str:
    """標準入力に渡す JSON の文字列にする。"""
    return json.dumps(data, ensure_ascii=False)


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """検討事項を足し、その答えと状態を直す（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    item_id = added.data["id"]
    after_add = _read_decisions(root)[0]
    updated = call_tool(
        "update",
        workspace=str(root),
        id=item_id,
        item={"answer": "種類ごとに分ける", "status": "決定済み"},
    )
    checked = call_tool("check", workspace=str(root))
    # 検証
    assert added.is_error is False
    assert item_id.startswith("D-")
    assert len(_read_decisions(root)) == 1
    assert after_add["title"] == "YAML のキーをどう分けるか"
    assert after_add["target"] == "mindmap"
    assert after_add["category"] == "データ構造"
    assert after_add["phase"] == "要件"
    assert after_add["lead"] == "種類ごとにキーを分けるかを決める。"
    assert after_add["weight"] == "大"
    # 足しただけの時点では、その項目は変更履歴を持たない
    assert "history" not in after_add
    assert updated.is_error is False
    after_update = _read_decisions(root)[0]
    assert after_update["answer"] == "種類ごとに分ける"
    assert after_update["status"] == "決定済み"
    assert after_update["created"] == after_add["created"]
    assert after_update["updated"] >= after_add["updated"]
    # 更新の後、その項目が変更履歴を 1 回分持ち、直す前の答えと状態が入っている
    assert len(after_update["history"]) == 1
    assert after_update["history"][0]["before"] == {"answer": None, "status": "未決定"}
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.is_error is False


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """状態に決めた名前に無い値を入れた検討事項は足さず、合わない箇所を示すエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "add", workspace=str(root), kind="decision", item={**NEW_DECISION, "status": "完了"}
    )
    # 検証
    assert result.is_error is True
    assert "status" in result.text
    assert "完了" in result.text
    assert snapshot_tree(root) == before


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID の答えは直せず、ID が無いエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-9", item={"answer": "決めた答え"})
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before


def _set_history_limit(root: Path, limit: int) -> None:
    """`mindmap.yaml` に保持する回数を書く。"""
    path = root / "mindmap.yaml"
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    settings["history_limit"] = limit
    path.write_text(yaml.safe_dump(settings, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_normal_when_over_history_limit(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """保持する回数を超えて直すと、古い変更履歴を消し、同じ中身で直しても履歴を積まない（正常系）。"""
    # 準備
    root = make_workspace()
    _set_history_limit(root, 1)
    added = call_tool(
        "add",
        workspace=str(root),
        kind="decision",
        item={**NEW_DECISION, "body_markdown": BODY_BEFORE},
    )
    item_id = added.data["id"]
    # 実行
    call_tool("update", workspace=str(root), id=item_id, item={"answer": "種類ごとに分ける"})
    call_tool("update", workspace=str(root), id=item_id, item={"body_markdown": BODY_AFTER})
    after_body = _read_decisions(root)[0]
    same = call_tool("update", workspace=str(root), id=item_id, item={"body_markdown": BODY_AFTER})
    after_same = _read_decisions(root)[0]
    # 検証
    assert len(after_body["history"]) == 1
    entry = after_body["history"][0]
    assert "answer" not in entry["before"]
    assert "body_diff" in entry
    # 本文を直す前の本文を組み立てられる（後ろの行から当てる）
    lines = BODY_AFTER.splitlines()
    for hunk in sorted(entry["body_diff"], key=lambda hunk: hunk["line"], reverse=True):
        start = hunk["line"] - 1
        assert lines[start : start + len(hunk["now"])] == hunk["now"]
        lines[start : start + len(hunk["now"])] = hunk["before"]
    assert "\n".join(lines) + "\n" == BODY_BEFORE
    assert BODY_AFTER not in json.dumps(entry, ensure_ascii=False)
    # 同じ中身で直しても、変更履歴はその前と同じ
    assert same.is_error is False
    assert after_same["history"] == after_body["history"]


def test_normal_when_history_limit_zero(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """保持する回数が 0 のときは、直しても変更履歴を持たない（正常系）。"""
    # 準備
    root = make_workspace()
    _set_history_limit(root, 0)
    item_id = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION).data["id"]
    # 実行
    call_tool("update", workspace=str(root), id=item_id, item={"answer": "種類ごとに分ける"})
    # 検証
    item = _read_decisions(root)[0]
    assert item["answer"] == "種類ごとに分ける"
    assert "history" not in item


def test_normal_when_changes_committed(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """直した項目と足した項目を `pending` で読み、`commit` で 1 つのまとまりにする（正常系）。"""
    # 準備
    root = make_workspace()
    item_id = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION).data["id"]
    call_tool("commit", workspace=str(root), summary="足す")
    # 実行
    call_tool("update", workspace=str(root), id=item_id, item={"answer": "種類ごとに分ける"})
    task_id = call_tool(
        "add",
        workspace=str(root),
        kind="task",
        item={"title": "決める", "kind": "作業", "status": "未着手"},
    ).data["id"]
    first = call_tool("pending", workspace=str(root))
    committed = call_tool("commit", workspace=str(root), summary="D-1 を決め、T-1 を積む")
    second = call_tool("pending", workspace=str(root))
    # 検証
    assert first.data["added"] == [{"id": task_id, "title": "決める"}]
    assert [row["id"] for row in first.data["changed"]] == [item_id]
    assert first.data["changed"][0]["keys"] == ["answer"]
    assert committed.data["summary"] == "D-1 を決め、T-1 を積む"
    changes = yaml.safe_load((root / "changes.yaml").read_text(encoding="utf-8"))
    assert [entry["summary"] for entry in changes["sets"]] == ["D-1 を決め、T-1 を積む", "足す"]
    assert changes["sets"][0]["added"] == [task_id]
    assert changes["sets"][0]["changed"] == [item_id]
    assert second.data == {"added": [], "changed": []}
    # 書き換えは `commit` を呼ぶ前からワークスペースに書かれている
    assert _read_decisions(root)[0]["answer"] == "種類ごとに分ける"
