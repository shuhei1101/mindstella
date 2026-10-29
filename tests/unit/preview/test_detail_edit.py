"""screens/detail-edit.ts（詳細パネルの編集の表示・編集できるキーの並び・記録で使われているタグ）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem
from .thread_data import make_thread

# 編集の表示を作って文書に置く JavaScript。呼ばれた操作は window.calls に溜める
MOUNT_SCRIPT = """({kind, item, settings, removing, referrers, usedTags}) => {
    window.calls = [];
    const form = MindmapPreview.detailEditForm({
        kind,
        item,
        settings,
        marks: {},
        removing,
        removedOptions: [],
        blocked: {},
        referrers,
        errors: {},
        usedTags,
        on: {
            change: (input) => window.calls.push(["change", input]),
            remove: () => window.calls.push(["remove"]),
            cancelRemove: () => window.calls.push(["cancelRemove"]),
        },
    });
    document.body.append(form);
}"""

# 編集の表示に渡す、案 A・B を持つ検討事項の引数
DECISION_OPTIONS = [
    {"key": "A", "content": "案 A", "adopted": True},
    {"key": "B", "content": "案 B"},
]


def _mount(
    preview_page: Page, item: dict[str, Any], valid_settings: dict[str, Any], **overrides: Any
) -> None:
    """検討事項の編集の表示を文書に置く。引数は overrides で上書きする。"""
    args: dict[str, Any] = {
        "kind": "decisions",
        "item": item,
        "settings": valid_settings,
        "removing": False,
        "referrers": [],
        "usedTags": [],
    }
    args.update(overrides)
    preview_page.evaluate(MOUNT_SCRIPT, args)


def test_detail_edit_form(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """離れたときにキー・案を溜める（正常系）。"""
    # 準備
    load_preview_scripts()
    _mount(preview_page, make_item("D-1", options=DECISION_OPTIONS), valid_settings)
    # 実行
    answer = preview_page.get_by_label("決定内容", exact=True)
    answer.fill("案 B にする")
    answer.blur()
    preview_page.get_by_role("radio", name="採用").nth(1).check()
    preview_page.get_by_role("button", name="案を追加").click()
    added = preview_page.get_by_label("案 C の中身")
    added.fill("案 C の中身")
    added.blur()
    calls = preview_page.evaluate(
        "() => window.calls.map(([name, input]) => [input.op, input.key])"
    )
    # 検証
    assert calls == [["set", "answer"], ["adopt", "B"], ["option-add", "C"]]


@pytest.mark.parametrize(
    ("overrides", "expected_texts"),
    [
        pytest.param(
            {"removing": True},
            ["削除を溜めています。削除を取り消すと編集できます。", "削除を取り消す"],
            id="removing",
        ),
        pytest.param(
            {"referrers": ["D-2"]},
            [
                "D-2 が指しているため、保存のときに削除できません。"
                "指している項目から外すと削除できます。"
            ],
            id="referrers",
        ),
    ],
)
def test_detail_edit_form_when_removing_or_referenced(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    overrides: dict[str, Any],
    expected_texts: list[str],
) -> None:
    """削除を溜めた項目は読むだけにし、指されている項目は警告を出す（異常系）。"""
    # 準備
    load_preview_scripts()
    _mount(preview_page, make_item("D-1", options=DECISION_OPTIONS), valid_settings, **overrides)
    # 実行
    text = preview_page.evaluate("() => document.body.textContent")
    changes = preview_page.evaluate("() => window.calls.length")
    # 検証
    assert all(expected in text for expected in expected_texts)
    assert changes == 0


def test_detail_edit_form_when_title_blank(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """空白だけのタイトルは溜めない（異常系）。"""
    # 準備
    load_preview_scripts()
    _mount(preview_page, make_item("D-1", options=DECISION_OPTIONS), valid_settings)
    title = preview_page.get_by_label("タイトル", exact=False).first
    # 実行
    title.fill("   ")
    title.blur()
    # 検証
    assert preview_page.evaluate("() => window.calls.length") == 0
    assert title.get_attribute("aria-invalid") == "true"
    assert "タイトルを書いてください。" in preview_page.evaluate("() => document.body.textContent")


@pytest.mark.parametrize(
    ("kind", "expected_keys", "absent_keys"),
    [
        pytest.param(
            "decisions",
            ["status", "title", "options", "answer", "reason", "body"],
            ["id"],
            id="decisions",
        ),
        pytest.param("notes", ["title", "content", "withdrawn", "reason"], ["id"], id="notes"),
    ],
)
def test_editable_keys(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    kind: str,
    expected_keys: list[str],
    absent_keys: list[str],
) -> None:
    """検討事項は案を含み、記録の種類は取り下げを含む（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    keys = preview_page.evaluate(
        "(kind) => MindmapPreview.editableKeys(kind).map((entry) => entry.key)", kind
    )
    # 検証
    assert set(expected_keys) <= set(keys)
    assert not set(absent_keys) & set(keys)


def test_used_tags(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """表記をそろえて重なりを除き、件数の多い順に並べる（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", tags=["API"])],
        tasks=[make_item("T-1", tags=["ａｐｉ", "画面"])],
        notes=[make_item("N-1", tags=["保存"])],
    )
    threads = [make_thread("TH-1", tags=["画面"])]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([data, threads]) => MindmapPreview.usedTags({
            index: MindmapPreview.buildIndex(data), threads,
        })""",
        [data, threads],
    )
    # 検証
    assert result == ["api", "画面", "保存"]
