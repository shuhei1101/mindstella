"""write-release（リリースの書き出し）の結合テスト。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from .fixture_types import CallTool, MakeWorkspace, SnapshotTree
from workspace_fixtures import RECORD_DIR


def test_normal(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """release/ の下に渡した名前で本文を書き、書いたパスとバイト数を返す（正常系）。"""
    # 準備
    root = make_workspace()
    content = "# 要件定義書\n\n要件を並べる。\n"
    # release/ の外のファイルの写し
    outside_before = {
        name: data
        for name, data in snapshot_tree(root).items()
        if not name.startswith(".mindstella/release/")
    }
    # 実行
    result = call_tool("write_release", workspace=str(root), path="要件定義書.md", content=content)
    # 検証
    assert result.is_error is False
    assert result.data == {"path": "要件定義書.md", "bytes": len(content.encode("utf-8"))}
    target = root / RECORD_DIR / "release" / "要件定義書.md"
    assert target.read_text(encoding="utf-8") == content
    outside_after = {
        name: data
        for name, data in snapshot_tree(root).items()
        if not name.startswith(".mindstella/release/")
    }
    assert outside_after == outside_before


def test_normal_when_nested_and_overwrite(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """release/ の下のフォルダを作って書き、同じ名前でもう一度呼ぶと上書きする（正常系）。"""
    # 準備
    root = make_workspace()
    shutil.rmtree(root / RECORD_DIR / "release")
    arguments = {"workspace": str(root), "path": "図/画面のモック.html"}
    # 実行
    first = call_tool("write_release", content="<p>前</p>", **arguments)
    second = call_tool("write_release", content="<p>後</p>", **arguments)
    # 検証
    assert first.is_error is False
    assert second.is_error is False
    release = root / RECORD_DIR / "release"
    assert (release / "図" / "画面のモック.html").read_text(encoding="utf-8") == "<p>後</p>"
    assert [path for path in release.rglob("*") if path.is_file()] == [
        release / "図" / "画面のモック.html"
    ]


@pytest.mark.parametrize(
    "path",
    ["../config.yaml", "ABSOLUTE", "資料.txt", ""],
    ids=["parent", "absolute", "extension", "empty"],
)
def test_error_when_path_outside_release(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
    path: str,
) -> None:
    """release/ の下の .md・.html を指さない path は、何も書かずにエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace()
    outside = tmp_path / "outside"
    outside.mkdir()
    if path == "ABSOLUTE":
        path = str(outside / "資料.md")
    before = snapshot_tree(root)
    # 実行
    result = call_tool("write_release", workspace=str(root), path=path, content="本文")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: path: ")
    assert snapshot_tree(root) == before
    assert list(outside.iterdir()) == []


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずにエラーで終わる（異常系）。"""
    # 実行
    result = call_tool("write_release", workspace=str(tmp_path), path="資料.md", content="本文")
    # 検証
    assert result.is_error is True
    assert str(tmp_path) in result.text
    assert not (tmp_path / RECORD_DIR).exists()
