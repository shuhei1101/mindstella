"""PoC: mdmark の HTML の埋め込み・部品・用語の一致・資料の書き出しを、プレビューの詳細パネルで測って JSON に残す。

成否は判定せず、測った値を `POC_RESULT` のパスへ書く（結論は計画書の `## PoC 結果` で突き合わせる）。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page
from preview_fixture_types import OpenPreview, WritePreview
from workspace_fixtures import MakeItem

POC_DIR = Path(__file__).resolve().parents[3] / "poc" / "mdmark-embed"
PANEL = "aside.panel .md:not(.md-value)"
MARKS = f"{PANEL} a.term"
TIP_OPEN = "#term-tip:popover-open"
CHART = f"{PANEL} figure.mdmark-diagram[data-diagram='chart']"
PARAM = f"{PANEL} .mdmark-param"
WAIT_MS = 15_000


def _private_memory_kb() -> int:
    """Playwright が立てた Chromium の全プロセスの私用メモリ（Private_Clean + Private_Dirty）の合計を返す。"""
    total = 0
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            cmdline = (proc / "cmdline").read_bytes().decode(errors="ignore")
            if "playwright" not in cmdline or "chrom" not in cmdline:
                continue
            rollup = (proc / "smaps_rollup").read_text()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        for key in ("Private_Clean", "Private_Dirty"):
            match = re.search(rf"^{key}:\s+(\d+) kB", rollup, re.MULTILINE)
            total += int(match.group(1)) if match else 0
    return total


def _js_heap(page: Page) -> int:
    """ページの JavaScript のヒープの使用量（バイト）を返す。"""
    session = page.context.new_cdp_session(page)
    session.send("Performance.enable")
    metrics = {m["name"]: m["value"] for m in session.send("Performance.getMetrics")["metrics"]}
    return int(metrics["JSHeapUsedSize"])


def _write_workspace(write_preview: WritePreview, make_item: MakeItem) -> str:
    """埋め込みの資料 A-1 と、用語・資料・調査（取り下げを含む）を持つワークスペースの配信の URL を返す。"""
    return write_preview(
        make_item("A-1", title="返信の速さの検討", aliases=["自分の別名"]),
        make_item("A-2", title="返信の設計", aliases=["latency"], description="返信までの段の分け方"),
        make_item("A-8", title="古い資料", aliases=["古い語"], withdrawn=True),
        make_item("R-1", title="応答時間の測り方", aliases=["応答時間"], description="測り方と結果"),
        make_item("R-2", title="古い調査", aliases=["古い調査の語"], withdrawn=True),
        make_item("G-1", title="応答時間", aliases=["response"], meaning="受け取りから返信までの時間"),
        make_item("G-2", title="反応の速さ", aliases=["response"], meaning="返信を始めるまでの速さ"),
        make_item("G-3", title="返答", aliases=["Response"], meaning="返す中身"),
        bodies={"A-1.md": (POC_DIR / "sample.md").read_text(encoding="utf-8"), "A-2.md": "資料 A-2 の本文\n"},
    )


def _measure_body(page: Page) -> dict[str, Any]:
    """埋め込んだ HTML・行の印・本文の印・ID のリンクを測る。"""
    return page.evaluate(
        """(panel) => {
          const root = document.querySelector(panel);
          const html = root.querySelector('.mdmark-html');
          return {
            mdmarkVersion: mdmark.version(),
            embedded: html === null ? null : {
              divs: html.querySelectorAll('div').length,
              hint: html.querySelector('[data-hint]') !== null,
              chart: html.querySelector("figure[data-diagram='chart']") !== null,
              param: html.querySelector("figure[data-diagram='param']") !== null,
              scripts: html.querySelectorAll('script').length,
            },
            lineMarks: [...root.querySelectorAll('[data-line-start]')].map((e) => [e.tagName, Number(e.dataset.lineStart)]),
            outsideHtmlBlocks: root.querySelectorAll('.html-block').length,
            outsideHtmlFrames: root.querySelectorAll('.html-block iframe').length,
            marks: [...root.querySelectorAll('a.term')].map((a) => ({
              text: a.textContent, id: a.dataset.id, ids: a.dataset.ids,
              inEmbedded: a.closest('.mdmark-html') !== null,
              describedby: a.getAttribute('aria-describedby'), details: a.getAttribute('aria-details'),
            })),
            idrefs: [...root.querySelectorAll('a.idref')].map((a) => ({ text: a.textContent, id: a.dataset.id, inEmbedded: a.closest('.mdmark-html') !== null })),
            mdmarkTerms: root.querySelectorAll('.mdmark-term').length,
          };
        }""",
        PANEL,
    )


def _measure_tip(page: Page, text: str) -> dict[str, Any]:
    """語の印に乗せてツールチップの中身を取り、最初のタイトルを押して移った先のハッシュを返す。"""
    mark = page.locator(MARKS, has_text=re.compile(rf"^{re.escape(text)}$")).first
    if mark.count() == 0:
        return {"found": False}
    mark.hover()
    try:
        page.wait_for_selector(TIP_OPEN, timeout=3_000)
    except Exception:  # ツールチップが出ないことも測った値として残す
        return {"found": True, "open": False}
    groups = page.eval_on_selector_all(
        f"{TIP_OPEN} .tt-group",
        "gs => gs.map(g => ({kind: g.querySelector('.tt-kind')?.textContent, n: g.querySelector('.tt-n')?.textContent, ids: [...g.querySelectorAll('.tt-link')].map(l => l.dataset.id)}))",
    )
    links = page.eval_on_selector_all(f"{TIP_OPEN} .tt-link", "ls => ls.map(l => l.dataset.id)")
    page.locator(f"{TIP_OPEN} .tt-link").first.click()
    page.wait_for_timeout(300)
    return {"found": True, "open": True, "groups": groups, "links": links, "hashAfterClick": page.evaluate("location.hash")}


def _measure_chart(page: Page) -> dict[str, Any]:
    """チャートの倍率の表示をボタンとキーで変え、拡大した後にドラッグして表示の位置を測る。"""
    chart = page.locator(CHART).first
    if chart.count() == 0:
        return {"found": False}
    zoom = chart.locator(".mdmark-diagram-zoom")
    viewport = chart.locator(".mdmark-diagram-viewport")
    before = zoom.inner_text()
    chart.locator("[data-tool='in']").click()
    after_button = zoom.inner_text()
    viewport.focus()
    page.keyboard.press("+")
    after_key = zoom.inner_text()
    scroll = "v => [v.scrollLeft, v.scrollTop]"
    scroll_before = viewport.evaluate(scroll)
    box = viewport.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 - 120, box["y"] + box["height"] / 2 - 80, steps=8)
    page.mouse.up()
    return {
        "found": True,
        "zoom": [before, after_button, after_key],
        "scrollBeforeDrag": scroll_before,
        "scrollAfterDrag": viewport.evaluate(scroll),
    }


def _measure_param(page: Page, figure: str) -> dict[str, Any]:
    """部品のスライダーを矢印キーで動かして系列の描き直しを測り、コピーのボタンでクリップボードの中身を取る。"""
    param = page.locator(figure).first
    if param.count() == 0:
        return {"found": False}
    slider = param.locator("input[type='range'], [role='slider']").first
    series = "f => [...f.parentElement.querySelectorAll('svg path, svg polyline, svg circle')].map(p => p.getAttribute('d') ?? p.getAttribute('points')).join('|')"
    before = param.evaluate(series)
    value_before = slider.evaluate("s => s.value ?? s.getAttribute('aria-valuenow')")
    slider.focus()
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(200)
    after = param.evaluate(series)
    value_after = slider.evaluate("s => s.value ?? s.getAttribute('aria-valuenow')")
    copy = param.locator(".mdmark-param-copy").first
    clipboard = None
    if copy.count() > 0:
        copy.click()
        page.wait_for_timeout(200)
        clipboard = page.evaluate("navigator.clipboard.readText()")
    return {
        "found": True,
        "slider": slider.evaluate("s => s.tagName + ' ' + (s.getAttribute('aria-label') ?? '')"),
        "value": [value_before, value_after],
        "seriesChanged": before != after,
        "copyButton": copy.inner_text() if copy.count() > 0 else None,
        "clipboard": clipboard,
    }


def _measure_collision(page: Page) -> Any:
    """正規化した後にだけ重なる別の語（Response と response）を別の用語にしたとき、mdmark の一致が何を返すかを測る。"""
    return page.evaluate(
        """() => mdmark.collectMatches === undefined ? null : mdmark.collectMatches({
          index: {docs: [{id: 'S', path: 's.md', title: 's'}], terms: [
            {id: 'W-0', term: 'response'}, {id: 'W-1', term: 'Response'}, {id: 'W-2', term: '応答時間'}]},
          documents: {'s.md': 'ＲＥＳＰＯＮＳＥ と 応答時間'},
        }).byDocument.S"""
    )


def _measure_export(page: Page, browser: Browser, tmp_path: Path) -> dict[str, Any]:
    """プレビューの画面で 1 枚の HTML を組み立て、通信を止めた別の画面で file:// から開いて測る。"""
    page.add_script_tag(path=str(POC_DIR / "export.js"))
    html = page.evaluate("pocExportDocument({id: 'A-1'})")
    path = tmp_path / "A-1.html"
    path.write_text(html, encoding="utf-8")
    context = browser.new_context(offline=True)
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    outside: list[str] = []
    context.on("request", lambda request: outside.append(request.url) if not request.url.startswith(("file:", "blob:", "data:")) else None)
    offline = context.new_page()
    errors: list[str] = []
    offline.on("pageerror", lambda error: errors.append(str(error)))
    offline.goto(path.as_uri())
    offline.wait_for_function("window.docReady === true", timeout=WAIT_MS)
    body = offline.evaluate(
        """() => ({
          embedded: document.querySelector('.mdmark-html') !== null,
          chart: document.querySelector("figure[data-diagram='chart'] svg") !== null,
          terms: [...document.querySelectorAll('.mdmark-term')].map((t) => t.textContent),
        })"""
    )
    term = offline.locator(".mdmark-term").first
    term.focus()
    offline.wait_for_timeout(200)
    tip = offline.evaluate(
        "() => { const t = document.activeElement; const tip = document.getElementById(t.getAttribute('aria-describedby')); return tip && {visible: tip.checkVisibility(), text: tip.textContent}; }"
    )
    param = _measure_param(offline, ".mdmark-param")
    context.close()
    return {"bytes": len(html.encode("utf-8")), "outsideRequests": outside, "errors": errors, "body": body, "tip": tip, "param": param}


def test_poc_mdmark_embed(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Page,
    browser: Browser,
    tmp_path: Path,
) -> None:
    """PoC の観点を詳細パネルと書き出した HTML で測り、`POC_RESULT` へ書く。"""
    url = _write_workspace(write_preview, make_item)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.goto("about:blank")
    memory_before = _private_memory_kb()
    open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector(f"{PANEL} p", timeout=WAIT_MS)
    page.wait_for_timeout(1_000)
    result: dict[str, Any] = {
        "memory": {"privateBeforeKb": memory_before, "privateAfterKb": _private_memory_kb(), "jsHeapBytes": _js_heap(page)},
        "body": _measure_body(page),
        "collision": _measure_collision(page),
    }
    result["tip"] = {
        "応答時間": _measure_tip(page, "応答時間"),
    }
    page.goto(f"{url}#tab=docs&view=table&id=A-1")
    page.wait_for_selector(f"{PANEL} p", timeout=WAIT_MS)
    result["tip"]["ＲＥＳＰＯＮＳＥ"] = _measure_tip(page, "ＲＥＳＰＯＮＳＥ")
    page.goto(f"{url}#tab=docs&view=table&id=A-1")
    page.wait_for_selector(f"{PANEL} p", timeout=WAIT_MS)
    idref = page.locator(f"{PANEL} a.idref").first
    if idref.count() > 0:
        idref.click()
        page.wait_for_timeout(300)
        result["idrefHashAfterClick"] = page.evaluate("location.hash")
    page.goto(f"{url}#tab=docs&view=table&id=A-1")
    page.wait_for_selector(f"{PANEL} p", timeout=WAIT_MS)
    result["chart"] = _measure_chart(page)
    result["param"] = _measure_param(page, PARAM)
    result["export"] = _measure_export(page, browser, tmp_path)
    Path(os.environ["POC_RESULT"]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
