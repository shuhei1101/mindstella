"""画面設計『保存待ちのパネル』の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Route, expect
from preview_edit_helpers import (
    DETAIL_PANEL,
    PENDING_BUTTON,
    PENDING_PANEL,
    SAVE_BUTTON,
    SAVE_PATTERN,
    open_pending,
    read_edits_file,
    read_items_file,
)
from preview_fixture_types import OpenPreview, WriteReviewPreview
from workspace_fixtures import RECORD_DIR, MakeEdit, MakeItem

# 溜めた編集を出す一覧の画面
DECISIONS_HASH = "#tab=decisions&view=board"

# 保存を待つ上限ミリ秒
SAVE_TIMEOUT_MS = 10_000

# 保存した知らせの消える上限ミリ秒（5 秒出す）
NOTICE_GONE_MS = 9_000

# 設定の題名（valid_settings）
SETTINGS_SUMMARY = "要件出しのスキル mindmap を設計する"

# AI が溜めた後に書き換えた項目として扱う、溜めたときより前の更新日時
OLD_STAMP = "2026-09-01T00:00:00+00:00"


def _edits(make_edit: MakeEdit) -> tuple[dict[str, Any], ...]:
    """項目のキー・削除・設定・項目の追加の 4 件の保存待ちの編集を返す。"""
    return (
        make_edit("E-1", value="案 A にする", before=""),
        make_edit("E-2", target="N-1", op="item-remove", key=None, value=None, before=None),
        make_edit(
            "E-3",
            target="settings",
            op="setting",
            key="summary",
            value="画面の編集",
            before=SETTINGS_SUMMARY,
            base=None,
        ),
        make_edit(
            "E-4",
            target="new-1",
            op="item-add",
            key="tasks",
            value={"title": "画面を作る", "kind": "作業", "status": "未着手"},
            before=None,
            base=None,
        ),
    )


def _open_panel(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
    *,
    edits: tuple[dict[str, Any], ...] | None = None,
) -> tuple[Page, Path]:
    """4 件の保存待ちの編集（または渡した編集）で検討事項の画面を開き、保存待ちのパネルを開いたページと、ワークスペースのフォルダを返す。"""
    url, root = write_edit_preview(
        make_item("D-1", title="最初の問い"),
        make_item("N-1", title="消すメモ"),
        edits=_edits(make_edit) if edits is None else edits,
    )
    page = open_preview(url, DECISIONS_HASH)
    page.wait_for_selector(PENDING_BUTTON)
    open_pending(page)
    return page, root


def test_heading(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """「保存待ち」と編集の件数を見出しに出し、開いたときにフォーカスを移す（正常系）。"""
    # 準備・実行
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 検証
    assert page.inner_text(f"{PENDING_PANEL} h2").replace("\n", " ") == "保存待ち 4 件"
    assert page.evaluate("document.activeElement.tagName") == "H2"
    assert page.get_attribute(PENDING_PANEL, "aria-label") == "保存待ちの編集"


def test_close(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """閉じるボタン・Esc・トップバーのボタンで閉じ、トップバーのボタンへフォーカスを戻す。溜めた編集は残る（正常系）。"""
    # 準備
    page, root = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    close = page.get_by_role("button", name="保存待ちの編集を閉じる")
    # 実行・検証（閉じるボタン）
    close.click()
    expect(page.locator(PENDING_PANEL)).to_have_count(0)
    assert page.evaluate("document.activeElement?.dataset.act") == "pending"
    # 実行・検証（トップバーのボタンで開閉）
    page.click(PENDING_BUTTON)
    expect(page.locator(PENDING_PANEL)).to_have_count(1)
    page.click(PENDING_BUTTON)
    expect(page.locator(PENDING_PANEL)).to_have_count(0)
    # 実行・検証（Esc）
    page.click(PENDING_BUTTON)
    page.wait_for_selector(PENDING_PANEL)
    page.keyboard.press("Escape")
    expect(page.locator(PENDING_PANEL)).to_have_count(0)
    assert len(read_edits_file(root)["items"]) == 4
    assert page.get_by_role("button", name="保存待ち（4 件）").count() == 1


def test_groups(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """編集を項目・設定・追加する項目ごとのまとまりにして、溜めた順に並べる（正常系）。"""
    # 準備・実行
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 検証
    heads = page.locator(f"{PENDING_PANEL} .pe-group-head").all_inner_texts()
    assert [" ".join(head.split()) for head in heads] == [
        "検討事項 D-1 最初の問い",
        "メモ N-1 消すメモ",
        f"設定 {SETTINGS_SUMMARY}",
        "タスクを追加 画面を作る",
    ]
    assert page.locator(f"{PENDING_PANEL} .pe-group").count() == 4


def test_group_opens_item(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """まとまりの見出しを押すと、項目を詳細パネルの編集の表示で開く（正常系）。"""
    # 準備
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 実行
    page.get_by_role("button", name="D-1「最初の問い」を開く").click()
    page.wait_for_selector(f"{DETAIL_PANEL}.open")
    # 検証
    assert page.inner_text(f"{DETAIL_PANEL} .panel-kind") == "検討事項 D-1"
    assert page.get_by_role("button", name="編集を終える").count() == 1
    assert page.locator(f"{DETAIL_PANEL} form.pe-form").count() == 1


def test_group_opens_settings(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """設定のまとまりの見出しを押すと、設定の画面を開く（正常系）。"""
    # 準備
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 実行
    page.get_by_role("button", name=f"設定「{SETTINGS_SUMMARY}」を開く").click()
    # 検証
    page.wait_for_selector(".pe-ws")
    assert page.get_by_role("heading", name="設定", exact=True).count() == 1


def test_rows(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """編集の行は「何を」と前 → 後を出す。読み上げに「前:」「後:」を添え、削除と追加は値を出さない（正常系）。"""
    # 準備・実行
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 検証
    rows = {row_id: page.locator(f"#pe-row-{row_id}") for row_id in ("E-1", "E-2", "E-3", "E-4")}
    assert rows["E-1"].locator(".pe-what").inner_text() == "決定内容"
    assert " ".join(rows["E-1"].locator("del").inner_text().split()) == "前: （空）"
    assert " ".join(rows["E-1"].locator("ins").inner_text().split()) == "後: 案 A にする"
    assert rows["E-1"].locator("del .sr-only").inner_text().strip() == "前:"
    assert rows["E-1"].locator("ins .sr-only").inner_text().strip() == "後:"
    assert rows["E-2"].locator(".pe-what").inner_text() == "項目を削除"
    assert rows["E-2"].locator("svg.icon").count() >= 1
    assert rows["E-2"].locator("ins, del").count() == 0
    assert rows["E-3"].locator(".pe-what").inner_text() == "題名"
    assert " ".join(rows["E-3"].locator("del").inner_text().split()).endswith(SETTINGS_SUMMARY)
    assert rows["E-4"].locator(".pe-what").inner_text() == "項目を追加"
    assert rows["E-4"].locator("ins").inner_text() == "画面を作る"


def test_undo(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """取り消すと 1 件を外し、次の行の取り消すボタン（最後の行なら前の行）へフォーカスを移す（正常系）。"""
    # 準備
    page, root = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 実行（先頭の行）
    page.get_by_role("button", name="D-1 の決定内容の編集を取り消す").click()
    expect(page.locator("#pe-row-E-1")).to_have_count(0)
    # 検証（先頭の行）
    assert page.evaluate("document.activeElement.getAttribute('aria-label')") == "N-1 の項目を削除の編集を取り消す"
    assert [edit["id"] for edit in read_edits_file(root)["items"]] == ["E-2", "E-3", "E-4"]
    assert page.inner_text(f"{PENDING_PANEL} h2").replace("\n", " ") == "保存待ち 3 件"
    # 実行（最後の行）
    page.get_by_role("button", name="タスクを追加 の項目を追加の編集を取り消す").click()
    expect(page.locator("#pe-row-E-4")).to_have_count(0)
    # 検証（最後の行）
    assert page.evaluate("document.activeElement.getAttribute('aria-label')") == (
        "設定 の題名の編集を取り消す"
    )


def test_empty(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """編集が 0 件になると、空の状態を出し、保存のボタンを押せなくする。見出しへフォーカスを移す（正常系）。"""
    # 準備
    page, root = _open_panel(
        write_edit_preview, make_item, make_edit, open_preview, edits=(make_edit("E-1"),)
    )
    # 実行
    page.get_by_role("button", name="D-1 の決定内容の編集を取り消す").click()
    # 検証
    expect(page.locator(f"{PENDING_PANEL} .comments-empty")).to_have_text("保存待ちの編集はありません。")
    assert page.locator(f"{PENDING_PANEL} .pe-foot-sum").count() == 0
    assert page.is_disabled(SAVE_BUTTON)
    assert page.evaluate("document.activeElement.tagName") == "H2"
    assert read_edits_file(root)["items"] == []


def test_summary(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """保存で書く件数と、そのうちの削除の件数を出す。削除が無ければ括弧を出さない（正常系）。"""
    # 準備・実行
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 検証
    assert page.inner_text(f"{PENDING_PANEL} .pe-foot-sum") == "4 件（うち削除 1 件）をワークスペースに書きます"
    # 削除を取り消すと括弧が消える
    page.get_by_role("button", name="N-1 の項目を削除の編集を取り消す").click()
    expect(page.locator(f"{PENDING_PANEL} .pe-foot-sum")).to_have_text("3 件をワークスペースに書きます")


def test_save_label(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """削除を含むときは、ボタンの文言に削除の件数を出す（正常系）。"""
    # 準備・実行
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 検証
    assert page.inner_text(SAVE_BUTTON).strip() == "まとめて保存する（1 件を削除）"
    page.get_by_role("button", name="N-1 の項目を削除の編集を取り消す").click()
    expect(page.locator(SAVE_BUTTON)).to_have_text("まとめて保存する")


def test_save(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """全て書けたらパネルを閉じ、書いた内容を画面に当て、保存した知らせを 5 秒出して消す（正常系）。"""
    # 準備
    page, root = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    # 実行
    page.click(SAVE_BUTTON)
    page.wait_for_selector(".pe-toast", timeout=SAVE_TIMEOUT_MS)
    # 検証
    assert page.get_attribute(".pe-toast", "role") == "status"
    assert page.inner_text(".pe-toast").strip() == "4 件を保存しました。"
    assert page.locator(PENDING_PANEL).count() == 0
    assert page.locator(PENDING_BUTTON).count() == 0
    decision = read_items_file(root, "decisions.yaml")[0]
    assert (decision["answer"], decision["updated_by"]) == ("案 A にする", "user")
    assert [item["id"] for item in read_items_file(root, "notes.yaml")] == []
    assert [item["title"] for item in read_items_file(root, "tasks.yaml")] == ["画面を作る"]
    assert read_edits_file(root)["items"] == []
    # 知らせは 5 秒で消える
    expect(page.locator(".pe-toast")).to_have_count(0, timeout=NOTICE_GONE_MS)


def test_saving(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """送信中は「保存しています…」にして押せなくし、aria-busy と回る印を出す（正常系）。"""
    # 準備
    page, _ = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    held: list[Route] = []
    # 応答を保留して、保存している途中の状態を保つ
    page.route(SAVE_PATTERN, lambda route: held.append(route))
    # 実行
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{SAVE_BUTTON}[aria-busy='true']")
    # 検証
    assert page.inner_text(SAVE_BUTTON).strip() == "保存しています…"
    assert page.is_disabled(SAVE_BUTTON)
    assert page.locator(f"{SAVE_BUTTON} .pe-spin").count() == 1
    # 保留を解くと保存が終わる
    held[0].continue_()
    page.wait_for_selector(".pe-toast", timeout=SAVE_TIMEOUT_MS)


def test_blocked(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """AI が溜めた後に項目を書き換えていたら、何も保存せず、書き込めない編集の知らせと行の理由を出す（異常系）。"""
    # 準備
    url, root = write_edit_preview(
        make_item("D-1", title="最初の問い", updated="2026-10-05T01:00:00+00:00"),
        make_item("N-1", title="消すメモ"),
        edits=(make_edit("E-1", base=OLD_STAMP), make_edit("E-2", target="N-1", op="item-remove", key=None, value=None, before=None)),
    )
    page = open_preview(url, DECISIONS_HASH)
    page.wait_for_selector(PENDING_BUTTON)
    open_pending(page)
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    # 実行
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{PENDING_PANEL} .pe-alert", timeout=SAVE_TIMEOUT_MS)
    # 検証
    alert = page.locator(f"{PENDING_PANEL} .pe-alert")
    assert alert.get_attribute("role") == "alert"
    text = alert.inner_text()
    assert "1 件の編集を書き込めないため、何も保存していません。" in text
    assert "D-1 の決定内容" in text
    assert "書き込めない編集を取り消してから、もう一度保存してください。" in text
    assert page.evaluate("document.activeElement.dataset.focus") == "alert"
    assert page.locator(PENDING_PANEL).count() == 1
    assert page.locator(".pe-toast").count() == 0
    assert page.locator(f"{PENDING_PANEL} .pe-group.is-blocked").count() == 1
    assert page.locator("#pe-row-E-1.is-blocked").count() == 1
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before
    assert [edit["id"] for edit in read_edits_file(root)["items"]] == ["E-1", "E-2"]
    # 知らせの一覧の項目を押すと、その編集の行の取り消すボタンへフォーカスを移す
    alert.get_by_role("link", name="D-1 の決定内容").click()
    assert page.evaluate("document.activeElement.getAttribute('aria-label')") == (
        "D-1 の決定内容の編集を取り消す"
    )
    # トップバーのボタンも書き込めない編集ありを知らせる
    assert page.get_by_role("button", name="保存待ち（2 件・書き込めない編集あり）").count() == 1


def test_offline(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """保存がサーバーに届かなければ、つながらない知らせを出して編集を残す。もう一度保存すれば書ける（異常系）。"""
    # 準備
    page, root = _open_panel(write_edit_preview, make_item, make_edit, open_preview)
    page.route(SAVE_PATTERN, lambda route: route.abort())
    # 実行
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{PENDING_PANEL} .pe-alert", timeout=SAVE_TIMEOUT_MS)
    # 検証
    alert = page.locator(f"{PENDING_PANEL} .pe-alert")
    assert alert.get_attribute("role") == "alert"
    text = alert.inner_text()
    assert "サーバーにつながらないため、保存できませんでした。" in text
    assert "保存待ちの編集は残っています。サーバーを立ち上げ直してから、もう一度保存してください。" in text
    assert len(read_edits_file(root)["items"]) == 4
    assert page.is_enabled(SAVE_BUTTON)
    # 直ったあとの保存は通る
    page.unroute(SAVE_PATTERN)
    page.click(SAVE_BUTTON)
    page.wait_for_selector(".pe-toast", timeout=SAVE_TIMEOUT_MS)
    assert read_edits_file(root)["items"] == []


# タグごとに、名前・主題か・title・マーカーの aria-hidden（マーカーが無ければ null）を読む（引数はタグを持つ要素の CSS セレクター）
ROW_TAGS_JS = """(selector) => [...document.querySelectorAll(`${selector} span.tag`)].map((tag) => ({
    name: tag.lastChild.textContent,
    main: tag.classList.contains("is-main"),
    title: tag.getAttribute("title"),
    marker: tag.querySelector("svg")?.getAttribute("aria-hidden") ?? null,
}))"""


def test_rows_when_tags(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """タグの編集の行は、前の値と後の値のそれぞれをタグの並びで描き、主題のタグを二重丸のマーカーで見分ける（「主題」は読み上げと title だけ）（正常系）。"""
    # 準備
    before = [{"name": "データ", "main": True}, {"name": "画面"}]
    after = [{"name": "データ"}, {"name": "画面", "main": True}]
    url, _ = write_edit_preview(
        make_item("D-1", title="最初の問い", tags=before),
        edits=(make_edit("E-1", key="tags", value=after, before=before),),
    )
    page = open_preview(url, DECISIONS_HASH)
    page.wait_for_selector(PENDING_BUTTON)
    # 実行
    open_pending(page)
    # 検証
    row = page.locator("#pe-row-E-1")
    assert row.locator(".pe-what").inner_text() == "タグ"
    assert page.evaluate(ROW_TAGS_JS, "#pe-row-E-1 del") == [
        {"name": "データ", "main": True, "title": "主題", "marker": "true"},
        {"name": "画面", "main": False, "title": None, "marker": None},
    ]
    assert page.evaluate(ROW_TAGS_JS, "#pe-row-E-1 ins") == [
        {"name": "データ", "main": False, "title": None, "marker": None},
        {"name": "画面", "main": True, "title": "主題", "marker": "true"},
    ]
    assert row.locator("del > .sr-only").inner_text().strip() == "前:"
    assert row.locator("ins > .sr-only").inner_text().strip() == "後:"
