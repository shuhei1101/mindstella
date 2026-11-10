"""部品設計『コメントの入力.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
import pytest
from .storybook_react_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 溜めている印と文言が出るまで待つ上限ミリ秒（部品は 1 秒を超えたら出す）
SAVING_NOTICE_TIMEOUT_MS = 3_000

# 入力欄の始めの高さの行数
MIN_ROWS = 1

# 入力欄の最大の高さの行数（これを超えたら入力欄の中を送る）
MAX_ROWS = 8

# 選んだ文を出す行数の上限（超えたら末尾を省く）
QUOTE_MAX_LINES = 3

# 入力欄の上下の余白と枠の合計（ピクセル）
TEXTAREA_PADDING_PX = 18

# 畳んだ入力欄の高さを 1 行の入力の高さと比べるときに許す誤差（ピクセル。小数の丸め）
HEIGHT_TOLERANCE_PX = 1

# 入力欄の高さと、行の高さ・中身の高さを読む
TEXTAREA_SIZES_SCRIPT = """e => ({
  height: e.clientHeight,
  lineHeight: parseFloat(getComputedStyle(e).lineHeight),
  scrollHeight: e.scrollHeight,
})"""

# 入力欄の枠を含む高さと、1 行の入力の高さ（`--control-h`）の実際の値を読む
BORDER_BOX_HEIGHT_SCRIPT = "e => e.getBoundingClientRect().height"
CONTROL_HEIGHT_SCRIPT = """(() => {
  const probe = document.createElement('i');
  probe.style.display = 'block';
  probe.style.height = 'var(--control-h)';
  document.body.append(probe);
  const height = probe.getBoundingClientRect().height;
  probe.remove();
  return height;
})()"""

# 選んだ文の行数の上限の指定と、出している高さ・省かないときの高さを読む
QUOTE_SIZES_SCRIPT = """e => {
  const style = getComputedStyle(e);
  const shown = { clamp: style.webkitLineClamp, overflow: style.overflow, height: e.clientHeight, lineHeight: parseFloat(style.lineHeight) };
  e.style.webkitLineClamp = 'none';
  const fullHeight = e.clientHeight;
  e.style.webkitLineClamp = '';
  return { ...shown, fullHeight };
}"""

# 要見直しの赤（`--st-review`）の実際の色を読む
REVIEW_COLOR_SCRIPT = """(() => {
  const probe = document.createElement('i');
  probe.style.color = 'var(--st-review)';
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
})()"""


# 入力欄と「レビューに追加」の位置（同じ行で、ボタンは入力欄の右・下端を合わせる）を読む
LINE_GEOMETRY_SCRIPT = """() => {
  const field = document.querySelector('textarea').getBoundingClientRect();
  const button = document.querySelector('button[aria-label="レビューに追加"]').getBoundingClientRect();
  return { fieldRight: field.right, fieldBottom: field.bottom, buttonLeft: button.left, buttonBottom: button.bottom };
}"""

# 位置を比べるときに許す誤差（ピクセル。小数の丸め）
POSITION_TOLERANCE_PX = 1


def assert_submit_beside_field(page: Page) -> None:
    """「レビューに追加」が文字を持たず、入力欄の右の同じ行で下端を合わせて置かれている。"""
    button = page.get_by_role("button", name="レビューに追加")
    assert button.inner_text().strip() == ""
    assert button.get_attribute("title") == "レビューに追加（Ctrl+Enter）"
    geometry = page.evaluate(LINE_GEOMETRY_SCRIPT)
    assert geometry["buttonLeft"] >= geometry["fieldRight"] - POSITION_TOLERANCE_PX
    assert abs(geometry["buttonBottom"] - geometry["fieldBottom"]) <= POSITION_TOLERANCE_PX

def test_idle(open_story: OpenStory) -> None:
    """入力欄が空。本文と線で区切って下端に置き、ラベル「{ID} へのコメント」を常に見せる（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--idle")
    # 検証
    assert page.inner_text("form label") == "D-022 へのコメント"
    assert page.get_attribute("form label", "for") == page.get_attribute("textarea", "id")
    assert page.input_value("textarea") == ""
    assert page.inner_text("form [role=status]") == ""
    assert page.get_attribute("form [role=status]", "role") == "status"
    assert page.get_attribute("textarea", "aria-describedby") == page.get_attribute(
        "form [role=status]", "id"
    )
    assert page.get_by_role("button", name="レビューに追加").is_enabled()
    assert_submit_beside_field(page)
    toggle = page.get_by_role("button", name="コメントの入力を閉じる")
    assert toggle.get_attribute("aria-expanded") == "true"
    assert (
        page.get_attribute(f"#{toggle.get_attribute('aria-controls')}", "id")
        == toggle.get_attribute("aria-controls")
    )
    assert (
        page.eval_on_selector("form", "e => getComputedStyle(e).borderTopWidth")
        == "1px"
    )
    # 空の入力欄は 1 行分の高さ
    sizes = page.eval_on_selector("textarea", TEXTAREA_SIZES_SCRIPT)
    assert sizes["lineHeight"] * MIN_ROWS <= sizes["height"]
    assert sizes["height"] <= sizes["lineHeight"] * MIN_ROWS + TEXTAREA_PADDING_PX


def test_typing(open_story: OpenStory) -> None:
    """入力中。入力欄に印の色の輪を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--typing")
    page.wait_for_function(
        "document.activeElement && document.activeElement.tagName === 'TEXTAREA'"
    )
    # 検証
    assert page.input_value("textarea") == "案 A にする"
    assert page.eval_on_selector("textarea", "e => getComputedStyle(e).outlineStyle") == "solid"
    assert page.inner_text("form [role=status]") == ""


def test_with_body_location(open_story: OpenStory) -> None:
    """本文の箇所を添えた。入力欄の上に「本文 3 行目」と選んだ文を出し、× で外せる（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--with-body-location")
    # 検証
    assert page.inner_text("form label") == "A-005 へのコメント"
    assert page.inner_text("[id$='-loc'] span") == "本文 3 行目"
    assert page.inner_text("[id$='-loc'] blockquote") == "受け取る人へ渡す形"
    assert page.get_by_role("button", name="箇所を外す").count() == 1
    # 添えた箇所は入力欄の説明として、結果の前に指す
    loc_id = page.get_attribute("[id$='-loc']", "id")
    message_id = page.get_attribute("form [role=status]", "id")
    assert page.get_attribute("textarea", "aria-describedby") == f"{loc_id} {message_id}"
    # 箇所は入力欄より上に出る
    loc_box = page.locator("[id$='-loc']").bounding_box()
    field_box = page.locator("textarea").bounding_box()
    assert loc_box is not None
    assert field_box is not None
    assert loc_box["y"] + loc_box["height"] <= field_box["y"]


def test_with_value_location(open_story: OpenStory) -> None:
    """値の箇所を添えた。箇所の名前にキーの名前を出し、選んだ文は 3 行までにして末尾を省く（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--with-value-location")
    # 選んだ文が 3 行を超える幅にする
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 検証
    assert page.inner_text("[id$='-loc'] span") == "案 C のデメリット"
    assert page.input_value("textarea") == "ここは別の言い方にしたい"
    quote = page.eval_on_selector("[id$='-loc'] blockquote", QUOTE_SIZES_SCRIPT)
    assert quote["clamp"] == str(QUOTE_MAX_LINES)
    assert quote["overflow"] == "hidden"
    # 省かなければ 3 行を超える長さで、出している高さは 3 行分まで
    assert quote["fullHeight"] > quote["lineHeight"] * QUOTE_MAX_LINES
    assert quote["height"] <= quote["lineHeight"] * QUOTE_MAX_LINES + 1


def test_saving(open_story: OpenStory) -> None:
    """溜めている。入力欄を書き換えられなくし、ボタンを押せなくする。1 秒を超えたら回る印と文言を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--saving")
    # 検証
    assert page.get_by_role("button", name="レビューに追加").is_disabled()
    assert page.get_attribute("textarea", "readonly") is not None
    page.wait_for_selector("form [role=status] svg.animate-spin", timeout=SAVING_NOTICE_TIMEOUT_MS)
    assert page.inner_text("form [role=status]") == "レビューに追加しています"


def test_saved(open_story: OpenStory) -> None:
    """溜めた。入力欄を空にし、「レビューに追加しました（レビュー中 3 件）。」を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--saved")
    # 検証
    assert page.input_value("textarea") == ""
    assert page.inner_text("form [role=status]") == "レビューに追加しました（レビュー中 3 件）。"
    assert page.locator("form [role=status] svg").count() == 1
    assert page.get_attribute("textarea", "aria-invalid") is None


def test_empty(open_story: OpenStory) -> None:
    """本文が空で溜めようとした。入力欄の枠と印を要見直しの赤にし、入れてから追加するよう出す。ボタンは押せるまま（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--empty")
    # 検証
    assert page.inner_text("form [role=status]") == "コメントを入れてから追加してください。"
    assert page.get_attribute("textarea", "aria-invalid") == "true"
    assert page.locator("form [role=status] svg").count() == 1
    assert page.get_by_role("button", name="レビューに追加").is_enabled()
    review = page.evaluate(REVIEW_COLOR_SCRIPT)
    border = page.eval_on_selector("textarea", "e => getComputedStyle(e).borderTopColor")
    icon = page.eval_on_selector("form [role=status] svg", "e => getComputedStyle(e).color")
    assert border == review
    assert icon == review
    # 文言は本文の文字色で出す（赤にしない）
    message_color = page.eval_on_selector("form [role=status]", "e => getComputedStyle(e).color")
    text_color = page.eval_on_selector("textarea", "e => getComputedStyle(e).color")
    assert message_color == text_color


def test_failed_unreachable(open_story: OpenStory) -> None:
    """サーバーに届かなかった。本文を残し、立ち上げ直して新しい URL で開くよう出して、本文のコピーのボタンを添える（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--failed-unreachable")
    # 検証
    assert page.input_value("textarea") == "案 A にする"
    message = page.inner_text("form [role=status]")
    assert "レビューに追加できませんでした。サーバーが止まっています。" in message
    assert "起動スクリプトで立ち上げ直し" in message
    assert "示された新しい URL で開いてから追加してください。" in message
    copy = page.get_by_role("button", name="本文をコピー")
    assert copy.count() == 1
    assert copy.inner_text().strip() == ""
    assert copy.get_attribute("title") == "本文をコピー"
    assert page.locator("form [role=status] svg").count() >= 1


def test_failed_detail(open_story: OpenStory) -> None:
    """サーバーが溜めなかった理由を返した。本文を残し、理由を出す。本文のコピーのボタンは出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--failed-detail")
    # 検証
    assert page.input_value("textarea") == "ここは言い換える"
    assert (
        page.inner_text("form [role=status]")
        == "レビューに追加できませんでした。選んだ文が本文の 3 行目にありません"
    )
    assert page.get_by_role("button", name="本文をコピー").count() == 0


def test_long(open_story: OpenStory) -> None:
    """長文。8 行を超えたら、入力欄の中を送る。「レビューに追加」は入力欄の下端に合わせる（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--long")
    # 検証
    sizes = page.eval_on_selector("textarea", TEXTAREA_SIZES_SCRIPT)
    assert sizes["scrollHeight"] > sizes["height"]
    # 入力欄の高さは 8 行分と上下の余白までで止まる
    assert sizes["lineHeight"] * MAX_ROWS <= sizes["height"]
    assert sizes["height"] <= sizes["lineHeight"] * MAX_ROWS + TEXTAREA_PADDING_PX
    assert_submit_beside_field(page)


def test_no_target(open_story: OpenStory) -> None:
    """項目を指さないコメント。見出しを出さず、入力欄と「レビューに追加」だけにする。名前は読み上げにだけ持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--no-target")
    # 検証
    assert page.locator("form label").count() == 0
    assert page.locator("[id$='-loc']").count() == 0
    assert page.get_attribute("textarea", "aria-label") == "項目を指さないコメント"
    assert page.get_by_role("button", name="レビューに追加").is_enabled()


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。部品の幅によらず入力欄と「レビューに追加」を 1 行に並べ、結果は入力欄の下に幅いっぱいで出す（正常系）。"""
    # 準備
    page = open_story("shared-sendform--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    form = page.locator("form").bounding_box()
    button = page.get_by_role("button", name="レビューに追加").bounding_box()
    message = page.locator("form [role=status]").bounding_box()
    assert form is not None
    assert button is not None
    assert message is not None
    assert form["width"] <= 390
    # ボタンは入力欄の右の同じ行で右端、結果は入力欄の下の行で幅いっぱい
    assert_submit_beside_field(page)
    assert button["x"] + button["width"] >= form["x"] + form["width"] - 16 - 1
    assert message["y"] >= button["y"] + button["height"] - 1
    assert message["width"] >= form["width"] - 2 * 16 - 2
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_no_target_collapsed(open_story: OpenStory) -> None:
    """項目を指さないコメントを畳んだ形。読み上げのラベルと 1 行の入力欄だけを出し、結果とボタンを出さない（正常系）。"""
    # 準備
    page = open_story("shared-sendform--no-target-collapsed")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert page.get_attribute("textarea", "aria-label") == "項目を指さないコメント"
    assert page.get_attribute("textarea", "rows") == "1"
    assert page.locator("form [role=status]").count() == 0
    assert page.get_by_role("button", name="レビューに追加").count() == 0
    assert page.locator("form[data-collapsed]").count() == 1
    # 畳んだ入力欄は 1 行の入力の高さ（`--control-h`）のまま
    height = page.eval_on_selector("textarea", BORDER_BOX_HEIGHT_SCRIPT)
    assert height == pytest.approx(page.evaluate(CONTROL_HEIGHT_SCRIPT), abs=HEIGHT_TOLERANCE_PX)


def test_no_target_expanded(open_story: OpenStory) -> None:
    """項目を指さないコメントを狭い幅で広げた形。入力欄と「レビューに追加」を出す（正常系）。"""
    # 準備
    page = open_story("shared-sendform--no-target-expanded")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert page.input_value("textarea") == "全体に目を通した"
    assert page.get_attribute("textarea", "rows") == "1"
    assert page.get_by_role("button", name="レビューに追加").is_visible()
    assert page.locator("form[data-collapsed]").count() == 0


def test_closed(open_story: OpenStory) -> None:
    """閉じた。「{ID} へのコメント」の 1 行と、右端の ^ の開閉のボタンだけを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--closed")
    # 検証
    toggle = page.get_by_role("button", name="コメントの入力を開く")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert toggle.get_attribute("title") == "コメントの入力を開く"
    assert "D-022 へのコメント" in page.inner_text("form")
    assert "書きかけ" not in page.inner_text("form")
    assert not page.locator("textarea").is_visible()
    assert not page.locator('button[aria-label="レビューに追加"]').is_visible()
    body = page.locator(f"#{toggle.get_attribute('aria-controls')}")
    assert body.count() == 1
    assert not body.is_visible()


def test_closed_with_draft(open_story: OpenStory) -> None:
    """書きかけを残して閉じた。「{ID} へのコメント」の右に鉛筆の印と「書きかけ」を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--closed-with-draft")
    # 検証
    assert "書きかけ" in page.inner_text("form")
    toggle = page.get_by_role("button", name="コメントの入力を開く")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert not page.locator("textarea").is_visible()


# 音声入力の結果の行（録音中・文字起こし中・送信・挿入・失敗）を読む場所
VOICE_MESSAGE = "form [role=status]"

# 最も狭い幅（Storybook の画面幅を 320px にしたときの幅と高さ）
NARROWEST_WIDTH = 320
NARROWEST_HEIGHT = 640

# 録音中の 2 つのボタンの位置と大きさを読む
RECORDING_GEOMETRY_SCRIPT = """() => {
  const field = document.querySelector('textarea').getBoundingClientRect();
  const cancel = document.querySelector('button[aria-label="キャンセル"]').getBoundingClientRect();
  const done = document.querySelector('button[aria-label="文字起こし"]').getBoundingClientRect();
  return {
    fieldRight: field.right, fieldBottom: field.bottom,
    cancelLeft: cancel.left, cancelRight: cancel.right, cancelBottom: cancel.bottom, cancelWidth: cancel.width, cancelHeight: cancel.height,
    doneLeft: done.left, doneRight: done.right, doneWidth: done.width, doneHeight: done.height,
  };
}"""


def assert_recording_buttons(page: Page) -> None:
    """マイクと「レビューに追加」の位置に、アイコンだけの × の「キャンセル」と ✓ の「文字起こし」を置いている。"""
    cancel = page.get_by_role("button", name="キャンセル")
    done = page.get_by_role("button", name="文字起こし", exact=True)
    assert cancel.get_attribute("title") == "キャンセル（録音を破棄）"
    assert done.get_attribute("title") == "文字起こし"
    assert cancel.inner_text().strip() == ""
    assert done.inner_text().strip() == ""
    assert cancel.is_enabled()
    assert done.is_enabled()
    assert page.get_by_role("button", name="音声で入力").count() == 0
    assert page.get_by_role("button", name="レビューに追加").count() == 0
    geometry = page.evaluate(RECORDING_GEOMETRY_SCRIPT)
    assert geometry["cancelLeft"] >= geometry["fieldRight"] - POSITION_TOLERANCE_PX
    assert geometry["doneLeft"] >= geometry["cancelRight"] - POSITION_TOLERANCE_PX
    assert abs(geometry["cancelBottom"] - geometry["fieldBottom"]) <= POSITION_TOLERANCE_PX
    assert (geometry["cancelWidth"], geometry["cancelHeight"]) == (geometry["doneWidth"], geometry["doneHeight"])


def assert_mic_blocked(page: Page, reason: str) -> None:
    """マイクのボタンを押せない見た目にし、フォーカスは受けたまま理由をツールチップと読み上げの説明に出す。「レビューに追加」は押せるまま。"""
    mic = page.get_by_role("button", name="音声で入力")
    assert mic.get_attribute("aria-disabled") == "true"
    assert mic.get_attribute("disabled") is None
    assert mic.get_attribute("title") == reason
    assert page.text_content(f"#{mic.get_attribute('aria-describedby')}") == reason
    mic.focus()
    assert page.evaluate("document.activeElement.getAttribute('aria-label')") == "音声で入力"
    assert page.get_by_role("button", name="レビューに追加").is_enabled()


def assert_mic_ready(page: Page) -> None:
    """元のボタン（マイクと「レビューに追加」）に戻っている。"""
    mic = page.get_by_role("button", name="音声で入力")
    assert mic.get_attribute("aria-disabled") is None
    assert mic.get_attribute("title") == "音声で入力"
    assert page.get_by_role("button", name="レビューに追加").is_enabled()


def test_recording(open_story: OpenStory) -> None:
    """録音中。マイクと「レビューに追加」の位置に × の「キャンセル」と ✓ の「文字起こし」を置き、結果の行に失敗の色の丸と経過の時間だけを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--recording")
    # 検証
    assert_recording_buttons(page)
    assert "0:12" in page.inner_text(VOICE_MESSAGE)
    assert "録音中" in (page.text_content(VOICE_MESSAGE) or "")
    assert page.input_value("textarea") == ""


def test_transcribing(open_story: OpenStory) -> None:
    """文字起こし中。2 つのボタンを押せなくし、✓ の位置と結果の行に回る印だけを出す。入力欄は読み取りだけ（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--transcribing")
    # 検証
    assert page.get_by_role("button", name="キャンセル").is_disabled()
    busy = page.get_by_role("button", name="文字起こし中")
    assert busy.is_disabled()
    assert page.get_attribute("textarea", "readonly") is not None
    assert page.input_value("textarea") == "確認: "
    assert "文字起こししています。" in (page.text_content(VOICE_MESSAGE) or "")


def test_recording_with_draft(open_story: OpenStory) -> None:
    """打ちかけがある録音中。入力欄の「確認: 」とカーソルの位置を残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--recording-with-draft")
    # 検証
    assert_recording_buttons(page)
    assert page.input_value("textarea") == "確認: "


def test_sent(open_story: OpenStory) -> None:
    """送信した。入力欄を空にし、元のボタンに戻して「送信し、Claude Code へ入力しました。」（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--sent")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "送信し、Claude Code へ入力しました。"
    assert page.input_value("textarea") == ""
    assert_mic_ready(page)


def test_sent_not_entered(open_story: OpenStory) -> None:
    """送信したが Claude Code へ入力しなかった。「送信しました。Claude Code へは入力していません。」（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--sent-not-entered")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "送信しました。Claude Code へは入力していません。"


def test_inserted(open_story: OpenStory) -> None:
    """入力欄へ挿入した。「文字起こしの結果を挿入しました。」（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--inserted")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "文字起こしの結果を挿入しました。"
    assert page.input_value("textarea") == "確認: 案 A にする"
    assert_mic_ready(page)


def test_voice_disabled(open_story: OpenStory) -> None:
    """文字起こしのサービスが起動していない。マイクのボタンを押せない見た目にし、理由のツールチップを出す。「レビューに追加」は押せるまま（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--voice-disabled")
    # 検証
    assert_mic_blocked(page, "文字起こしのサービスが起動していないため、音声で入力できません。")


def test_voice_unsupported(open_story: OpenStory) -> None:
    """文字起こしのサービスが音声の受け付けに対応していない。押せない理由のツールチップ（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--voice-unsupported")
    # 検証
    assert_mic_blocked(page, "文字起こしのサービスが音声の受け付けに対応していないため、音声で入力できません。")


def test_voice_no_microphone(open_story: OpenStory) -> None:
    """ブラウザがマイクを使えない。押せない理由のツールチップ（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--voice-no-microphone")
    # 検証
    assert_mic_blocked(page, "このページではマイクを使用できません。HTTPS か localhost の URL で開いてください。")


def test_voice_failed(open_story: OpenStory) -> None:
    """文字起こしに失敗した。入力欄の中身を残し、元のボタンに戻して理由を結果の行に出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--voice-failed")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "文字起こしできませんでした。もう一度お試しください。"
    assert page.input_value("textarea") == "案 B も見たい"
    assert_mic_ready(page)


def test_voice_denied(open_story: OpenStory) -> None:
    """マイクの許可を拒否した。録音を始めず、許可が要ることを結果の行に出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--voice-denied")
    # 検証
    assert (
        page.inner_text(VOICE_MESSAGE).strip()
        == "マイクを使用できませんでした。ブラウザの設定でこのページのマイクを許可してください。"
    )
    assert_mic_ready(page)


def test_voice_send_failed(open_story: OpenStory) -> None:
    """文字起こしはできたが送信できなかった。挿入した全文を入力欄に残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--voice-send-failed")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "送信できませんでした。文字起こしの結果は入力欄に残しています。"
    assert page.input_value("textarea") == "確認: 案 A にする"


def test_recording_narrow(open_story: OpenStory) -> None:
    """最も狭い幅（320px）の録音中。2 つのボタンは同じ大きさで、入力欄の右に並んだまま収まる（正常系）。"""
    # 準備・実行
    page = open_story("shared-sendform--recording-narrow")
    page.set_viewport_size({"width": NARROWEST_WIDTH, "height": NARROWEST_HEIGHT})
    page.wait_for_function(f"innerWidth === {NARROWEST_WIDTH}")
    # 検証
    assert_recording_buttons(page)
    form = page.locator("form").bounding_box()
    assert form is not None
    assert form["width"] <= NARROWEST_WIDTH
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
