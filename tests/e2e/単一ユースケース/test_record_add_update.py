"""記録の追加と更新（スキルが検討事項などを足し、後から直す）の E2E テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace, SnapshotTree

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
    return yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))["items"]


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
    assert after_add["updated_by"] == "ai"
    assert updated.is_error is False
    after_update = _read_decisions(root)[0]
    assert after_update["answer"] == "種類ごとに分ける"
    assert after_update["status"] == "決定済み"
    assert after_update["created"] == after_add["created"]
    assert after_update["updated"] >= after_add["updated"]
    # 更新の後、その項目が変更履歴を 1 回分持ち、直す前の答えと状態が入っている
    assert len(after_update["history"]) == 1
    assert after_update["history"][0]["before"] == {"answer": None, "status": "未決定"}
    assert after_update["history"][0]["by"] == "ai"
    assert after_update["updated_by"] == "ai"
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
    """`config.yaml` に保持する回数を書く。"""
    path = root / RECORD_DIR / "config.yaml"
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
    changes = yaml.safe_load((root / RECORD_DIR / "changes.yaml").read_text(encoding="utf-8"))
    assert [entry["summary"] for entry in changes["sets"]] == ["D-1 を決め、T-1 を積む", "足す"]
    assert changes["sets"][0]["added"] == [task_id]
    assert changes["sets"][0]["changed"] == [item_id]
    assert second.data == {"added": [], "changed": []}
    # 書き換えは `commit` を呼ぶ前からワークスペースに書かれている
    assert _read_decisions(root)[0]["answer"] == "種類ごとに分ける"


def test_normal_when_batched(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """追加・先の追加を指す追加・更新・取得を 1 回で当てる（正常系）。"""
    # 準備
    root = make_workspace()
    call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    call_tool("commit", workspace=str(root), summary="足す")
    operations = [
        {
            "op": "add",
            "kind": "decision",
            "item": {**NEW_DECISION, "title": "記録の単位", "options": [{"key": "A", "content": "1 日ごと"}]},
        },
        {
            "op": "add",
            "kind": "task",
            "item": {"title": "記録の単位を調べる", "kind": "調査", "status": "未着手", "for": ["$1"]},
        },
        {"op": "update", "id": "D-1", "item": {"answer": "月ごとに分ける", "status": "決定済み"}},
        {"op": "show", "id": "D-1"},
    ]
    # 実行
    batched = call_tool("batch", workspace=str(root), operations=operations)
    pending = call_tool("pending", workspace=str(root))
    checked = call_tool("check", workspace=str(root))
    # 検証
    assert batched.is_error is False, batched.text
    results = batched.data["results"]
    # 結果が渡した操作と同じ順に 4 件あり、足した検討事項が D-2、タスクが T-1 である
    assert [entry["op"] for entry in results] == ["add", "add", "update", "show"]
    assert results[0]["result"]["id"] == "D-2"
    assert results[1]["result"]["id"] == "T-1"
    # T-1 が for: [D-2] を持つ
    tasks = yaml.safe_load((root / RECORD_DIR / "tasks.yaml").read_text(encoding="utf-8"))["items"]
    assert tasks[0]["for"] == ["D-2"]
    # 4 つ目の取得の結果が、直した後の D-1 の答えと状態を持つ
    shown = results[3]["result"]["item"]
    assert shown["answer"] == "月ごとに分ける"
    assert shown["status"] == "決定済み"
    # D-1 が変更履歴を 1 回分持ち、直す前の答えと状態が入っている
    decision = _read_decisions(root)[0]
    assert len(decision["history"]) == 1
    assert decision["history"][0]["before"] == {"answer": None, "status": "未決定"}
    # pending が D-2・T-1（足した）と D-1（変えた）を返す
    assert [row["id"] for row in pending.data["added"]] == ["D-2", "T-1"]
    assert [row["id"] for row in pending.data["changed"]] == ["D-1"]
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.is_error is False
    assert checked.data["problems"] == []


def test_error_when_batch_has_invalid_operation(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """まとめた操作の途中が合わないと、合わない操作と箇所を示すエラーになり、何も書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    operations = [
        {"op": "add", "kind": "decision", "item": NEW_DECISION},
        {"op": "update", "id": "D-1", "item": {"status": "完了"}},
    ]
    # 実行
    result = call_tool("batch", workspace=str(root), operations=operations)
    # 検証
    # まとめて読み書きするツールがエラーを返し、本文に 2 つ目の操作・キー status・値 完了 がある
    assert result.is_error is True
    assert "2 番目の操作" in result.text
    assert "status" in result.text
    assert "完了" in result.text
    # 1 つ目の検討事項も足されていない。ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_unread_history_kept(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """読んでいない回は保持する回数を超えても残し、読み終えた後の書き換えで古い回を消す（正常系）。"""
    # 準備
    root = make_workspace()
    _set_history_limit(root, 1)
    item_id = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION).data["id"]
    call_tool("changes_since_read", workspace=str(root))
    # 実行
    call_tool("update", workspace=str(root), id=item_id, item={"answer": "種類ごとに分ける"})
    call_tool("update", workspace=str(root), id=item_id, item={"reason": "探しやすい"})
    after_two = _read_decisions(root)[0]
    read = call_tool("changes_since_read", workspace=str(root))
    call_tool("update", workspace=str(root), id=item_id, item={"answer": "1 つにまとめる"})
    after_three = _read_decisions(root)[0]
    # 検証
    # 2 回直した後、D-1 が変更履歴を 2 回分持ち、history_dropped_seq を持たない
    assert len(after_two["history"]) == 2
    assert "history_dropped_seq" not in after_two
    # 前回読んだ時点からの変更が、答えと理由の両方を前の値つきで返す
    assert [entry["id"] for entry in read.data["changed"]] == [item_id]
    assert read.data["changed"][0]["before"] == {"answer": None, "reason": None}
    # 3 回目に直した後、変更履歴が 3 回目の 1 回分だけで、history_dropped_seq が消した回の最も大きい通し番号である
    assert len(after_three["history"]) == 1
    assert after_three["history_dropped_seq"] == max(entry["seq"] for entry in after_two["history"])


def test_normal_when_body_for_every_kind(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """タスク・用語集・メモにも本文を書き、メモの本文を直して差分を変更履歴に積む（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    task_body = "経緯: 会話で持ち越した\n終わり方: 検証の結果を残す\n"
    term_body = "由来: 話し合いで決めた\n使い方: 画面の名前に使う\n"
    note_body = "調べたこと: 用語の由来\n補足: 最初の版\n"
    note_rewritten = "調べたこと: 用語の由来\n補足: 書き直した\n"
    items = [
        ("task", {"title": "調べる", "kind": "調査", "status": "未着手", "body_markdown": task_body}),
        ("term", {"title": "ワークスペース", "meaning": "話し合いの記録のフォルダ", "body_markdown": term_body}),
        ("note", {"title": "脱線", "content": "用語の由来を調べた", "body_markdown": note_body}),
    ]
    # 実行
    added = [call_tool("add", **ws, kind=kind, item=item) for kind, item in items]
    rewritten = call_tool("update", **ws, id="N-1", item={"body_markdown": note_rewritten})
    shown = {item_id: call_tool("show", **ws, id=item_id) for item_id in ("T-1", "G-1", "N-1")}
    checked = call_tool("check", **ws)
    # 検証
    assert [result.is_error for result in added] == [False, False, False]
    assert [result.data["id"] for result in added] == ["T-1", "G-1", "N-1"]
    records = root / RECORD_DIR
    for item_id, file_name in (("T-1", "tasks.yaml"), ("G-1", "terms.yaml"), ("N-1", "notes.yaml")):
        item = yaml.safe_load((records / file_name).read_text(encoding="utf-8"))["items"][0]
        assert item["body"] == f"{item_id}.md"
        assert item["updated_by"] == "ai"
        assert (records / "docs" / f"{item_id}.md").is_file()
    # 表示の body_markdown が、T-1・G-1 は渡した本文、N-1 は直した後の本文である
    assert shown["T-1"].data["body_markdown"] == task_body
    assert shown["G-1"].data["body_markdown"] == term_body
    assert rewritten.is_error is False
    assert shown["N-1"].data["body_markdown"] == note_rewritten
    # N-1 が変更履歴を 1 回分持ち、その回が本文の 2 行目の差分を持つ
    note = yaml.safe_load((records / "notes.yaml").read_text(encoding="utf-8"))["items"][0]
    assert len(note["history"]) == 1
    assert note["history"][0]["body_diff"] == [
        {"line": 2, "now": ["補足: 書き直した"], "before": ["補足: 最初の版"]}
    ]
    # ワークスペースの全ての YAML がスキーマに合い、点検が問題を 0 件で返す
    assert checked.is_error is False
    assert checked.data == {"ok": True, "problems": []}
