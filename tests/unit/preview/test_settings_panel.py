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
        minimap: args.minimap,
        message: null,
        storageOk: true,
        on: {
            kinds: (value) => calls.push(["kinds", [...value].sort()]),
            minimap: (value) => calls.push(["minimap", value]),
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
    const radios = [...panel.querySelectorAll('input[type="radio"]')];
    const checkboxes = [...panel.querySelectorAll('input[type="checkbox"]')];
    const findCheckbox = (name) => checkboxes.find((box) => rowText(box).includes(name));
    const minimapBox = findCheckbox("差分のミニマップ");
    const operate = args.operate ?? [];
    const result = {
        text: panel.textContent,
        buttons: [...panel.querySelectorAll("button")].map((button) => button.textContent.trim()),
        radioCount: radios.length,
        // 表示する種類のチェックボックスの数（差分のミニマップのチェックは数えない）
        checkboxCount: checkboxes.filter((box) => box !== minimapBox).length,
        // 差分のミニマップのチェックボックスの状態と、それを包む凡例の文字（押す前の値）
        minimapBox: minimapBox === undefined ? null : {
            checked: minimapBox.checked,
            legend: minimapBox.closest("fieldset")?.querySelector("legend")?.textContent ?? null,
        },
        alwaysShownCheckboxes: checkboxes.filter((box) =>
            ["概要", "ネットワーク"].some((name) => rowText(box).includes(name))
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
        "minimap": True,
        "operate": [],
    }
    args.update(overrides)
    return preview_page.evaluate(PANEL_SCRIPT, args)


@pytest.mark.parametrize(
    ("args", "expected_buttons", "absent_buttons", "expected_texts"),
    [
        pytest.param(
            {},
            [],
            ["既定に戻す", "ワークスペースの既定にする"],
            [
                "ワークスペースの既定のまま表示しています。",
                "見た目と表示する種類は、ワークスペースの既定と同じです。",
            ],
            id="no_override_same_as_default",
        ),
        pytest.param(
            {
                "look": "dust",
                "defaultLook": "starlight",
                "defaultKinds": KINDS_WITHOUT_NOTES,
                "overrides": ["ネットワークの見た目", "表示する種類"],
            },
            ["既定に戻す", "ワークスペースの既定にする"],
            [],
            ["この端末で変えている項目", "ネットワークの見た目・表示する種類"],
            id="overridden",
        ),
        pytest.param(
            {
                "look": "dust",
                "defaultLook": "starlight",
                "defaultKinds": KINDS_WITHOUT_NOTES,
                "overrides": ["ネットワークの見た目", "表示する種類"],
                "canSave": False,
            },
            ["既定に戻す"],
            ["ワークスペースの既定にする"],
            ["ネットワークの見た目・表示する種類"],
            id="export_cannot_save",
        ),
        pytest.param(
            {"overrides": ["ライト / ダーク"]},
            ["既定に戻す"],
            ["ワークスペースの既定にする"],
            ["見た目と表示する種類は、ワークスペースの既定と同じです。"],
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
    assert observed["radioCount"] == 0


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


@pytest.mark.parametrize(
    ("args", "expected_checked", "expected_call", "expected_buttons", "expected_texts"),
    [
        pytest.param(
            {"minimap": True, "overrides": []},
            True,
            ["minimap", False],
            [],
            [],
            id="shown",
        ),
        pytest.param(
            {"minimap": False, "overrides": ["差分のミニマップ"]},
            False,
            ["minimap", True],
            ["既定に戻す"],
            ["見た目と表示する種類は、ワークスペースの既定と同じです。"],
            id="hidden",
        ),
    ],
)
def test_settings_panel_when_minimap(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    args: dict[str, Any],
    expected_checked: bool,
    expected_call: list[Any],
    expected_buttons: list[str],
    expected_texts: list[str],
) -> None:
    """差分のミニマップのチェックを出し、切り替えを知らせる。保存のボタンの比べには使わない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行（差分のミニマップのチェックを押す）
    observed = _observe(preview_page, operate=["差分のミニマップ"], **args)
    # 検証
    assert observed["minimapBox"] == {"checked": expected_checked, "legend": "詳細に表示するもの"}
    assert observed["calls"] == [expected_call]
    assert all(label in observed["buttons"] for label in expected_buttons)
    assert "ワークスペースの既定にする" not in observed["buttons"]
    assert all(text in observed["text"] for text in expected_texts)
