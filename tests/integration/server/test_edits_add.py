"""保存待ちの編集の追加（POST /api/edits）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import MakeEdit, MakeItem, MakeWorkspace, SnapshotTree, WriteEdits
from .http_helpers import http_request, post_json
from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR

# 保存待ちの編集の追加のパス
EDITS_PATH = "/api/edits"

# 別のサイトのページから送る送り元
FOREIGN_ORIGIN = {"Origin": "https://attacker.example"}


def _read_edits(root: Path) -> dict[str, Any]:
    """ワークスペースの edits.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "edits.yaml").read_text(encoding="utf-8"))


def _edits_path(root: Path) -> Path:
    """ワークスペースの edits.yaml のパスを返す。"""
    return root / RECORD_DIR / "edits.yaml"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """項目のキーの編集を溜め、項目と変更履歴は書き換えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", answer=""))
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = post_json(
        url,
        EDITS_PATH,
        {"op": "set", "target": "D-1", "key": "answer", "value": "ゴールはフェーズごとに 1 つ持つ"},
    )
    # 検証
    assert result.status == 201
    payload = result.json()
    assert (payload["id"], payload["target"], payload["count"]) == ("E-1", "D-1", 1)
    saved = _read_edits(root)
    assert saved["seq"] == 1
    edit = saved["items"][0]
    assert (edit["id"], edit["before"], edit["base"]) == ("E-1", "", DEFAULT_TIMESTAMP)
    after = snapshot_tree(root)
    changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
    assert changed == {f"{RECORD_DIR}/edits.yaml"}


def test_normal_when_same_key(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """同じ項目の同じキーへの編集は、新しい値で書き換えて 1 件のままにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    created = "2026-10-02T00:00:00+00:00"
    write_edits(root, make_edit("E-1", value="案 A", before="元", created=created))
    url = serve_preview(root)
    # 実行
    result = post_json(
        url, EDITS_PATH, {"op": "set", "target": "D-1", "key": "answer", "value": "案 B"}
    )
    # 検証
    assert result.status == 200
    payload = result.json()
    assert (payload["id"], payload["count"]) == ("E-1", 1)
    edit = _read_edits(root)["items"][0]
    assert (edit["value"], edit["created"], edit["before"], edit["base"]) == (
        "案 B",
        created,
        "元",
        DEFAULT_TIMESTAMP,
    )


def test_normal_when_back_to_current(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """今の値と同じ値に戻した編集は外し、id は null で返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", status="未着手"))
    write_edits(
        root,
        make_edit("E-1", target="T-1", key="status", value="中止", before="未着手"),
    )
    url = serve_preview(root)
    # 実行
    result = post_json(
        url, EDITS_PATH, {"op": "set", "target": "T-1", "key": "status", "value": "未着手"}
    )
    # 検証
    assert result.status == 200
    payload = result.json()
    assert (payload["id"], payload["count"]) == (None, 0)
    assert _read_edits(root)["items"] == []


def test_normal_when_item_add(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """足す項目に仮の ID を振って溜め、その後のキーの変更は同じ 1 件を書き換える（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1"))
    url = serve_preview(root)
    # 実行
    first = post_json(
        url,
        EDITS_PATH,
        {"op": "item-add", "key": "tasks", "value": {"title": "画面を作る", "status": "未着手"}},
    )
    second = post_json(
        url,
        EDITS_PATH,
        {
            "op": "item-add",
            "target": "new-1",
            "key": "tasks",
            "value": {"title": "画面を作る", "status": "進行中"},
        },
    )
    # 検証
    assert first.status == 201
    assert first.json()["target"] == "new-1"
    assert second.status == 200
    assert second.json()["count"] == 1
    saved = _read_edits(root)
    assert saved["new_seq"] == 1
    assert [(e["target"], e["op"], e["value"]["status"]) for e in saved["items"]] == [
        ("new-1", "item-add", "進行中")
    ]
    tasks = yaml.safe_load((root / RECORD_DIR / "tasks.yaml").read_text(encoding="utf-8"))
    assert [item["id"] for item in tasks["items"]] == ["T-1"]


def test_normal_when_item_remove(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """削除を溜め、同じ項目へのほかの編集は残し、取り消すと削除だけが外れる（正常系）。"""
    # 準備
    root = make_workspace(make_item("N-1"))
    write_edits(root, make_edit("E-1", target="N-1", key="title", value="新しい題", before="N-1の題"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, EDITS_PATH, {"op": "item-remove", "target": "N-1"})
    saved_with_remove = _read_edits(root)["items"]
    cancel = http_request(url, f"{EDITS_PATH}/E-2", method="DELETE")
    # 検証
    assert result.status == 201
    payload = result.json()
    assert (payload["id"], payload["count"]) == ("E-2", 2)
    assert [edit["id"] for edit in saved_with_remove] == ["E-1", "E-2"]
    notes = yaml.safe_load((root / RECORD_DIR / "notes.yaml").read_text(encoding="utf-8"))
    assert [item["id"] for item in notes["items"]] == ["N-1"]
    assert cancel.status == 200
    assert [edit["id"] for edit in _read_edits(root)["items"]] == ["E-1"]


def test_normal_when_setting(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    valid_settings: dict[str, Any],
) -> None:
    """設定のキーの編集を溜め、config.yaml は書き換えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "summary": "話し合い"})
    url = serve_preview(root)
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    result = post_json(
        url,
        EDITS_PATH,
        {"op": "setting", "target": "settings", "key": "summary", "value": "画面の編集"},
    )
    # 検証
    assert result.status == 201
    edit = _read_edits(root)["items"][0]
    assert edit["before"] == "話し合い"
    assert edit["base"] is None
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before


def test_error_when_key_not_editable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """ID・更新者など編集できないキーと、空のタイトルは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    not_editable = post_json(
        url, EDITS_PATH, {"op": "set", "target": "D-1", "key": "updated_by", "value": "user"}
    )
    blank_title = post_json(
        url, EDITS_PATH, {"op": "set", "target": "D-1", "key": "title", "value": "  "}
    )
    # 検証
    assert not_editable.status == 400
    assert "updated_by" in not_editable.json()["detail"]
    assert blank_title.status == 400
    assert "title" in blank_title.json()["detail"]
    assert not _edits_path(root).exists()


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(
        url,
        EDITS_PATH,
        {"op": "set", "target": "D-1", "key": "answer", "value": "答え"},
        headers=FOREIGN_ORIGIN,
    )
    # 検証
    assert result.status == 403
    assert not _edits_path(root).exists()


def test_error_when_target_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """ワークスペースに無い項目へは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(
        url, EDITS_PATH, {"op": "set", "target": "D-99", "key": "answer", "value": "答え"}
    )
    # 検証
    assert result.status == 404
    assert "D-99" in result.json()["detail"]
    assert not _edits_path(root).exists()


def test_error_when_target_removing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """削除を溜めた項目のキーは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("N-1"))
    write_edits(
        root, make_edit("E-1", target="N-1", op="item-remove", key=None, value=None, before=None)
    )
    url = serve_preview(root)
    before = _edits_path(root).read_bytes()
    # 実行
    result = post_json(
        url, EDITS_PATH, {"op": "set", "target": "N-1", "key": "title", "value": "画面の形"}
    )
    # 検証
    assert result.status == 409
    assert "削除" in result.json()["detail"]
    assert _edits_path(root).read_bytes() == before


def test_error_when_not_json(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """フォームの形の本文は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(
        url,
        EDITS_PATH,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="op=set&target=D-1",
    )
    # 検証
    assert result.status == 415
    assert not _edits_path(root).exists()


def test_normal_when_adopt_added_option(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """溜めた案の追加を、そのまま採用する切り替えで指して溜める（正常系）。"""
    # 準備
    options = [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}]
    root = make_workspace(make_item("D-1", options=options))
    url = serve_preview(root)
    # 実行
    added = post_json(
        url,
        EDITS_PATH,
        {
            "op": "option-add",
            "target": "D-1",
            "key": "C",
            "value": {"content": "ゴールはフェーズごとに 1 つ持つ"},
        },
    )
    adopted = post_json(
        url, EDITS_PATH, {"op": "adopt", "target": "D-1", "key": "C", "value": "C"}
    )
    # 検証
    assert added.status == 201
    assert adopted.status == 201
    assert adopted.json()["count"] == 2
    assert [(e["id"], e["op"], e["key"]) for e in _read_edits(root)["items"]] == [
        ("E-1", "option-add", "C"),
        ("E-2", "adopt", "C"),
    ]
    decisions = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))
    decision = decisions["items"][0]
    assert [option["key"] for option in decision["options"]] == ["A", "B"]
    assert not any(option.get("adopted") for option in decision["options"])
