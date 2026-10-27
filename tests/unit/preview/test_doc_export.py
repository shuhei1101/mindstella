"""core/doc-export.ts（資料のエクスポートの組み立てとダウンロード）の単体テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import (
    LoadPreviewScripts,
    MakeData,
    MakeItem,
    MdmarkDist,
    PutEmbeddedMdmark,
    PutMdmarkCss,
    PutMdmarkImportMap,
    ServeMdmark,
)

# エクスポートした HTML を開く、仮のオリジン
EXPORT_URL = "https://export.test/doc.html"

# 本文に置く、キー rps のスライダーを持つ操作できる部品の定義（JSON）
PARAM_DEFINITION = {
    "title": "リクエスト数の見積もり",
    "knob": {"key": "rps", "label": "リクエスト数", "min": 0, "max": 10, "step": 1, "value": 5},
    "chart": {
        "title": "応答時間",
        "scope": "ピーク時",
        "updated": "2026-10-27",
        "x": {"label": "経過", "ticks": ["0", "1"]},
        "y": {"label": "ミリ秒", "min": 0, "max": 100, "step": 50},
    },
    "table": {str(value): [value * 10, value * 10 + 5] for value in range(11)},
}

# 用語・資料・取り下げた資料に一致する語と、埋め込んだ HTML の範囲（操作できる部品）を持つ本文
EXPORT_SOURCE = (
    "応答時間 と 仕様書 と 旧仕様 と 自分自身\n\n"
    "<!-- html -->\n```html\n"
    f"<mdmark-param>{json.dumps(PARAM_DEFINITION, ensure_ascii=False)}</mdmark-param>\n"
    "```\n<!-- /html -->\n"
)

# 1 枚の HTML を、書き出す前のページで組み立てる
BUILD_DOC_HTML_SCRIPT = """({data, source, assets}) => {
    const index = MindmapPreview.buildIndex(data);
    const item = data.docs.find((doc) => doc.id === "A-1");
    return MindmapPreview.buildDocHtml({item, source, index, assets});
}"""


def _make_export_data(make_data: MakeData, make_item: MakeItem, *, title: str) -> dict[str, Any]:
    """用語 G-1・資料 A-1（書き出す資料）・A-2・取り下げた資料 A-3 を持つ埋め込みのデータを返す。"""
    return make_data(
        terms=[make_item("G-1", title="応答時間", meaning="返すまでの時間")],
        docs=[
            make_item("A-1", title=title, aliases=["自分自身"]),
            make_item("A-2", title="仕様書の題", aliases=["仕様書"]),
            make_item("A-3", title="旧仕様の題", aliases=["旧仕様"], withdrawn=True),
        ],
    )


def _open_exported_html(page: Page, html: str) -> tuple[Page, list[str]]:
    """組み立てた HTML を、外への通信を全て落とした別のページで開き、そのページと落とした要求の URL を返す。"""
    blocked: list[str] = []
    exported = page.context.new_page()

    def _route(route: Any) -> None:
        """書き出した文書の URL だけに本文を返し、ほかの http(s) は記録して落とす。"""
        if route.request.url == EXPORT_URL:
            route.fulfill(body=html, content_type="text/html")
        else:
            blocked.append(route.request.url)
            route.abort()

    exported.route("**/*", _route)
    exported.goto(EXPORT_URL)
    exported.wait_for_selector(".mdmark")
    return exported, blocked


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param("embedded", id="embedded"),
        pytest.param("served", id="served"),
    ],
)
def test_mdmark_assets(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    mdmark_dist: MdmarkDist,
    mdmark_css_dist: MdmarkDist,
    put_embedded_mdmark: PutEmbeddedMdmark,
    put_mdmark_css: PutMdmarkCss,
    put_mdmark_import_map: PutMdmarkImportMap,
    serve_mdmark: ServeMdmark,
    mode: str,
) -> None:
    """配る書き出しとサーバーの配信のどちらでも中身を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    if mode == "embedded":
        # 配る書き出し: JavaScript と CSS を中身に持つ要素
        put_embedded_mdmark()
        preview_page.evaluate(
            """(css) => {
                const style = document.createElement("style");
                style.id = "mindmap-mdmark-css";
                style.textContent = css;
                document.head.append(style);
            }""",
            mdmark_css_dist.body,
        )
    else:
        # サーバーの配信: CSS の link と JavaScript の import map
        serve_mdmark()
        put_mdmark_import_map()
        put_mdmark_css()
    # 実行
    result = preview_page.evaluate("() => MindmapPreview.mdmarkAssets()")
    # 検証
    assert result == {"ok": True, "css": mdmark_css_dist.body, "js": mdmark_dist.body}


@pytest.mark.parametrize(
    ("css_status", "tamper"),
    [
        pytest.param(404, False, id="not_found"),
        pytest.param(200, True, id="integrity_mismatch"),
    ],
)
def test_mdmark_assets_when_unavailable(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    put_mdmark_css: PutMdmarkCss,
    put_mdmark_import_map: PutMdmarkImportMap,
    serve_mdmark: ServeMdmark,
    css_status: int,
    tamper: bool,
) -> None:
    """取れないときは理由を返す（異常系）。"""
    # 準備
    load_preview_scripts()
    serve_mdmark()
    put_mdmark_import_map()
    put_mdmark_css(status=css_status, tamper=tamper)
    # 実行
    result = preview_page.evaluate("() => MindmapPreview.mdmarkAssets()")
    # 検証
    assert result["ok"] is False
    assert result["reason"] != ""


def test_build_doc_html(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    mdmark_dist: MdmarkDist,
    mdmark_css_dist: MdmarkDist,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """ネットにつながらない画面で本文と部品とツールチップが動く（正常系）。"""
    # 準備
    load_preview_scripts()
    data = _make_export_data(make_data, make_item, title="エクスポートする資料")
    html = preview_page.evaluate(
        BUILD_DOC_HTML_SCRIPT,
        {
            "data": data,
            "source": EXPORT_SOURCE,
            "assets": {"css": mdmark_css_dist.body, "js": mdmark_dist.body},
        },
    )
    # 実行
    exported, blocked = _open_exported_html(preview_page, html)
    exported.locator(".mdmark-param input[type=range]").focus()
    exported.keyboard.press("ArrowRight")
    result = exported.evaluate(
        """() => ({
            terms: [...document.querySelectorAll(".mdmark-term")].map((term) => term.textContent),
            value: document.querySelector(".mdmark-param output")?.textContent ?? null,
            copyLabel: document.querySelector("button.mdmark-param-copy")?.textContent.trim() ?? null,
        })"""
    )
    # 検証
    # 外への要求が無い
    assert blocked == []
    # 用語 G-1 と資料 A-2 には印が付き、書き出す A-1 自身と取り下げた A-3 には付かない
    assert result["terms"] == ["応答時間", "仕様書"]
    # スライダーを動かすと値が変わる
    assert result["value"] == "6"
    assert result["copyLabel"] == "今の値をコピー"


def test_build_doc_html_when_title_has_markup(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    mdmark_dist: MdmarkDist,
    mdmark_css_dist: MdmarkDist,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """タイトルと本文の `<` で HTML が崩れない（正常系）。"""
    # 準備
    load_preview_scripts()
    title = '<b>&"x"</b>'
    data = _make_export_data(make_data, make_item, title=title)
    html = preview_page.evaluate(
        BUILD_DOC_HTML_SCRIPT,
        {
            "data": data,
            "source": "本文の `</script>` の例\n",
            "assets": {"css": mdmark_css_dist.body, "js": mdmark_dist.body},
        },
    )
    # 実行
    exported, _ = _open_exported_html(preview_page, html)
    result = exported.evaluate(
        """() => ({
            title: document.title,
            code: document.querySelector(".mdmark code")?.textContent ?? null,
        })"""
    )
    # 検証
    assert result == {"title": title, "code": "</script>"}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "前\n\n<!-- html -->\n```html\n<p>a</p>\n```\n<!-- /html -->\n\n間\n\n"
            "<!-- html -->\n```html\n<p>b</p>\n```\n<!-- /html -->\n\n後\n",
            "前\n\n\n間\n\n\n後\n",
            id="two_ranges",
        ),
        pytest.param(
            "前\n\n```text\n<!-- html -->\n```\n\n後\n",
            "前\n\n```text\n<!-- html -->\n```\n\n後\n",
            id="marker_inside_fence",
        ),
        pytest.param(
            "前\n\n<!-- html -->\n```html\n<p>x</p>\n```\n",
            "前\n\n<!-- html -->\n```html\n<p>x</p>\n```\n",
            id="unclosed",
        ),
    ],
)
def test_strip_embedded_html(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    source: str,
    expected: str,
) -> None:
    """範囲だけを除き、フェンスの中と閉じていない印は残す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    stripped = preview_page.evaluate("(source) => MindmapPreview.stripEmbeddedHtml(source)", source)
    # 検証
    assert stripped == expected


def test_download_text(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """名前と中身のとおりに保存される（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    with preview_page.expect_download() as download_info:
        preview_page.evaluate(
            """() => MindmapPreview.downloadText({
                name: "A-1.md",
                text: "# 見出し",
                type: "text/markdown",
            })"""
        )
    download = download_info.value
    # 検証
    assert download.suggested_filename == "A-1.md"
    assert Path(download.path()).read_text(encoding="utf-8") == "# 見出し"

