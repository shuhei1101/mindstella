"""components/tag-list.ts（主題のマーカーを持つタグの並び）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, LoadPreviewStyles

# 読み上げだけの文字とみなす、描いた大きさの上限（px）
SPOKEN_ONLY_MAX_PX = 1

# タグの並びを描き、`span.tag` ごとに名前・マーカー・読み上げだけの「主題」・title を返す JavaScript
DESCRIBE_SCRIPT = """({values, maxPx}) => {
    const node = MindmapPreview.tagList(values ?? undefined);
    if (node.childNodes.length === 0) {
        return {nodeType: node.nodeType, childCount: 0};
    }
    const host = document.createElement("div");
    host.append(node);
    document.body.append(host);
    return [...host.querySelectorAll("span.tag")].map((tag) => {
        // 「主題」の文字を持つ要素（マーカーの svg を除く）
        const spoken = [...tag.querySelectorAll("*")].find(
            (element) => !(element instanceof SVGElement) && element.textContent === "主題",
        );
        const rect = spoken?.getBoundingClientRect();
        return {
            name: tag.textContent.replace("主題", "").trim(),
            mark: tag.querySelector('svg[aria-hidden="true"]') !== null,
            spokenOnly: rect === undefined ? null : rect.width <= maxPx && rect.height <= maxPx,
            title: tag.getAttribute("title"),
        };
    });
}"""

# 主題でないタグの見え方
PLAIN = {"mark": False, "spokenOnly": None, "title": None}

# 主題のタグの見え方
MAIN = {"mark": True, "spokenOnly": True, "title": "主題"}


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        pytest.param(
            [{"name": "画面"}, {"name": "データ", "main": True}],
            [{"name": "画面", **PLAIN}, {"name": "データ", **MAIN}],
            id="main_tag",
        ),
        pytest.param(
            ["UI", "性能"],
            [{"name": "UI", **PLAIN}, {"name": "性能", **PLAIN}],
            id="string_tags",
        ),
        pytest.param(None, {"nodeType": 11, "childCount": 0}, id="undefined"),
    ],
)
def test_tag_list(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    values: list[Any] | None,
    expected: Any,
) -> None:
    """主題のタグにマーカーを付け、記録の順のまま並べる（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    result = preview_page.evaluate(
        DESCRIBE_SCRIPT, {"values": values, "maxPx": SPOKEN_ONLY_MAX_PX}
    )
    # 検証
    assert result == expected
