"""migrations/v0.8.0/scripts/submissions_to_threads.py（送信をスレッドにする変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import (
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteSubmissions,
)
from workspace_fixtures import RECORD_DIR

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.8.0" / "scripts" / "submissions_to_threads.py"

# 変換が書くファイルの、ワークスペースからの相対パス
THREADS_PATH = f"{RECORD_DIR}/threads.yaml"

# 取り込み済みの送信が持つ、取り込んだ日時
TAKEN_AT = "2026-10-02T08:00:00+00:00"

# 本文の 2 行目を指す箇所（資料 A-1 の本文 `A_BODY` の 2 行目）
LINE2_LOC = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 資料 A-1 の本文
A_BODY = "1 行目\n言い換えたい文\n3 行目"


@pytest.fixture
def submissions_to_threads(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_8_0_submissions_to_threads", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_threads(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの threads.yaml のスレッドの並びを読む。"""
    data = yaml.safe_load((root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8"))
    return data["items"]


def test_submissions_to_threads(
    submissions_to_threads: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """取り込み済みはクローズ、取り込んでいないものはオープンのスレッドにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    no_target = make_submission("S-3")
    del no_target["target"]
    write_submissions(
        root,
        no_target,
        make_submission("S-1", target="D-1", taken=TAKEN_AT, comment="C-1"),
        make_submission("S-2", target="A-1", loc=LINE2_LOC),
    )
    # 実行
    changed = submissions_to_threads.migrate(root)
    # 検証
    assert changed == [THREADS_PATH]
    first, second, third = _read_threads(root)
    assert (first["id"], first["status"], first["target"]) == ("TH-1", "closed", "D-1")
    assert first["events"] == [
        {"kind": "closed", "author": "ai", "reason": None, "created": TAKEN_AT}
    ]
    assert first["posts"][0]["taken"] == TAKEN_AT
    assert "comment" not in first["posts"][0]
    assert (second["id"], second["status"], second["loc"]) == ("TH-2", "open", LINE2_LOC)
    assert (third["id"], third["status"]) == ("TH-3", "open")
    assert ("target" in third, "loc" in third) == (False, False)
    assert [thread["posts"][0]["read"] for thread in (first, second, third)] == [False] * 3
    assert (root / RECORD_DIR / "submissions.yaml").exists()
    # 変換が書いたファイルを、サーバーのスレッドの読み込みで読める
    import threads

    assert [thread.id for thread in threads.load_threads(root)] == ["TH-1", "TH-2", "TH-3"]


def test_submissions_to_threads_when_no_file(
    submissions_to_threads: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """submissions.yaml が無ければ何も書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    changed = submissions_to_threads.migrate(root)
    # 検証
    assert changed == []
    assert not (root / RECORD_DIR / "threads.yaml").exists()


@pytest.mark.parametrize(
    "raw_files",
    [
        pytest.param(
            {"submissions.yaml": "items: []\n", "threads.yaml": "items: []\n"},
            id="threads_exists",
        ),
        pytest.param({"submissions.yaml": "- S-1\n- S-2\n"}, id="top_level_list"),
        pytest.param({"submissions.yaml": "items: 送信\n"}, id="items_not_list"),
    ],
)
def test_submissions_to_threads_when_rejected(
    submissions_to_threads: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    raw_files: dict[str, str],
) -> None:
    """スレッドが既にある・送信の形が崩れているときは移さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files=raw_files)
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(ValueError, match=r"threads\.yaml|submissions\.yaml"):
        submissions_to_threads.migrate(root)
    assert snapshot_tree(root) == before


def test_submissions_to_threads_when_empty(
    submissions_to_threads: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """送信が 0 件でも空のスレッドのファイルを作る（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"submissions.yaml": "items: []\n"})
    # 実行
    submissions_to_threads.migrate(root)
    # 検証
    assert _read_threads(root) == []
