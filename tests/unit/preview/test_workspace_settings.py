"""screens/workspace-settings.ts（設定の画面・設定の値を使っている件数）の単体テスト。"""

from __future__ import annotations

import re
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem
from .thread_data import make_thread

# 設定の画面を作って文書に置く JavaScript。呼ばれた操作は window.calls に溜める
MOUNT_SCRIPT = """({data}) => {
    window.calls = [];
    const index = MindmapPreview.buildIndex(data);
    const screen = MindmapPreview.workspaceSettings({
        settings: data.settings,
        index,
        marks: {},
        errors: {},
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
    assert legends == ["話し合い", "進め方", "タグと関連", "変更履歴"]
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
        pytest.param("phases", "問い", 1, id="phase"),
        pytest.param("tags", "画面", 3, id="tag"),
        pytest.param("tags", "保存", 0, id="unused_tag"),
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
        decisions=[make_item("D-1", phase="問い", tags=["画面"])],
        tasks=[make_item("T-1", tags=["画面"])],
    )
    threads = [make_thread("TH-1", tags=["画面"])]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([data, threads, key, value]) => MindmapPreview.usageCount({
            index: MindmapPreview.buildIndex(data), threads, key, value,
        })""",
        [data, threads, key, value],
    )
    # 検証
    assert result == expected
