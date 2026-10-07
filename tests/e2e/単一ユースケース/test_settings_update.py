"""設定の更新（スキルが話し合いの途中で設定を書き換え、フェーズが変わるときは項目のフェーズも付け替える）の E2E テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 壁打ちのフェーズ
WALL_PHASES = ["問い", "発散", "整理", "絞り込み", "結論"]

# 書き換える話し合いの概要
DESCRIPTION = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"


def _wall_settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """プレイブック `[壁打ち]`・壁打ちのフェーズ・ゴールのフェーズが 結論 の設定を返す。"""
    return {
        **valid_settings,
        "playbooks": ["壁打ち"],
        "phases": WALL_PHASES,
        "goal": {"phase": "結論", "summary": "結論まで出す", "deliverables": []},
    }


def _two_phase_settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """フェーズが 問い → 発散 で、ゴールを持たない設定を返す。"""
    settings = {key: value for key, value in valid_settings.items() if key != "goal"}
    return {**settings, "phases": ["問い", "発散"]}


def test_normal(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """題名・話し合いの概要・最上位の軸の呼び名・ゴールの概要を置き換え、納品物を足す（正常系）。"""
    # 準備
    root = make_workspace(
        settings={
            **valid_settings,
            "target_label": "システム",
            "goal": {
                "phase": "要件",
                "summary": "要件が決まる",
                "deliverables": [{"title": "要件定義書"}],
            },
        }
    )
    ws = {"workspace": str(root)}
    before = read_yaml(root, "config.yaml")
    # 実行
    replay(
        "update_settings",
        **ws,
        settings={
            "summary": "要件出しのスキル mindmap を設計し直す",
            "description": DESCRIPTION,
            "target_label": "機能",
            "goal": {
                "phase": "要件",
                "summary": "要件と構成が決まる",
                "deliverables": [{"title": "要件定義書"}, {"title": "構成図"}],
            },
        },
    )
    checked = call_tool("check", **ws)
    # 検証
    settings = read_yaml(root, "config.yaml")
    # summary・話し合いの概要・target_label・goal.summary が渡した値である
    assert settings["summary"] == "要件出しのスキル mindmap を設計し直す"
    assert settings["description"] == DESCRIPTION
    assert settings["target_label"] == "機能"
    assert settings["goal"]["summary"] == "要件と構成が決まる"
    # goal.deliverables が要件定義書と構成図の 2 件である
    assert [deliverable["title"] for deliverable in settings["goal"]["deliverables"]] == [
        "要件定義書",
        "構成図",
    ]
    # playbooks・phases・targets・categories が呼ぶ前と同じである
    for key in ("playbooks", "phases", "targets", "categories"):
        assert settings[key] == before[key]
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.is_error is False
    assert checked.data == {"ok": True, "problems": []}


def test_normal_when_playbooks_replaced(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """プレイブックを足し、フェーズを置き換えて、対応で項目の phase と goal.phase を付け替える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        settings=_wall_settings(valid_settings),
    )
    ws = {"workspace": str(root)}
    new_phases = ["目的", "発散", "要件", "構成", "インターフェース", "コンテンツ"]
    # 実行
    # 新しい並びにも同じ名前がある発散は、対応を渡さない
    replay(
        "update_settings",
        **ws,
        settings={"playbooks": ["壁打ち", "システム開発"], "phases": new_phases},
        phase_map={"問い": "目的", "整理": "要件", "絞り込み": "要件", "結論": "要件"},
    )
    checked = replay("check", **ws)
    # 検証
    settings = read_yaml(root, "config.yaml")
    # playbooks が壁打ち・システム開発の 2 件で、phases が渡した並びである
    assert settings["playbooks"] == ["壁打ち", "システム開発"]
    assert settings["phases"] == new_phases
    # D-1 の phase が目的、D-2 の phase が発散である
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    assert decisions["D-1"]["phase"] == "目的"
    assert decisions["D-2"]["phase"] == "発散"
    # 付け替えた D-1 の updated_by が ai で、付け替えていない D-2 は編集した人を持たない
    assert decisions["D-1"]["updated_by"] == "ai"
    assert "updated_by" not in decisions["D-2"]
    # goal.phase が要件である
    assert settings["goal"]["phase"] == "要件"
    # 点検が問題を 0 件で返す
    assert checked == {"ok": True, "problems": []}


def test_normal_when_goal_removed(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """ゴールを空にして渡すと、ゴールのキーが消える（正常系）。"""
    # 準備
    root = make_workspace(settings=valid_settings)
    ws = {"workspace": str(root)}
    # 実行
    replay("update_settings", **ws, settings={"goal": None})
    checked = replay("check", **ws)
    # 検証
    # config.yaml が goal のキーを持たない
    assert "goal" not in read_yaml(root, "config.yaml")
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked == {"ok": True, "problems": []}


def test_error_when_unmapped_phase(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """新しい phases に無いフェーズを持つ項目が残る書き換えは、何も書かずにエラーになる（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="問い"),
        make_item("D-2", phase="発散"),
        settings=_two_phase_settings(valid_settings),
    )
    before = snapshot_tree(root)
    # 実行
    # 発散の対応を渡さない
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"phases": ["目的", "要件"]},
        phase_map={"問い": "目的"},
    )
    # 検証
    # 設定を書き換えるツールがエラーを返し、本文に D-2 とフェーズ発散がある
    assert result.is_error is True
    assert "D-2: 発散" in result.text.splitlines()
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """プレイブックを空の配列にして渡すと、何も書かずにエラーになる（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update_settings", workspace=str(root), settings={"playbooks": []})
    # 検証
    # 設定を書き換えるツールがエラーを返し、本文に合わないキー playbooks がある
    assert result.is_error is True
    assert "playbooks" in result.text
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_targets_remapped(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """対象・カテゴリーを置き換え、対応で項目とカテゴリーの target・category を付け替える（正常系）。"""
    # 準備
    root = make_workspace(
        settings={
            **valid_settings,
            "targets": [
                {"name": "本体", "summary": "アプリの本体"},
                {"name": "管理画面", "summary": "運用の画面"},
            ],
            "categories": [
                {"name": "画面", "target": "本体", "summary": "画面の部品"},
                {"name": "API", "target": "本体", "summary": "呼び出しの口"},
                {"name": "設定", "target": "管理画面", "summary": "設定の画面"},
            ],
        }
    )
    ws = {"workspace": str(root)}
    replay(
        "add",
        **ws,
        kind="decision",
        item={
            "title": "画面の問い",
            "status": "未決定",
            "options": [{"key": "A", "content": "案 A"}],
            "target": "本体",
            "category": "画面",
        },
    )
    replay(
        "add",
        **ws,
        kind="decision",
        item={
            "title": "設定の問い",
            "status": "未決定",
            "options": [{"key": "A", "content": "案 A"}],
            "target": "管理画面",
            "category": "設定",
        },
    )
    replay("commit", **ws, summary="足す")
    new_targets = [
        {"name": "アプリ", "summary": "アプリの本体"},
        {"name": "管理画面", "summary": "運用の画面"},
    ]
    new_categories = [
        {"name": "画面", "target": "アプリ", "summary": "画面の部品"},
        {"name": "API", "target": "アプリ", "summary": "呼び出しの口"},
        {"name": "運用", "target": "管理画面", "summary": "運用の設定"},
    ]
    # 実行
    replay(
        "update_settings",
        **ws,
        settings={"targets": new_targets, "categories": new_categories},
        target_map={"本体": "アプリ"},
        category_map={"設定": "運用"},
    )
    pending = replay("pending", **ws)
    checked = call_tool("check", **ws)
    # 検証
    settings = read_yaml(root, "config.yaml")
    # targets・categories が渡した値である
    assert settings["targets"] == new_targets
    assert settings["categories"] == new_categories
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    # D-1 の target が アプリ、category が 画面。D-2 の target が 管理画面、category が 運用
    assert (decisions["D-1"]["target"], decisions["D-1"]["category"]) == ("アプリ", "画面")
    assert (decisions["D-2"]["target"], decisions["D-2"]["category"]) == ("管理画面", "運用")
    # 付け替えた D-1・D-2 の updated_by が ai である
    assert [decisions[item_id]["updated_by"] for item_id in ("D-1", "D-2")] == ["ai", "ai"]
    # D-1・D-2 が変更履歴を持たず、pending が空を返す
    assert "history" not in decisions["D-1"]
    assert "history" not in decisions["D-2"]
    assert pending == {"added": [], "changed": []}
    # 点検が問題を 0 件で返す
    assert checked.data["problems"] == []


def test_normal_when_links_and_history_limit(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """関連する場所と保持する回数を書き換える（正常系）。"""
    # 準備
    root = make_workspace(
        settings={key: value for key, value in valid_settings.items() if key != "links"}
    )
    ws = {"workspace": str(root)}
    before = read_yaml(root, "config.yaml")
    links = [{"title": "仕様", "url": "https://example.com/spec"}]
    # 実行
    replay("update_settings", **ws, settings={"links": links, "history_limit": 3})
    checked = call_tool("check", **ws)
    # 検証
    settings = read_yaml(root, "config.yaml")
    # links が渡した 1 件で、history_limit が 3 である
    assert settings["links"] == links
    assert settings["history_limit"] == 3
    # 題名・プレイブック・フェーズ・対象・カテゴリー・ゴールが呼ぶ前と同じである
    for key in ("summary", "playbooks", "phases", "targets", "categories", "goal"):
        assert settings[key] == before[key]
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.data["problems"] == []


def test_normal_when_display_defaults_changed(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """ネットワークの見た目の既定と表示する種類の既定を書き換える（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "history_limit": 5})
    ws = {"workspace": str(root)}
    before = read_yaml(root, "config.yaml")
    display = {
        "network_look": "starlight",
        "visible_kinds": ["decisions", "tasks", "research", "docs", "terms", "notes"],
    }
    # 実行
    replay("update_settings", **ws, settings={"display": display})
    checked = call_tool("check", **ws)
    # 検証
    settings = read_yaml(root, "config.yaml")
    # 見た目の既定が starlight で、表示する種類の既定が会話ログを除いた種類である
    assert settings["display"]["network_look"] == "starlight"
    assert settings["display"]["visible_kinds"] == [
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
    ]
    # summary・playbooks・phases・goal・history_limit が呼ぶ前と同じである
    for key in ("summary", "playbooks", "phases", "goal", "history_limit"):
        assert settings[key] == before[key]
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.data["problems"] == []


def test_error_when_unmapped_category(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """新しいカテゴリーに無いカテゴリーを持つ項目が残る書き換えは、何も書かずにエラーになる（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", category="画面"),
        make_item("D-2", category="設定"),
        settings={
            **valid_settings,
            "categories": [
                {"name": "画面", "target": "mindmap", "summary": "画面の部品"},
                {"name": "設定", "target": "mindmap", "summary": "設定の画面"},
            ],
        },
    )
    before = snapshot_tree(root)
    # 実行
    # 設定の対応を渡さない
    result = call_tool(
        "update_settings",
        workspace=str(root),
        settings={"categories": [{"name": "画面", "target": "mindmap", "summary": "画面の部品"}]},
    )
    # 検証
    # 設定を書き換えるツールがエラーを返し、本文に D-2 とカテゴリー 設定 がある
    assert result.is_error is True
    assert "D-2: category: 設定" in result.text.splitlines()
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before
