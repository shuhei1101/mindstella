"""画面設計『設定の画面.tsx』の結合テスト。"""

from __future__ import annotations

import re

from preview_edit_helpers import wait_edits_match
from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import wait_transcription_status

from typing import Any

import pytest
from playwright.sync_api import Page, expect
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeEdit, MakeItem


def test_title_is_stored(page: Page, spa_preview: str) -> None:
    """題名を書き換えると保存待ちに溜まる（正常系）。"""
    open_spa(page, spa_preview, "?tab=settings")
    title = page.get_by_role("textbox", name="題名")
    title.fill("画面の編集")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    expect(page.get_by_role("complementary", name="保存待ちの編集")).to_contain_text("画面の編集")


def test_close_returns_to_overview(page: Page, spa_preview: str) -> None:
    """閉じると概要へ戻る（正常系）。"""
    open_spa(page, spa_preview, "?tab=settings")
    page.get_by_role("button", name="閉じる").click()
    expect(page.locator("#tile-next")).to_be_visible()


# ─── 画面設計の要素の確認項目 ───


def test_heading_label(page: Page, spa_preview: str) -> None:
    """画面の見出しは「設定」で、開いたときに見出しへフォーカスを移す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=settings")
    heading = page.get_by_role("heading", level=1)
    # 検証
    expect(heading).to_have_text("設定")
    expect(heading).to_be_focused()


def test_close_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """閉じるの文言は「閉じる」で、開く前の画面（保存待ちのパネルから開いたタスク）に戻り、溜めた編集は保存待ちに残る（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("T-1"), edits=(make_edit("E-1", target="settings", op="setting", key="summary", value="画面の編集", before="要件出しのスキル mindmap を設計する"),))
    open_spa(page, url, "?tab=tasks&panel=pending")
    page.get_by_role("complementary", name="保存待ちの編集").get_by_role("button", name="を開く").click()
    close = page.get_by_role("button", name="閉じる", exact=True)
    expect(page.get_by_role("heading", name="設定", level=1)).to_be_visible()
    # 実行
    expect(close).to_have_text("閉じる")
    close.click()
    # 検証
    expect(page.get_by_role("link", name="タスク")).to_have_attribute("aria-current", "page")
    expect(page.get_by_role("button", name="保存待ち").first).to_contain_text("1")


def test_title_and_label_label(page: Page, spa_preview: str) -> None:
    """題名・最上位の軸の呼び名は、それぞれ「題名」「最上位の軸の呼び名」の 1 行の入力（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=settings")
    # 検証
    expect(page.get_by_role("textbox", name="題名")).to_have_attribute("type", "text")
    expect(page.get_by_role("textbox", name="最上位の軸の呼び名")).to_have_attribute("type", "text")


def test_playbooks_and_phases_label(page: Page, spa_preview: str) -> None:
    """プレイブック・フェーズは「プレイブック」「フェーズ」の名前で、値をチップで並べ、入力欄で足す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=settings")
    # 検証
    expect(page.get_by_role("group", name="プレイブック")).to_be_visible()
    expect(page.get_by_role("group", name="フェーズ")).to_be_visible()
    expect(page.get_by_role("combobox", name="フェーズを追加")).to_be_visible()
    expect(page.get_by_role("group", name="フェーズ").get_by_role("button", name="を外す").first).to_be_visible()


def test_goal_label(page: Page, spa_preview: str) -> None:
    """ゴールは「ゴール」の名前で、届けるフェーズ・ゴールの中身・納品物を並べる（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=settings")
    goal = page.locator("[data-key=goal]")
    # 検証
    expect(goal).to_contain_text("ゴール")
    expect(goal.get_by_role("combobox", name="届けるフェーズ")).to_be_visible()
    expect(goal.get_by_role("textbox", name="ゴールの中身")).to_be_visible()
    expect(goal).to_contain_text("納品物")


@pytest.mark.parametrize(("key", "label"), [("targets", "対象"), ("categories", "カテゴリー"), ("links", "関連する場所")])
def test_table_label(page: Page, spa_preview: str, key: str, label: str) -> None:
    """対象・カテゴリー・関連する場所は、その名前の表と「{呼び名}を追加」を並べ、狭い幅でも画面を横に送らない（正常系）。"""
    # 準備・実行
    page.set_viewport_size({"width": 390, "height": 844})
    open_spa(page, spa_preview, "?tab=settings")
    # 検証
    expect(page.get_by_role("table", name=label)).to_be_visible()
    expect(page.locator(f"[data-key={key}]").get_by_role("button", name=f"{label}を追加")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_history_limit_label(page: Page, spa_preview: str) -> None:
    """保持する回数は「保持する回数」の数の入力（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=settings")
    # 検証
    expect(page.get_by_role("spinbutton", name="保持する回数")).to_be_visible()


def test_description_label(page: Page, spa_preview: str) -> None:
    """説明は「説明」の何行も書く欄で、空にして離れると説明を消す編集を溜める（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=settings")
    description = page.get_by_role("textbox", name="説明", exact=True)
    # 実行
    expect(description).to_have_js_property("tagName", "TEXTAREA")
    description.fill("話し合いの説明")
    description.blur()
    # 検証
    expect(page.locator("[data-key=description] [title=保存待ち]")).to_have_count(1)


def test_move_target_label(page: Page, write_preview: WritePreview, make_item: MakeItem, valid_settings: dict[str, Any]) -> None:
    """使っているフェーズを外すと「{値} を使っている {n} 件の付け替え先」を出し、選ぶまでは溜めない（正常系）。"""
    # 準備
    settings = {**valid_settings, "phases": ["目的", "要件", "構成"]}
    url = write_preview(make_item("D-1", phase="要件"), make_item("D-2", phase="要件"), settings=settings)
    open_spa(page, url, "?tab=settings")
    # 実行
    page.get_by_role("group", name="フェーズ").get_by_role("button", name="要件 を外す").click()
    # 検証
    expect(page.get_by_role("combobox", name="要件 を使っている 2 件の付け替え先")).to_be_visible()
    expect(page.get_by_text("付け替え先を選ぶと保存待ちに入ります。")).to_be_visible()
    expect(page.locator("[data-key=phases] [title=保存待ち]")).to_have_count(0)


def test_move_target_visible(page: Page, write_preview: WritePreview, make_item: MakeItem, valid_settings: dict[str, Any]) -> None:
    """使われていない値を外したときは付け替え先を出さずに溜める（正常系）。"""
    # 準備
    settings = {**valid_settings, "phases": ["目的", "要件", "構成"]}
    url = write_preview(make_item("D-1", phase="要件"), settings=settings)
    open_spa(page, url, "?tab=settings")
    # 実行
    page.get_by_role("group", name="フェーズ").get_by_role("button", name="構成 を外す").click()
    # 検証
    expect(page.get_by_text("付け替え先を選ぶと保存待ちに入ります。")).to_have_count(0)
    expect(page.locator("[data-key=phases] [title=保存待ち]")).to_have_count(1)


# 保存待ちの編集に、文字起こしの設定の編集が溜まったか（arg は action と preset）
TRANSCRIPTION_EDIT_MATCH_JS = (
    "(items, arg) => items.some(e => e.key === 'transcription'"
    " && e.value.action === arg.action && e.value.preset === arg.preset)"
)

# 用語集のプリセットの下のヒント
PRESET_HINT = "#pe-ws-transcription-preset-hint"


def _open_voice_settings(
    page: Page, start_voice_preview: _StartVoicePreview, transcriber_url: str, settings: dict[str, Any]
) -> None:
    """文字起こしのサービスの URL を渡して配信し、文字起こしの可否を取得し終えた設定の画面を開く。"""
    url, _ = start_voice_preview(transcriber_url, settings=settings)
    with wait_transcription_status(page):
        open_spa(page, url, "?tab=settings")


def test_transcription(
    page: Page,
    start_voice_preview: _StartVoicePreview,
    start_fake_transcriber: Any,
    valid_settings: dict[str, Any],
) -> None:
    """文字起こし後の挙動と用語集のプリセットを選ぶと、もう一方の値を保った transcription を 1 件溜める。挙動を持たない設定では既定の「レビュー中に追加する」を選び、選択肢は「レビュー中に追加する」「入力欄へ挿入する」「送信する」の順。候補は文字起こしの可否の presets（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    _open_voice_settings(
        page, start_voice_preview, fake.url, {**valid_settings, "transcription": {"preset": "開発"}}
    )
    preset = page.get_by_label("用語集のプリセット", exact=True)
    # 検証（今の値と候補）
    expect(page.get_by_role("group", name="音声入力")).to_be_visible()
    expect(page.get_by_role("radio", name="レビュー中に追加する")).to_be_checked()
    radios = page.get_by_role("radio", name=re.compile("^(レビュー中に追加する|入力欄へ挿入する|送信する)$"))
    assert [radios.nth(i).get_attribute("value") for i in range(radios.count())] == ["review", "insert", "send"]
    expect(preset).to_have_value("開発")
    expect(preset.locator("option")).to_have_text(["サービスの既定", "一般", "開発"])
    expect(page.locator(PRESET_HINT)).to_have_text("文字起こしの補正に使用する用語集です。候補は文字起こしのサービスから取得します。")
    # 実行（文字起こし後の挙動）
    page.get_by_role("radio", name="送信する").check()
    # 検証
    wait_edits_match(page, TRANSCRIPTION_EDIT_MATCH_JS, {"action": "send", "preset": "開発"})
    # 実行（用語集のプリセット）
    preset.select_option("一般")
    # 検証
    wait_edits_match(page, TRANSCRIPTION_EDIT_MATCH_JS, {"action": "send", "preset": "一般"})


def test_transcription_when_service_stopped(
    page: Page,
    start_voice_preview: _StartVoicePreview,
    unreachable_transcriber_url: str,
    valid_settings: dict[str, Any],
) -> None:
    """文字起こしのサービスが使えないときは、用語集のプリセットを今の値だけにして押せなくし、理由の文を出す。文字起こし後の挙動は書き換えられるまま（正常系）。"""
    # 準備・実行
    _open_voice_settings(
        page,
        start_voice_preview,
        unreachable_transcriber_url,
        {**valid_settings, "transcription": {"action": "send", "preset": "開発"}},
    )
    # 検証
    preset = page.get_by_label("用語集のプリセット", exact=True)
    expect(preset).to_be_disabled()
    assert preset.locator("option").all_inner_texts() == ["開発"]
    expect(page.locator(PRESET_HINT)).to_have_text(
        "文字起こしのサービスが起動していないため、候補を取得できません。サービスを起動してから設定の画面を開き直してください。"
    )
    expect(page.get_by_role("radio", name="入力欄へ挿入する")).to_be_enabled()
