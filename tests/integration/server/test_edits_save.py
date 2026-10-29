"""保存待ちの編集をまとめて保存（POST /api/edits/save）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    CallTool,
    MakeEdit,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
    StartServer,
    WriteEdits,
)
from .history_helpers import read_changes, read_items, update_item
from .http_helpers import post_json
from workspace_fixtures import RECORD_DIR

# 保存のパス
SAVE_PATH = "/api/edits/save"

# 別のサイトのページから送る送り元
FOREIGN_ORIGIN = {"Origin": "https://attacker.example"}

# edits.yaml の置き換えだけを失敗させる sitecustomize
FAIL_EDITS_REPLACE = """\
import os

_replace = os.replace


def _failing_replace(src, dst, *args, **kwargs):
    if str(dst).endswith("edits.yaml"):
        raise PermissionError(13, "置き換えを許さない", str(dst))
    return _replace(src, dst, *args, **kwargs)


os.replace = _failing_replace
"""


def _read_edits(root: Path) -> dict[str, Any]:
    """ワークスペースの edits.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "edits.yaml").read_text(encoding="utf-8"))


def _find(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    """項目の並びから、ID の項目を返す。"""
    return next(item for item in items if item["id"] == item_id)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """検討事項のキー・案・採用の編集を当て、編集した人を利用者にして 1 つのまとまりにする（正常系）。"""
    # 準備
    options = [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}]
    root = make_workspace(make_item("D-1", tags=["画面"], options=options))
    write_edits(
        root,
        make_edit("E-1", value="案 C にする"),
        make_edit("E-2", key="tags", value=["画面", "記録の形"], before=["画面"]),
        make_edit("E-3", op="option-add", key="C", value={"content": "案 C"}, before=None),
        make_edit("E-4", op="adopt", key="C", value="C"),
    )
    url = serve_preview(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 200
    payload = result.json()
    assert (payload["set"], payload["changed"]) == ("V-1", ["D-1"])
    decision = _find(read_items(root, "decisions.yaml"), "D-1")
    assert decision["answer"] == "案 C にする"
    assert decision["tags"] == ["画面", "記録の形"]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["C"]
    assert decision["updated_by"] == "user"
    assert [entry["by"] for entry in decision["history"]] == ["user"]
    changes = read_changes(root)
    first = changes["sets"][0]
    assert (first["id"], first["summary"], first["changed"]) == ("V-1", "画面からの編集", ["D-1"])
    assert changes["pending"] == {"added": [], "changed": []}
    assert _read_edits(root)["items"] == []


def test_normal_when_add_remove_settings(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
) -> None:
    """足す項目に ID を振り、消す項目を消し、設定を書き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("T-1"), make_item("N-1"), settings={**valid_settings, "summary": "話し合い"}
    )
    write_edits(
        root,
        make_edit(
            "E-1",
            target="new-1",
            op="item-add",
            key="tasks",
            value={"title": "画面を作る", "kind": "作業", "status": "未着手", "depends_on": ["T-1"]},
            before=None,
            base=None,
        ),
        make_edit("E-2", target="N-1", op="item-remove", key=None, value=None, before=None),
        make_edit(
            "E-3",
            target="settings",
            op="setting",
            key="summary",
            value="画面の編集",
            before="話し合い",
            base=None,
        ),
    )
    url = serve_preview(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 200
    payload = result.json()
    assert payload["added"] == [{"temp": "new-1", "id": "T-2"}]
    assert payload["removed"] == ["N-1"]
    assert payload["settings"] == ["summary"]
    added = _find(read_items(root, "tasks.yaml"), "T-2")
    assert (added["depends_on"], added["updated_by"]) == (["T-1"], "user")
    assert read_items(root, "notes.yaml") == []
    assert [entry["id"] for entry in read_changes(root)["sets"][0]["removed"]] == ["N-1"]
    config = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert config["summary"] == "画面の編集"



def test_normal_when_ai_pending(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """AI のまだまとめていない変更を先にまとめ、利用者の編集を別のまとまりにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("T-1"))
    update_item(call_tool, root, "T-1", {"status": "進行中"})
    write_edits(root, make_edit("E-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 200
    assert result.json()["set"] == "V-2"
    changes = read_changes(root)
    assert [(s["id"], s["summary"], s["changed"]) for s in changes["sets"][:2]] == [
        ("V-2", "画面からの編集", ["D-1"]),
        ("V-1", "まとめる前の AI の書き換え", ["T-1"]),
    ]
    assert changes["pending"] == {"added": [], "changed": []}
    task = _find(read_items(root, "tasks.yaml"), "T-1")
    assert task["history"][-1]["by"] == "ai"


def test_error_when_no_edits(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """保存待ちの編集が 0 件なら何もしない（異常系）。"""
    # 準備
    root = make_workspace(make_item("T-1"))
    update_item(call_tool, root, "T-1", {"status": "進行中"})
    url = serve_preview(root)
    changes_before = read_changes(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 400
    assert read_changes(root) == changes_before
    assert changes_before["pending"]["changed"] == ["T-1"]


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """別のサイトのページからは保存しない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = post_json(url, SAVE_PATH, {}, headers=FOREIGN_ORIGIN)
    # 検証
    assert result.status == 403
    assert snapshot_tree(root) == before


def test_error_when_item_changed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """溜めた後に書き換わった項目への編集があれば、どの編集も当てない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("T-1"))
    write_edits(
        root,
        make_edit("E-1"),
        make_edit("E-2", target="T-1", key="status", value="完了", before="未着手"),
    )
    update_item(call_tool, root, "D-1", {"title": "AI が書き換えた題"})
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 409
    blocked = result.json()["blocked"]
    assert [(entry["id"], entry["reason"]) for entry in blocked] == [("E-1", "changed")]
    assert snapshot_tree(root) == before
    assert [edit["id"] for edit in _read_edits(root)["items"]] == ["E-1", "E-2"]
    assert _find(read_items(root, "decisions.yaml"), "D-1")["title"] == "AI が書き換えた題"


def test_error_when_item_referenced(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """ほかの項目が指している項目の削除があれば、どの編集も当てない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", depends_on=["D-1"]))
    write_edits(
        root,
        make_edit("E-1", op="item-remove", key=None, value=None, before=None),
        make_edit("E-2", target="D-2"),
    )
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 409
    blocked = result.json()["blocked"]
    assert [(entry["id"], entry["reason"], entry["refs"]) for entry in blocked] == [
        ("E-1", "referenced", ["D-2"])
    ]
    assert snapshot_tree(root) == before


def test_error_when_invalid_value(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """当てた後の項目が参照の指す先に合わなければ、どの編集も当てない。まだ使われていないタグは止めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["画面"]))
    write_edits(
        root,
        make_edit("E-1", key="tags", value=["保存"], before=[]),
        make_edit("E-2", key="depends_on", value=["D-99"], before=[]),
    )
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = post_json(url, SAVE_PATH, {})
    # 検証
    assert result.status == 409
    blocked = {entry["id"]: entry for entry in result.json()["blocked"]}
    assert set(blocked) == {"E-2"}
    assert blocked["E-2"]["reason"] == "invalid"
    assert "D-99" in blocked["E-2"]["detail"]
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    start_server: StartServer,
    tmp_path: Path,
    snapshot_tree: SnapshotTree,
) -> None:
    """edits.yaml だけ書けなければ、先に書いたファイルを前の中身に戻す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1"))
    hook_dir = tmp_path / "failing-replace"
    hook_dir.mkdir()
    (hook_dir / "sitecustomize.py").write_text(FAIL_EDITS_REPLACE, encoding="utf-8")
    server = start_server(extra_env={"PYTHONPATH": str(hook_dir)})
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    before = snapshot_tree(root)
    # 実行
    result = post_json(str(served.data["url"]), SAVE_PATH, {})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root / RECORD_DIR / "edits.yaml") in detail
    assert "Traceback" not in detail
    assert snapshot_tree(root) == before
