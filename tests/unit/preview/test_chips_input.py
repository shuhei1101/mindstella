"""components/chips-input.ts（値のチップと、値を追加する入力欄。項目のタグは主題のトグルを持つ）の単体テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 部品を描いて body に置き、呼ばれた onChange を window.calls に積む JavaScript
MOUNT_SCRIPT = """(props) => {
    window.calls = [];
    const element = MindmapPreview.chipsInput({
        controlId: "pe-tags",
        name: "タグ",
        hint: "タグを入れる",
        suggestions: null,
        monospace: false,
        disabled: false,
        ...props,
        onChange: (values, removed) => window.calls.push([values, removed]),
    });
    document.body.append(element);
}"""


def _mount(page: Page, **props: Any) -> None:
    """渡した引数を既定の引数に重ねて部品を描く。"""
    page.evaluate(MOUNT_SCRIPT, props)


def _calls(page: Page) -> list[Any]:
    """呼ばれた onChange の引数の並びを返す。"""
    return page.evaluate("() => window.calls")


def _add(page: Page, text: str) -> None:
    """入力欄に値を入れて Enter を押す。"""
    page.locator("#pe-tags").fill(text)
    page.locator("#pe-tags").press("Enter")


def _toggle_state(page: Page, name: str) -> dict[str, Any]:
    """タグの主題のトグルの押した状態・title と、フォーカスがそのトグルにあるかを返す。"""
    toggle = page.get_by_role("button", name=f"{name} を主題", exact=True)
    return {
        "pressed": toggle.get_attribute("aria-pressed"),
        "title": toggle.get_attribute("title"),
        "focused": toggle.evaluate("(element) => element === document.activeElement"),
    }


def test_chips_input(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """値を追加し・外し、並びに有るものは追加しない（正常系）。"""
    # 準備
    load_preview_scripts()
    _mount(preview_page, values=["UI"], mainToggle=False)
    # 実行
    _add(preview_page, "性能")
    _add(preview_page, "UI")
    preview_page.get_by_role("button", name="UI を外す", exact=True).click()
    # 検証
    assert _calls(preview_page) == [[["UI", "性能"], None], [["性能"], "UI"]]


def test_chips_input_when_main_toggle(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """主題のトグルで main を付け外しし、追加したタグは主題でない（正常系）。"""
    # 準備
    load_preview_scripts()
    _mount(
        preview_page,
        values=[{"name": "画面"}, {"name": "データ", "main": True}],
        mainToggle=True,
    )
    initial_screen = _toggle_state(preview_page, "画面")
    initial_data = _toggle_state(preview_page, "データ")
    # 実行
    preview_page.get_by_role("button", name="画面 を主題", exact=True).click()
    after_first = _toggle_state(preview_page, "画面")
    preview_page.get_by_role("button", name="データ を主題", exact=True).click()
    after_second = _toggle_state(preview_page, "データ")
    _add(preview_page, "保存")
    # 検証
    assert initial_data["pressed"] == "true"
    assert initial_data["title"] == "主題を外す"
    assert initial_screen["pressed"] == "false"
    assert initial_screen["title"] == "主題にする"
    assert after_first == {"pressed": "true", "title": "主題を外す", "focused": True}
    assert after_second == {"pressed": "false", "title": "主題にする", "focused": True}
    assert _calls(preview_page) == [
        [[{"name": "画面", "main": True}, {"name": "データ", "main": True}], None],
        [[{"name": "画面", "main": True}, {"name": "データ"}], None],
        [[{"name": "画面", "main": True}, {"name": "データ"}, {"name": "保存"}], None],
    ]


def test_chips_input_when_disabled(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """disabled の間は操作できない（異常系）。"""
    # 準備
    load_preview_scripts()
    _mount(
        preview_page,
        values=[{"name": "画面", "main": True}, {"name": "データ"}],
        mainToggle=True,
        disabled=True,
    )
    toggle = preview_page.get_by_role("button", name="画面 を主題", exact=True)
    remove = preview_page.get_by_role("button", name="画面 を外す", exact=True)
    # 実行
    toggle.click(force=True)
    remove.click(force=True)
    # 検証
    assert preview_page.locator("#pe-tags").is_disabled()
    assert toggle.is_disabled()
    assert remove.is_disabled()
    assert _calls(preview_page) == []


# 入れた値を確かめる関数を渡して部品を描く JavaScript
VALIDATE_MOUNT_SCRIPT = """() => {
    window.calls = [];
    const results = {
        "D-1": {value: "D-1"},
        "保存先": {value: "D-2"},
        "D-99": {error: "D-99 が見つかりません。ID を確認してください。"},
    };
    const element = MindmapPreview.chipsInput({
        controlId: "pe-tags",
        name: "前提",
        hint: "ID かタイトルを入れる",
        suggestions: null,
        monospace: true,
        disabled: false,
        values: [],
        mainToggle: false,
        validate: (value) => results[value],
        onChange: (values, removed) => window.calls.push([values, removed]),
    });
    document.body.append(element);
}"""


def _error_state(page: Page) -> dict[str, Any]:
    """入力欄の値・aria-invalid と、aria-describedby が指す文を返す。"""
    return page.evaluate(
        """() => {
            const input = document.getElementById("pe-tags");
            const described = input.getAttribute("aria-describedby");
            const message = described ? document.getElementById(described) : null;
            return {
                value: input.value,
                invalid: input.getAttribute("aria-invalid"),
                message: message ? message.textContent : null,
            };
        }"""
    )


def test_chips_input_when_validate(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """validate の値で追加し、誤りは入力欄に残して直下に出し、書き換えると消す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(VALIDATE_MOUNT_SCRIPT)
    # 実行
    _add(preview_page, "保存先")
    _add(preview_page, "D-99")
    after_error = _error_state(preview_page)
    preview_page.locator("#pe-tags").press("Backspace")
    after_edit = _error_state(preview_page)
    # 検証
    assert _calls(preview_page) == [[["D-2"], None]]
    assert after_error == {
        "value": "D-99",
        "invalid": "true",
        "message": "入力の誤り: D-99 が見つかりません。ID を確認してください。",
    }
    assert after_edit == {"value": "D-9", "invalid": None, "message": None}
