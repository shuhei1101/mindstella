"""readme（直下の README.md の書き出し）の結合テスト。"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from workspace_fixtures import RECORD_DIR

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree
from .readme_helpers import (
    PLUGIN_DIR,
    README_MARK,
    expected_readme,
    section_of,
    session_name_of,
)

# 利用者の README の更新日時として置く、十分に古い日時（ナノ秒）
OLD_MTIME_NS = 1_000_000_000 * 1_000_000_000

# 接続のコマンドの行から、`-t =` に続くセッションの名前の部分を取る
ATTACH_PATTERN = re.compile(r"^tmux attach-session -t =(\S+)$", re.MULTILINE)

# 書き換える前の版のプラグインのフォルダ
OLD_PLUGIN_DIR = "/old/plugins/mindstella/0.6.0"


def test_normal(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """README.md が無ければ、コマンドの一覧を書く（正常系）。"""
    # 準備
    root = make_workspace(name="家計簿アプリ")
    records_before = snapshot_tree(root / RECORD_DIR)
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"path": str(root / "README.md"), "written": True, "preview_url": None}
    text = (root / "README.md").read_text(encoding="utf-8")
    assert text.splitlines()[0] == README_MARK
    assert text == expected_readme(root)
    # 接続のコマンドのセッションの名前が、フォルダ名と絶対パスのハッシュからできている
    attach = ATTACH_PATTERN.search(text)
    assert attach is not None
    session = shlex.split(attach.group(1))[0]
    assert session == session_name_of(root)
    assert re.fullmatch(r"mindstella-家計簿アプリ-[0-9a-f]{6}", session)
    assert snapshot_tree(root / RECORD_DIR) == records_before


def test_normal_when_serving(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
) -> None:
    """このプロセスがワークスペースを配っていれば、プレビューの節にその URL を書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), name="家計簿アプリ")
    served = call_tool("preview_url", workspace=str(root))
    assert served.is_error is False
    assert served.data is not None
    url = served.data["url"]
    # 配信を立てたときに書かれた README を消して、readme が書き直すことを確かめる
    (root / "README.md").unlink()
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["written"] is True
    assert result.data["preview_url"] == url
    text = (root / "README.md").read_text(encoding="utf-8")
    assert url in section_of(text, "## プレビュー")
    assert text == expected_readme(root, preview_url=url)


def test_normal_when_generated_readme_exists(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """自動で書いた印のある README.md は、今の値で書き直す（正常系）。"""
    # 準備
    root = make_workspace(name="家計簿アプリ")
    call_tool("readme", workspace=str(root))
    readme = root / "README.md"
    # 起動のコマンドを別の版のプラグインのフォルダに書き換える（1 行目の印は残す）
    old_text = readme.read_text(encoding="utf-8").replace(str(PLUGIN_DIR), OLD_PLUGIN_DIR)
    readme.write_text(old_text, encoding="utf-8")
    assert OLD_PLUGIN_DIR in old_text
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["written"] is True
    text = readme.read_text(encoding="utf-8")
    assert OLD_PLUGIN_DIR not in text
    assert f"{shlex.quote(str(PLUGIN_DIR / 'bin' / 'mindstella'))} " in text
    assert text == expected_readme(root)


def test_normal_when_user_readme_exists(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """自動で書いた印の無い README.md は書き換えない（正常系）。"""
    # 準備
    root = make_workspace(name="家計簿アプリ")
    readme = root / "README.md"
    readme.write_text("# 家計簿アプリの話し合い\n", encoding="utf-8")
    os.utime(readme, ns=(OLD_MTIME_NS, OLD_MTIME_NS))
    content_before = readme.read_bytes()
    mtime_before = readme.stat().st_mtime_ns
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["written"] is False
    assert readme.read_bytes() == content_before
    assert readme.stat().st_mtime_ns == mtime_before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、README を書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert not (root / "README.md").exists()


def test_error_when_write_fails(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """直下に README.md を書けなければ、エラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(name="家計簿アプリ")
    (root / "README.md").mkdir()
    records_before = snapshot_tree(root / RECORD_DIR)
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root / "README.md") in result.text
    assert (root / "README.md").is_dir()
    assert list((root / "README.md").iterdir()) == []
    assert snapshot_tree(root / RECORD_DIR) == records_before
