"""components/send-form.ts（回答・意見の送信の部品と日時の表示）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 部品の状態を見て返す JavaScript（部品を作って文書に置き、入力欄・送るボタン・結果の要素の属性を集める）
OBSERVE_SCRIPT = """(props) => {
    const noop = () => {};
    const form = MindmapPreview.sendForm({
        ...props, onInput: noop, onSend: noop, onCopy: noop,
    });
    document.body.append(form);
    const textarea = form.querySelector("textarea");
    const submit = form.querySelector('button[type="submit"]');
    const status = form.querySelector('[role="status"]');
    const buttonLabels = [...form.querySelectorAll("button")].map(
        (button) => button.textContent.trim()
    );
    return {
        submitDisabled: submit.disabled,
        readOnly: textarea.readOnly,
        invalid: textarea.getAttribute("aria-invalid"),
        hasCopy: buttonLabels.includes("本文を写す"),
        describedByStatus: status !== null && textarea.getAttribute("aria-describedby") === status.id,
        statusText: status === null ? "" : status.textContent,
    };
}"""


@pytest.mark.parametrize(
    ("props", "expected", "expected_text"),
    [
        pytest.param(
            {"target": "D-1", "body": "案 A にする", "status": "sending"},
            {
                "submitDisabled": True,
                "readOnly": True,
                "invalid": None,
                "hasCopy": False,
                "describedByStatus": True,
            },
            "",
            id="sending",
        ),
        pytest.param(
            {"target": "D-1", "body": "", "status": "empty"},
            {
                "submitDisabled": False,
                "readOnly": False,
                "invalid": "true",
                "hasCopy": False,
                "describedByStatus": True,
            },
            "回答・意見を入れてから送ってください。",
            id="empty",
        ),
        pytest.param(
            {"target": "D-1", "body": "案 A にする", "status": "failed"},
            {
                "submitDisabled": False,
                "readOnly": False,
                "invalid": None,
                "hasCopy": True,
                "describedByStatus": True,
            },
            "起動スクリプトで立ち上げ直し",
            id="failed_unreachable",
        ),
        pytest.param(
            {
                "target": "D-1",
                "body": "案 A にする",
                "status": "failed",
                "detail": "項目 D-022 がワークスペースにありません",
            },
            {
                "submitDisabled": False,
                "readOnly": False,
                "invalid": None,
                "hasCopy": False,
                "describedByStatus": True,
            },
            "項目 D-022 がワークスペースにありません",
            id="failed_detail",
        ),
    ],
)
def test_send_form(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected: dict[str, Any],
    expected_text: str,
) -> None:
    """状態ごとの入力欄と結果（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(OBSERVE_SCRIPT, props)
    # 検証
    status_text = observed.pop("statusText")
    assert observed == expected
    assert expected_text in status_text


@pytest.mark.parametrize(
    ("status", "expected_sent"),
    [
        pytest.param("idle", ["案 A にする"], id="idle"),
        pytest.param("sending", [], id="sending"),
    ],
)
def test_send_form_when_ctrl_enter(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str,
    expected_sent: list[str],
) -> None:
    """Ctrl+Enter で送り、送っている間は送らない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    sent = preview_page.evaluate(
        """(status) => {
            const sent = [];
            const noop = () => {};
            const form = MindmapPreview.sendForm({
                target: "D-1", body: "案 A にする", status,
                onInput: noop, onSend: (body) => sent.push(body), onCopy: noop,
            });
            document.body.append(form);
            form.querySelector("textarea").dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: "Enter", ctrlKey: true, bubbles: true, cancelable: true,
                })
            );
            return sent;
        }""",
        status,
    )
    # 検証
    assert sent == expected_sent


@pytest.mark.parametrize(
    ("iso", "expected"),
    [
        pytest.param("2026-10-04T02:23:00+00:00", "10/04 11:23", id="same_day"),
        pytest.param("2026-10-04T16:05:00+00:00", "10/05 01:05", id="next_day"),
    ],
)
def test_format_jst(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, iso: str, expected: str
) -> None:
    """UTC を JST にする（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    formatted = preview_page.evaluate("(iso) => MindmapPreview.formatJst(iso)", iso)
    # 検証
    assert formatted == expected
