"""部品設計『コメントの入力』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 溜めている印と文言が出るまで待つ上限ミリ秒（部品は 1 秒を超えたら出す）
SAVING_NOTICE_TIMEOUT_MS = 3_000

# 入力欄の最大の高さの行数（これを超えたら入力欄の中を送る）
MAX_ROWS = 8

# 選んだ文を出す行数の上限（超えたら末尾を省く）
QUOTE_MAX_LINES = 3

# 入力欄の上下の余白と枠の合計（ピクセル）
TEXTAREA_PADDING_PX = 18

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


def test_idle(open_story: OpenStory) -> None:
    """入力欄が空。本文と線で区切って下端に置き、ラベル「{ID} へのコメント」を常に見せる（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--idle")
    # 検証
    assert page.inner_text("label.send-label") == "D-022 へのコメント"
    assert page.get_attribute("label.send-label", "for") == page.get_attribute("textarea", "id")
    assert page.input_value("textarea") == ""
    assert page.inner_text(".send-msg") == ""
    assert page.get_attribute(".send-msg", "role") == "status"
    assert page.get_attribute("textarea", "aria-describedby") == page.get_attribute(
        ".send-msg", "id"
    )
    assert page.get_by_role("button", name="レビューに追加").is_enabled()
    assert (
        page.eval_on_selector("form.send-footer", "e => getComputedStyle(e).borderTopWidth")
        == "1px"
    )


def test_typing(open_story: OpenStory) -> None:
    """入力中。入力欄に印の色の輪を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--typing")
    page.wait_for_function(
        "document.activeElement && document.activeElement.tagName === 'TEXTAREA'"
    )
    # 検証
    assert page.input_value("textarea") == "案 A にする"
    assert page.eval_on_selector("textarea", "e => getComputedStyle(e).outlineStyle") == "solid"
    assert page.inner_text(".send-msg") == ""


def test_with_body_location(open_story: OpenStory) -> None:
    """本文の箇所を添えた。入力欄の上に「本文 3 行目」と選んだ文を出し、× で外せる（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--with-body-location")
    # 検証
    assert page.inner_text("label.send-label") == "A-005 へのコメント"
    assert page.inner_text(".send-loc-name") == "本文 3 行目"
    assert page.inner_text(".send-quote") == "受け取る人へ渡す形"
    assert page.get_by_role("button", name="箇所を外す").count() == 1
    # 添えた箇所は入力欄の説明として、結果の前に指す
    assert page.get_attribute("textarea", "aria-describedby") == (
        f"{page.get_attribute('.send-loc', 'id')} {page.get_attribute('.send-msg', 'id')}"
    )
    # 箇所は入力欄より上に出る
    loc_box = page.locator(".send-loc").bounding_box()
    field_box = page.locator("textarea").bounding_box()
    assert loc_box is not None
    assert field_box is not None
    assert loc_box["y"] + loc_box["height"] <= field_box["y"]


def test_with_value_location(open_story: OpenStory) -> None:
    """値の箇所を添えた。箇所の名前にキーの名前を出し、選んだ文は 3 行までにして末尾を省く（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--with-value-location")
    # 選んだ文が 3 行を超える幅にする
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 検証
    assert page.inner_text(".send-loc-name") == "案 C のデメリット"
    assert page.input_value("textarea") == "ここは別の言い方にしたい"
    quote = page.eval_on_selector(".send-quote", QUOTE_SIZES_SCRIPT)
    assert quote["clamp"] == str(QUOTE_MAX_LINES)
    assert quote["overflow"] == "hidden"
    # 省かなければ 3 行を超える長さで、出している高さは 3 行分まで
    assert quote["fullHeight"] > quote["lineHeight"] * QUOTE_MAX_LINES
    assert quote["height"] <= quote["lineHeight"] * QUOTE_MAX_LINES + 1


def test_saving(open_story: OpenStory) -> None:
    """溜めている。入力欄を書き換えられなくし、ボタンを押せなくする。1 秒を超えたら回る印と文言を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--saving")
    # 検証
    assert page.get_by_role("button", name="レビューに追加").is_disabled()
    assert page.get_attribute("textarea", "readonly") is not None
    page.wait_for_selector(".send-msg .spinner", timeout=SAVING_NOTICE_TIMEOUT_MS)
    assert page.inner_text(".send-msg") == "レビューに追加しています"


def test_saved(open_story: OpenStory) -> None:
    """溜めた。入力欄を空にし、「レビューに追加しました（レビュー中 3 件）。」を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--saved")
    # 検証
    assert page.input_value("textarea") == ""
    assert page.inner_text(".send-msg") == "レビューに追加しました（レビュー中 3 件）。"
    assert page.locator(".send-msg svg.icon").count() == 1
    assert page.get_attribute("textarea", "aria-invalid") is None


def test_empty(open_story: OpenStory) -> None:
    """本文が空で溜めようとした。入力欄の枠と印を要見直しの赤にし、入れてから追加するよう出す。ボタンは押せるまま（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--empty")
    # 検証
    assert page.inner_text(".send-msg") == "コメントを入れてから追加してください。"
    assert page.get_attribute("textarea", "aria-invalid") == "true"
    assert page.locator(".send-msg svg.icon").count() == 1
    assert page.get_by_role("button", name="レビューに追加").is_enabled()
    review = page.evaluate(REVIEW_COLOR_SCRIPT)
    border = page.eval_on_selector("textarea", "e => getComputedStyle(e).borderTopColor")
    icon = page.eval_on_selector(".send-msg svg.icon", "e => getComputedStyle(e).color")
    assert border == review
    assert icon == review
    # 文言は本文の文字色で出す（赤にしない）
    message_color = page.eval_on_selector(".send-msg", "e => getComputedStyle(e).color")
    text_color = page.eval_on_selector("textarea", "e => getComputedStyle(e).color")
    assert message_color == text_color


def test_failed_unreachable(open_story: OpenStory) -> None:
    """サーバーに届かなかった。本文を残し、立ち上げ直して新しい URL で開くよう出して、本文を写すボタンを添える（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--failed-unreachable")
    # 検証
    assert page.input_value("textarea") == "案 A にする"
    message = page.inner_text(".send-msg")
    assert "レビューに追加できませんでした。サーバーが止まっています。" in message
    assert "起動スクリプトで立ち上げ直し" in message
    assert "示された新しい URL で開いてから追加してください。" in message
    assert page.get_by_role("button", name="本文を写す").count() == 1
    assert page.locator(".send-msg svg.icon").count() >= 1


def test_failed_detail(open_story: OpenStory) -> None:
    """サーバーが溜めなかった理由を返した。本文を残し、理由を出す。本文を写すボタンは出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--failed-detail")
    # 検証
    assert page.input_value("textarea") == "ここは言い換える"
    assert (
        page.inner_text(".send-msg")
        == "レビューに追加できませんでした。選んだ文が本文の 3 行目にありません"
    )
    assert page.get_by_role("button", name="本文を写す").count() == 0


def test_long(open_story: OpenStory) -> None:
    """長文。8 行を超えたら、入力欄の中を送る（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--long")
    # 検証
    sizes = page.eval_on_selector(
        "textarea",
        "e => ({ lineHeight: parseFloat(getComputedStyle(e).lineHeight), height: e.clientHeight, scrollHeight: e.scrollHeight })",
    )
    assert sizes["scrollHeight"] > sizes["height"]
    # 入力欄の高さは 8 行分と上下の余白までに収まる
    assert sizes["height"] <= sizes["lineHeight"] * MAX_ROWS + TEXTAREA_PADDING_PX


def test_no_target(open_story: OpenStory) -> None:
    """項目を指さないコメント。見出しを出さず、入力欄と「レビューに追加」だけにする。名前は読み上げにだけ持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--no-target")
    # 検証
    assert page.locator("label.send-label").count() == 0
    assert page.locator(".send-loc").count() == 0
    assert page.get_attribute("textarea", "aria-label") == "項目を指さないコメント"
    assert page.get_by_role("button", name="レビューに追加").is_enabled()


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。入力の幅が 360px 以下ではボタンを右に置いたまま、結果を下の行に幅いっぱいで出す（正常系）。"""
    # 準備
    page = open_story("preview-sendform--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    form = page.locator("form.send-footer").bounding_box()
    button = page.get_by_role("button", name="レビューに追加").bounding_box()
    message = page.locator(".send-msg").bounding_box()
    assert form is not None
    assert button is not None
    assert message is not None
    assert form["width"] <= 390
    # ボタンは右端、結果はボタンの下の行で幅いっぱい
    assert button["x"] + button["width"] >= form["x"] + form["width"] - 16 - 1
    assert message["y"] >= button["y"] + button["height"] - 1
    assert message["width"] >= form["width"] - 2 * 16 - 2
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_no_target_collapsed(open_story: OpenStory) -> None:
    """項目を指さないコメントを畳んだ形。読み上げのラベルと 1 行の入力欄だけを出し、結果とボタンを出さない（正常系）。"""
    # 準備
    page = open_story("preview-sendform--no-target-collapsed")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert page.get_attribute("textarea", "aria-label") == "項目を指さないコメント"
    assert page.get_attribute("textarea", "rows") == "1"
    assert page.locator(".send-msg").count() == 0
    assert page.get_by_role("button", name="レビューに追加").count() == 0
    assert page.locator("form.send-footer.collapsed").count() == 1


def test_no_target_expanded(open_story: OpenStory) -> None:
    """項目を指さないコメントを狭い幅で広げた形。入力欄と「レビューに追加」を出す（正常系）。"""
    # 準備
    page = open_story("preview-sendform--no-target-expanded")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert page.input_value("textarea") == "全体に目を通した"
    assert page.get_attribute("textarea", "rows") == "2"
    assert page.get_by_role("button", name="レビューに追加").is_visible()
    assert page.locator("form.send-footer.collapsed").count() == 0
