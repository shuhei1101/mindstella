"""README の書き直し（`session` の準備とプレビューの URL の取得で、直下の README.md をコマンドの一覧に書き直す）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、`readme` とプレビューの URL の取得を MCP のクライアントで呼ぶ。
"""

from __future__ import annotations

from launch_fixtures import PLUGIN_DIR
from readme_helpers import (
    PREVIEW_HINT,
    README_MARK,
    assert_readme_commands,
    preview_section,
)
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
)

# 書き換える前の版のプラグインのフォルダ
OLD_PLUGIN_DIR = "/old/plugins/mindstella/0.6.0"

# 利用者が書いた README の中身（自動で書いた印が無い）
USER_README = "# 家計簿アプリの話し合い\n"

# 配信の URL の頭と、URL が指すページの路
URL_PREFIX = "http://127.0.0.1:"
PAGE_PATH = "/mindstella.html"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """別の版のプラグインのフォルダで書いた README を今の値に書き直し、プレビューの URL を頼むとその節が URL になる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    readme = root / "README.md"
    call_tool("readme", workspace=str(root))
    # 起動のコマンドを別の版のプラグインのフォルダに書き換える（1 行目の印は残す）
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(str(PLUGIN_DIR), OLD_PLUGIN_DIR),
        encoding="utf-8",
    )
    records_before = snapshot_tree(root / RECORD_DIR)
    # 実行
    rewritten = call_tool("readme", workspace=str(root))
    text_before_preview = readme.read_text(encoding="utf-8")
    served = call_tool("preview_url", workspace=str(root))
    text_after_preview = readme.read_text(encoding="utf-8")
    # 検証
    assert rewritten.is_error is False
    assert rewritten.data is not None
    assert rewritten.data["path"] == str(readme)
    # 書き直しの後、起動・接続・セッション・セットアップ・アップグレードのコマンドが今の値で、別の版のフォルダを含まない
    assert_readme_commands(root, text_before_preview)
    assert OLD_PLUGIN_DIR not in text_before_preview
    # プレビューの URL を頼む前は、プレビューの節が URL を持たず、頼み方の案内である
    assert preview_section(text_before_preview).splitlines()[1] == PREVIEW_HINT
    # プレビューの URL を頼んだ後は、プレビューの節が返った URL である
    assert served.is_error is False
    assert served.data is not None
    url = served.data["url"]
    assert url.startswith(URL_PREFIX)
    assert url.endswith(PAGE_PATH)
    assert preview_section(text_after_preview).splitlines()[1] == url
    assert_readme_commands(root, text_after_preview)
    # .mindstella/ の全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root / RECORD_DIR) == records_before


def test_normal_when_readme_missing(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """直下に README.md が無ければ、コマンドの一覧を新しく書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    assert not (root / "README.md").exists()
    # 実行
    result = call_tool("readme", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["written"] is True
    text = (root / "README.md").read_text(encoding="utf-8")
    assert text.splitlines()[0] == README_MARK
    assert preview_section(text).splitlines()[1] == PREVIEW_HINT
    assert_readme_commands(root, text)


def test_normal_when_user_readme_exists(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """利用者が書いた README.md は、書き直しもプレビューの URL の取得でも書き換えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    readme = root / "README.md"
    readme.write_text(USER_README, encoding="utf-8")
    # 実行
    result = call_tool("readme", workspace=str(root))
    text_after_readme = readme.read_text(encoding="utf-8")
    served = call_tool("preview_url", workspace=str(root))
    text_after_preview = readme.read_text(encoding="utf-8")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["written"] is False
    assert text_after_readme == USER_README
    # プレビューの URL がエラーにならず、127.0.0.1 の /mindstella.html を指す
    assert served.is_error is False
    assert served.data is not None
    assert served.data["url"].startswith(URL_PREFIX)
    assert served.data["url"].endswith(PAGE_PATH)
    assert text_after_preview == USER_README
