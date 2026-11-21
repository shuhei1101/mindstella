"""presets.py（絞り込みのプリセットのタグの式の検証・当てはめ・件数と、作成・更新・削除）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import presets
from errors import PresetNameTakenError
from fixture_types import MakeItem, MakeWorkspace
from store import load_workspace
from workspace_fixtures import RECORD_DIR


def _tags(*names: str) -> list[dict[str, str]]:
    """タグの名前の並びを項目の `tags` にする。"""
    return [{"name": name} for name in names]


def _eq(*values: str, match: str | None = None) -> dict[str, Any]:
    """タグが値を持つ条件を作る。"""
    condition: dict[str, Any] = {"field": "tags", "op": "eq", "values": list(values)}
    # match を指定したときだけキーを持たせる
    if match is not None:
        condition["match"] = match
    return condition


def _ne(*values: str) -> dict[str, Any]:
    """タグが値を持たない条件を作る。"""
    return {"field": "tags", "op": "ne", "values": list(values)}


def _with_presets(valid_settings: dict[str, Any], *entries: dict[str, Any]) -> dict[str, Any]:
    """設定に presets を加えた辞書を返す。"""
    return {**valid_settings, "presets": list(entries)}


def _read_presets(root: Path) -> list[dict[str, Any]] | None:
    """config.yaml の presets を読む。"""
    data = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    return data.get("presets")


def test_validate_preset_filter() -> None:
    """3 レイヤーの式（正常系）。"""
    # 実行
    lines = presets.validate_preset_filter({"and": [{"or": [{"not": _eq("a")}]}]})
    # 検証
    assert lines == []


@pytest.mark.parametrize(
    ("expr", "reason"),
    [
        pytest.param({"and": []}, "空の束", id="empty_bundle"),
        pytest.param({"and": [{"or": [{"not": {"and": [_eq("a")]}}]}]}, "3 レイヤー", id="too_deep"),
        pytest.param({**_eq("a"), "case_sensitive": True}, "case_sensitive", id="unknown_key"),
        pytest.param({"field": "tags", "op": "contains", "values": ["a"]}, "contains", id="unknown_op"),
    ],
)
def test_validate_preset_filter_when_invalid(expr: dict[str, Any], reason: str) -> None:
    """空の束・4 レイヤー・受け付けないキー（異常系）。"""
    # 実行
    lines = presets.validate_preset_filter(expr)
    # 検証
    assert len(lines) == 1
    assert lines[0].startswith("filter")
    assert reason in lines[0]


@pytest.mark.parametrize(
    ("tags", "expr", "expected"),
    [
        pytest.param(["画面"], {"and": [_eq("画面"), _ne("廃止")]}, True, id="eq_and_ne"),
        pytest.param(["画面", "廃止"], {"and": [_eq("画面"), _ne("廃止")]}, False, id="has_excluded"),
        pytest.param([], _ne("廃止"), True, id="untagged_ne"),
        pytest.param([], _eq("画面"), False, id="untagged_eq"),
        pytest.param(["画面"], _eq("画面", "保存", match="all"), False, id="match_all"),
    ],
)
def test_matches_preset(tags: list[str], expr: dict[str, Any], expected: bool) -> None:
    """eq と ne の組み合わせ（正常系）。"""
    # 実行
    result = presets.matches_preset(tags, expr)
    # 検証
    assert result is expected


def test_preset_counts(make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]) -> None:
    """種類をまたいで数える（正常系）。"""
    # 準備
    settings = _with_presets(
        valid_settings,
        {"name": "画面の設計", "filter": {"and": [_eq("画面"), _ne("廃止")]}},
        {"name": "古い分類", "filter": _eq("廃止したタグ")},
    )
    root = make_workspace(
        make_item("A-1", tags=_tags("画面")),
        make_item("A-2", tags=_tags("画面", "廃止")),
        make_item("D-1", tags=_tags("画面")),
        settings=settings,
    )
    # 実行
    counts = presets.preset_counts(load_workspace(root))
    # 検証
    assert counts == {"画面の設計": 2, "古い分類": 0}


def test_create_preset_when_name_taken(make_workspace: MakeWorkspace, valid_settings: dict[str, Any]) -> None:
    """全角半角・大文字小文字だけ違う名前（異常系）。"""
    # 準備
    root = make_workspace(settings=_with_presets(valid_settings, {"name": "UI の設計", "filter": _eq("画面")}))
    before = (root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8")
    # 実行・検証
    with pytest.raises(PresetNameTakenError, match="UI の設計"):
        presets.create_preset(root, name="ｕｉ の設計", description=None, expr=_eq("画面"))
    assert (root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8") == before


def test_update_preset_when_move(make_workspace: MakeWorkspace, valid_settings: dict[str, Any]) -> None:
    """並びを移す（正常系）。"""
    # 準備
    root = make_workspace(
        settings=_with_presets(
            valid_settings,
            {"name": "画面の設計", "filter": _eq("画面")},
            {"name": "通知", "filter": _eq("通知")},
        )
    )
    # 実行
    result = presets.update_preset(root, name="通知", changes=presets.PresetChanges(position=1))
    # 検証
    assert result["position"] == 1
    assert [entry["name"] for entry in _read_presets(root) or []] == ["通知", "画面の設計"]


def test_delete_preset_when_last(make_workspace: MakeWorkspace, valid_settings: dict[str, Any]) -> None:
    """最後の 1 件（正常系）。"""
    # 準備
    root = make_workspace(settings=_with_presets(valid_settings, {"name": "画面の設計", "filter": _eq("画面")}))
    # 実行
    result = presets.delete_preset(root, name="画面の設計")
    # 検証
    assert result["remaining"] == 0
    assert _read_presets(root) is None
