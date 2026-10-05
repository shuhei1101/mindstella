"""話し合いの範囲の見直し（範囲が広がったとき、たたき台と対応を確かめて設定を書き換える）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねる設定の更新と会話ログの追加を決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import MakeItem, MakeWorkspace

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 壁打ちのフェーズ
WALL_PHASES = ["問い", "発散", "整理", "絞り込み", "結論"]

# 利用者が確定した、書き換えた後のフェーズの並び（壁打ちとシステム開発のフェーズをつないだもの）
NEW_PHASES = ["目的", "発散", "要件", "構成", "インターフェース", "コンテンツ"]

# 利用者が確定した、古いフェーズから新しいフェーズへの対応（発散は新しい並びにもあるので渡さない）
PHASE_MAP = {"問い": "目的", "整理": "要件", "絞り込み": "要件", "結論": "要件"}

# 利用者が確定した、書き換えた後のゴール（システム開発の要件まで）
NEW_GOAL = {
    "phase": "要件",
    "summary": "要件が決まる",
    "deliverables": [{"title": "要件定義書"}],
}

# 壁打ちで作った対象とカテゴリー（どちらも 話題 の下）
OLD_TARGETS = [{"name": "話題", "summary": "話し合う話題"}]
OLD_CATEGORIES = [
    {"name": "論点", "target": "話題", "summary": "決める論点"},
    {"name": "アイデア", "target": "話題", "summary": "出たアイデア"},
]

# 利用者が確定した、書き換えた後の対象とカテゴリーと、古い名前から新しい名前への対応
NEW_TARGETS = [{"name": "本体", "summary": "作るシステムの本体"}]
NEW_CATEGORIES = [{"name": "論点", "target": "本体", "summary": "決める論点"}]
TARGET_MAP = {"話題": "本体"}
CATEGORY_MAP = {"アイデア": "論点"}

# 会話の日付
TODAY = "2026-10-02"

# 納品物の資料の本文（概要・背景・最終的な構成の見出しを先に置く）
DELIVERABLE_BODY = "# 要件定義書\n\n## 概要\n\n家計簿アプリの要件。\n\n## 背景\n\n## 構成\n\n- 画面\n- データ\n"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """プレイブックを足し、フェーズの対応を確かめて付け替え、題名・最上位の軸の呼び名・ゴールを書き換えて、足した納品物の資料を作る（正常系）。"""
    # 準備
    # ゴールを持たない壁打ちのワークスペースに、問いと発散の検討事項を足しておく
    settings = {
        **{key: value for key, value in valid_settings.items() if key != "goal"},
        "playbooks": ["壁打ち"],
        "target_label": "テーマ",
        "phases": WALL_PHASES,
        "targets": OLD_TARGETS,
        "categories": OLD_CATEGORIES,
    }
    root = make_workspace(
        make_item("D-1", phase="問い", target="話題", category="論点"),
        make_item("D-2", phase="発散", target="話題", category="アイデア"),
        settings=settings,
    )
    ws = {"workspace": str(root)}
    # 実行
    # 利用者がたたき台と対応の表を確定した後に、設定を書き換える
    replay(
        "update_settings",
        **ws,
        settings={
            "summary": "家計簿アプリの要件を決める",
            "playbooks": ["壁打ち", "システム開発"],
            "phases": NEW_PHASES,
            "target_label": "機能",
            "targets": NEW_TARGETS,
            "categories": NEW_CATEGORIES,
            "goal": NEW_GOAL,
        },
        phase_map=PHASE_MAP,
        target_map=TARGET_MAP,
        category_map=CATEGORY_MAP,
    )
    # 書き換えた設定で足した納品物の資料を作り、納品物の doc から指す
    replay(
        "add",
        **ws,
        kind="doc",
        item={
            "title": "要件定義書",
            "kind": "文書",
            "deliverable": True,
            "status": "下書き",
            "target": "本体",
            "body_markdown": DELIVERABLE_BODY,
        },
    )
    goal = read_yaml(root, "config.yaml")["goal"]
    replay(
        "update_settings",
        **ws,
        settings={"goal": {**goal, "deliverables": [{"title": "要件定義書", "doc": "A-1"}]}},
    )
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "範囲の見直し",
            "date": TODAY,
            "related": ["D-1"],
            "body_markdown": "システム開発を足し、要件まで決めることにした",
        },
    )
    checked = replay("check", **ws)
    # 検証
    # playbooks が壁打ちとシステム開発の 2 件で、summary・target_label・phases が確定した値である
    updated = read_yaml(root, "config.yaml")
    assert updated["playbooks"] == ["壁打ち", "システム開発"]
    assert updated["summary"] == "家計簿アプリの要件を決める"
    assert updated["target_label"] == "機能"
    assert updated["phases"] == NEW_PHASES
    assert updated["targets"] == NEW_TARGETS
    assert updated["categories"] == NEW_CATEGORIES
    # goal が確定したたたき台の値で、納品物 要件定義書 の doc が A-1 である
    assert updated["goal"] == {**NEW_GOAL, "deliverables": [{"title": "要件定義書", "doc": "A-1"}]}
    # 資料 A-1 が deliverable: true を持ち、docs/ の本文が概要・背景・構成の見出しを持つ
    assert read_yaml(root, "docs.yaml")["items"][0]["deliverable"] is True
    body = (root / "docs" / "A-1.md").read_text(encoding="utf-8")
    assert [heading in body for heading in ("## 概要", "## 背景", "## 構成")] == [True] * 3
    # D-1 の phase が目的、D-2 の phase が発散である
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    assert decisions["D-1"]["phase"] == "目的"
    assert decisions["D-2"]["phase"] == "発散"
    # D-1・D-2 の target が 本体、category が 論点 である
    assert [(decisions[item_id]["target"], decisions[item_id]["category"]) for item_id in ("D-1", "D-2")] == [
        ("本体", "論点"),
        ("本体", "論点"),
    ]
    # 会話ログが 1 件足されている
    assert [item["id"] for item in read_yaml(root, "logs.yaml")["items"]] == ["L-1"]
    # check が問題を 0 件で返す
    assert checked == {"ok": True, "problems": []}
