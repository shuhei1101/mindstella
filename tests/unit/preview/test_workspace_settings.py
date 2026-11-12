"""screens/workspace-settings.ts（設定の画面・設定の値を使っている件数）の単体テスト。"""

from __future__ import annotations

import re
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem

# 設定の画面を作って文書に置く JavaScript。呼ばれた操作は window.calls に溜める
MOUNT_SCRIPT = """({data, transcription}) => {
    window.calls = [];
    const index = MindmapPreview.buildIndex(data);
    const screen = MindmapPreview.workspaceSettings({
        settings: data.settings,
        index,
        marks: {},
        errors: {},
        transcription: transcription ?? null,
        on: {
            change: (input) => window.calls.push(["change", input]),
            close: () => window.calls.push(["close"]),
        },
    });
    document.body.append(screen);
    return [...screen.querySelectorAll("fieldset legend")].map((node) => node.textContent.trim());
}"""


def test_workspace_settings(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
) -> None:
    """まとまりごとに並べ、離れたときにキーを溜める（正常系）。"""
    # 準備
    data = make_data(settings={**make_data()["settings"], "summary": "話し合い"})
    load_preview_scripts()
    legends = preview_page.evaluate(MOUNT_SCRIPT, {"data": data})
    # 実行
    title = preview_page.get_by_label("題名", exact=True)
    title.fill("画面の編集")
    title.blur()
    limit = preview_page.get_by_label("保持する回数", exact=True)
    limit.fill("3")
    limit.blur()
    calls = preview_page.evaluate(
        "() => window.calls.map(([name, input]) => [name, input.key, input.value])"
    )
    # 検証
    assert legends == ["話し合い", "進め方", "関連", "変更履歴", "音声入力"]
    assert calls == [["change", "summary", "画面の編集"], ["change", "history_limit", 3]]


def test_workspace_settings_when_used_value_removed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """使われている値を外すと付け替え先を選ぶまで溜めない（正常系）。"""
    # 準備
    base_settings = make_data()["settings"]
    settings = {
        **{key: value for key, value in base_settings.items() if key != "goal"},
        "phases": ["問い", "発散"],
    }
    data = make_data(
        settings=settings,
        decisions=[make_item("D-1", phase="問い"), make_item("D-2", phase="問い")],
    )
    load_preview_scripts()
    preview_page.evaluate(MOUNT_SCRIPT, {"data": data})
    # 実行
    preview_page.get_by_role(
        "button", name=re.compile("問い.*(外す|削除|×)|(外す|削除|×).*問い")
    ).click()
    texts = preview_page.evaluate("() => document.body.textContent")
    calls_before = preview_page.evaluate("() => window.calls.length")
    preview_page.get_by_label(re.compile("付け替え先")).select_option("発散")
    calls_after = preview_page.evaluate(
        "() => window.calls.map(([name, input]) => [name, input.key, input.value, input.map])"
    )
    # 検証
    assert "問い を使っている 2 件の付け替え先" in texts
    assert "付け替え先を選ぶと保存待ちに入ります。" in texts
    assert calls_before == 0
    assert calls_after == [["change", "phases", ["発散"], {"問い": "発散"}]]


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        pytest.param("phases", "問い", 2, id="phase"),
        pytest.param("categories", "画面", 1, id="category"),
        pytest.param("phases", "発散", 0, id="unused_phase"),
    ],
)
def test_usage_count(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    key: str,
    value: str,
    expected: int,
) -> None:
    """キーごとに使っている件数を数える（正常系）。"""
    # 準備
    data: dict[str, Any] = make_data(
        decisions=[make_item("D-1", phase="問い"), make_item("D-2", phase="問い")],
        tasks=[make_item("T-1", category="画面")],
    )
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([data, key, value]) => MindmapPreview.usageCount({
            index: MindmapPreview.buildIndex(data), key, value,
        })""",
        [data, key, value],
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("transcription", "settings_preset", "select_preset", "expected_calls", "expected_options", "disabled", "hint"),
    [
        pytest.param(
            {"available": True, "reason": None, "detail": None, "presets": ["一般", "開発"], "action": "send", "preset": None},
            None,
            "開発",
            [
                ["change", "transcription", {"action": "send", "preset": None}],
                ["change", "transcription", {"action": "send", "preset": "開発"}],
            ],
            ["サービスの既定", "一般", "開発"],
            False,
            "文字起こしの補正に使用する用語集です。候補は文字起こしのサービスから取得します。",
            id="available",
        ),
        pytest.param(
            {"available": False, "reason": "unsupported", "detail": "x", "presets": [], "action": "send", "preset": "開発"},
            "開発",
            None,
            [["change", "transcription", {"action": "send", "preset": "開発"}]],
            ["開発"],
            True,
            "文字起こしのサービスが音声の受け付けに対応していないため、候補を取得できません。",
            id="unsupported",
        ),
    ],
)
def test_workspace_settings_when_transcription(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    transcription: dict[str, Any],
    settings_preset: str | None,
    select_preset: str | None,
    expected_calls: list[list[Any]],
    expected_options: list[str],
    disabled: bool,
    hint: str,
) -> None:
    """音声入力のまとまりで挙動とプリセットを溜め、使えないときはプリセットを押せなくする（正常系）。"""
    # 準備
    data = make_data(settings={**make_data()["settings"], "transcription": {"preset": settings_preset}})
    load_preview_scripts()
    legends = preview_page.evaluate(MOUNT_SCRIPT, {"data": data, "transcription": transcription})
    # 実行
    preview_page.get_by_label("送信する", exact=True).check()
    preset = preview_page.get_by_label("用語集のプリセット", exact=True)
    observed = preview_page.evaluate(
        """({select}) => {
            const node = [...document.querySelectorAll("select")].find(
                (candidate) => candidate.labels?.[0]?.textContent.trim() === "用語集のプリセット"
            );
            if (select !== null) {
                node.value = select;
                node.dispatchEvent(new Event("change", {bubbles: true}));
            }
            return {
                options: [...node.options].map((option) => option.textContent.trim()),
                disabled: node.disabled,
                hint: document.getElementById(node.getAttribute("aria-describedby")).textContent.trim(),
                calls: window.calls.map(([name, input]) => [name, input.key, input.value]),
            };
        }""",
        {"select": select_preset},
    )
    # 検証
    assert legends[-1] == "音声入力"
    assert preset.count() == 1
    assert observed["calls"] == expected_calls
    assert observed["options"] == expected_options
    assert observed["disabled"] is disabled
    assert observed["hint"] == hint
