"""部品設計『絞り込み』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 広い幅でのドロワーの幅（ピクセル）
DRAWER_WIDTH_PX = 420

# ドロワーの条件の並び（見出し・選んだ数の文言・「解除」の読み上げ名・値ごとの `[値, 件数, チェック, 薄い]`）を読む
GROUPS_SCRIPT = """() => [...document.querySelectorAll('dialog.drawer .fd-group')].map((group) => ({
    label: group.querySelector('legend').childNodes[0].textContent,
    sel: group.querySelector('.fd-sel')?.textContent ?? null,
    clear: group.querySelector('.fd-clear')?.getAttribute('aria-label') ?? null,
    values: [...group.querySelectorAll('.fd-opt')].map((opt) => [
        opt.querySelector('.fd-v').textContent,
        Number(opt.querySelector('.n').textContent),
        opt.querySelector('input').checked,
        opt.classList.contains('zero'),
    ]),
}))"""

# ドロワーの見出しの右の件数と、下端のボタンの文字を読む
HEAD_SCRIPT = """() => ({
    count: document.querySelector('dialog.drawer .fd-count').textContent,
    foot: [...document.querySelectorAll('dialog.drawer .fd-foot button')].map((b) => b.textContent),
})"""

# ドロワーが横にあふれず、各値の件数の列がドロワーの中に収まっているかを読む
OVERFLOW_SCRIPT = """() => {
    const drawer = document.querySelector('dialog.drawer').getBoundingClientRect();
    const body = document.querySelector('dialog.drawer .fd-body');
    return {
        bodyScrolls: body.scrollWidth > body.clientWidth,
        countsInside: [...document.querySelectorAll('dialog.drawer .fd-opt .n')].every(
            (n) => n.getBoundingClientRect().right <= drawer.right,
        ),
        valueWraps: [...document.querySelectorAll('dialog.drawer .fd-v')].some(
            (v) => v.getBoundingClientRect().height > parseFloat(getComputedStyle(v).lineHeight) * 1.5,
        ),
    };
}"""

# 値の文字の色を値の名前で読む
VALUE_COLOR_SCRIPT = """() => Object.fromEntries([...document.querySelectorAll('dialog.drawer .fd-v')].map(
    (v) => [v.textContent, getComputedStyle(v).color],
))"""


def _open_drawer(open_story: OpenStory, story_id: str) -> Page:
    """ストーリーを開き、ドロワーが開いて出る動きが終わるのを待つ。"""
    page = open_story(story_id)
    page.wait_for_selector("dialog.drawer[open]")
    page.wait_for_function("document.getAnimations().length === 0")
    return page


def _groups(page: Page) -> list[dict[str, Any]]:
    """ドロワーの条件を並びの順に返す。"""
    return page.evaluate(GROUPS_SCRIPT)


def test_default(open_story: OpenStory) -> None:
    """何も選んでいない。見出しの右は「8 件」で、「解除」と「すべて解除」を出さない（正常系）。"""
    # 準備・実行
    page = _open_drawer(open_story, "preview-filterdrawer--default")
    # 検証
    # ドロワーは読み上げの名前「絞り込み」を持つ非モーダルのダイアログで、幅は 420px
    assert page.eval_on_selector("dialog.drawer", "d => d.getAttribute('aria-labelledby')") == "drawer-title"
    assert page.inner_text("#drawer-title") == "絞り込み"
    assert page.eval_on_selector("dialog.drawer", "d => d.matches(':modal')") is False
    assert page.locator("dialog.drawer").bounding_box()["width"] == DRAWER_WIDTH_PX
    # 条件は種類・状態・タグの順で、選んだ値も「解除」も無い
    groups = _groups(page)
    assert [group["label"] for group in groups] == ["種類", "状態", "タグ"]
    assert all(group["sel"] is None and group["clear"] is None for group in groups)
    assert all(not checked for group in groups for _, _, checked, _ in group["values"])
    assert page.evaluate(HEAD_SCRIPT) == {"count": "8 件", "foot": ["8 件を表示"]}
    # 開くと最初の値へフォーカスが移る
    assert page.evaluate("document.activeElement.dataset.key + '/' + document.activeElement.value") == "kind/作業"


def test_selected(open_story: OpenStory) -> None:
    """検討事項で状態に 4 つ・タグに 1 つを選んでいる。選んだ条件に「{件数} 件を選択」と「解除」、下端に「すべて解除」と「3 件を表示」（正常系）。"""
    # 準備・実行
    page = _open_drawer(open_story, "preview-filterdrawer--selected")
    # 検証
    groups = _groups(page)
    assert [group["label"] for group in groups] == ["状態", "タグ"]
    assert [(group["sel"], group["clear"]) for group in groups] == [
        ("4 件を選択", "状態の条件を解除"),
        ("1 件を選択", "タグの条件を解除"),
    ]
    status = {value: checked for value, _, checked, _ in groups[0]["values"]}
    assert [value for value, checked in status.items() if checked] == ["要見直し", "未決定", "未整理", "保留"]
    assert status["決定済み"] is False
    assert [value for value, _, checked, _ in groups[1]["values"] if checked] == ["プレビュー"]
    assert page.evaluate(HEAD_SCRIPT) == {"count": "36 件中 3 件", "foot": ["すべて解除", "3 件を表示"]}
    # 「解除」の読み上げ名が条件の見出しを含み、押せるボタンとして並ぶ
    assert page.locator('dialog.drawer button[aria-label="状態の条件を解除"]').inner_text() == "解除"


def test_zero_value(open_story: OpenStory) -> None:
    """今の条件では 0 件になる値がある。その値は文字と件数を薄くし、選べるまま残す（正常系）。"""
    # 準備・実行
    page = _open_drawer(open_story, "preview-filterdrawer--zero-value")
    # 検証
    status = _groups(page)[0]["values"]
    # 0 件の値は 0 を件数に出し、薄い見た目の印を持つ
    assert [(value, count, zero) for value, count, _, zero in status if zero] == [
        ("未整理", 0, True),
        ("対象外", 0, True),
        ("取り下げ", 0, True),
    ]
    assert page.get_attribute('dialog.drawer input[value="未整理"]', "disabled") is None
    assert page.get_attribute('dialog.drawer .fd-opt.zero .n >> nth=0', "aria-label") == "0 件"
    # 0 件の値の文字は、件数のある値の文字より薄い色にする
    colors = page.evaluate(VALUE_COLOR_SCRIPT)
    assert colors["未整理"] != colors["決定済み"]
    assert colors["対象外"] == colors["未整理"]
    # 0 件の値も選べる
    page.click('dialog.drawer label.fd-opt:has(input[value="未整理"])')
    assert page.is_checked('dialog.drawer input[value="未整理"]')


def test_long_tag(open_story: OpenStory) -> None:
    """長いタグ。値の文字を折り返し、件数の列を押し出さない（正常系）。"""
    # 準備・実行
    page = _open_drawer(open_story, "preview-filterdrawer--long-tag")
    # 検証
    assert page.evaluate(OVERFLOW_SCRIPT) == {"bodyScrolls": False, "countsInside": True, "valueWraps": True}
    # 長いタグの件数は、短いタグの件数と同じ右端にそろう
    rights = page.eval_on_selector_all(
        "dialog.drawer .fd-opt .n", "ns => ns.map(n => Math.round(n.getBoundingClientRect().right))"
    )
    assert len(set(rights)) == 1


def test_keyword_hits(open_story: OpenStory) -> None:
    """検討事項のマップでキーワードに一致した項目がある。一致した件数を件数の左に印の色で出す（正常系）。"""
    # 準備・実行
    page = _open_drawer(open_story, "preview-filterdrawer--keyword-hits")
    # 検証
    # 一致が 1 件以上の値にだけ、読み上げ名つきで一致した件数を出す
    hits = page.eval_on_selector_all(
        "dialog.drawer .fd-opt",
        "opts => opts.map(o => [o.querySelector('.fd-v').textContent, o.querySelector('.hit-n')?.textContent ?? null, o.querySelector('.hit-n')?.getAttribute('aria-label') ?? null])",
    )
    assert hits == [
        ["要見直し", "1", "キーワードに一致した項目 1 件"],
        ["未決定", "2", "キーワードに一致した項目 2 件"],
        ["保留", None, None],
    ]
    # 一致した件数は件数の左にあり、背景が付く
    boxes = page.evaluate(
        """() => {
            const opt = document.querySelector('dialog.drawer .fd-opt');
            return [opt.querySelector('.hit-n'), opt.querySelector('.n')].map(
                (e) => e.getBoundingClientRect().right,
            );
        }"""
    )
    assert boxes[0] < boxes[1]
    assert page.eval_on_selector("dialog.drawer .hit-n", "e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"


def test_no_match(open_story: OpenStory) -> None:
    """該当なし。見出しの右は「8 件中 0 件」、下端のボタンは「0 件を表示」（正常系）。"""
    # 準備・実行
    page = _open_drawer(open_story, "preview-filterdrawer--no-match")
    # 検証
    assert page.evaluate(HEAD_SCRIPT) == {"count": "8 件中 0 件", "foot": ["すべて解除", "0 件を表示"]}
    groups = _groups(page)
    assert [(group["label"], group["sel"]) for group in groups] == [
        ("種類", "1 件を選択"),
        ("状態", "1 件を選択"),
        ("タグ", None),
    ]


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。トップバーの下から画面の幅いっぱいに重ねる（正常系）。"""
    # 準備
    page = open_story("preview-filterdrawer--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    page.wait_for_selector("dialog.drawer[open]")
    page.wait_for_function("document.getAnimations().length === 0")
    # 実行・検証
    box = page.locator("dialog.drawer").bounding_box()
    assert box["x"] == 0
    assert box["width"] == NARROW_SIZE["width"]
    # トップバーの高さ（52px）の下から重ね、タブの帯は覆う
    assert box["y"] == page.evaluate(
        "parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--topbar-h'))"
    )
    assert page.eval_on_selector("dialog.drawer", "d => d.classList.contains('narrow')") is True
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
