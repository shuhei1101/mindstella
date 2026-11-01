"""screens/pending-edits.ts（保存待ちのパネル・編集の行の文言・項目ごとのまとまり）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeEdit, MakeItem

# パネルを作って文書に置き、見た目を集めて返す JavaScript。呼ばれた操作は window.calls に溜める
PANEL_SCRIPT = """({data, edits, blocked, status}) => {
    window.calls = [];
    const record = (name) => (...args) => window.calls.push([name, ...args]);
    const panel = MindmapPreview.pendingEditsPanel({
        edits,
        blocked,
        index: MindmapPreview.buildIndex(data),
        status,
        on: {
            close: record("close"),
            open: record("open"),
            undo: record("undo"),
            save: record("save"),
        },
    });
    document.body.append(panel);
    const norm = (text) => text.replace(/\\s+/g, " ").trim();
    const saveButton = [...panel.querySelectorAll("button")].find((button) =>
        norm(button.textContent).startsWith("まとめて保存する") ||
        norm(button.textContent).startsWith("保存しています")
    );
    return {
        text: norm(panel.textContent),
        alert: [...panel.querySelectorAll('[role="alert"]')].map((node) => norm(node.textContent)),
        saveText: saveButton === undefined ? null : norm(saveButton.textContent),
        saveDisabled: saveButton === undefined ? null : saveButton.disabled,
        saveBusy: saveButton === undefined ? null : saveButton.getAttribute("aria-busy"),
    };
}"""


def _data(make_data: MakeData, make_item: MakeItem) -> dict[str, Any]:
    """パネルが項目の種類とタイトルを引く記録を作る。"""
    return make_data(
        decisions=[make_item("D-1", title="最初の問い")],
        notes=[make_item("N-1", title="消すメモ")],
    )


def test_pending_edits_panel(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    make_edit: MakeEdit,
) -> None:
    """項目ごとのまとまりと件数、削除の件数を出し、操作を知らせる（正常系）。"""
    # 準備
    edits = [
        make_edit("E-1"),
        make_edit("E-2", target="N-1", op="item-remove", key=None, value=None),
        make_edit(
            "E-3",
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
        PANEL_SCRIPT,
        {"data": _data(make_data, make_item), "edits": edits, "blocked": [], "status": "idle"},
    )
    undo_buttons = preview_page.get_by_role("button", name="の編集を取り消す")
    undo_buttons.first.click()
    preview_page.get_by_role("button", name="まとめて保存する（1 件を削除）").click()
    calls = preview_page.evaluate("() => window.calls")
    # 検証
    assert "保存待ち" in result["text"]
    assert "3 件" in result["text"]
    assert "D-1" in result["text"]
    assert "最初の問い" in result["text"]
    assert "N-1" in result["text"]
    assert "設定" in result["text"]
    assert "3 件（うち削除 1 件）をワークスペースに書きます" in result["text"]
    assert result["saveText"] == "まとめて保存する（1 件を削除）"
    assert calls == [["undo", "E-1"], ["save"]]


@pytest.mark.parametrize(
    ("edit_count", "blocked", "status", "expected_alerts", "expected_text", "expected_save"),
    [
        pytest.param(
            0,
            [],
            "idle",
            [],
            "保存待ちの編集はありません。",
            {"disabled": True, "busy": None},
            id="empty",
        ),
        pytest.param(
            1,
            [{"id": "E-1", "reason": "changed", "detail": "書き換わっています", "refs": []}],
            "idle",
            ["1 件の編集を書き込めないため、何も保存していません。"],
            "書き込めない編集を取り消してから、もう一度保存してください。",
            {"disabled": False, "busy": None},
            id="blocked",
        ),
        pytest.param(
            1,
            [],
            "offline",
            ["サーバーにつながらないため、保存できませんでした。"],
            "保存待ちの編集は残っています。",
            {"disabled": False, "busy": None},
            id="offline",
        ),
        pytest.param(
            1,
            [],
            "saving",
            [],
            "保存しています…",
            {"disabled": True, "busy": "true"},
            id="saving",
        ),
    ],
)
def test_pending_edits_panel_when_empty_or_blocked(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    make_edit: MakeEdit,
    edit_count: int,
    blocked: list[dict[str, Any]],
    status: str,
    expected_alerts: list[str],
    expected_text: str,
    expected_save: dict[str, Any],
) -> None:
    """空・書き込めない・届かない・送信中の表示（異常系）。"""
    # 準備
    edits = [make_edit("E-1")][:edit_count]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        PANEL_SCRIPT,
        {
            "data": _data(make_data, make_item),
            "edits": edits,
            "blocked": blocked,
            "status": status,
        },
    )
    # 検証
    assert len(result["alert"]) == len(expected_alerts)
    assert all(
        actual.startswith(expected)
        for actual, expected in zip(result["alert"], expected_alerts, strict=True)
    )
    assert expected_text in result["text"]
    assert result["saveDisabled"] is expected_save["disabled"]
    assert result["saveBusy"] == expected_save["busy"]


@pytest.mark.parametrize(
    ("edit", "expected"),
    [
        pytest.param(
            {"key": "status", "value": "中止", "before": "未着手"},
            {"what": "状態", "before": "未着手", "after": "中止"},
            id="set_status",
        ),
        pytest.param(
            {"key": "body", "value": "本文", "before": "前の本文"},
            {"what": "本文", "before": None, "after": None},
            id="set_body",
        ),
        pytest.param(
            {"op": "option-add", "key": "C", "value": {"content": "中身"}, "before": None},
            {"what": "案 C を追加", "before": None, "after": "中身"},
            id="option_add",
        ),
        pytest.param(
            {"op": "adopt", "key": "C", "value": "C", "before": "A"},
            {"what": "採用する案", "before": "A", "after": "C"},
            id="adopt",
        ),
        pytest.param(
            {"op": "item-remove", "key": None, "value": None},
            {"what": "項目を削除", "before": None, "after": None},
            id="item_remove",
        ),
    ],
)
def test_edit_row_text(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_edit: MakeEdit,
    edit: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """編集の種類ごとの文言（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        "(edit) => MindmapPreview.editRowText(edit)", make_edit("E-1", **edit)
    )
    # 検証
    assert result == expected


def test_edit_row_text_when_setting(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_edit: MakeEdit
) -> None:
    """設定のキーはキーの呼び名で出す（正常系）。"""
    # 準備
    load_preview_scripts()
    edit = make_edit(
        "E-1",
        target="settings",
        op="setting",
        key="categories",
        value=["画面", "保存"],
        before=["画面"],
        base=None,
    )
    # 実行
    result = preview_page.evaluate("(edit) => MindmapPreview.editRowText(edit)", edit)
    # 検証
    assert result["what"] == "カテゴリー"
    assert "保存" in result["after"]


def test_group_edits(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_edit: MakeEdit
) -> None:
    """最初に溜めた順にまとめる（正常系）。"""
    # 準備
    edits = [
        make_edit("E-1", target="D-1"),
        make_edit("E-2", target="T-1", key="status", value="中止"),
        make_edit("E-3", target="D-1", key="reason", value="理由"),
    ]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(edits) => MindmapPreview.groupEdits(edits).map(
            (group) => [group.target, group.edits.map((edit) => edit.id)]
        )""",
        edits,
    )
    # 検証
    assert result == [["D-1", ["E-1", "E-3"]], ["T-1", ["E-2"]]]
