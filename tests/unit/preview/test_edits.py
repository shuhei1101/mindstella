"""core/edits.ts（保存待ちの編集を当てた記録・保存待ちの印の種類）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeEdit, MakeItem


def test_apply_edits(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    make_edit: MakeEdit,
    valid_settings: dict[str, Any],
) -> None:
    """編集の種類ごとに当て、元の記録を変えない（正常系）。"""
    # 準備
    options = [
        {"key": "A", "content": "案 A", "adopted": True},
        {"key": "B", "content": "案 B"},
    ]
    data = make_data(
        decisions=[make_item("D-1", options=options)],
        tasks=[make_item("T-1")],
        settings={**valid_settings, "summary": "話し合い"},
    )
    edits = [
        make_edit("E-1", value="編集した答え"),
        make_edit("E-2", op="option-add", key="C", value={"content": "案 C"}, before=None),
        make_edit("E-3", op="adopt", key="C", value="C", before="A"),
        make_edit("E-4", target="T-1", op="item-remove", key=None, value=None),
        make_edit(
            "E-5",
            target="new-1",
            op="item-add",
            key="tasks",
            value={"title": "画面を作る", "kind": "作業", "status": "未着手"},
            before=None,
            base=None,
        ),
        make_edit(
            "E-6",
            target="settings",
            op="setting",
            key="summary",
            value="画面の編集",
            before="話し合い",
            base=None,
        ),
    ]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([data, edits]) => {
            const before = JSON.stringify(data);
            const applied = MindmapPreview.applyEdits(data, edits);
            const decision = applied.decisions.find((item) => item.id === "D-1");
            return {
                answer: decision.answer,
                optionKeys: decision.options.map((option) => option.key),
                adopted: decision.options.filter((option) => option.adopted).map((o) => o.key),
                taskIds: applied.tasks.map((item) => item.id),
                summary: applied.settings.summary,
                unchanged: JSON.stringify(data) === before,
            };
        }""",
        [data, edits],
    )
    # 検証
    assert result == {
        "answer": "編集した答え",
        "optionKeys": ["A", "B", "C"],
        "adopted": ["C"],
        "taskIds": ["T-1", "new-1"],
        "summary": "画面の編集",
        "unchanged": True,
    }


@pytest.mark.parametrize(
    ("target", "key", "blocked", "expected"),
    [
        pytest.param("D-1", None, [], "pending", id="item"),
        pytest.param("D-1", "answer", [], "pending", id="key"),
        pytest.param("D-1", "C", [], "pending", id="option"),
        pytest.param("N-1", None, [], "remove", id="removing"),
        pytest.param("T-1", None, [], None, id="no_edit"),
        pytest.param("D-1", None, ["E-1"], "blocked", id="blocked"),
    ],
)
def test_pending_mark_of(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_edit: MakeEdit,
    target: str,
    key: str | None,
    blocked: list[str],
    expected: str | None,
) -> None:
    """書き込めない・削除・保存待ちの順に決める（正常系）。"""
    # 準備
    edits = [
        make_edit("E-1"),
        make_edit("E-2", target="N-1", op="item-remove", key=None, value=None),
        make_edit("E-3", op="option-add", key="C", value={"content": "案 C"}, before=None),
    ]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([edits, blocked, target, key]) => {
            const args = {edits, blocked: new Set(blocked), target};
            if (key !== null) args.key = key;
            return MindmapPreview.pendingMarkOf(args);
        }""",
        [edits, blocked, target, key],
    )
    # 検証
    assert result == expected
