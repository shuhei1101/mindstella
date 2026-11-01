"""プレビューを配る（記録を見るだけの 1 枚の HTML に書き出し、通信を止めたブラウザで開いて読む）の E2E テスト。

正常シナリオは、実際の jsDelivr から描画のライブラリとライセンスの本文を取って書き出す。
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml
from display_settings_helpers import (
    KINDS_WITHOUT_TERMS,
    SAVE_DEFAULT_BUTTON,
    SETTINGS_PANEL_OPEN,
    graph_look,
    open_settings,
    tab_keys,
)
from playwright.sync_api import Page
from preview_helpers import OpenPreview, click_item_ball
from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace, SnapshotTree

# このファイルから見たリポジトリの直下（tests/e2e/単一ユースケース の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]
    / "plugins"
    / "mindstella"
    / "skills"
    / "mindmap"
    / "preview"
    / "template.html"
)

# 埋め込み先・ライセンスの表示の要素の開きタグ
DATA_ELEMENT_OPEN = '<script type="application/json" id="mindmap-data">'
LICENSES_ELEMENT_OPEN = '<script type="text/plain" id="mindmap-licenses">'

# 資料 A-1 の本文（表と mermaid の図を 1 つずつ持つ）
DOC_BODY = """## 仕様

| 列 | 値 |
| --- | --- |
| 数 | 3 |

```mermaid
flowchart LR
  A --> B
```
"""

# 画面に出ない書き込みの操作（ボタンの名前に含まれる語）
WRITE_ACTION_PATTERN = re.compile("追加|編集|削除|送信|保存")

# 中に持つライブラリごとの、表示に出る名前・ライセンスの名前・著作権の表示（雛形の URL のパッケージ名 → 表示）
EXPECTED_LICENSES = {
    "marked": ("marked", "MIT", "Copyright (c) 2018+, MarkedJS"),
    "elkjs": ("elkjs", "EPL-2.0", "(c) Kiel University and others"),
    "mermaid": ("mermaid", "MIT", "Copyright (c) 2014 - 2022 Knut Sveidqvist"),
    "diff": ("jsdiff", "BSD-3-Clause", "Copyright (c) 2009-2015, Kevin Decker"),
}

# mdmark の表示に出る名前・ライセンスの名前・著作権の表示（mdmark は ES モジュールで、雛形の import map の URL から版を読む）
EXPECTED_MDMARK_LICENSE = ("mdmark", "MIT", "Copyright (c) 2026 shuhei1101")

# mdmark の配布物が中に束ねた依存のライセンスの本文の先頭の行（`THIRD_PARTY_LICENSES.txt` の最初の依存）
MDMARK_BUNDLED_LICENSES_HEAD = "dayjs 1.11.23 (MIT)"

# 詳細パネルの Markdown の本文（mdmark が描いた本文の要素）
MDMARK_BODY = "aside.panel .md:not(.md-value).mdmark"

# elkjs のソースコードの入手先（リポジトリ）
ELKJS_REPOSITORY = "https://github.com/kieler/elkjs"

# 画面に出ているボタンの名前（文字と aria-label）を読む
BUTTON_LABELS_SCRIPT = """() => [...document.querySelectorAll('button, [role="button"]')].map(
    b => `${b.textContent ?? ''} ${b.getAttribute('aria-label') ?? ''}`
)"""

# 読めなかったライブラリの知らせ（role="alert"）を数える
ALERT_SELECTOR = '[role="alert"]'

# ワークスペースの既定の見た目
DEFAULT_LOOK = "starlight"

# 描画のライブラリを描いた後の図（SVG）が出るまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000


class _ExternalReferences(HTMLParser):
    """script・img の src と link の href を持つ要素を集める。"""

    def __init__(self) -> None:
        """集めた要素のタグ名と属性の並びを空で持つ。"""
        super().__init__()
        self.found: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """外のファイルや URL を指す属性を持つ要素を控える。"""
        values = dict(attrs)
        if (tag in ("script", "img") and "src" in values) or (tag == "link" and "href" in values):
            self.found.append((tag, values))


def _is_not_file_url(url: str) -> bool:
    """`file:` で始まらない URL（外への要求）かを返す。"""
    return not url.startswith("file:")


def _read_element(html: str, open_tag: str) -> str:
    """HTML の指定した script 要素の中身を返す。"""
    return html.split(open_tag, 1)[1].split("</script>", 1)[0]


def _template_versions() -> dict[str, str]:
    """雛形の描画のライブラリの `<script src>` から、パッケージ名 → 版を読む。"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return dict(re.findall(r'src="https://cdn\.jsdelivr\.net/npm/([^@"]+)@([^/"]+)/', template))


def _template_mdmark_version() -> str:
    """雛形の import map の mdmark の URL から、版のタグを読む。"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    import_map = json.loads(re.search(r'<script type="importmap">(.*?)</script>', template, re.DOTALL).group(1))  # type: ignore[union-attr]
    (url,) = import_map["integrity"]
    return re.search(r"/mdmark@([^/]+)/", url).group(1)  # type: ignore[union-attr]


def _records(make_item: MakeItem, valid_settings: dict[str, Any]) -> list[dict[str, Any]]:
    """検討事項 D-1 と、D-1 を前提に持つ D-2、本文を持つ資料 A-1。"""
    placement: dict[str, Any] = {
        "target": valid_settings["targets"][0]["name"],
        "category": valid_settings["categories"][0]["name"],
        "phase": valid_settings["phases"][0],
    }
    return [
        make_item("D-1", status="未決定", **placement),
        make_item("D-2", status="未決定", depends_on=["D-1"], **placement),
        make_item("A-1", status="完成"),
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    snapshot_tree: SnapshotTree,
    page: Page,
    tmp_path: Path,
    valid_settings: dict[str, Any],
) -> None:
    """記録を人に渡すために書き出し、通信を止めたブラウザで開いて本文・図・マップ・ネットワークを読む（正常系）。"""
    # 準備
    # ワークスペースの既定は、見た目が starlight で、表示する種類から用語集を外す
    settings = {
        **valid_settings,
        "display": {"network_look": DEFAULT_LOOK, "visible_kinds": KINDS_WITHOUT_TERMS},
    }
    root = make_workspace(
        *_records(make_item, valid_settings), settings=settings, bodies={"A-1.md": DOC_BODY}
    )
    before = snapshot_tree(root)
    out = tmp_path / "配る.html"
    # 実行（書き出す）
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証（書き出し）
    assert result.is_error is False, result.text
    assert result.data == {"path": str(out)}
    html = out.read_text(encoding="utf-8")
    references = _ExternalReferences()
    references.feed(html)
    assert references.found == []
    licenses = _read_element(html, LICENSES_ELEMENT_OPEN)
    versions = _template_versions()
    for package, (name, license_name, notice) in EXPECTED_LICENSES.items():
        assert f"{name} {versions[package]}" in licenses
        assert notice in licenses
        assert f"License: {license_name}" in licenses
    # mdmark は、名前・版・著作権の表示・ライセンスの名前と、配布物が中に束ねた依存のライセンスの本文を持つ
    mdmark_name, mdmark_license, mdmark_notice = EXPECTED_MDMARK_LICENSE
    assert f"{mdmark_name} {_template_mdmark_version()}" in licenses
    assert mdmark_notice in licenses
    assert f"License: {mdmark_license}" in licenses
    assert MDMARK_BUNDLED_LICENSES_HEAD in licenses
    assert "DOMPurify" not in licenses
    assert f"{ELKJS_REPOSITORY}/tree/{versions['elkjs']}" in licenses
    assert snapshot_tree(root) == before
    # 実行（外への通信を全て止めたブラウザで開く）
    blocked: list[str] = []

    def _block(route: Any) -> None:
        """外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    page.route(_is_not_file_url, _block)
    button_labels: list[str] = []
    open_preview(out.as_uri())
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # 検討事項のタブはボードで開くので、表示形式の切り替えでマップに切り替えると、マップに D-1 と D-2 が描かれる
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.click('.segment button[data-view="map"]')
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    map_ids = page.eval_on_selector_all(
        "#decision-map .map-node.n-item", "nodes => nodes.map(n => n.dataset.node).sort()"
    )
    assert map_ids == ["D-1", "D-2"]
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # A-1 の詳細パネルの本文に、表が table 要素で、mermaid の図が SVG で描かれる
    page.click('nav.tabbar a[data-tab="docs"]')
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    assert page.locator(MDMARK_BODY).count() == 1
    assert page.locator("aside.panel .md table").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # ネットワークに玉が描かれる（D-1 の玉を押すと、詳細パネルに D-1 が開く）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    click_item_ball(page, "D-1")
    assert page.inner_text("aside.panel .d-title") == "D-1の題"
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # トップバーに用語集のタブが無く、ネットワークに渡る見た目が starlight である
    assert "terms" not in tab_keys(page)
    assert graph_look(page) == DEFAULT_LOOK
    # トップバーの表示の設定でパネルが開き、「ワークスペースの既定にする」が無い
    open_settings(page)
    assert page.locator(SETTINGS_PANEL_OPEN).count() == 1
    assert page.locator(SAVE_DEFAULT_BUTTON).count() == 0
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # 検証（ブラウザ）
    assert blocked == []
    # ボタンを 1 つも読めていないと、書き込む操作が無いことを確かめたことにならない
    assert button_labels
    assert [label for label in button_labels if WRITE_ACTION_PATTERN.search(label)] == []
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
) -> None:
    """手で崩した YAML があると、書き出す先のファイルを書き換えずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    assert call_tool("export", workspace=str(root), out=str(out)).is_error is False
    (root / RECORD_DIR / "decisions.yaml").write_text(
        yaml.safe_dump({"items": [make_item("D-1", status="完了")]}, allow_unicode=True),
        encoding="utf-8",
    )
    out_before = out.read_bytes()
    workspace_before = snapshot_tree(root)
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is True
    assert "decisions.yaml" in result.text
    assert "status" in result.text
    assert out.read_bytes() == out_before
    assert snapshot_tree(root) == workspace_before


# 詳細パネルの HTML の本文の枠
HTML_BODY_FRAME = "aside.panel iframe.html-frame[data-html-body]"

# `<style>` で全ての要素と本文を塗り、見出し・表・図・スクリプトを持つ資料 A-1 の HTML の本文（スクリプトは実行されると印を残す）
HTML_DOC_BODY = """<style>
  * { margin: 40px !important; color: rgb(255, 0, 0) !important; }
  body { background: rgb(0, 0, 255) !important; }
</style>
<h1>画面のモック</h1>
<table><tr><th>列</th><td>値</td></tr></table>
<svg width="40" height="40"><circle cx="20" cy="20" r="18" fill="orange"/></svg>
<script>window.__leak = 1; parent.__leak = 1;</script>
"""

# 詳細パネルの外のタイトルとトップバーの色・余白・背景を返す
OUTSIDE_STYLE_SCRIPT = """() => ['aside.panel .d-title', 'header.topbar'].map((selector) => {
    const style = getComputedStyle(document.querySelector(selector));
    return [style.color, style.marginTop, style.backgroundColor];
})"""

# ページの変数に残る印を、親の画面と枠の中で返す
LEAK_SCRIPT = """() => [
    window.__leak ?? null,
    document.querySelector('aside.panel iframe.html-frame[data-html-body]').contentWindow.__leak ?? null,
]"""


def test_normal_when_html_doc_exported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
    tmp_path: Path,
) -> None:
    """HTML の本文の資料を書き出し、通信を止めたブラウザで開いて、描いた本文を読む（正常系）。"""
    # 準備（本文が Markdown の資料 A-2 を描いたときの、枠の外の見た目を比べる見本にする）
    root = make_workspace(
        make_item("A-1", body="A-1.html"),
        make_item("A-2"),
        bodies={"A-1.html": HTML_DOC_BODY, "A-2.md": "資料の本文\n"},
    )
    out = tmp_path / "配る.html"
    # 実行（書き出す）
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # 実行（外への通信を全て止めたブラウザで開く）
    blocked: list[str] = []

    def _block(route: Any) -> None:
        """外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    page.route(_is_not_file_url, _block)
    open_preview(out.as_uri(), "#tab=docs&id=A-2")
    page.wait_for_selector("aside.panel.open .d-title")
    before = page.evaluate(OUTSIDE_STYLE_SCRIPT)
    page.evaluate("location.hash = '#tab=docs&id=A-1'")
    page.wait_for_selector(f"{HTML_BODY_FRAME}[data-rendered]", state="attached", timeout=DIAGRAM_TIMEOUT_MS)
    frame = page.frame_locator(HTML_BODY_FRAME)
    # 検証
    # A-1 の詳細パネルに、本文の見出し・表・図が HTML を描いた結果で出る
    assert frame.locator("h1").inner_text() == "画面のモック"
    assert frame.locator("table").count() == 1
    assert frame.locator("svg").count() == 1
    # ページの変数に印が残らない（本文のスクリプトが実行されていない）
    assert page.evaluate(LEAK_SCRIPT) == [None, None]
    # 本文の `<style>` が、詳細パネルの外の色と余白を変えない
    assert page.evaluate(OUTSIDE_STYLE_SCRIPT) == before
    # 開いてから操作を終えるまでに、ブラウザが外へ出した要求が 0 件
    assert blocked == []
