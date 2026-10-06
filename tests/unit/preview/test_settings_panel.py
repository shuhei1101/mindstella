"""components/settings-panel.ts（表示の設定の中身）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 表示する種類の全て
ALL_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# メモを除いた 6 種類
KINDS_WITHOUT_NOTES = ["decisions", "tasks", "research", "docs", "terms", "logs"]

# 用語集と会話ログを除いた 5 種類
KINDS_WITHOUT_TERMS_LOGS = ["decisions", "tasks", "research", "docs", "notes"]

# 種類 → 件数
COUNTS = {
    "decisions": 12,
    "tasks": 8,
    "research": 3,
    "docs": 5,
    "terms": 4,
    "notes": 2,
    "logs": 6,
}

# 表示の設定の中身を作って文書に置き、見た目と操作の結果を集めて返す JavaScript
PANEL_SCRIPT = """(args) => {
    const calls = [];
    const props = {
        look: args.look,
        defaultLook: args.defaultLook,
        kinds: new Set(args.kinds),
        defaultKinds: new Set(args.defaultKinds),
        counts: args.counts,
        overrides: args.overrides,
        canSave: args.canSave,
        message: null,
        storageOk: true,
        on: {
            look: (value) => calls.push(["look", value]),
            kinds: (value) => calls.push(["kinds", [...value].sort()]),
            reset: () => calls.push(["reset"]),
            save: () => calls.push(["save"]),
            close: () => calls.push(["close"]),
        },
    };
    const panel = MindmapPreview.settingsPanel(props);
    document.body.append(panel);
    // 入力の行（ラジオボタン・チェックボックスを包む行）の文字と読み上げの名前
    const rowText = (input) =>
        (input.closest("label") ?? input.closest("li") ?? input.parentElement).textContent +
        (input.getAttribute("aria-label") ?? "");
    // 「既定」の札（文字がちょうど「既定」の末端の要素）を持つ行か
    const hasDefaultBadge = (input) =>
        [...(input.closest("label") ?? input.closest("li") ?? input.parentElement).querySelectorAll("*")].some(
            (element) => element.children.length === 0 && element.textContent.trim() === "既定"
        );
    const looks = ["グロウ", "星の光", "星図", "深宇宙", "星屑"];
    const radios = [...panel.querySelectorAll('input[type="radio"]')];
    const checkboxes = [...panel.querySelectorAll('input[type="checkbox"]')];
    const findCheckbox = (name) => checkboxes.find((box) => rowText(box).includes(name));
    const operate = args.operate ?? [];
    const result = {
        text: panel.textContent,
        buttons: [...panel.querySelectorAll("button")].map((button) => button.textContent.trim()),
        defaultLooks: looks.filter((name) =>
            radios.some((radio) => rowText(radio).includes(name) && hasDefaultBadge(radio))
        ),
        radioCount: radios.length,
        checkboxCount: checkboxes.length,
        alwaysShownCheckboxes: checkboxes.filter((box) =>
            ["概要", "つながり"].some((name) => rowText(box).includes(name))
        ).length,
        allBoxIndeterminate: findCheckbox("すべて")?.indeterminate ?? null,
    };
    // 渡された順に、名前の行のチェックボックスを押す
    for (const name of operate) findCheckbox(name).click();
    result.calls = calls;
    return result;
}"""


def _observe(preview_page: Page, **overrides: Any) -> dict[str, Any]:
    """表示の設定の中身を作って見た目と操作の結果を返す。引数は overrides で上書きする。"""
    args: dict[str, Any] = {
        "look": "deep",
        "defaultLook": "deep",
        "kinds": ALL_KINDS,
        "defaultKinds": ALL_KINDS,
        "counts": COUNTS,
        "overrides": [],
        "canSave": True,
        "operate": [],
    }
    args.update(overrides)
    return preview_page.evaluate(PANEL_SCRIPT, args)


@pytest.mark.parametrize(
    ("args", "expected_buttons", "absent_buttons", "expected_texts", "expected_default_looks"),
    [
        pytest.param(
            {},
            [],
            ["既定に戻す", "ワークスペースの既定にする"],
            [
                "ワークスペースの既定のまま表示しています。",
                "今の選びはワークスペースの既定と同じです。",
            ],
            ["深宇宙"],
            id="no_override_same_as_default",
        ),
        pytest.param(
            {
                "look": "dust",
                "defaultLook": "starlight",
                "defaultKinds": KINDS_WITHOUT_NOTES,
                "overrides": ["つながりの見た目", "表示する種類"],
            },
            ["既定に戻す", "ワークスペースの既定にする"],
            [],
            ["この端末で変えている項目", "つながりの見た目・表示する種類"],
            ["星の光"],
            id="overridden",
        ),
        pytest.param(
            {
                "look": "dust",
                "defaultLook": "starlight",
                "defaultKinds": KINDS_WITHOUT_NOTES,
                "overrides": ["つながりの見た目", "表示する種類"],
                "canSave": False,
            },
            ["既定に戻す"],
            ["ワークスペースの既定にする"],
            ["つながりの見た目・表示する種類"],
            ["星の光"],
            id="export_cannot_save",
        ),
        pytest.param(
            {"overrides": ["ライト / ダーク"]},
            ["既定に戻す"],
            ["ワークスペースの既定にする"],
            ["今の選びはワークスペースの既定と同じです。"],
            ["深宇宙"],
            id="override_same_as_default",
        ),
    ],
)
def test_settings_panel(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    args: dict[str, Any],
    expected_buttons: list[str],
    absent_buttons: list[str],
    expected_texts: list[str],
    expected_default_looks: list[str],
) -> None:
    """上書きの有無と既定との違いで、既定に戻すと保存のボタンを出し分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, **args)
    # 検証
    assert all(label in observed["buttons"] for label in expected_buttons)
    assert all(label not in observed["buttons"] for label in absent_buttons)
    assert all(text in observed["text"] for text in expected_texts)
    assert observed["defaultLooks"] == expected_default_looks
    assert observed["radioCount"] == 5


def test_settings_panel_when_kinds_changed(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """種類のチェックと「すべて」で変えた後の並びを知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行（タスクのチェックを外し、次に「すべて」を押す）
    observed = _observe(
        preview_page,
        kinds=KINDS_WITHOUT_TERMS_LOGS,
        overrides=["表示する種類"],
        operate=["タスク", "すべて"],
    )
    # 検証
    assert observed["allBoxIndeterminate"] is True
    assert "5/7" in observed["text"]
    assert observed["calls"] == [
        ["kinds", ["decisions", "docs", "notes", "research"]],
        ["kinds", sorted(ALL_KINDS)],
    ]
    assert observed["checkboxCount"] == 8
    assert observed["alwaysShownCheckboxes"] == 0
    assert "常に表示" in observed["text"]
