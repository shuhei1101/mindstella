"""update_settings（設定の更新）の結合テスト。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import DEFAULT_TIMESTAMP

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree

# 話し合いの概要（ゴールと一緒に外すテストで使う）
DESCRIPTION = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"

# 壁打ちのフェーズ
WALL_PHASES = ["問い", "発散", "整理", "絞り込み", "結論"]


def _read_yaml(root: Path, file_name: str) -> Any:
    """ワークスペースの YAML を読む。"""
    return yaml.safe_load((root / file_name).read_text(encoding="utf-8"))


def _wall_settings(valid_settings: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """プレイブック `[壁打ち]`・壁打ちのフェーズ・ゴールのフェーズが 結論 の設定を返す。"""
    return {
        **valid_settings,
        "playbooks": ["壁打ち"],
        "phases": WALL_PHASES,
        "goal": {"phase": "結論", "summary": "結論まで出す", "deliverables": []},
        **overrides,
    }


def _two_phase_settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """フェーズが 問い → 発散 で、ゴールを持たない設定を返す。"""
    settings = {key: value for key, value in valid_settings.items() if key != "goal"}
    return {**settings, "phases": ["問い", "発散"]}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """題名・話し合いの概要・最上位の軸の呼び名・ゴールを置き換え、渡さないキーを残す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="目的"),
        settings={
            **valid_settings,
            "goal": {
                "phase": "要件",
                "summary": "要件が決まる",
                "deliverables": [{"title": "要件定義書"}],
            },
        },
    )
    before = snapshot_tree(root)
    settings_before = _read_yaml(root, "mindmap.yaml")
    new_goal = {
        "phase": "要件",
        "summary": "要件が決まる",
        "deliverables": [{"title": "要件定義書"}, {"title": "構成図"}],
    }
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={
            "summary": "要件出しのスキル mindmap を設計し直す",
            "description": DESCRIPTION,
            "target_label": "機能",
            "goal": new_goal,
        },
    )
    # 検証
    assert result.is_error is False
    assert result.data == {
        "changed": ["summary", "description", "target_label", "goal"],
        "remapped": [],
        "files": ["mindmap.yaml"],
    }
    settings = _read_yaml(root, "mindmap.yaml")
    assert settings["summary"] == "要件出しのスキル mindmap を設計し直す"
    assert settings["description"] == DESCRIPTION
    assert settings["target_label"] == "機能"
    assert settings["goal"] == new_goal
    for key in ("playbooks", "phases", "targets", "categories", "links"):
        assert settings[key] == settings_before[key]
    # 設定以外のファイルの中身が、呼ぶ前と同じ
    after = snapshot_tree(root)
    assert {name: text for name, text in after.items() if name != "mindmap.yaml"} == {
        name: text for name, text in before.items() if name != "mindmap.yaml"
    }


def test_normal_when_phases_remapped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """フェーズを置き換え、対応で項目の phase と goal.phase を付け替える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        make_item("T-1", phase="整理"),
        settings=_wall_settings(valid_settings),
    )
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={
            "playbooks": ["壁打ち", "システム開発"],
            "phases": ["目的", "発散", "要件", "構成", "インターフェース", "コンテンツ"],
        },
        phase_map={"問い": "目的", "整理": "要件", "絞り込み": "要件", "結論": "要件"},
    )
    # 検証
    assert result.is_error is False
    assert result.data == {
        "changed": ["playbooks", "phases", "goal"],
        "remapped": [
            {"id": "D-1", "from": "問い", "to": "目的"},
            {"id": "T-1", "from": "整理", "to": "要件"},
        ],
        "files": ["mindmap.yaml", "decisions.yaml", "tasks.yaml"],
    }
    decisions = {item["id"]: item for item in _read_yaml(root, "decisions.yaml")["items"]}
    tasks = {item["id"]: item for item in _read_yaml(root, "tasks.yaml")["items"]}
    assert decisions["D-1"]["phase"] == "目的"
    assert decisions["D-2"]["phase"] == "発散"
    assert tasks["T-1"]["phase"] == "要件"
    assert _read_yaml(root, "mindmap.yaml")["goal"]["phase"] == "要件"
    # 付け替えた項目だけ updated が書き換えた日時になる
    assert decisions["D-2"]["updated"] == DEFAULT_TIMESTAMP
    for remapped in (decisions["D-1"], tasks["T-1"]):
        assert remapped["updated"] != DEFAULT_TIMESTAMP
        assert datetime.fromisoformat(remapped["updated"]).tzinfo is not None
    # 点検が問題を 0 件で返す
    checked = call_tool("check", workspace=str(root))
    assert checked.data is not None
    assert checked.data["problems"] == []


def test_normal_when_goal_removed(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """値が null のキーを消す（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "description": DESCRIPTION})
    # 実行
    result = call_tool(
        "update_settings", workspace=str(root), settings={"goal": None, "description": None}
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["changed"] == ["goal", "description"]
    settings = _read_yaml(root, "mindmap.yaml")
    assert "goal" not in settings
    assert "description" not in settings


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"summary": "題名"})
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_unmapped_phase(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """新しい phases に無いフェーズを持つ項目が残ると、何も書かずに残る項目を返す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        settings=_two_phase_settings(valid_settings),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"phases": ["目的", "要件"]},
        phase_map={"問い": "目的"},
    )
    # 検証
    assert result.is_error is True
    assert "D-2: 発散" in result.text.splitlines()
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """空のプレイブックを渡すと、何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"playbooks": []})
    # 検証
    assert result.is_error is True
    assert any(line.startswith("mindmap.yaml: playbooks") for line in result.text.splitlines())
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、どのファイルも書き換えずにエラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"), settings=_two_phase_settings(valid_settings)
    )
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"phases": ["目的", "発散"]},
        phase_map={"問い": "目的"},
    )
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_bad_argument(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """新しい phases にもあるフェーズを phase_map のキーに渡すと、何も書かない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        settings=_two_phase_settings(valid_settings),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"phases": ["目的", "発散", "要件"]},
        phase_map={"問い": "目的", "発散": "要件"},
    )
    # 検証
    assert result.is_error is True
    assert "発散" in result.text
    assert snapshot_tree(root) == before
