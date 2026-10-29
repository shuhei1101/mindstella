"""画面設計『設定の画面』の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect
from preview_edit_helpers import PENDING_BUTTON, read_edits_file
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_settings_helpers import SETTINGS_PANEL_OPEN, open_settings
from workspace_fixtures import RECORD_DIR, MakeItem

# 設定の画面
WS = ".pe-ws"

# 設定のキー 1 つの入力欄の外枠
FIELD = f"{WS} .pe-field"

# 一覧の画面
DECISIONS_HASH = "#tab=decisions&view=board"

# 溜めた編集を待つ上限ミリ秒
EDIT_TIMEOUT_MS = 10_000

# 関連する場所の 1 行目の項目が、保存待ちに溜まったかを読む
SAVED_LINK_JS = """async ({field, value}) => {
  const edits = (await (await fetch('/api/edits')).json()).items;
  const links = edits.find(e => e.key === 'links');
  return links !== undefined && links.value[0][field] === value;
}"""


def _settings(valid_settings: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """フェーズ 3 つ・説明つきの設定を返す。"""
    return {**valid_settings, "description": "元の説明", **overrides}


def _open_workspace(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    **overrides: Any,
) -> tuple[Page, Path]:
    """フェーズ「目的」・対象「mindmap」を使う検討事項 D-1 を持つワークスペースで、設定の画面を開いたページとフォルダを返す。"""
    url, root = write_edit_preview(
        make_item("D-1", phase="目的", target="mindmap", category="データ構造"),
        settings=_settings(valid_settings, **overrides),
    )
    page = open_preview(url, DECISIONS_HASH)
    open_settings(page)
    page.get_by_role("button", name="設定を編集する").click()
    page.wait_for_selector(WS)
    return page, root


def _commit(page: Page, label: str, value: str) -> None:
    """名前で引いた入力欄に値を入れて離れ、編集が溜まって画面が描き直されるのを待つ。"""
    field = page.get_by_label(label, exact=True)
    field.fill(value)
    field.blur()


def _edit_of(root: Path, key: str) -> dict[str, Any]:
    """edits.yaml に溜めた、設定のキーの編集を返す（溜まるまで待たない）。"""
    return next(
        edit
        for edit in read_edits_file(root)["items"]
        if edit["target"] == "settings" and edit["key"] == key
    )


def _wait_edits(page: Page, count: int) -> None:
    """トップバーの保存待ちの件数が揃うのを待つ。"""
    expect(page.locator(PENDING_BUTTON)).to_have_attribute(
        "aria-label", f"保存待ち（{count} 件）", timeout=EDIT_TIMEOUT_MS
    )


def test_open_and_close(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """表示の設定のパネルの「設定を編集する」で開き、本文の区画を置き換える。見出しへフォーカスを移し、閉じると元の画面に戻る（正常系）。"""
    # 準備・実行
    page, _ = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    # 検証
    assert page.locator(f"{WS} h1").inner_text() == "設定"
    assert page.evaluate("document.activeElement.tagName") == "H1"
    assert page.locator("main#main").is_hidden()
    assert page.locator(SETTINGS_PANEL_OPEN).count() == 0
    # 実行（閉じる）
    page.get_by_role("button", name="閉じる").click()
    # 検証（閉じる）
    expect(page.locator(WS)).to_have_count(0)
    assert page.locator("main#main").is_visible()


def test_groups(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """設定のキーを「話し合い」「進め方」「関連」「変更履歴」の fieldset に分けて並べる（正常系）。"""
    # 準備・実行
    page, _ = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    # 検証
    assert page.locator(f"{WS} form").get_attribute("aria-label") == "ワークスペースの設定"
    assert page.locator(f"{WS} fieldset legend").all_inner_texts() == [
        "話し合い",
        "進め方",
        "関連",
        "変更履歴",
    ]
    keys = page.locator(f"{WS} fieldset").evaluate_all(
        "sets => sets.map(set => [...set.querySelectorAll(':scope > .pe-field')].map(f => f.dataset.key))"
    )
    assert keys == [
        ["summary", "description", "playbooks", "goal"],
        ["phases", "target_label", "targets", "categories"],
        ["links"],
        ["history_limit"],
    ]


def test_text_inputs(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """題名と最上位の軸の呼び名は、入力欄を離れたときに保存待ちに溜め、溜めたキーに印を付ける。元の値に戻すと外れる（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    original = valid_settings["summary"]
    # 実行（題名を直す）
    _commit(page, "題名", "画面の編集")
    _wait_edits(page, 1)
    _commit(page, "最上位の軸の呼び名", "機能")
    _wait_edits(page, 2)
    # 検証
    assert _edit_of(root, "summary")["value"] == "画面の編集"
    assert _edit_of(root, "summary")["before"] == original
    assert _edit_of(root, "target_label")["value"] == "機能"
    assert page.get_by_label("題名", exact=True).input_value() == "画面の編集"
    summary = page.locator(f"{FIELD}[data-key='summary']")
    assert "is-pending" in summary.get_attribute("class")
    assert summary.locator(".pm.pm-compact").count() == 1
    assert page.locator(f"{FIELD}[data-key='description'] .pm").count() == 0
    # 実行（元の値に戻す）
    _commit(page, "題名", original)
    _wait_edits(page, 1)
    # 検証（元の値に戻す）
    assert [edit["key"] for edit in read_edits_file(root)["items"]] == ["target_label"]
    assert page.locator(f"{FIELD}[data-key='summary'] .pm").count() == 0


def test_description(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """説明は何行も書く欄で、空にして離れると説明を消す編集（値が null）を溜める（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    area = page.get_by_label("説明", exact=True)
    assert area.evaluate("e => e.tagName") == "TEXTAREA"
    assert area.input_value() == "元の説明"
    # 実行
    _commit(page, "説明", "")
    _wait_edits(page, 1)
    # 検証
    edit = _edit_of(root, "description")
    assert edit["value"] is None
    assert edit["before"] == "元の説明"


def test_history_limit(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """保持する回数は数字だけの入力で、補助文を持つ。整数を書いて離れたときに溜め、1 未満は溜めない（正常系）。"""
    # 準備
    page, root = _open_workspace(
        write_edit_preview, make_item, valid_settings, open_preview, history_limit=20
    )
    field = page.get_by_label("保持する回数", exact=True)
    assert field.get_attribute("inputmode") == "numeric"
    assert page.locator(f"{FIELD}[data-key='history_limit'] .pe-hint").inner_text() == (
        "変更履歴に残す書き換えのまとまりの数"
    )
    # 実行（1 未満）
    _commit(page, "保持する回数", "0")
    page.wait_for_timeout(500)
    # 検証（1 未満）
    assert not (root / RECORD_DIR / "edits.yaml").exists()
    # 実行
    _commit(page, "保持する回数", "50")
    _wait_edits(page, 1)
    # 検証
    assert _edit_of(root, "history_limit")["value"] == 50


def test_chips(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """プレイブックは値をチップで並べ、入力欄で足し、チップの × で外す。操作したときに溜める（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    group = page.get_by_role("group", name="プレイブック")
    assert group.locator(".pe-chip").all_inner_texts() == ["システム開発"]
    # 実行（足す）
    page.get_by_label("プレイブックを追加").fill("調査")
    page.get_by_label("プレイブックを追加").press("Enter")
    _wait_edits(page, 1)
    # 検証（足す）
    assert _edit_of(root, "playbooks")["value"] == ["システム開発", "調査"]
    # 実行（外す）
    page.get_by_role("button", name="システム開発 を外す").click()
    expect(page.locator(PENDING_BUTTON)).to_be_visible()
    page.wait_for_function(
        "() => document.querySelectorAll('.pe-ws [data-key=playbooks] .pe-chip').length === 1"
    )
    # 検証（外す）
    assert _edit_of(root, "playbooks")["value"] == ["調査"]


def test_goal(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """ゴールは届けるフェーズとゴールの中身を書き換え、納品物はタイトルを読むだけで並べる（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    goal = page.locator(f"{FIELD}[data-key='goal']")
    assert goal.locator("li").all_inner_texts() == ["YAML のスキーマ"]
    assert goal.locator("li input, li textarea").count() == 0
    # 実行
    page.get_by_label("届けるフェーズ").select_option("要件")
    _wait_edits(page, 1)
    _commit(page, "ゴールの中身", "作り始められる状態\n2 行目")
    expect(page.locator(f"{FIELD}[data-key='goal'] textarea")).to_have_value("作り始められる状態\n2 行目")
    page.wait_for_function(
        "() => document.querySelector('.pe-ws [data-key=goal] textarea').value.includes('2 行目')"
    )
    # 検証
    value = _edit_of(root, "goal")["value"]
    assert value["phase"] == "要件"
    assert value["summary"] == "作り始められる状態\n2 行目"
    assert [entry["title"] for entry in value["deliverables"]] == ["YAML のスキーマ"]


def test_tables(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """対象・カテゴリー・関連する場所は 1 行ずつの表で、行の削除と、表の下の「{呼び名}を追加」を持つ（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    targets = page.locator(f"{FIELD}[data-key='targets'] table")
    assert targets.locator("th[scope='col']").all_inner_texts() == ["名前", "説明"]
    categories = page.locator(f"{FIELD}[data-key='categories'] table")
    assert categories.locator("th[scope='col']").all_inner_texts() == ["名前", "対象", "説明"]
    assert page.locator(f"{FIELD}[data-key='links'] table").count() == 1
    # 実行（関連する場所を足す）
    page.get_by_role("button", name="関連する場所を追加").click()
    _wait_edits(page, 1)
    # 検証（関連する場所を足す）
    assert _edit_of(root, "links")["value"] == [{"title": "", "url": ""}]
    _commit(page, "1 行目の表示名", "仕様")
    page.wait_for_function(SAVED_LINK_JS, arg={"field": "title", "value": "仕様"})
    _commit(page, "1 行目のURL", "https://example.test/spec")
    page.wait_for_function(SAVED_LINK_JS, arg={"field": "url", "value": "https://example.test/spec"})
    expect(page.get_by_label("1 行目の表示名")).to_have_value("仕様")
    assert _edit_of(root, "links")["value"] == [{"title": "仕様", "url": "https://example.test/spec"}]
    # 実行（行を削除する。使われていない行は付け替えを聞かない）
    page.get_by_role("button", name="1 行目を削除").last.click()
    page.wait_for_function(
        "() => document.querySelectorAll('.pe-ws [data-key=links] tbody tr').length === 0"
    )
    # 検証（行を削除する）
    assert page.locator(f"{WS} .pe-move").count() == 0


def test_rename_target(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """対象の名前を書き換えると、古い名前 → 新しい名前の対応を自動で付け、付け替え先を聞かない（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    # 実行
    page.get_by_label("1 行目の名前").first.fill("mm")
    page.get_by_label("1 行目の名前").first.blur()
    _wait_edits(page, 1)
    # 検証
    edit = _edit_of(root, "targets")
    assert edit["map"] == {"mindmap": "mm"}
    assert edit["value"][0]["name"] == "mm"
    assert page.locator(f"{WS} .pe-move").count() == 0


def test_move_target_phase(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """項目が使っているフェーズを外すと、付け替え先を聞く。選ぶまでは溜めず、選んだときに対応つきで溜める（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    # 実行（外す）
    page.get_by_role("button", name="目的 を外す").click()
    page.wait_for_selector(f"{FIELD}[data-key='phases'] .pe-move")
    # 検証（外した直後は溜めない）
    move = page.locator(f"{FIELD}[data-key='phases'] .pe-move")
    assert move.locator("label").inner_text() == "目的 を使っている 1 件の付け替え先"
    assert move.locator("p.pe-hint").inner_text() == "付け替え先を選ぶと保存待ちに入ります。"
    assert move.locator("select option").all_inner_texts() == ["選んでください", "要件", "構成"]
    assert move.locator("select").input_value() == ""
    assert not (root / RECORD_DIR / "edits.yaml").exists()
    # 実行（選ぶ）
    move.locator("select").select_option("要件")
    _wait_edits(page, 1)
    # 検証（選ぶ）
    edit = _edit_of(root, "phases")
    assert edit["value"] == ["要件", "構成"]
    assert edit["map"] == {"目的": "要件"}
