"""部品設計『返信の入力』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 入力欄の始めの高さの行数
MIN_ROWS = 1

# 入力欄の最大の高さの行数（これを超えたら入力欄の中を送る）
MAX_ROWS = 8

# 入力欄の上下の余白と枠の合計（ピクセル）
TEXTAREA_PADDING_PX = 18

# 入力欄の高さと、行の高さ・中身の高さを読む
TEXTAREA_SIZES_SCRIPT = """e => ({
  height: e.clientHeight,
  lineHeight: parseFloat(getComputedStyle(e).lineHeight),
  scrollHeight: e.scrollHeight,
})"""

SEND = "button[data-focus='reply-send']"
MESSAGE = ".send-msg"


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

def test_empty(open_story: OpenStory) -> None:
    """入力欄が空。ラベル「返信」を常に見せ、「レビューに追加」を押せなくする（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--empty")
    # 検証
    assert page.inner_text("label.send-label") == "返信"
    assert page.get_attribute("label.send-label", "for") == page.get_attribute("textarea", "id")
    assert page.input_value("textarea") == ""
    assert page.get_attribute("textarea", "rows") == "1"
    # 空の入力欄は 1 行分の高さ
    sizes = page.eval_on_selector("textarea", TEXTAREA_SIZES_SCRIPT)
    assert sizes["lineHeight"] * MIN_ROWS <= sizes["height"]
    assert sizes["height"] <= sizes["lineHeight"] * MIN_ROWS + TEXTAREA_PADDING_PX
    assert page.get_attribute("textarea", "aria-keyshortcuts") == "Control+Enter"
    assert page.get_attribute("textarea", "aria-describedby") == page.get_attribute(MESSAGE, "id")
    assert page.get_attribute(MESSAGE, "role") == "status"
    assert page.inner_text(MESSAGE) == ""
    assert page.get_attribute(SEND, "title") == "レビューに追加（Ctrl+Enter）"
    assert page.get_attribute(SEND, "aria-label") == "レビューに追加"
    assert page.inner_text(SEND).strip() == ""
    assert page.is_disabled(SEND)
    assert_submit_beside_field(page)


def test_typing(open_story: OpenStory) -> None:
    """入力中。入力欄に印の色の輪を出し、「レビューに追加」を押せる（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--typing")
    # 検証
    assert page.input_value("textarea") == "起票してよい。題は「版の範囲から当てる手順を返すコマンド」に縮めてほしい"
    assert page.is_enabled(SEND)
    page.focus("textarea")
    assert page.eval_on_selector("textarea", "e => getComputedStyle(e).outlineStyle") == "solid"


def test_saving(open_story: OpenStory) -> None:
    """溜めている。入力欄を読み取りだけにし、「レビューに追加」を押せなくする。回る印と「レビューに追加しています」を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--saving")
    # 検証
    assert page.get_attribute("textarea", "readonly") is not None
    assert page.is_disabled(SEND)
    assert page.inner_text(MESSAGE) == "レビューに追加しています"
    assert page.locator(f"{MESSAGE} .spinner").count() == 1


def test_saved(open_story: OpenStory) -> None:
    """溜めた。入力欄を空にし、「レビューに追加しました（レビュー中 3 件）。」を出す。入力を始めたら消す（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--saved")
    # 検証
    assert page.input_value("textarea") == ""
    assert page.inner_text(MESSAGE) == "レビューに追加しました（レビュー中 3 件）。"
    assert page.locator(f"{MESSAGE} svg.icon").count() == 1


def test_failed_unreachable(open_story: OpenStory) -> None:
    """サーバーに届かなかった。本文を残し、印のアイコンと立ち上げ直しの案内を出す（異常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--failed-unreachable")
    # 検証
    assert page.input_value("textarea") == "起票してよい"
    assert (
        page.inner_text(MESSAGE)
        == "レビューに追加できませんでした。サーバーが止まっています。立ち上げ直してから追加してください。"
    )
    assert page.locator(f"{MESSAGE} svg.icon").count() == 1


def test_failed_detail(open_story: OpenStory) -> None:
    """サーバーが溜めなかった理由を返した。本文を残し、理由を続けて出す（異常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--failed-detail")
    # 検証
    assert page.input_value("textarea") == "version は文字列で持つ？"
    assert page.inner_text(MESSAGE) == "レビューに追加できませんでした。スレッド TH-5 はクローズです"


def test_long(open_story: OpenStory) -> None:
    """長文。入力欄は 8 行まで広がり、それより長いと中でスクロールする。「レビューに追加」は入力欄の下端に合わせる（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--long")
    # 検証
    sizes = page.eval_on_selector("textarea", TEXTAREA_SIZES_SCRIPT)
    assert sizes["lineHeight"] * MAX_ROWS <= sizes["height"]
    assert sizes["height"] <= sizes["lineHeight"] * MAX_ROWS + TEXTAREA_PADDING_PX
    assert sizes["scrollHeight"] > sizes["height"]
    assert_submit_beside_field(page)


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。部品の幅によらず入力欄と「レビューに追加」を 1 行に並べ、結果は入力欄の下に幅いっぱいで出す（正常系）。"""
    # 準備
    page = open_story("preview-replyform--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    form = page.locator("form.reply").bounding_box()
    button = page.locator(SEND).bounding_box()
    message = page.locator(MESSAGE).bounding_box()
    assert form is not None
    assert button is not None
    assert message is not None
    assert form["width"] <= 390
    assert_submit_beside_field(page)
    assert button["x"] + button["width"] >= form["x"] + form["width"] - 16 - 1
    assert message["y"] >= button["y"] + button["height"] - 1
    assert message["width"] >= form["width"] - 2 * 16 - 2
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


# 音声入力の結果の行（録音中・文字起こし中・送信・挿入・失敗）を読む場所
VOICE_MESSAGE = ".send-msg"

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
    """マイクのボタンを押せない見た目にし、フォーカスは受けたまま理由をツールチップと読み上げの説明に出す。"""
    mic = page.get_by_role("button", name="音声で入力")
    assert mic.get_attribute("aria-disabled") == "true"
    assert mic.get_attribute("disabled") is None
    assert mic.get_attribute("title") == reason
    assert page.text_content(f"#{mic.get_attribute('aria-describedby')}") == reason
    mic.focus()
    assert page.evaluate("document.activeElement.getAttribute('aria-label')") == "音声で入力"
    assert page.get_by_role("button", name="レビューに追加").is_visible()


def assert_mic_ready(page: Page) -> None:
    """元のボタン（マイクと「レビューに追加」）に戻っている（「レビューに追加」は入力欄が空なら押せない）。"""
    mic = page.get_by_role("button", name="音声で入力")
    assert mic.get_attribute("aria-disabled") is None
    assert mic.get_attribute("title") == "音声で入力"
    assert page.get_by_role("button", name="レビューに追加").is_visible()


def test_recording(open_story: OpenStory) -> None:
    """録音中。マイクと「レビューに追加」の位置に × の「キャンセル」と ✓ の「文字起こし」を置き、結果の行に失敗の色の丸と経過の時間だけを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--recording")
    # 検証
    assert_recording_buttons(page)
    assert "0:12" in page.inner_text(VOICE_MESSAGE)
    assert "録音中" in (page.text_content(VOICE_MESSAGE) or "")
    assert page.input_value("textarea") == ""


def test_transcribing(open_story: OpenStory) -> None:
    """文字起こし中。2 つのボタンを押せなくし、✓ の位置と結果の行に回る印だけを出す。入力欄は読み取りだけ（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--transcribing")
    # 検証
    assert page.get_by_role("button", name="キャンセル").is_disabled()
    busy = page.get_by_role("button", name="文字起こし中")
    assert busy.is_disabled()
    assert page.get_attribute("textarea", "readonly") is not None
    assert page.input_value("textarea") == "確認: "
    assert "文字起こししています。" in (page.text_content(VOICE_MESSAGE) or "")


def test_sent(open_story: OpenStory) -> None:
    """送信した。入力欄を空にし、元のボタンに戻して「送信し、Claude Code へ入力しました。」（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--sent")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "送信し、Claude Code へ入力しました。"
    assert page.input_value("textarea") == ""
    assert_mic_ready(page)


def test_sent_not_entered(open_story: OpenStory) -> None:
    """送信したが Claude Code へ入力しなかった。「送信しました。Claude Code へは入力していません。」（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--sent-not-entered")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "送信しました。Claude Code へは入力していません。"


def test_voice_disabled(open_story: OpenStory) -> None:
    """文字起こしのサービスが起動していない。マイクのボタンを押せない見た目にし、理由のツールチップを出す。「レビューに追加」は押せるまま（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--voice-disabled")
    # 検証
    assert_mic_blocked(page, "文字起こしのサービスが起動していないため、音声で入力できません。")


def test_voice_failed(open_story: OpenStory) -> None:
    """文字起こしに失敗した。入力欄の中身を残し、元のボタンに戻して理由を結果の行に出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--voice-failed")
    # 検証
    assert page.inner_text(VOICE_MESSAGE).strip() == "文字起こしできませんでした。もう一度お試しください。"
    assert page.input_value("textarea") == "案 B も見たい"
    assert_mic_ready(page)


def test_recording_narrow(open_story: OpenStory) -> None:
    """最も狭い幅（320px）の録音中。2 つのボタンは同じ大きさで、入力欄の右に並んだまま収まる（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--recording-narrow")
    page.set_viewport_size({"width": NARROWEST_WIDTH, "height": NARROWEST_HEIGHT})
    page.wait_for_function(f"innerWidth === {NARROWEST_WIDTH}")
    # 検証
    assert_recording_buttons(page)
    form = page.locator("form").bounding_box()
    assert form is not None
    assert form["width"] <= NARROWEST_WIDTH
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
