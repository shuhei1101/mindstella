"""部品設計『回答・意見の送信』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 送っている印と文言が出るまで待つ上限ミリ秒（部品は 1 秒を超えたら出す）
SENDING_NOTICE_TIMEOUT_MS = 3_000

# 入力欄の最大の高さの行数（これを超えたら入力欄の中を送る）
MAX_ROWS = 8


def test_idle(open_story: OpenStory) -> None:
    """入力欄が空。本文と線で区切って下端に置き、ラベルで送る先の ID を示す（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--idle")
    # 検証
    assert page.inner_text("label.send-label") == "D-22 への回答・意見"
    assert page.get_attribute("label.send-label", "for") == page.get_attribute("textarea", "id")
    assert page.input_value("textarea") == ""
    assert page.inner_text(".send-msg") == ""
    assert page.get_attribute(".send-msg", "role") == "status"
    assert page.get_attribute("textarea", "aria-describedby") == page.get_attribute(
        ".send-msg", "id"
    )
    assert page.is_enabled("button[type=submit]")
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


def test_sending(open_story: OpenStory) -> None:
    """送っている。送るボタンを押せず、入力欄を書き換えられず、1 秒を超えたら印と文言を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--sending")
    # 検証
    assert page.is_disabled("button[type=submit]")
    assert page.get_attribute("textarea", "readonly") is not None
    page.wait_for_selector(".send-msg .spinner", timeout=SENDING_NOTICE_TIMEOUT_MS)
    assert page.inner_text(".send-msg") == "送っています"


def test_sent(open_story: OpenStory) -> None:
    """送った。入力欄を空にし、送った旨と日時（JST）を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--sent")
    # 検証
    assert page.input_value("textarea") == ""
    assert (
        page.inner_text(".send-msg")
        == "送りました（10/04 11:23）。次の話し合いの最初に取り込みます。"
    )
    assert page.locator(".send-msg svg.icon").count() == 1
    assert page.get_attribute("textarea", "aria-invalid") is None


def test_empty(open_story: OpenStory) -> None:
    """本文が空で送った。入力欄を要見直しの赤にし、入れてから送るよう出す。送るボタンは押せるまま（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--empty")
    # 検証
    assert page.inner_text(".send-msg") == "回答・意見を入れてから送ってください。"
    assert page.get_attribute("textarea", "aria-invalid") == "true"
    assert page.locator(".send-msg svg.icon").count() == 1
    assert page.is_enabled("button[type=submit]")
    border = page.eval_on_selector("textarea", "e => getComputedStyle(e).borderTopColor")
    review = page.evaluate(
        "(() => { const probe = document.createElement('i'); probe.style.color = 'var(--st-review)'; "
        "document.body.append(probe); const color = getComputedStyle(probe).color; probe.remove(); return color; })()"
    )
    assert border == review


def test_failed_unreachable(open_story: OpenStory) -> None:
    """サーバーに届かなかった。本文を残し、立ち上げ直して新しい URL で開くよう出して、本文を写すボタンを添える（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--failed-unreachable")
    # 検証
    assert page.input_value("textarea") == "案 A にする"
    message = page.inner_text(".send-msg")
    assert "サーバーが止まっています" in message
    assert "起動スクリプトで立ち上げ直し" in message
    assert page.get_by_role("button", name="本文を写す").count() == 1
    assert page.locator(".send-msg svg.icon").count() >= 1


def test_failed_detail(open_story: OpenStory) -> None:
    """サーバーが送らなかった理由を返した。本文を残し、理由を出す。本文を写すボタンは出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-sendform--failed-detail")
    # 検証
    assert page.input_value("textarea") == "案 A にする"
    assert (
        page.inner_text(".send-msg") == "送れませんでした。項目 D-22 がワークスペースにありません"
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
    # 入力欄の高さは 8 行分と上下の余白（16px）までに収まる
    assert sizes["height"] <= sizes["lineHeight"] * MAX_ROWS + 16 + 2


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。入力の幅が 360px 以下のとき、送るボタンを右に置いたまま、結果を下の行に幅いっぱいで出す（正常系）。"""
    # 準備
    page = open_story("preview-sendform--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    form = page.locator("form.send-footer").bounding_box()
    button = page.locator("button[type=submit]").bounding_box()
    message = page.locator(".send-msg").bounding_box()
    assert form is not None
    assert button is not None
    assert message is not None
    assert form["width"] <= 390
    # 送るボタンは右端、結果はボタンの下の行で幅いっぱい
    assert button["x"] + button["width"] >= form["x"] + form["width"] - 16 - 1
    assert message["y"] >= button["y"] + button["height"] - 1
    assert message["width"] >= form["width"] - 2 * 16 - 2
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
