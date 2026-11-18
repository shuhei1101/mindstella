"""update_settings（設定の更新）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import RECORD_DIR

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree

# 話し合いの概要
DESCRIPTION = (
    "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"
)

# 表示の既定
DISPLAY = {"network_look": "deep"}


def _read_yaml(root: Path, file_name: str) -> Any:
    """ワークスペースの YAML を読む。"""
    return yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """題名・話し合いの概要・関連する場所を置き換え、渡さないキーを残す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        settings={**valid_settings, "history_limit": 3, "display": DISPLAY},
    )
    before = snapshot_tree(root)
    links = [{"title": "設計書", "url": "https://example.com"}]
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={
            "summary": "要件出しのスキル mindmap を設計し直す",
            "description": DESCRIPTION,
            "links": links,
        },
    )
    # 検証
    assert result.is_error is False, result.text
    assert result.data == {
        "changed": ["summary", "description", "links"],
        "files": [".mindstella/config.yaml"],
    }
    settings = _read_yaml(root, "config.yaml")
    assert settings["summary"] == "要件出しのスキル mindmap を設計し直す"
    assert settings["description"] == DESCRIPTION
    assert settings["links"] == links
    assert (settings["history_limit"], settings["display"]) == (3, DISPLAY)
    # 設定以外のファイルの中身が、呼ぶ前と同じ
    after = snapshot_tree(root)
    assert {name: text for name, text in after.items() if name != ".mindstella/config.yaml"} == {
        name: text for name, text in before.items() if name != ".mindstella/config.yaml"
    }


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"summary": "題名"})
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """空の題名を渡すと、何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"summary": ""})
    # 検証
    assert result.is_error is True
    assert any(line.startswith("config.yaml: summary") for line in result.text.splitlines())
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、どのファイルも書き換えずにエラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"summary": "題名"})
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_removed_key_given(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """削除したキー（playbooks）を渡すと、何も書かずにエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "update_settings", workspace=str(root), settings={"summary": "題", "playbooks": ["壁打ち"]}
    )
    # 検証
    assert result.is_error is True
    assert "playbooks" in result.text
    assert snapshot_tree(root) == before


def test_normal_when_links_and_history_limit(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """関連する場所と保持する回数を書き換える（正常系）。"""
    # 準備
    settings = {key: value for key, value in valid_settings.items() if key != "links"}
    root = make_workspace(settings=settings)
    settings_before = _read_yaml(root, "config.yaml")
    links = [{"title": "仕様", "url": "https://example.com/spec"}]
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"links": links, "history_limit": 3},
    )
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["changed"] == ["links", "history_limit"]
    settings_after = _read_yaml(root, "config.yaml")
    assert settings_after["links"] == links
    assert settings_after["history_limit"] == 3
    assert {key: value for key, value in settings_after.items() if key not in ("links", "history_limit")} == {
        key: value for key, value in settings_before.items() if key not in ("links", "history_limit")
    }


def test_normal_when_display(
    make_workspace: MakeWorkspace, call_tool: CallTool, valid_settings: dict[str, Any]
) -> None:
    """見た目の既定と表示する種類の既定を書き換え、ほかのキーを変えない（正常系）。"""
    # 準備
    root = make_workspace()
    before = _read_yaml(root, "config.yaml")
    display = {
        "network_look": "starlight",
        "visible_kinds": ["decisions", "tasks", "research", "docs", "terms", "notes"],
    }
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"display": display})
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["changed"] == ["display"]
    after = _read_yaml(root, "config.yaml")
    assert after["display"] == display
    assert {key: value for key, value in after.items() if key != "display"} == before
    assert before == valid_settings


def test_normal_when_transcription(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """文字起こし後の挙動と用語集のプリセットを書き換える（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"transcription": {"action": "insert", "preset": "開発"}},
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["changed"] == ["transcription"]
    after = _read_yaml(root, "config.yaml")
    assert (after["transcription"]["action"], after["transcription"]["preset"]) == ("insert", "開発")


def test_error_when_transcription_action_invalid(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """review・send・insert のどれでもない挙動を渡すと、何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"transcription": {"action": "paste"}})
    # 検証
    assert result.is_error is True
    assert any(line.startswith("config.yaml: transcription.action") for line in result.text.splitlines())
    assert snapshot_tree(root) == before


def test_normal_when_mdmark_version(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """画面が読み込む mdmark のバージョンをタグにし、ほかのキーと map の種類を残す（正常系）。"""
    # 準備
    mdmark_map = {"kinds": {"llm": {"label": "LLM"}}}
    root = make_workspace(settings={**valid_settings, "mdmark": {"map": mdmark_map}})
    before = _read_yaml(root, "config.yaml")
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"mdmark": {"version": "v0.13.0"}})
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["changed"] == ["mdmark"]
    after = _read_yaml(root, "config.yaml")
    assert after["mdmark"] == {"map": mdmark_map, "version": "v0.13.0"}
    assert {key: value for key, value in after.items() if key != "mdmark"} == {
        key: value for key, value in before.items() if key != "mdmark"
    }


def test_error_when_mdmark_version_invalid(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """latest でもタグでもないバージョンを渡すと、何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"mdmark": {"version": "develop"}})
    # 検証
    assert result.is_error is True
    assert any(line.startswith("config.yaml: mdmark.version") for line in result.text.splitlines())
    assert snapshot_tree(root) == before
