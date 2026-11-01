"""部品設計『チップの入力』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# チップごとに、名前・等幅か・主題か・主題のトグルの読み上げ名・押した状態・title・外すボタンの読み上げ名を読む
CHIPS_SCRIPT = """() => [...document.querySelectorAll("#storybook-root .pe-chip")].map((chip) => {
    const toggle = chip.querySelector(".pe-chip-main");
    return {
        name: [...chip.childNodes].find((node) => node.nodeType === Node.TEXT_NODE).textContent,
        mono: chip.classList.contains("mono"),
        main: chip.classList.contains("is-main"),
        toggle: toggle === null ? null : {
            label: toggle.getAttribute("aria-label"),
            pressed: toggle.getAttribute("aria-pressed"),
            title: toggle.getAttribute("title"),
        },
        remove: chip.querySelector(".pe-chip-x").getAttribute("aria-label"),
    };
})"""

# 入力欄の読み上げ名・プレースホルダ・押せないか・候補
FIELD_SCRIPT = """() => {
    const field = document.querySelector("#storybook-root .pe-chip-input");
    const list = field.list;
    return {
        label: field.getAttribute("aria-label"),
        placeholder: field.placeholder,
        disabled: field.disabled,
        suggestions: list === null ? null : [...list.options].map((option) => option.value),
    };
}"""

# 押せないボタンの数と、全てのボタンの数
DISABLED_BUTTONS_SCRIPT = """() => {
    const buttons = [...document.querySelectorAll("#storybook-root .pe-chips button")];
    return { disabled: buttons.filter((button) => button.disabled).length, all: buttons.length };
}"""

# 主題のトグルの押せる範囲の幅と高さの最小
TOGGLE_SIZE_SCRIPT = """() => {
    const boxes = [...document.querySelectorAll("#storybook-root .pe-chip-main")].map((toggle) => toggle.getBoundingClientRect());
    return { width: Math.min(...boxes.map((box) => box.width)), height: Math.min(...boxes.map((box) => box.height)) };
}"""

# フォーカスを持つ要素の class と data-index
FOCUS_SCRIPT = """() => ({
    className: document.activeElement.className,
    index: document.activeElement.getAttribute("data-index"),
})"""

# 台の幅・全てのチップが台に収まるか・行の数と、1 つ目のチップの中にトグルと名前が同じ行で収まるか
LAYOUT_SCRIPT = """() => {
    const stage = document.querySelector("#storybook-root > div");
    const stageBox = stage.getBoundingClientRect();
    const chips = [...stage.querySelectorAll(".pe-chip")];
    const boxes = chips.map((chip) => chip.getBoundingClientRect());
    const first = boxes[0];
    const toggle = chips[0].querySelector(".pe-chip-main").getBoundingClientRect();
    const range = document.createRange();
    range.selectNodeContents([...chips[0].childNodes].find((node) => node.nodeType === Node.TEXT_NODE));
    const name = range.getClientRects();
    return {
        width: stage.offsetWidth,
        inside: boxes.every((box) => box.right <= stageBox.right),
        rows: new Set(boxes.map((box) => box.top)).size,
        nameLines: name.length,
        toggleInFirst: first.top <= toggle.top && toggle.bottom <= first.bottom,
        toggleBesideName: toggle.top < name[0].bottom && name[0].top < toggle.bottom,
    };
}"""

# 主題のトグルの押せる範囲の縦横の最小
TOGGLE_TARGET_PX = 24

# MainToggleLongNarrow のストーリーの台の幅
NARROW_WIDTH_PX = 320


def test_default(open_story: OpenStory) -> None:
    """参照の ID を等幅の文字のチップで並べ、主題のトグルを持たない。候補が無いときは入力欄に候補を出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-chipsinput--default")
    # 検証
    assert page.evaluate(CHIPS_SCRIPT) == [
        {"name": "D-1", "mono": True, "main": False, "toggle": None, "remove": "D-1 を外す"},
        {"name": "T-3", "mono": True, "main": False, "toggle": None, "remove": "T-3 を外す"},
    ]
    assert page.evaluate(FIELD_SCRIPT) == {
        "label": "関係を追加",
        "placeholder": "ID を入れる",
        "disabled": False,
        "suggestions": None,
    }
    assert page.locator("#storybook-root .pe-chips").get_attribute("aria-label") == "関係"


def test_main_toggle(open_story: OpenStory) -> None:
    """項目のタグは、チップの名前の前に主題のトグルを置き、主題のタグは押した状態、主題でないタグは押していない状態で出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-chipsinput--main-toggle")
    # 検証
    assert page.evaluate(CHIPS_SCRIPT) == [
        {
            "name": "画面",
            "mono": False,
            "main": True,
            "toggle": {"label": "画面 を主題", "pressed": "true", "title": "主題を外す"},
            "remove": "画面 を外す",
        },
        {
            "name": "記録の形",
            "mono": False,
            "main": False,
            "toggle": {"label": "記録の形 を主題", "pressed": "false", "title": "主題にする"},
            "remove": "記録の形 を外す",
        },
        {
            "name": "通知",
            "mono": False,
            "main": False,
            "toggle": {"label": "通知 を主題", "pressed": "false", "title": "主題にする"},
            "remove": "通知 を外す",
        },
    ]
    assert page.evaluate(FIELD_SCRIPT) == {
        "label": "タグを追加",
        "placeholder": "タグを入れる",
        "disabled": False,
        "suggestions": ["画面", "記録の形", "通知", "タスク"],
    }
    # 主題のトグルの押せる範囲は縦横 24px 以上
    size = page.evaluate(TOGGLE_SIZE_SCRIPT)
    assert size["width"] >= TOGGLE_TARGET_PX
    assert size["height"] >= TOGGLE_TARGET_PX


def test_main_toggle_when_toggled(open_story: OpenStory) -> None:
    """主題のトグルを押すと主題を付け外しし、主題は複数にできる。押した後も同じタグのトグルにフォーカスを残す（正常系）。"""
    # 準備
    page = open_story("preview-chipsinput--main-toggle")
    # 実行
    page.get_by_role("button", name="記録の形 を主題").click()
    # 検証
    assert page.evaluate(FOCUS_SCRIPT) == {"className": "pe-chip-main", "index": "1"}
    assert page.get_by_role("button", name="画面 を主題").get_attribute("aria-pressed") == "true"
    assert page.get_by_role("button", name="記録の形 を主題").get_attribute("aria-pressed") == "true"
    assert page.get_by_role("button", name="記録の形 を主題").get_attribute("title") == "主題を外す"
    # 実行
    page.get_by_role("button", name="画面 を主題").press("Enter")
    # 検証
    assert page.evaluate(FOCUS_SCRIPT) == {"className": "pe-chip-main", "index": "0"}
    assert page.get_by_role("button", name="画面 を主題").get_attribute("aria-pressed") == "false"
    assert page.get_by_role("button", name="画面 を主題").get_attribute("title") == "主題にする"


def test_main_toggle_when_added_and_removed(open_story: OpenStory) -> None:
    """入力欄から追加したタグは主題でないまま末尾に並べ、外すボタンでチップを外す（正常系）。"""
    # 準備
    page = open_story("preview-chipsinput--main-toggle")
    # 実行
    page.get_by_role("combobox", name="タグを追加").fill("タスク")
    page.get_by_role("combobox", name="タグを追加").press("Enter")
    page.get_by_role("button", name="通知 を外す").click()
    # 検証
    chips = page.evaluate(CHIPS_SCRIPT)
    assert [chip["name"] for chip in chips] == ["画面", "記録の形", "タスク"]
    assert chips[2]["main"] is False
    assert chips[2]["toggle"] == {"label": "タスク を主題", "pressed": "false", "title": "主題にする"}
    assert chips[0]["toggle"]["pressed"] == "true"


def test_main_toggle_disabled(open_story: OpenStory) -> None:
    """削除を溜めた項目のタグは、入力欄・外すボタン・主題のトグルを押せない（正常系）。"""
    # 準備・実行
    page = open_story("preview-chipsinput--main-toggle-disabled")
    # 検証
    assert page.evaluate(FIELD_SCRIPT)["disabled"] is True
    # トグルと外すボタンが 2 つずつ、全て押せない
    assert page.evaluate(DISABLED_BUTTONS_SCRIPT) == {"disabled": 4, "all": 4}
    assert page.get_by_role("button", name="画面 を主題").get_attribute("aria-pressed") == "true"


def test_main_toggle_long_narrow(open_story: OpenStory) -> None:
    """幅 320px で長い名前の主題のタグを並べる。収まらないチップは次の行へ回し、トグルは名前と同じ行に残す（正常系）。"""
    # 準備・実行
    page = open_story("preview-chipsinput--main-toggle-long-narrow")
    # 検証
    layout = page.evaluate(LAYOUT_SCRIPT)
    assert layout["width"] == NARROW_WIDTH_PX
    assert layout["inside"] is True
    assert layout["rows"] > 1
    assert layout["nameLines"] == 1
    assert layout["toggleInFirst"] is True
    assert layout["toggleBesideName"] is True
