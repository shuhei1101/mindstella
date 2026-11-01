"""edits.py（保存待ちの編集の読み書き・取り消し・まとめて保存）の単体テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

import commands
import edits
from errors import (
    EditConflictError,
    EditInvalidError,
    EditNotFoundError,
    EditsBlockedError,
    SchemaMismatchError,
)
from fixture_types import MakeEdit, MakeItem, MakeWorkspace, SnapshotTree, WriteEdits
from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR

# now の代わりに返す日時
FIXED_NOW = "2026-10-21T05:02:00+00:00"


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _read_edits(root: Path) -> dict[str, Any]:
    """ワークスペースの edits.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "edits.yaml").read_text(encoding="utf-8"))


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML を読んで、項目の並びを返す。"""
    data = yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))
    return data["items"]


def _read_changes(root: Path) -> dict[str, Any]:
    """ワークスペースの書き換えのまとまり（changes.yaml）を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "changes.yaml").read_text(encoding="utf-8"))


def _find(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    """項目の並びから、ID の項目を返す。"""
    return next(item for item in items if item["id"] == item_id)


def _no_rewrite(root: Path) -> None:
    """保存待ちを溜めた後に、ワークスペースを書き換えない。"""


def _rewrite_title_of_d1(root: Path) -> None:
    """保存待ちを溜めた後に、MCP のツールの書き込みで D-1 のタイトルを書き換える。"""
    commands.run_update(root, "D-1", {"title": "AI が書き換えた題"}, now=_fixed_now)


def _with_settings(settings: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """ゴールを持たない設定に、渡したキーを重ねた設定を返す。"""
    return {**{key: value for key, value in settings.items() if key != "goal"}, **overrides}


def test_load_edits(
    make_workspace: MakeWorkspace, make_edit: MakeEdit, write_edits: WriteEdits
) -> None:
    """連番の順に読む（正常系）。"""
    # 準備
    root = make_workspace()
    write_edits(root, make_edit("E-3"), make_edit("E-1"), seq=3, new_seq=1)
    # 実行
    loaded = edits.load_edits(root)
    # 検証
    assert loaded.seq == 3
    assert loaded.new_seq == 1
    assert [edit.id for edit in loaded.items] == ["E-1", "E-3"]


def test_load_edits_when_missing(make_workspace: MakeWorkspace) -> None:
    """ファイルが無ければ空（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    loaded = edits.load_edits(root)
    # 検証
    assert loaded == edits.EditFile(seq=0, new_seq=0, items=[])


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("items: [\n", id="broken_yaml"),
        pytest.param(
            "seq: 1\nnew_seq: 0\nitems:\n"
            "  - {id: E-1, target: D-1, op: rename, key: answer, value: a, before: null,"
            " base: '2026-10-01T00:00:00+00:00', created: '2026-10-01T00:00:00+00:00'}\n",
            id="unknown_op",
        ),
    ],
)
def test_load_edits_when_invalid(make_workspace: MakeWorkspace, text: str) -> None:
    """読めない・合わないファイルは読まない（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"edits.yaml": text})
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as raised:
        edits.load_edits(root)
    assert raised.value.lines
    assert all(line.startswith("edits.yaml: ") for line in raised.value.lines)


def test_list_edits(
    make_workspace: MakeWorkspace, make_edit: MakeEdit, write_edits: WriteEdits
) -> None:
    """控えのキーを除いて溜めた順に返す（正常系）。"""
    # 準備
    root = make_workspace()
    write_edits(
        root,
        make_edit("E-1"),
        make_edit(
            "E-2",
            target="settings",
            op="setting",
            key="phases",
            value=["目的"],
            before=["問い"],
            base=None,
            map={"問い": "目的"},
        ),
    )
    # 実行
    listed = edits.list_edits(root)
    # 検証
    assert [item["id"] for item in listed["items"]] == ["E-1", "E-2"]
    assert all("base" not in item and "map" not in item for item in listed["items"])
    assert listed["count"] == 2


def test_add_edit(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """新しく溜め、元の値と更新日時を控える（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", updated=DEFAULT_TIMESTAMP))
    data = {"op": "set", "target": "D-1", "key": "answer", "value": "案 A"}
    # 実行
    body, created = edits.add_edit(root, data, now=_fixed_now)
    # 検証
    assert (body, created) == ({"id": "E-1", "target": "D-1", "count": 1}, True)
    saved = _read_edits(root)
    assert saved["seq"] == 1
    assert saved["items"][0]["before"] is None
    assert saved["items"][0]["base"] == DEFAULT_TIMESTAMP
    assert saved["items"][0]["created"] == FIXED_NOW


def test_add_edit_when_same_key(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """同じ項目の同じキーは書き換え、ID と控えを変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1", value="案 A"))
    data = {"op": "set", "target": "D-1", "key": "answer", "value": "案 B"}
    # 実行
    body, created = edits.add_edit(root, data, now=_fixed_now)
    # 検証
    assert (body, created) == ({"id": "E-1", "target": "D-1", "count": 1}, False)
    saved = _read_edits(root)
    assert saved["seq"] == 1
    assert saved["items"] == [make_edit("E-1", value="案 B")]


def test_add_edit_when_reverted(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """元の値に戻すと外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", status="未着手"))
    write_edits(
        root,
        make_edit("E-1", target="T-1", key="status", value="中止", before="未着手"),
    )
    data = {"op": "set", "target": "T-1", "key": "status", "value": "未着手"}
    # 実行
    body, created = edits.add_edit(root, data, now=_fixed_now)
    # 検証
    assert (body, created) == ({"id": None, "target": "T-1", "count": 0}, False)
    saved = _read_edits(root)
    assert saved["items"] == []
    assert saved["seq"] == 1


def test_add_edit_when_item_add(make_workspace: MakeWorkspace) -> None:
    """足す項目に仮の ID を振り、続くキーは同じ編集の値を書き換える（正常系）。"""
    # 準備
    root = make_workspace()
    first = {"op": "item-add", "key": "tasks", "value": {"title": "画面を作る", "status": "未着手"}}
    # 実行
    first_result = edits.add_edit(root, first, now=_fixed_now)
    second = {
        "op": "item-add",
        "target": "new-1",
        "key": "tasks",
        "value": {"title": "画面を作る", "status": "進行中"},
    }
    second_result = edits.add_edit(root, second, now=_fixed_now)
    # 検証
    assert first_result == ({"id": "E-1", "target": "new-1", "count": 1}, True)
    assert second_result == ({"id": "E-1", "target": "new-1", "count": 1}, False)
    saved = _read_edits(root)
    assert saved["new_seq"] == 1
    assert saved["items"][0]["value"]["status"] == "進行中"


def test_add_edit_when_setting_with_map(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any]
) -> None:
    """設定の編集は付け替えの対応を一緒に持つ（正常系）。"""
    # 準備
    root = make_workspace(settings=_with_settings(valid_settings, phases=["問い", "発散"]))
    data = {
        "op": "setting",
        "target": "settings",
        "key": "phases",
        "value": ["目的", "発散"],
        "map": {"問い": "目的"},
    }
    # 実行
    edits.add_edit(root, data, now=_fixed_now)
    # 検証
    saved = _read_edits(root)["items"][0]
    assert saved["map"] == {"問い": "目的"}
    assert saved["before"] == ["問い", "発散"]
    assert saved["base"] is None


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"op": "rename"}, id="unknown_op"),
        pytest.param(
            {"op": "set", "target": "D-1", "key": "updated_by", "value": "user"},
            id="uneditable_key",
        ),
        pytest.param(
            {"op": "set", "target": "D-1", "key": "title", "value": "  "}, id="blank_title"
        ),
        pytest.param(
            {"op": "set", "target": "D-1", "key": "answer", "value": "a", "map": {"a": "b"}},
            id="map_not_allowed",
        ),
        pytest.param(
            {
                "op": "setting",
                "target": "settings",
                "key": "phases",
                "value": ["目的", "発散"],
                "map": {"問い": None},
            },
            id="map_value_not_string",
        ),
    ],
)
def test_add_edit_when_invalid(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    data: dict[str, Any],
) -> None:
    """形の合わない編集は何も書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditInvalidError):
        edits.add_edit(root, data, now=_fixed_now)
    assert snapshot_tree(root) == before


@pytest.mark.parametrize(
    ("data", "missing"),
    [
        pytest.param(
            {"op": "set", "target": "D-99", "key": "answer", "value": "a"}, "D-99", id="item"
        ),
        pytest.param(
            {"op": "option-edit", "target": "D-1", "key": "Z", "value": {"content": "案 Z"}},
            "Z",
            id="option",
        ),
        pytest.param(
            {"op": "item-add", "target": "new-5", "key": "tasks", "value": {"title": "t"}},
            "new-5",
            id="temporary_id",
        ),
    ],
)
def test_add_edit_when_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    data: dict[str, Any],
    missing: str,
) -> None:
    """無い項目・案には溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditNotFoundError, match=missing):
        edits.add_edit(root, data, now=_fixed_now)
    assert snapshot_tree(root) == before


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {"op": "option-add", "target": "D-1", "key": "A", "value": {"content": "重なる案"}},
            id="option_symbol_exists",
        ),
        pytest.param(
            {"op": "set", "target": "N-1", "key": "title", "value": "新しい題"},
            id="edit_of_removing_item",
        ),
    ],
)
def test_add_edit_when_conflict(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    snapshot_tree: SnapshotTree,
    data: dict[str, Any],
) -> None:
    """既にある案の記号・削除を溜めた項目への編集は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("N-1"))
    write_edits(root, make_edit("E-1", target="N-1", op="item-remove", key=None, value=None))
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditConflictError):
        edits.add_edit(root, data, now=_fixed_now)
    assert snapshot_tree(root) == before


def test_add_edit_when_item_add_with_options(make_workspace: MakeWorkspace) -> None:
    """足す検討事項の案を `value` の `options` で溜める（正常系）。"""
    # 準備
    root = make_workspace()
    data = {
        "op": "item-add",
        "key": "decisions",
        "value": {
            "title": "保存の単位",
            "status": "決定済み",
            "options": [
                {"key": "A", "content": "項目ごと"},
                {"key": "B", "content": "まとめて", "adopted": True},
            ],
        },
    }
    # 実行
    body, created = edits.add_edit(root, data, now=_fixed_now)
    # 検証
    assert (body, created) == ({"id": "E-1", "target": "new-1", "count": 1}, True)
    saved = _read_edits(root)["items"][0]
    assert saved["id"] == "E-1"
    assert saved["value"]["options"] == [
        {"key": "A", "content": "項目ごと"},
        {"key": "B", "content": "まとめて", "adopted": True},
    ]
    assert "A" not in saved["value"]
    assert "B" not in saved["value"]


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "op": "item-add",
                "key": "decisions",
                "value": {
                    "title": "保存の単位",
                    "status": "未決定",
                    "options": [
                        {"key": "A", "content": "項目ごと"},
                        {"key": "A", "content": "まとめて"},
                    ],
                },
            },
            id="duplicate_symbol",
        ),
        pytest.param(
            {
                "op": "item-add",
                "key": "decisions",
                "value": {"title": "保存の単位", "status": "未決定", "options": [{"key": "A"}]},
            },
            id="content_missing",
        ),
        pytest.param(
            {
                "op": "item-add",
                "key": "tasks",
                "value": {
                    "title": "画面を作る",
                    "status": "未着手",
                    "options": [{"key": "A", "content": "項目ごと"}],
                },
            },
            id="kind_without_options",
        ),
        pytest.param(
            {
                "op": "set",
                "target": "D-1",
                "key": "options",
                "value": [{"key": "A", "content": "項目ごと"}],
            },
            id="set_options",
        ),
    ],
)
def test_add_edit_when_item_add_options_invalid(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    data: dict[str, Any],
) -> None:
    """足す項目の案が合わないときは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditInvalidError, match="options"):
        edits.add_edit(root, data, now=_fixed_now)
    assert snapshot_tree(root) == before


def test_delete_edit(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """1 件を外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("T-1"))
    write_edits(
        root,
        make_edit("E-1"),
        make_edit("E-2", target="T-1", key="status", value="中止", before="未着手"),
    )
    # 実行
    result = edits.delete_edit(root, "E-2")
    # 検証
    assert result == {"removed": ["E-2"], "count": 1}
    saved = _read_edits(root)
    assert [item["id"] for item in saved["items"]] == ["E-1"]
    assert saved["seq"] == 2


def test_delete_edit_when_option_add(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """足した案の取り消しはその採用も外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(
        root,
        make_edit("E-1", op="option-add", key="C", value={"content": "案 C"}),
        make_edit("E-2", op="adopt", key="C", value="C", before="A"),
    )
    # 実行
    result = edits.delete_edit(root, "E-1")
    # 検証
    assert result == {"removed": ["E-1", "E-2"], "count": 0}
    assert _read_edits(root)["items"] == []


def test_delete_edit_when_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    snapshot_tree: SnapshotTree,
) -> None:
    """無い ID は何も書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1"))
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditNotFoundError, match="E-9"):
        edits.delete_edit(root, "E-9")
    assert snapshot_tree(root) == before


def test_save_edits(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    valid_settings: dict[str, Any],
) -> None:
    """キー・案・採用を当て、編集した人を利用者にして 1 つのまとまりにする（まだ使われていないタグも書く）（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            status="未決定",
            tags=["画面"],
            options=[{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
        ),
        settings=valid_settings,
    )
    write_edits(
        root,
        make_edit("E-1", value="案 C にする"),
        make_edit("E-2", key="tags", value=["画面", "記録の形"], before=["画面"]),
        make_edit("E-3", op="option-add", key="C", value={"content": "案 C"}, before=None),
        make_edit("E-4", op="adopt", key="C", value="C"),
    )
    # 実行
    result = edits.save_edits(root, now=_fixed_now)
    # 検証
    assert result["set"] == "V-1"
    assert result["changed"] == ["D-1"]
    decision = _find(_read_items(root, "decisions.yaml"), "D-1")
    assert decision["answer"] == "案 C にする"
    assert decision["tags"] == ["画面", "記録の形"]
    assert [option["key"] for option in decision["options"]] == ["A", "B", "C"]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["C"]
    assert decision["updated_by"] == "user"
    assert len(decision["history"]) == 1
    assert decision["history"][0]["by"] == "user"
    changes = _read_changes(root)
    assert changes["sets"][0]["summary"] == "画面からの編集"
    assert changes["pending"]["added"] == []
    assert changes["pending"]["changed"] == []
    assert _read_edits(root)["items"] == []


def test_save_edits_when_add_remove_settings(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    valid_settings: dict[str, Any],
) -> None:
    """設定 → 追加 → 削除の順に当て、仮の ID を振った ID に置き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("T-1"),
        make_item("N-1"),
        settings={**valid_settings, "summary": "話し合い"},
    )
    task = {"kind": "作業", "status": "未着手"}
    write_edits(
        root,
        make_edit(
            "E-1",
            target="new-1",
            op="item-add",
            key="tasks",
            value={"title": "画面を作る", **task, "depends_on": ["new-2"]},
            base=None,
        ),
        make_edit(
            "E-2",
            target="new-2",
            op="item-add",
            key="tasks",
            value={"title": "部品を作る", **task},
            base=None,
        ),
        make_edit("E-3", target="N-1", op="item-remove", key=None, value=None),
        make_edit(
            "E-4",
            target="settings",
            op="setting",
            key="summary",
            value="画面の編集",
            before="話し合い",
            base=None,
        ),
    )
    # 実行
    result = edits.save_edits(root, now=_fixed_now)
    # 検証
    assert result["added"] == [{"temp": "new-1", "id": "T-2"}, {"temp": "new-2", "id": "T-3"}]
    assert result["removed"] == ["N-1"]
    assert result["settings"] == ["summary"]
    added = _find(_read_items(root, "tasks.yaml"), "T-2")
    assert added["depends_on"] == ["T-3"]
    assert added["updated_by"] == "user"


def test_save_edits_when_item_add_with_options(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """案を持つ足す検討事項を、案ごと書き込む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(
        root,
        make_edit(
            "E-1",
            target="new-1",
            op="item-add",
            key="decisions",
            value={
                "title": "保存の単位",
                "status": "決定済み",
                "options": [
                    {"key": "A", "content": "項目ごと"},
                    {"key": "B", "content": "まとめて", "adopted": True},
                ],
            },
            base=None,
        ),
    )
    # 実行
    result = edits.save_edits(root, now=_fixed_now)
    # 検証
    assert result["added"] == [{"temp": "new-1", "id": "D-2"}]
    added = _find(_read_items(root, "decisions.yaml"), "D-2")
    assert [option["key"] for option in added["options"]] == ["A", "B"]
    assert [option["key"] for option in added["options"] if option.get("adopted")] == ["B"]
    assert added["status"] == "決定済み"
    assert added["updated_by"] == "user"
    assert _read_edits(root)["items"] == []


def test_save_edits_when_ai_pending(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """まだまとめていない AI の書き換えを先に別のまとまりにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("T-1"))
    commands.run_update(root, "T-1", {"status": "進行中"}, now=_fixed_now)
    write_edits(root, make_edit("E-1", value="答え"))
    # 実行
    result = edits.save_edits(root, now=_fixed_now)
    # 検証
    assert result["set"] == "V-2"
    changes = _read_changes(root)
    assert [(entry["id"], entry["summary"], entry["changed"]) for entry in changes["sets"]] == [
        ("V-2", "画面からの編集", ["D-1"]),
        ("V-1", "まとめる前の AI の書き換え", ["T-1"]),
    ]
    assert changes["pending"]["changed"] == []
    task = _find(_read_items(root, "tasks.yaml"), "T-1")
    assert task["history"][0]["by"] == "ai"


def test_save_edits_drops_edits_of_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
) -> None:
    """削除する項目へのほかの編集は捨てる（正常系）。"""
    # 準備
    root = make_workspace(make_item("N-1"))
    write_edits(
        root,
        make_edit("E-1", target="N-1", key="title", value="新しい題"),
        make_edit("E-2", target="N-1", op="item-remove", key=None, value=None),
    )
    # 実行
    result = edits.save_edits(root, now=_fixed_now)
    # 検証
    assert result["removed"] == ["N-1"]
    assert result["changed"] == []


@pytest.mark.parametrize(
    ("rewrite", "items", "settings_overrides", "staged", "expected_blocked", "detail_part"),
    [
        pytest.param(
            _rewrite_title_of_d1,
            [("D-1", {})],
            {},
            [("E-1", {})],
            [("E-1", "changed", [])],
            "",
            id="changed",
        ),
        pytest.param(
            _no_rewrite,
            [("D-1", {}), ("D-2", {"depends_on": ["D-1"]})],
            {},
            [("E-1", {"op": "item-remove", "key": None, "value": None})],
            [("E-1", "referenced", ["D-2"])],
            "",
            id="referenced",
        ),
        pytest.param(
            _no_rewrite,
            [("D-1", {})],
            {},
            [("E-1", {"key": "depends_on", "value": ["D-99"]})],
            [("E-1", "invalid", [])],
            "D-99",
            id="invalid_reference",
        ),
        pytest.param(
            _no_rewrite,
            [("D-1", {"phase": "問い"})],
            {"phases": ["問い", "発散"]},
            [
                (
                    "E-1",
                    {
                        "target": "settings",
                        "op": "setting",
                        "key": "phases",
                        "value": ["発散"],
                        "before": ["問い", "発散"],
                        "base": None,
                    },
                )
            ],
            [("E-1", "invalid", [])],
            "",
            id="invalid_phase_without_map",
        ),
    ],
)
def test_save_edits_when_blocked(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    snapshot_tree: SnapshotTree,
    valid_settings: dict[str, Any],
    rewrite: Callable[[Path], None],
    items: list[tuple[str, dict[str, Any]]],
    settings_overrides: dict[str, Any],
    staged: list[tuple[str, dict[str, Any]]],
    expected_blocked: list[tuple[str, str, list[str]]],
    detail_part: str,
) -> None:
    """書き込めない編集を全て集め、何も書かない（異常系）。"""
    # 準備
    root = make_workspace(
        *(make_item(item_id, **overrides) for item_id, overrides in items),
        settings=_with_settings(valid_settings, **settings_overrides),
    )
    write_edits(root, *(make_edit(edit_id, **overrides) for edit_id, overrides in staged))
    rewrite(root)
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditsBlockedError) as raised:
        edits.save_edits(root, now=_fixed_now)
    blocked = [(entry.id, entry.reason, entry.refs) for entry in raised.value.blocked]
    assert blocked == expected_blocked
    assert detail_part in raised.value.blocked[0].detail
    assert snapshot_tree(root) == before


def test_save_edits_when_empty(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """保存待ちが空なら何もしない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    commands.run_update(root, "D-1", {"answer": "a"}, now=_fixed_now)
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(EditInvalidError):
        edits.save_edits(root, now=_fixed_now)
    assert snapshot_tree(root) == before
