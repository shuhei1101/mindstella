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
from fixture_types import (
    FailingReplace,
    MakeItem,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)
from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR

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
    "tags": [{"name": "保存"}, {"name": "通知"}],
}

type MakeSettings = Callable[..., dict[str, Any]]


def _validate(
    settings: dict[str, Any] | None,
    phase_map: dict[str, str] | None = None,
    *,
    target_map: dict[str, str] | None = None,
    category_map: dict[str, str] | None = None,
    tag_map: dict[str, str | None] | None = None,
    current: dict[str, Any] = CURRENT_SETTINGS,
    used_tags: frozenset[str] | None = None,
) -> None:
    """今の phases を 問い・発散、今の設定を current（既定は CURRENT_SETTINGS）にして、引数を確かめる。"""
    # tag_map と used_tags は渡したときだけ引数にする
    tag_kwargs: dict[str, Any] = {} if tag_map is None else {"tag_map": tag_map}
    if used_tags is not None:
        tag_kwargs["used_tags"] = used_tags
    settings_update.validate_settings_input(
        settings,
        phase_map,
        ["問い", "発散"],
        target_map=target_map,
        category_map=category_map,
        current=current,
        **tag_kwargs,
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


@pytest.mark.parametrize(
    ("settings", "tag_map", "expected_error_name", "message"),
    [
        pytest.param(
            {"summary": "新しい題名"},
            {"通知": "保存"},
            "ArgumentError",
            "tag_map",
            id="without_tags",
        ),
        pytest.param(
            {"tags": [{"name": "保存"}, {"name": "通知"}]},
            {"保存": "通知"},
            "ArgumentError",
            "tag_map",
            id="key_in_new_tags",
        ),
        pytest.param(
            {"tags": [{"name": "保存"}]},
            {"不明": "保存"},
            "ArgumentError",
            "tag_map",
            id="key_in_neither_vocabulary_nor_items",
        ),
        pytest.param(
            {"tags": [{"name": "保存"}]},
            {"通知": "不明"},
            "UnmappedTagError",
            "対応の無いタグ",
            id="value_not_in_new_tags",
        ),
        pytest.param(
            {"summary": "新しい題名"},
            {"保存処理": "不明"},
            "UnmappedTagError",
            "対応の無いタグ",
            id="candidate_value_not_in_current_tags",
        ),
        pytest.param(
            {"tags": [{"name": "保存"}, {"name": "保存"}]},
            None,
            "SchemaMismatchError",
            "同じ名前のタグが重なっています",
            id="duplicated_tags",
        ),
    ],
)
def test_validate_settings_input_when_bad_tag_map(
    settings: dict[str, Any],
    tag_map: dict[str, str | None] | None,
    expected_error_name: str,
    message: str,
) -> None:
    """tag_map の誤った渡し方と語彙の名前の重なりを拒む（異常系）。"""
    # 準備
    expected_error = getattr(errors, expected_error_name)
    # 実行・検証
    with pytest.raises(expected_error) as raised:
        _validate(settings, tag_map=tag_map, used_tags=frozenset({"保存", "保存処理"}))
    assert message in "\n".join([str(raised.value), *raised.value.lines])


def test_validate_settings_input_when_tag_removed() -> None:
    """値が None の対応は外す対応として通す（正常系）。"""
    # 準備
    current = {**CURRENT_SETTINGS, "tags": [{"name": "保存"}, {"name": "下書き"}]}
    settings = {"tags": [{"name": "保存"}]}
    # 実行・検証
    _validate(settings, tag_map={"下書き": None}, current=current)


def test_validate_settings_input_when_candidate_mapped() -> None:
    """settings を渡さず、未登録の候補を今の語彙のタグへ付け替える対応を通す（正常系）。"""
    # 準備
    current = {**CURRENT_SETTINGS, "tags": [{"name": "保存"}]}
    # 実行・検証
    _validate(
        None,
        tag_map={"保存処理": "保存"},
        current=current,
        used_tags=frozenset({"保存処理"}),
    )


def test_validate_settings_input_when_nothing_given() -> None:
    """settings も tag_map も渡さなければ引数の誤りにする（異常系）。"""
    # 実行・検証
    with pytest.raises(ArgumentError) as raised:
        _validate(None)
    assert raised.value.argument == "settings"


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
    assert decisions["D-1"]["updated_by"] == "ai"
    assert decisions["D-2"]["phase"] == "発散"
    assert decisions["D-2"]["updated"] == DEFAULT_TIMESTAMP
    assert "updated_by" not in decisions["D-2"]
    assert tasks["T-1"]["phase"] == "要件"
    assert tasks["T-1"]["updated"] == NOW
    assert tasks["T-1"]["updated_by"] == "ai"
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
    assert files == [".mindstella/config.yaml", ".mindstella/decisions.yaml"]
    assert (
        yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8")) == settings
    )
    assert yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8")) == {
        "items": change.items
    }
    assert list(root.rglob("*.tmp")) == []


def test_save_settings_with_threads(
    make_workspace: MakeWorkspace,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
) -> None:
    """スレッドも一緒に書く（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "tags": [{"name": "保存"}, {"name": "通知"}]})
    write_threads(root, make_thread("TH-1", tags=["通知"]))
    workspace = store.load_workspace(root)
    settings = {**workspace.settings, "tags": [{"name": "保存"}, {"name": "お知らせ"}]}
    threads = [make_thread("TH-1", tags=["お知らせ"])]
    # 実行
    files = settings_update.save_settings(workspace, settings, [], threads=threads)
    # 検証
    assert files == [".mindstella/config.yaml", ".mindstella/threads.yaml"]
    saved = yaml.safe_load((root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8"))
    assert saved["items"][0]["tags"] == ["お知らせ"]


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
    assert any(line.startswith("config.yaml: playbooks") for line in raised.value.lines)
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
    # settings_update モジュールの参照を、config.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(settings_update.os, "replace", failing_replace("config.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"config\.yaml"):
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
        "files": [".mindstella/config.yaml", ".mindstella/decisions.yaml"],
    }
    saved = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert saved["goal"]["phase"] == "目的"
    decisions = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))
    assert decisions["items"][0]["updated_by"] == "ai"


def test_stage_settings(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_settings: MakeSettings,
    snapshot_tree: SnapshotTree,
) -> None:
    """書かずに付け替えを当て、編集した人を渡した人にする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"), settings=make_settings(["問い", "発散"])
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # 実行
    staged = settings_update.stage_settings(
        workspace,
        {"phases": ["目的", "発散"]},
        threads=[],
        phase_map={"問い": "目的"},
        editor="user",
        now=_fixed_now,
    )
    # 検証
    assert staged.changed == ["phases"]
    assert staged.remapped == [
        settings_update.PhaseRemap(id="D-1", key="phase", from_value="問い", to_value="目的")
    ]
    assert staged.items["decision"][0]["phase"] == "目的"
    assert staged.items["decision"][0]["updated_by"] == "user"
    assert snapshot_tree(root) == before


def test_update_settings_when_tags_remapped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
) -> None:
    """語彙を置き換え、項目とスレッドのタグを付け替えて書く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["通知"]),
        settings={**valid_settings, "tags": [{"name": "保存"}, {"name": "通知"}]},
    )
    write_threads(root, make_thread("TH-1", tags=["通知"]))
    settings = {"tags": [{"name": "保存"}, {"name": "お知らせ"}]}
    # 実行
    result = settings_update.update_settings(
        root, settings, None, now=_fixed_now, tag_map={"通知": "お知らせ"}
    )
    # 検証
    assert result == {
        "changed": ["tags"],
        "remapped": [
            {"id": "D-1", "key": "tags", "from": "通知", "to": "お知らせ"},
            {"id": "TH-1", "key": "tags", "from": "通知", "to": "お知らせ"},
        ],
        "files": [
            ".mindstella/config.yaml",
            ".mindstella/decisions.yaml",
            ".mindstella/threads.yaml",
        ],
    }


def test_update_settings_when_candidate_mapped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
) -> None:
    """settings を渡さず、未登録の候補を既存のタグへ付け替えて書く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存処理"]),
        settings={**valid_settings, "tags": [{"name": "保存"}]},
    )
    write_threads(root, make_thread("TH-1", tags=["保存処理"]))
    config_path = root / RECORD_DIR / "config.yaml"
    config_before = config_path.read_text(encoding="utf-8")
    # 実行
    result = settings_update.update_settings(
        root, None, None, now=_fixed_now, tag_map={"保存処理": "保存"}
    )
    # 検証
    assert result == {
        "changed": [],
        "remapped": [
            {"id": "D-1", "key": "tags", "from": "保存処理", "to": "保存"},
            {"id": "TH-1", "key": "tags", "from": "保存処理", "to": "保存"},
        ],
        "files": [".mindstella/decisions.yaml", ".mindstella/threads.yaml"],
    }
    assert config_path.read_text(encoding="utf-8") == config_before


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


# 表示する種類の既定のうち、用語集を除いた 6 種類
KINDS_WITHOUT_TERMS = ["decisions", "tasks", "research", "docs", "notes", "logs"]

# 表示する種類の既定のうち、会話ログを除いた 6 種類
KINDS_WITHOUT_LOGS = ["decisions", "tasks", "research", "docs", "terms", "notes"]


def test_update_settings_when_display(make_workspace: MakeWorkspace) -> None:
    """表示の既定を丸ごと置き換え、ほかのキーと項目を変えない（正常系）。"""
    # 準備
    root = make_workspace()
    before = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    display = {"network_look": "starlight", "visible_kinds": KINDS_WITHOUT_LOGS}
    # 実行
    first = settings_update.update_settings(root, {"display": display}, None)
    after_first = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    second = settings_update.update_settings(root, {"display": {"network_look": "glow"}}, None)
    after_second = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    # 検証
    assert first["changed"] == ["display"]
    assert first["files"] == [".mindstella/config.yaml"]
    assert after_first["display"] == display
    assert {key: value for key, value in after_first.items() if key != "display"} == before
    assert second["changed"] == ["display"]
    assert after_second["display"] == {"network_look": "glow"}


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
    assert decisions["D-1"]["updated_by"] == "ai"
    assert decisions["D-2"]["updated_by"] == "ai"
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


def test_remap_tags(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
) -> None:
    """対応で付け替え、null の対応は外し、スレッドも付け替える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存", "下書き"]),
        make_item("D-2", tags=["通知", "お知らせ"]),
    )
    workspace = store.load_workspace(root)
    threads = [make_thread("TH-1", tags=["通知"])]
    tag_map = {"通知": "お知らせ", "下書き": None}
    # 実行
    items, new_threads, remapped = settings_update.remap_tags(
        workspace.items, threads, tag_map, now=_fixed_now, removed=frozenset({"通知", "下書き"})
    )
    # 検証
    decisions = {item["id"]: item for item in items["decision"]}
    assert decisions["D-1"]["tags"] == ["保存"]
    assert decisions["D-2"]["tags"] == ["お知らせ"]
    assert new_threads[0]["tags"] == ["お知らせ"]
    assert remapped == [
        settings_update.PhaseRemap(id="D-1", key="tags", from_value="下書き", to_value=None),
        settings_update.PhaseRemap(id="D-2", key="tags", from_value="通知", to_value="お知らせ"),
        settings_update.PhaseRemap(id="TH-1", key="tags", from_value="通知", to_value="お知らせ"),
    ]
    assert decisions["D-1"]["updated_by"] == "ai"
    assert decisions["D-2"]["updated_by"] == "ai"
    assert decisions["D-1"]["updated"] == NOW


def test_remap_tags_when_unmapped(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """対応の無い外したタグが残ると止める（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["保存"]), make_item("D-2", tags=["通知"]))
    workspace = store.load_workspace(root)
    # 実行・検証
    with pytest.raises(errors.UnmappedTagError) as raised:
        settings_update.remap_tags(
            workspace.items, [], {}, now=_fixed_now, removed=frozenset({"通知"})
        )
    assert raised.value.unmapped == [("D-2", "通知")]


def test_remap_tags_when_tags_not_given(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_thread: MakeThread
) -> None:
    """語彙を置き換えず対応も無ければ何も変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["通知"]))
    workspace = store.load_workspace(root)
    threads = [make_thread("TH-1", tags=["起票"])]
    # 実行
    items, new_threads, remapped = settings_update.remap_tags(
        workspace.items, threads, {}, now=_fixed_now, removed=frozenset()
    )
    # 検証
    assert items == workspace.items
    assert new_threads == threads
    assert remapped == []


def test_remap_tags_when_vocabulary_removed(
    make_workspace: MakeWorkspace, make_item: MakeItem, make_thread: MakeThread
) -> None:
    """tags: null で語彙を消すとき、外したタグに対応が無ければ止め、未登録の候補は残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["保存"]))
    workspace = store.load_workspace(root)
    threads = [make_thread("TH-1", tags=["起票"])]
    # 実行・検証
    with pytest.raises(errors.UnmappedTagError) as raised:
        settings_update.remap_tags(
            workspace.items, threads, {}, now=_fixed_now, removed=frozenset({"保存"})
        )
    assert raised.value.unmapped == [("D-1", "保存")]


def test_remap_tags_when_candidate_mapped(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """語彙を置き換えずに、未登録の候補を既存のタグへ付け替え、対応の無い候補は残す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存処理", "保存"]),
        make_item("D-2", tags=["通知"]),
    )
    workspace = store.load_workspace(root)
    # 実行
    items, _, remapped = settings_update.remap_tags(
        workspace.items, [], {"保存処理": "保存"}, now=_fixed_now, removed=frozenset()
    )
    # 検証
    decisions = {item["id"]: item for item in items["decision"]}
    assert decisions["D-1"]["tags"] == ["保存"]
    assert decisions["D-2"]["tags"] == ["通知"]
    assert remapped == [
        settings_update.PhaseRemap(id="D-1", key="tags", from_value="保存処理", to_value="保存")
    ]


def test_update_display(make_workspace: MakeWorkspace) -> None:
    """display だけを置き換え、ほかのキーと並びを保つ（正常系）。"""
    # 準備
    root = make_workspace()
    before = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    body = {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS}
    # 実行
    result = settings_update.update_display(root, body)
    # 検証
    saved = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert result == {"display": body}
    assert list(saved) == [*before, "display"]
    assert {key: value for key, value in saved.items() if key != "display"} == before
    assert saved["display"] == body
    assert not (root / RECORD_DIR / "changes.yaml").exists()


@pytest.mark.parametrize(
    ("body", "words"),
    [
        pytest.param(
            {"network_look": "rainbow", "visible_kinds": KINDS_WITHOUT_TERMS},
            ["network_look", "glow"],
            id="unknown_look",
        ),
        pytest.param({"visible_kinds": KINDS_WITHOUT_TERMS}, ["network_look"], id="no_look"),
        pytest.param(
            {"network_look": "glow", "visible_kinds": ["decisions", "decisions"]},
            ["visible_kinds"],
            id="duplicate_kinds",
        ),
        pytest.param(
            {"network_look": "glow", "visible_kinds": ["graph"]},
            ["visible_kinds"],
            id="unknown_kind",
        ),
        pytest.param(
            {"network_look": "glow", "visible_kinds": "decisions"},
            ["visible_kinds"],
            id="kinds_string",
        ),
    ],
)
def test_update_display_when_body_invalid(
    make_workspace: MakeWorkspace, body: dict[str, Any], words: list[str]
) -> None:
    """合わない本文は書かない（異常系）。"""
    # 準備
    root = make_workspace()
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行・検証
    with pytest.raises(errors.SettingsInvalidError) as raised:
        settings_update.update_display(root, body)
    assert all(word in str(raised.value) for word in words)
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == before


def test_update_display_when_settings_broken(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any]
) -> None:
    """崩れた config.yaml には書き足さない（異常系）。"""
    # 準備
    broken = {key: value for key, value in valid_settings.items() if key != "phases"}
    root = make_workspace(settings=broken)
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    body = {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS}
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as raised:
        settings_update.update_display(root, body)
    assert any(line.startswith("config.yaml: ") and "phases" in line for line in raised.value.lines)
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == before
