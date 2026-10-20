"""部品設計『返信の入力』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

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
    assert page.is_disabled(SEND)


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
    """長文。入力欄は 8 行まで広がり、それより長いと中でスクロールする（正常系）。"""
    # 準備・実行
    page = open_story("preview-replyform--long")
    # 検証
    sizes = page.eval_on_selector("textarea", TEXTAREA_SIZES_SCRIPT)
    assert sizes["lineHeight"] * MAX_ROWS <= sizes["height"]
    assert sizes["height"] <= sizes["lineHeight"] * MAX_ROWS + TEXTAREA_PADDING_PX
    assert sizes["scrollHeight"] > sizes["height"]


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。入力の幅が 360px 以下ではボタンを右に置いたまま、結果を下の行に幅いっぱいで出す（正常系）。"""
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
    assert button["x"] + button["width"] >= form["x"] + form["width"] - 16 - 1
    assert message["y"] >= button["y"] + button["height"] - 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
