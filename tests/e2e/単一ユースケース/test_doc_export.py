"""資料を書き出す（資料 1 件を Markdown か、mindstella が無くても開ける 1 枚の HTML で書き出す）の E2E テスト。

モデルを呼ばず、サーバーが配るプレビューを実際のブラウザで開いて確かめる。
HTML での書き出しは、実際の jsDelivr から mdmark の CSS と JavaScript を読む。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from embed_helpers import (
    CHART,
    CLIPBOARD_PERMISSIONS,
    EMBED_TIMEOUT_MS,
    EXPORT_BODY,
    EXPORT_ENTRY_NAME,
    EXPORT_MENU,
    MARKDOWN_EXPORT_BODY,
    save_download,
)
from playwright.sync_api import Download, Page, Route, expect
from preview_helpers import OpenPreview, ServeWorkspace, snapshot_records
from workspace_fixtures import MakeItem, SnapshotTree

# 資料のタブのカード（資料の ID を持つ）
DOC_CARD = '.doc-card[data-id="A-1"]'

# 詳細パネルの全画面表示のボタンと、全画面のモーダル
FULL_BUTTON = 'aside.panel button[data-act="full"]'
FULL_DIALOG = "dialog.full[open]"


def _open_doc(page: Page, open_preview: OpenPreview, url: str) -> None:
    """資料のタブを開いて A-1 のカードを押し、詳細パネルが開くのを待つ。"""
    open_preview(url, "#tab=docs")
    page.click(DOC_CARD)
    page.wait_for_selector("aside.panel.open .d-title")


def _is_not_file_url(url: str) -> bool:
    """`file:` で始まらない URL（外への要求）かを返す。"""
    return not url.startswith("file:")


def test_normal(
    serve_workspace: ServeWorkspace,
    open_preview: OpenPreview,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    page: Page,
    tmp_path: Path,
) -> None:
    """HTML で書き出すと、通信を止めて開いても本文・用語のツールチップ・チャート・操作できる部品が動く 1 枚の HTML になる（正常系）。"""
    # 準備
    page.context.grant_permissions(CLIPBOARD_PERMISSIONS)
    url, root = serve_workspace(
        make_item("A-1", title="書き出す資料"),
        make_item("G-1", title="用語", aliases=["応答時間"], meaning="返すまでの時間"),
        bodies={"A-1.md": EXPORT_BODY},
    )
    _open_doc(page, open_preview, url)
    page.wait_for_selector(CHART, timeout=EMBED_TIMEOUT_MS)
    before = snapshot_records(snapshot_tree(root))
    hash_text = page.evaluate("location.hash")
    history_length = page.evaluate("history.length")
    entry = page.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True)
    # 実行（書き出しの入口を押す）
    entry.click()
    # 検証（形式を選ぶメニューが出る）
    menu = page.locator(EXPORT_MENU)
    expect(menu).to_be_visible()
    expect(menu.get_by_role("button", name="HTML でエクスポート")).to_be_visible()
    expect(menu.get_by_role("button", name="Markdown でエクスポート")).to_be_visible()
    # 実行（「HTML でエクスポート」を押す）
    with page.expect_download() as download_info:
        page.get_by_role("button", name="HTML でエクスポート").click()
    exported = save_download(download_info.value, tmp_path)
    # 検証（拡張子 .html の 1 つのファイルで、画面は移らず、メニューを閉じた後は入口にフォーカスが戻る）
    assert exported.suffix == ".html"
    assert page.evaluate("location.hash") == hash_text
    assert page.evaluate("history.length") == history_length
    expect(menu).to_be_hidden()
    expect(entry).to_be_focused()
    # 実行（ダウンロードした HTML を、通信を止めて file:// で開く）
    blocked: list[str] = []

    def _block(route: Route) -> None:
        """`file:` 以外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    opened = page.context.new_page()
    opened.route(_is_not_file_url, _block)
    opened.goto(exported.as_uri())
    opened.wait_for_selector(".mdmark figure", timeout=EMBED_TIMEOUT_MS)
    # 検証（本文が共通のスタイルで描かれ、外への要求が 0 件）
    assert blocked == []
    assert opened.locator(".mdmark").count() == 1
    assert "応答時間の段落" in opened.inner_text(".mdmark")
    # 実行・検証（「応答時間」に乗せると、G-1 の意味のツールチップが出る）
    opened.hover(".mdmark-term")
    expect(opened.locator(".mdmark-term-tip")).to_be_visible()
    expect(opened.locator(".mdmark-term-tip")).to_contain_text("返すまでの時間")
    # 実行（スライダーを動かして、今の値をコピーする）
    opened.focus("input[type=range]")
    opened.keyboard.press("ArrowRight")
    opened.get_by_role("button", name="今の値をコピー").click()
    # 検証（グラフが描き直され、クリップボードに今の値の JSON が入る）
    assert "今の値（6）" in opened.inner_text(".mdmark-param .mdmark-diagram-legend")
    assert opened.evaluate("navigator.clipboard.readText().then(JSON.parse)") == {
        "rps": {"name": "リクエスト数", "value": 6}
    }
    opened.close()
    # ワークスペースの YAML と本文の中身が、書き出す前と同じ
    assert snapshot_records(snapshot_tree(root)) == before


def test_normal_when_markdown(
    serve_workspace: ServeWorkspace,
    open_preview: OpenPreview,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """Markdown で書き出すと、警告を挟んでから、範囲の HTML を除いた本文の Markdown をダウンロードさせる（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("A-1"), bodies={"A-1.md": MARKDOWN_EXPORT_BODY})
    _open_doc(page, open_preview, url)
    before = snapshot_records(snapshot_tree(root))
    # 実行（全画面表示にして、書き出しの入口を押す）
    page.click(FULL_BUTTON)
    page.wait_for_selector(FULL_DIALOG)
    hash_text = page.evaluate("location.hash")
    history_length = page.evaluate("history.length")
    downloads: list[Download] = []
    page.on("download", lambda download: downloads.append(download))
    entry = page.locator("dialog.full").get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True)
    entry.click()
    menu = page.locator(EXPORT_MENU)
    # 実行（「Markdown でエクスポート」を押す）
    page.get_by_role("button", name="Markdown でエクスポート").click()
    # 検証（ダウンロードされず、埋め込んだ HTML が消えることと共通のスタイルが外れることの警告が出る）
    assert downloads == []
    expect(menu).to_contain_text("埋め込んだ HTML")
    expect(menu).to_contain_text("共通のスタイルも外れます")
    # 実行（警告の「エクスポート」を押す）
    with page.expect_download() as download_info:
        menu.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True).click()
    download = download_info.value
    exported = Path(download.path()).read_text(encoding="utf-8")
    # 検証（拡張子 .md の 1 つのファイルで、範囲の外の段落を持ち、範囲の HTML を持たない）
    assert download.suggested_filename.endswith(".md")
    assert "範囲の外の段落" in exported
    assert "範囲の中の段落" not in exported
    assert "<!-- html -->" not in exported
    # 検証（詳細の全画面が開いたまま、入口にフォーカスが戻り、画面と履歴は変わらない）
    expect(menu).to_be_hidden()
    expect(page.locator(FULL_DIALOG)).to_have_count(1)
    expect(entry).to_be_focused()
    assert page.evaluate("location.hash") == hash_text
    assert page.evaluate("history.length") == history_length
    # ワークスペースの YAML と本文の中身が、書き出す前と同じ
    assert snapshot_records(snapshot_tree(root)) == before


def test_normal_when_back_from_warning(
    serve_workspace: ServeWorkspace,
    open_preview: OpenPreview,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """警告から「戻る」で形式を選ぶメニューへ戻り、Esc でメニューを閉じる。ダウンロードも履歴の増加も起きない（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("A-1"), bodies={"A-1.md": MARKDOWN_EXPORT_BODY})
    _open_doc(page, open_preview, url)
    before = snapshot_records(snapshot_tree(root))
    history_length = page.evaluate("history.length")
    downloads: list[Download] = []
    page.on("download", lambda download: downloads.append(download))
    entry = page.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True)
    menu = page.locator(EXPORT_MENU)
    # 実行（入口を押し、「Markdown でエクスポート」を押して警告を出す）
    entry.click()
    page.get_by_role("button", name="Markdown でエクスポート").click()
    expect(menu).to_contain_text("共通のスタイルも外れます")
    # 実行（警告の「戻る」を押す）
    menu.get_by_role("button", name="戻る", exact=True).click()
    # 検証（形式を選ぶメニューに戻り、ファイルはダウンロードされない）
    expect(menu.get_by_role("button", name="HTML でエクスポート")).to_be_visible()
    expect(menu.get_by_role("button", name="Markdown でエクスポート")).to_be_focused()
    assert downloads == []
    # 実行（Esc を押す）
    page.keyboard.press("Escape")
    # 検証（メニューが閉じ、入口にフォーカスが戻る。詳細パネルは開いたまま）
    expect(menu).to_be_hidden()
    expect(entry).to_be_focused()
    expect(page.locator("aside.panel.open")).to_have_count(1)
    assert downloads == []
    # 検証（メニューの開閉と警告への切り替えで、履歴の数が増えない）
    assert page.evaluate("history.length") == history_length
    # ワークスペースの YAML と本文の中身が、開く前と同じ
    assert snapshot_records(snapshot_tree(root)) == before


def test_normal_when_html_body(
    serve_workspace: ServeWorkspace,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Page,
) -> None:
    """本文が HTML の資料には、詳細パネルにも詳細の全画面にも書き出しの入口が出ない（正常系）。"""
    # 準備
    url, _ = serve_workspace(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": "<p>HTML の本文</p>\n"}
    )
    # 実行（資料のタブで A-1 を押す）
    _open_doc(page, open_preview, url)
    entries: Any = page.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True)
    # 検証（詳細パネル）
    expect(entries).to_have_count(0)
    # 実行（全画面表示にする）
    page.click(FULL_BUTTON)
    page.wait_for_selector(FULL_DIALOG)
    # 検証（詳細の全画面）
    expect(entries).to_have_count(0)
