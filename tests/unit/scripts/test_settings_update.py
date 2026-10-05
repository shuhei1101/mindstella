"""settings_update.py（設定の更新の引数の確かめ・設定の置き換え・フェーズの付け替え・まとめた書き込み）の単体テスト。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import yaml

import errors
import settings_update
import store
from errors import (
    ArgumentError,
    SchemaMismatchError,
    UnmappedPhaseError,
    WriteFailedError,
)
from fixture_types import FailingReplace, MakeItem, MakeWorkspace, SnapshotTree
from workspace_fixtures import DEFAULT_TIMESTAMP

# フェーズを付け替えた項目に入る更新日時
NOW = "2026-10-05T00:00:00+00:00"

# 対象・カテゴリーの付け替えを確かめるときの今の設定（targets・categories の名前だけを引く）
CURRENT_SETTINGS: dict[str, Any] = {
    "targets": [
        {"name": "本体", "summary": "アプリの本体"},
        {"name": "管理画面", "summary": "運用の画面"},
    ],
    "categories": [
        {"name": "画面", "target": "本体", "summary": "画面の部品"},
        {"name": "設定", "target": "管理画面", "summary": "設定の画面"},
    ],
}

type MakeSettings = Callable[..., dict[str, Any]]


def _validate(
    settings: dict[str, Any],
    phase_map: dict[str, str] | None = None,
    *,
    target_map: dict[str, str] | None = None,
    category_map: dict[str, str] | None = None,
) -> None:
    """今の phases を 問い・発散、今の設定を CURRENT_SETTINGS にして、引数を確かめる。"""
    settings_update.validate_settings_input(
        settings,
        phase_map,
        ["問い", "発散"],
        target_map=target_map,
        category_map=category_map,
        current=CURRENT_SETTINGS,
    )


def _fixed_now() -> str:
    """付け替えた項目の更新日時として、決めた日時を返す。"""
    return NOW


@pytest.fixture
def make_settings() -> MakeSettings:
    """プレイブックの配列を持つ設定（ゴールは渡したときだけ持つ）を作る関数を返す。"""

    def _make(phases: list[str], goal: dict[str, Any] | None = None) -> dict[str, Any]:
        """フェーズだけを決め、他のキーは固定にした設定を返す。"""
        settings: dict[str, Any] = {
            "summary": "要件出しのスキル mindmap を設計する",
            "playbooks": ["壁打ち"],
            "target_label": "テーマ",
            "phases": phases,
            "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
            "categories": [
                {"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}
            ],
        }
        # ゴールは渡したときだけ持つ
        if goal is not None:
            settings["goal"] = goal
        return settings

    return _make


def test_validate_settings_input() -> None:
    """正しい引数は通す（正常系）。"""
    # 準備
    settings = {"phases": ["目的", "発散"], "goal": None}
    phase_map = {"問い": "目的"}
    # 実行・検証
    _validate(settings, phase_map)


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param({}, id="empty"),
        pytest.param({"field": "システム開発"}, id="not_editable_key"),
        pytest.param({"summary": None}, id="required_key_null"),
    ],
)
def test_validate_settings_input_when_bad_key(settings: dict[str, Any]) -> None:
    """書き換えられないキーと必須のキーの null を拒む（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        _validate(settings)


@pytest.mark.parametrize(
    ("settings", "phase_map", "expected_error", "message"),
    [
        pytest.param(
            {"summary": "新しい題名"},
            {"問い": "目的"},
            ArgumentError,
            "phase_map",
            id="without_phases",
        ),
        pytest.param(
            {"phases": ["目的", "発散"]},
            {"発散": "目的"},
            ArgumentError,
            "発散",
            id="key_in_new_phases",
        ),
        pytest.param(
            {"phases": ["目的", "発散"]},
            {"整理": "目的"},
            ArgumentError,
            "整理",
            id="key_not_in_current_phases",
        ),
        pytest.param(
            {"phases": ["目的", "発散"]},
            {"問い": "要件"},
            UnmappedPhaseError,
            "対応の無いフェーズ",
            id="value_not_in_new_phases",
        ),
    ],
)
def test_validate_settings_input_when_bad_phase_map(
    settings: dict[str, Any],
    phase_map: dict[str, str],
    expected_error: type[Exception],
    message: str,
) -> None:
    """phase_map の誤った渡し方を拒む（異常系）。"""
    # 実行・検証
    with pytest.raises(expected_error, match=message):
        _validate(settings, phase_map)


@pytest.mark.parametrize(
    ("settings", "target_map", "expected_error_name", "message"),
    [
        pytest.param(
            {"summary": "新しい題名"},
            {"本体": "アプリ"},
            "ArgumentError",
            "target_map",
            id="without_targets",
        ),
        pytest.param(
            {
                "targets": [
                    {"name": "アプリ", "summary": "アプリの本体"},
                    {"name": "管理画面", "summary": "運用の画面"},
                ]
            },
            {"管理画面": "アプリ"},
            "ArgumentError",
            "管理画面",
            id="key_in_new_targets",
        ),
        pytest.param(
            {
                "targets": [
                    {"name": "アプリ", "summary": "アプリの本体"},
                    {"name": "管理画面", "summary": "運用の画面"},
                ]
            },
            {"本体": "画面"},
            "UnmappedTargetError",
            "対応の無い対象",
            id="value_not_in_new_targets",
        ),
    ],
)
def test_validate_settings_input_when_bad_target_map(
    settings: dict[str, Any],
    target_map: dict[str, str],
    expected_error_name: str,
    message: str,
) -> None:
    """target_map・category_map の誤った渡し方を拒む（異常系）。"""
    # 準備
    expected_error = getattr(errors, expected_error_name)
    # 実行・検証
    with pytest.raises(expected_error, match=message):
        _validate(settings, target_map=target_map)


def test_merge_settings(make_settings: MakeSettings) -> None:
    """渡したキーだけを置き換え、null で消し、並びを保つ（正常系）。"""
    # 準備
    current = make_settings(
        ["目的", "要件"], {"phase": "要件", "summary": "要件が決まる", "deliverables": []}
    )
    settings = {
        "summary": "新しい題名",
        "goal": None,
        "description": "概要",
        "phases": ["目的", "要件"],
    }
    # 実行
    merged, changed = settings_update.merge_settings(current, settings)
    # 検証
    assert merged["summary"] == "新しい題名"
    assert "goal" not in merged
    assert list(merged) == [
        "summary",
        "playbooks",
        "target_label",
        "phases",
        "targets",
        "categories",
        "description",
    ]
    assert changed == ["summary", "goal", "description"]
    # 渡した設定そのものは書き換えない
    assert "goal" in current


def test_remap_phases(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_settings: MakeSettings
) -> None:
    """対応で項目と goal.phase を付け替え、同じ名前のフェーズはそのままにする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        make_item("T-1", phase="整理"),
        settings=make_settings(
            ["問い", "発散", "整理", "結論"],
            {"phase": "結論", "summary": "まとめる", "deliverables": []},
        ),
    )
    workspace = store.load_workspace(root)
    settings = {**workspace.settings, "phases": ["目的", "発散", "要件"]}
    phase_map = {"問い": "目的", "整理": "要件", "結論": "要件"}
    # 実行
    changes, remapped, new_settings = settings_update.remap_phases(
        workspace, settings, phase_map, now=_fixed_now
    )
    # 検証
    assert [change.kind for change in changes] == ["decision", "task"]
    decisions = {item["id"]: item for item in changes[0].items}
    tasks = {item["id"]: item for item in changes[1].items}
    assert decisions["D-1"]["phase"] == "目的"
    assert decisions["D-1"]["updated"] == NOW
    assert decisions["D-2"]["phase"] == "発散"
    assert decisions["D-2"]["updated"] == DEFAULT_TIMESTAMP
    assert tasks["T-1"]["phase"] == "要件"
    assert tasks["T-1"]["updated"] == NOW
    assert remapped == [
        settings_update.PhaseRemap(id="D-1", key="phase", from_value="問い", to_value="目的"),
        settings_update.PhaseRemap(id="T-1", key="phase", from_value="整理", to_value="要件"),
    ]
    assert new_settings["goal"]["phase"] == "要件"


def test_remap_phases_when_unmapped(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_settings: MakeSettings
) -> None:
    """対応の無いフェーズを全て挙げて止める（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        settings=make_settings(
            ["問い", "発散", "結論"],
            {"phase": "結論", "summary": "まとめる", "deliverables": []},
        ),
    )
    workspace = store.load_workspace(root)
    settings = {**workspace.settings, "phases": ["目的", "要件"]}
    # 実行・検証
    with pytest.raises(UnmappedPhaseError) as raised:
        settings_update.remap_phases(workspace, settings, {"問い": "目的"})
    assert set(raised.value.lines) == {"D-2: 発散", "goal: 結論"}


def test_save_settings(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_settings: MakeSettings
) -> None:
    """設定と付け替えた種類を書き、一時ファイルを残さない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"), settings=make_settings(["問い", "発散"])
    )
    workspace = store.load_workspace(root)
    settings = make_settings(["目的", "発散"])
    change = store.Change(kind="decision", items=[make_item("D-1", phase="目的")])
    # 実行
    files = settings_update.save_settings(workspace, settings, [change])
    # 検証
    assert files == ["mindmap.yaml", "decisions.yaml"]
    assert yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8")) == settings
    assert yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8")) == {
        "items": change.items
    }
    assert list(root.rglob("*.tmp")) == []


def test_save_settings_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_settings: MakeSettings,
    snapshot_tree: SnapshotTree,
) -> None:
    """スキーマに合わない設定は書かない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"), settings=make_settings(["問い", "発散"])
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    settings = {**make_settings(["問い", "発散"]), "playbooks": []}
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as raised:
        settings_update.save_settings(workspace, settings, [])
    assert any(line.startswith("mindmap.yaml: playbooks") for line in raised.value.lines)
    assert snapshot_tree(root) == before


def test_save_settings_when_replace_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_settings: MakeSettings,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """途中の置き換えに失敗したら、置き換えたファイルを戻す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"), settings=make_settings(["問い", "発散"])
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(kind="decision", items=[make_item("D-1", phase="目的")])
    # settings_update モジュールの参照を、mindmap.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(settings_update.os, "replace", failing_replace("mindmap.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"mindmap\.yaml"):
        settings_update.save_settings(workspace, make_settings(["目的", "発散"]), [change])
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_update_settings(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_settings: MakeSettings
) -> None:
    """フェーズを付け替えて設定と種類の YAML を書き、結果を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        settings=make_settings(
            ["問い", "発散"], {"phase": "問い", "summary": "問いを決める", "deliverables": []}
        ),
    )
    # 実行
    result = settings_update.update_settings(
        root, {"phases": ["目的", "発散"]}, {"問い": "目的"}, now=_fixed_now
    )
    # 検証
    assert result == {
        "changed": ["phases", "goal"],
        "remapped": [{"id": "D-1", "key": "phase", "from": "問い", "to": "目的"}],
        "files": ["mindmap.yaml", "decisions.yaml"],
    }
    saved = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    assert saved["goal"]["phase"] == "目的"


def test_update_settings_when_goal_phase_unknown(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_settings: MakeSettings,
    snapshot_tree: SnapshotTree,
) -> None:
    """phases に無い goal.phase のゴールだけを渡すと何も書かない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"), settings=make_settings(["問い", "発散"])
    )
    before = snapshot_tree(root)
    settings = {"goal": {"phase": "結論", "summary": "まとめる", "deliverables": []}}
    # 実行・検証
    with pytest.raises(UnmappedPhaseError) as raised:
        settings_update.update_settings(root, settings, None)
    assert raised.value.lines == ["goal: 結論"]
    assert snapshot_tree(root) == before


def test_remap_names(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_settings: MakeSettings
) -> None:
    """対応で項目とカテゴリーの target・category を付け替え、同じ名前はそのままにする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", target="本体", category="画面"),
        make_item("D-2", target="管理画面", category="設定"),
        settings=make_settings(["問い"]),
    )
    workspace = store.load_workspace(root)
    settings = {
        **workspace.settings,
        "targets": [
            {"name": "アプリ", "summary": "アプリの本体"},
            {"name": "管理画面", "summary": "運用の画面"},
        ],
        "categories": [
            {"name": "画面", "target": "本体", "summary": "画面の部品"},
            {"name": "API", "target": "本体", "summary": "呼び出しの口"},
            {"name": "運用", "target": "管理画面", "summary": "運用の設定"},
        ],
    }
    # 実行
    items, remapped, new_settings = settings_update.remap_names(
        workspace.items, settings, {"本体": "アプリ"}, {"設定": "運用"}, now=_fixed_now
    )
    # 検証
    decisions = {item["id"]: item for item in items["decision"]}
    assert (decisions["D-1"]["target"], decisions["D-1"]["category"]) == ("アプリ", "画面")
    assert (decisions["D-2"]["target"], decisions["D-2"]["category"]) == ("管理画面", "運用")
    assert decisions["D-1"]["updated"] == NOW
    assert decisions["D-2"]["updated"] == NOW
    assert remapped == [
        settings_update.PhaseRemap(id="D-1", key="target", from_value="本体", to_value="アプリ"),
        settings_update.PhaseRemap(id="D-2", key="category", from_value="設定", to_value="運用"),
    ]
    assert [category["target"] for category in new_settings["categories"]] == [
        "アプリ",
        "アプリ",
        "管理画面",
    ]
    # 付け替えは変更履歴を積まない
    assert "history" not in decisions["D-1"]
    assert "history" not in decisions["D-2"]


def test_remap_names_when_unmapped(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_settings: MakeSettings
) -> None:
    """対応の無いカテゴリーを全て挙げて止める（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", target="mindmap", category="画面"),
        make_item("D-2", target="mindmap", category="設定"),
        settings=make_settings(["問い"]),
    )
    workspace = store.load_workspace(root)
    settings = {
        **workspace.settings,
        "categories": [{"name": "画面", "target": "mindmap", "summary": "画面の部品"}],
    }
    # 実行・検証
    with pytest.raises(errors.UnmappedTargetError) as raised:
        settings_update.remap_names(workspace.items, settings, {}, {})
    assert raised.value.lines == ["D-2: category: 設定"]
