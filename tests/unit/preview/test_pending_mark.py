"""components/pending-mark.ts（保存待ちの印）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 印を作り、見える文字・読み上げの文字・title を返す JavaScript
MARK_SCRIPT = """({kind, compact}) => {
    const element = MindmapPreview.pendingEditMark({kind, compact});
    const visible = element.cloneNode(true);
    visible.querySelectorAll(".sr-only").forEach((node) => node.remove());
    return {
        tag: element.tagName,
        visible: visible.textContent.trim(),
        spoken: element.querySelector(".sr-only")?.textContent ?? null,
        title: element.title,
    };
}"""


def _mark(preview_page: Page, load_preview_scripts: LoadPreviewScripts, **args: Any) -> Any:
    """スクリプトを読んで、渡した引数で印を作った結果を返す。"""
    load_preview_scripts()
    return preview_page.evaluate(MARK_SCRIPT, args)


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        pytest.param("pending", "保存待ち", id="pending"),
        pytest.param("remove", "保存で削除", id="remove"),
        pytest.param("blocked", "書き込めない", id="blocked"),
    ],
)
def test_pending_mark(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, kind: str, label: str
) -> None:
    """種類ごとの文字を出す（正常系）。"""
    # 実行
    result = _mark(preview_page, load_preview_scripts, kind=kind, compact=False)
    # 検証
    assert result["tag"] == "SPAN"
    assert result["visible"] == label


def test_pending_mark_when_compact(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """印だけのときは見える文字が無く、読み上げの文字と title に残す（正常系）。"""
    # 実行
    result = _mark(preview_page, load_preview_scripts, kind="pending", compact=True)
    # 検証
    assert result["visible"] == ""
    assert result["spoken"] == "保存待ち"
    assert result["title"] == "保存待ち"
