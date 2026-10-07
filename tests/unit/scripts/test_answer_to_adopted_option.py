"""migrations/v0.7.0/scripts/answer_to_adopted_option.py（決定済みの答えから採用した案を作る変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from fixture_types import MakeItem, MakeWorkspace, SnapshotTree
from migration_helpers import snapshot_mtimes
from workspace_fixtures import RECORD_DIR

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.7.0" / "scripts" / "answer_to_adopted_option.py"

# 変換が書き換えるファイルの、ワークスペースからの相対パス
DECISIONS_PATH = f"{RECORD_DIR}/decisions.yaml"


@pytest.fixture
def answer_to_adopted_option(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_7_0_answer_to_adopted_option", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_decisions(root: Path) -> list[dict[str, object]]:
    """ワークスペースの decisions.yaml の項目の並びを読む。"""
    data = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))
    return data["items"]


def _without_options(item: dict[str, object]) -> dict[str, object]:
    """項目から案のキー（options）を外した写しを返す（案を持たない形を作る・ほかのキーを比べる）。"""
    return {key: value for key, value in item.items() if key != "options"}


def test_answer_to_adopted_option(
    answer_to_adopted_option: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """決定済みで答えを持ち案を持たない検討事項にだけ採用した案を作る（正常系）。"""
    # 準備
    root = make_workspace(
        _without_options(
            make_item("D-1", status="決定済み", answer="月ごとに分ける", reason="探しやすい")
        ),
        make_item("D-2", status="決定済み", options=[], answer="1 つにまとめる"),
        _without_options(make_item("D-3", status="未決定")),
        make_item(
            "D-4",
            status="決定済み",
            options=[{"key": "A", "content": "案 A", "adopted": True}],
            answer="案 A",
        ),
        _without_options(make_item("D-5", status="決定済み")),
    )
    before = {item["id"]: item for item in _read_decisions(root)}
    # 実行
    changed = answer_to_adopted_option.migrate(root)
    # 検証
    assert changed == [DECISIONS_PATH]
    after = {item["id"]: item for item in _read_decisions(root)}
    assert after["D-1"]["options"] == [
        {"key": "A", "content": "月ごとに分ける", "reason": "探しやすい", "adopted": True}
    ]
    assert after["D-2"]["options"] == [{"key": "A", "content": "1 つにまとめる", "adopted": True}]
    # 作った検討事項のほかのキー（状態・答え・更新日時）と、作らない検討事項は変えない
    assert _without_options(after["D-1"]) == _without_options(before["D-1"])
    assert _without_options(after["D-2"]) == _without_options(before["D-2"])
    assert after["D-3"] == before["D-3"]
    assert after["D-4"] == before["D-4"]
    assert after["D-5"] == before["D-5"]
    assert list(root.rglob("*.tmp")) == []


def test_answer_to_adopted_option_when_applied_twice(
    answer_to_adopted_option: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """もう一度当てても何も書かない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="決定済み", options=[], answer="月ごとに分ける"),
    )
    answer_to_adopted_option.migrate(root)
    before = snapshot_tree(root)
    before_mtimes = snapshot_mtimes(root)
    # 実行
    changed = answer_to_adopted_option.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == before_mtimes


def test_answer_to_adopted_option_when_no_file(
    answer_to_adopted_option: ModuleType, make_workspace: MakeWorkspace
) -> None:
    """decisions.yaml が無ければ何も書かない（正常系）。"""
    # 準備
    root = make_workspace()
    (root / RECORD_DIR / "decisions.yaml").unlink(missing_ok=True)
    # 実行
    changed = answer_to_adopted_option.migrate(root)
    # 検証
    assert changed == []
    assert not (root / RECORD_DIR / "decisions.yaml").exists()


@pytest.mark.parametrize(
    "broken_text",
    [
        pytest.param("- id: D-1\n", id="top_level_list"),
        pytest.param("items: 文字列\n", id="items_string"),
    ],
)
def test_answer_to_adopted_option_when_shape_broken(
    answer_to_adopted_option: ModuleType,
    make_workspace: MakeWorkspace,
    snapshot_tree: SnapshotTree,
    broken_text: str,
) -> None:
    """形の崩れた decisions.yaml は何も書かない（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"decisions.yaml": broken_text})
    before = snapshot_tree(root)
    before_mtimes = snapshot_mtimes(root)
    # 実行
    changed = answer_to_adopted_option.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == before_mtimes
