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

# 本文の見せ方の既定（折りたたみはオン）
BODY_VIEW_DEFAULT = {"fold": True}

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
        kinds: new Set(args.kinds),
        defaultKinds: new Set(args.defaultKinds),
        counts: args.counts,
        overrides: args.overrides,
        canSave: args.canSave,
        minimap: args.minimap,
        bodyView: args.bodyView,
        focusAfterAdd: args.focusAfterAdd,
        pointerCoarse: args.pointerCoarse,
        message: null,
        storageOk: true,
        on: {
            kinds: (value) => calls.push(["kinds", [...value].sort()]),
            minimap: (value) => calls.push(["minimap", value]),
            bodyView: (change) => calls.push(["bodyView", change]),
            focusAfterAdd: (value) => calls.push(["focusAfterAdd", value]),
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
    const bodyViewNames = ["表の列の固定", "表の見出しの固定", "表のしま模様", "セクションの折りたたみ"];
    const bodyViewBoxes = bodyViewNames.map(findCheckbox);
    // 凡例「詳細に表示するもの」の中のチェックボックスを、並びのまま名前と状態にする（押す前の値）
    const detailNames = ["差分のミニマップ", ...bodyViewNames];
    const detailChecks = minimapBox === undefined ? [] : [
        ...minimapBox.closest("fieldset").querySelectorAll('input[type="checkbox"]'),
    ].map((box) => ({
        name: detailNames.find((name) => rowText(box).includes(name)) ?? null,
        checked: box.checked,
    }));
    // 凡例「レビューに追加した後のフォーカス」のラジオのグループ（押す前の値）
    const focusGroup = [...panel.querySelectorAll("fieldset")].find(
        (set) => set.querySelector(":scope > legend")?.textContent === "レビューに追加した後のフォーカス"
    );
    const focusRadios = focusGroup === undefined ? [] : [...focusGroup.querySelectorAll('input[type="radio"]')];
    const describedBy = focusGroup?.getAttribute("aria-describedby") ?? null;
    const focus = focusGroup === undefined ? null : {
        section: focusGroup.parentElement.closest("fieldset")?.querySelector(":scope > legend")?.textContent ?? null,
        radios: focusRadios.map((radio) => ({text: rowText(radio).trim(), checked: radio.checked})),
        description: describedBy === null ? null : document.getElementById(describedBy)?.textContent ?? null,
    };
    const operate = args.operate ?? [];
    const result = {
        text: panel.textContent,
        buttons: [...panel.querySelectorAll("button")].map((button) => button.textContent.trim()),
        // 見た目のラジオの数（「レビューに追加した後のフォーカス」のラジオは数えない）
        radioCount: radios.filter((radio) => !focusRadios.includes(radio)).length,
        focus,
        // 表示する種類のチェックボックスの数（詳細に表示するもののチェックは数えない）
        checkboxCount: checkboxes.filter((box) => box !== minimapBox && !bodyViewBoxes.includes(box)).length,
        // 差分のミニマップのチェックボックスの状態と、それを包む凡例の文字（押す前の値）
        minimapBox: minimapBox === undefined ? null : {
            checked: minimapBox.checked,
            legend: minimapBox.closest("fieldset")?.querySelector("legend")?.textContent ?? null,
        },
        detailChecks,
        alwaysShownCheckboxes: checkboxes.filter((box) =>
            rowText(box).includes("概要")
        ).length,
        allBoxIndeterminate: findCheckbox("すべて")?.indeterminate ?? null,
    };
    // 渡された順に、名前の行のチェックボックスを押す
    for (const name of operate) findCheckbox(name).click();
    // 渡された名前で始まる行の「レビューに追加した後のフォーカス」のラジオを押す
    if (args.operateFocus) focusRadios.find((radio) => rowText(radio).trim().startsWith(args.operateFocus)).click();
    result.calls = calls;
    return result;
}"""


def _observe(preview_page: Page, **overrides: Any) -> dict[str, Any]:
    """表示の設定の中身を作って見た目と操作の結果を返す。引数は overrides で上書きする。"""
    args: dict[str, Any] = {
        "kinds": ALL_KINDS,
        "defaultKinds": ALL_KINDS,
        "counts": COUNTS,
        "overrides": [],
        "canSave": True,
        "minimap": True,
        "bodyView": BODY_VIEW_DEFAULT,
        "focusAfterAdd": "auto",
        "pointerCoarse": False,
        "operate": [],
        "operateFocus": None,
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
                "表示する種類は、ワークスペースの既定と同じです。",
            ],
            id="no_override_same_as_default",
        ),
        pytest.param(
            {
                "kinds": KINDS_WITHOUT_NOTES,
                "overrides": ["表示する種類", "ライト / ダーク"],
            },
            ["既定に戻す", "ワークスペースの既定にする"],
            [],
            ["この端末で変えている項目", "表示する種類・ライト / ダーク"],
            id="overridden",
        ),
        pytest.param(
            {
                "kinds": KINDS_WITHOUT_NOTES,
                "overrides": ["表示する種類", "ライト / ダーク"],
                "canSave": False,
            },
            ["既定に戻す"],
            ["ワークスペースの既定にする"],
            ["表示する種類・ライト / ダーク"],
            id="export_cannot_save",
        ),
        pytest.param(
            {"overrides": ["ライト / ダーク"]},
            ["既定に戻す"],
            ["ワークスペースの既定にする"],
            ["表示する種類は、ワークスペースの既定と同じです。"],
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
    # 削除したネットワークの行は無い
    assert "ネットワーク" not in observed["text"]


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
            ["表示する種類は、ワークスペースの既定と同じです。"],
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


@pytest.mark.parametrize(
    ("args", "expected_checks", "expected_call", "expected_buttons", "expected_texts"),
    [
        pytest.param(
            {"bodyView": BODY_VIEW_DEFAULT, "overrides": [], "operate": ["セクションの折りたたみ"]},
            [("差分のミニマップ", True), ("セクションの折りたたみ", True)],
            ["bodyView", {"key": "fold", "value": False}],
            [],
            [],
            id="default_press_fold",
        ),
        pytest.param(
            {
                "bodyView": {"fold": False},
                "overrides": ["セクションの折りたたみ"],
                "operate": ["セクションの折りたたみ"],
            },
            [("差分のミニマップ", True), ("セクションの折りたたみ", False)],
            ["bodyView", {"key": "fold", "value": True}],
            ["既定に戻す"],
            ["表示する種類は、ワークスペースの既定と同じです。"],
            id="overridden_press_fold",
        ),
    ],
)
def test_settings_panel_when_body_view(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    args: dict[str, Any],
    expected_checks: list[tuple[str, bool]],
    expected_call: list[Any],
    expected_buttons: list[str],
    expected_texts: list[str],
) -> None:
    """セクションの折りたたみのチェックを出し、切り替えを知らせる。保存のボタンの比べには使わない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行（本文の見せ方のチェックを押す）
    observed = _observe(preview_page, **args)
    # 検証
    checks = [(check["name"], check["checked"]) for check in observed["detailChecks"]]
    assert checks == expected_checks
    assert observed["calls"] == [expected_call]
    assert all(label in observed["buttons"] for label in expected_buttons)
    assert "ワークスペースの既定にする" not in observed["buttons"]
    assert all(text in observed["text"] for text in expected_texts)


# 「レビューに追加した後のフォーカス」の区画の下の説明
FOCUS_DESCRIPTION = "自動は、マウスで操作する端末では入力欄へ戻し、タッチで操作する端末では戻しません。"


@pytest.mark.parametrize(
    ("args", "expected_checked", "expected_auto_sub", "expected_call", "expected_buttons", "expected_texts"),
    [
        pytest.param(
            {"focusAfterAdd": "auto", "pointerCoarse": False, "operateFocus": "戻さない"},
            "自動",
            "この端末では入力欄へ戻します",
            ["focusAfterAdd", "none"],
            [],
            [],
            id="auto_fine_press_none",
        ),
        pytest.param(
            {
                "focusAfterAdd": "none",
                "pointerCoarse": True,
                "overrides": ["レビューに追加した後のフォーカス"],
                "operateFocus": "自動",
            },
            "戻さない",
            "この端末では戻しません",
            ["focusAfterAdd", "auto"],
            ["既定に戻す"],
            ["表示する種類は、ワークスペースの既定と同じです。"],
            id="none_coarse_press_auto",
        ),
    ],
)
def test_settings_panel_when_focus_after_add(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    args: dict[str, Any],
    expected_checked: str,
    expected_auto_sub: str,
    expected_call: list[Any],
    expected_buttons: list[str],
    expected_texts: list[str],
) -> None:
    """「レビューに追加した後のフォーカス」のラジオを出し、切り替えを知らせる。保存のボタンの比べには使わない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行（ラジオを押す）
    observed = _observe(preview_page, **args)
    # 検証
    focus = observed["focus"]
    assert focus is not None
    assert focus["section"] == "コメントの入力"
    assert [radio["text"].split("この端末")[0] for radio in focus["radios"]] == ["自動", "入力欄へ戻す", "戻さない"]
    assert next(radio["text"] for radio in focus["radios"] if radio["checked"]).startswith(expected_checked)
    assert expected_auto_sub in focus["radios"][0]["text"]
    assert focus["description"] == FOCUS_DESCRIPTION
    assert observed["calls"] == [expected_call]
    assert all(label in observed["buttons"] for label in expected_buttons)
    assert "ワークスペースの既定にする" not in observed["buttons"]
    assert all(text in observed["text"] for text in expected_texts)
