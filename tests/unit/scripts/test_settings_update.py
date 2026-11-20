"""settings_update.py（設定の更新の引数の確かめ・設定の置き換え・書き込み）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

import errors
import settings_update
import store
from errors import ArgumentError, SchemaMismatchError, WriteFailedError
from fixture_types import FailingReplace, MakeItem, MakeWorkspace, SnapshotTree
from workspace_fixtures import RECORD_DIR


def test_validate_settings_input() -> None:
    """書き換えられるキーだけなら通す（正常系）。"""
    # 準備
    settings = {"summary": "題", "links": None}
    # 実行・検証
    settings_update.validate_settings_input(settings)


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param({}, id="empty"),
        pytest.param({"field": "システム開発"}, id="not_editable_key"),
        pytest.param({"summary": None}, id="required_key_null"),
        pytest.param({"tags": []}, id="tags_removed"),
        pytest.param({"mdmark": {"version": "v0.13.0", "map": {}}}, id="mdmark_map_given"),
        pytest.param({"mdmark": None}, id="mdmark_null"),
    ],
)
def test_validate_settings_input_when_bad_key(settings: dict[str, Any]) -> None:
    """書き換えられないキー・必須のキーの null を弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        settings_update.validate_settings_input(settings)


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        pytest.param({"summary": "題", "playbooks": ["壁打ち"]}, "playbooks", id="playbooks"),
        pytest.param({"goal": None}, "goal", id="goal_null"),
        pytest.param({"phases": [], "categories": []}, "phases.*categories|categories.*phases", id="phases_categories"),
    ],
)
def test_validate_settings_input_when_removed_key(settings: dict[str, Any], message: str) -> None:
    """削除したキーは引数の誤り（異常系）。"""
    # 実行・検証
    with pytest.raises(ArgumentError, match=message) as raised:
        settings_update.validate_settings_input(settings)
    assert raised.value.argument == "settings"


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param({"confirm_on_comment": False}, id="false"),
        pytest.param({"confirm_on_comment": None}, id="null"),
    ],
)
def test_validate_settings_input_confirm_on_comment(settings: dict[str, Any]) -> None:
    """コメントの送信で確認済みにするかを書き換え・消せる（正常系）。"""
    # 実行・検証
    settings_update.validate_settings_input(settings)


def test_validate_settings_input_confirm_on_comment_invalid() -> None:
    """真偽値でない confirm_on_comment は断る（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as raised:
        settings_update.validate_settings_input({"confirm_on_comment": "yes"})
    assert any(line.startswith("config.yaml: confirm_on_comment") for line in raised.value.lines)


def test_merge_settings() -> None:
    """渡したキーだけを置き換え、null で消し、並びを保つ（正常系）。"""
    # 準備
    current = {"summary": "前の題名", "links": [], "history_limit": 3}
    settings = {"summary": "新しい題名", "links": None, "description": "概要", "history_limit": 3}
    # 実行
    merged, changed = settings_update.merge_settings(current, settings)
    # 検証
    assert merged == {"summary": "新しい題名", "history_limit": 3, "description": "概要"}
    assert list(merged) == ["summary", "history_limit", "description"]
    assert changed == ["summary", "links", "description"]
    # 渡した設定そのものは書き換えない
    assert "links" in current


def test_merge_settings_when_mdmark() -> None:
    """mdmark は version だけを置き換え、移し替えが書いた map を残す（正常系）。"""
    # 準備
    current = {"summary": "題名", "mdmark": {"version": "latest", "map": {"kinds": {"llm": {}}}}}
    # 実行
    merged, changed = settings_update.merge_settings(current, {"mdmark": {"version": "v0.13.0"}})
    # 検証
    assert merged["mdmark"] == {"version": "v0.13.0", "map": {"kinds": {"llm": {}}}}
    assert changed == ["mdmark"]


def test_save_settings(make_workspace: MakeWorkspace) -> None:
    """設定を書き、一時ファイルを残さない（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    settings = {"summary": "新しい題名", "links": []}
    # 実行
    files = settings_update.save_settings(workspace, settings)
    # 検証
    assert files == [".mindstella/config.yaml"]
    assert yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8")) == settings
    assert list(root.rglob("*.tmp")) == []


def test_save_settings_when_settings_unchanged(make_workspace: MakeWorkspace) -> None:
    """設定が変わらないときは書かない（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    config_path = root / RECORD_DIR / "config.yaml"
    config_before = config_path.read_text(encoding="utf-8")
    # 実行
    files = settings_update.save_settings(workspace, workspace.settings)
    # 検証
    assert files == []
    assert config_path.read_text(encoding="utf-8") == config_before


def test_save_settings_when_schema_mismatch(
    make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """スキーマに合わない設定は書かない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    settings = {"summary": "題名", "links": [], "history_limit": -1}
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as raised:
        settings_update.save_settings(workspace, settings)
    assert any(line.startswith("config.yaml: history_limit") for line in raised.value.lines)
    assert snapshot_tree(root) == before


def test_save_settings_when_replace_fails(
    make_workspace: MakeWorkspace,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """置き換えに失敗したら一時ファイルを残さない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # settings_update モジュールの参照を、config.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(settings_update.os, "replace", failing_replace("config.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"config\.yaml"):
        settings_update.save_settings(workspace, {"summary": "新しい題名", "links": []})
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_update_settings(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """設定を置き換えて書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    links = [{"title": "仕様", "url": "https://example.com"}]
    # 実行
    result = settings_update.update_settings(root, {"summary": "新しい題名", "links": links})
    # 検証
    assert result == {"changed": ["summary", "links"], "files": [".mindstella/config.yaml"]}
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before


def test_update_settings_when_removed_key(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """削除したキーを渡すと何も書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(ArgumentError, match="playbooks"):
        settings_update.update_settings(root, {"summary": "題", "playbooks": ["壁打ち"]})
    assert snapshot_tree(root) == before


def test_stage_settings(make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree) -> None:
    """書かずに当てた設定を返す（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # 実行
    staged = settings_update.stage_settings(workspace, {"summary": "新しい題名"})
    # 検証
    assert staged.changed == ["summary"]
    assert staged.settings["summary"] == "新しい題名"
    assert snapshot_tree(root) == before


# 表示する種類の既定のうち、用語集を除いた 6 種類
KINDS_WITHOUT_TERMS = ["decisions", "tasks", "research", "docs", "notes", "logs"]

# 表示する種類の既定のうち、会話ログを除いた 6 種類
KINDS_WITHOUT_LOGS = ["decisions", "tasks", "research", "docs", "terms", "notes"]


def test_update_settings_when_display(make_workspace: MakeWorkspace) -> None:
    """表示の既定を丸ごと置き換え、ほかのキーと項目を変えない（正常系）。"""
    # 準備
    root = make_workspace(settings={"summary": "題名", "links": [], "history_limit": 3})
    before = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    display = {"network_look": "starlight", "visible_kinds": KINDS_WITHOUT_LOGS}
    # 実行
    first = settings_update.update_settings(root, {"display": display})
    after_first = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    second = settings_update.update_settings(root, {"display": {"network_look": "glow"}})
    after_second = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    # 検証
    assert first["changed"] == ["display"]
    assert first["files"] == [".mindstella/config.yaml"]
    assert after_first["display"] == display
    assert {key: value for key, value in after_first.items() if key != "display"} == before
    assert second["changed"] == ["display"]
    assert after_second["display"] == {"network_look": "glow"}


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
    broken = {key: value for key, value in valid_settings.items() if key != "summary"}
    root = make_workspace(settings=broken)
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    body = {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS}
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as raised:
        settings_update.update_display(root, body)
    assert any(line.startswith("config.yaml: ") and "summary" in line for line in raised.value.lines)
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == before
