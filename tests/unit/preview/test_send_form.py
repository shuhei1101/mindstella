"""components/send-form.ts（コメントの入力の部品と日時の表示）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 部品の状態を見て返す JavaScript（部品を作って文書に置き、入力欄・ボタン・結果の要素の属性を集める）
OBSERVE_SCRIPT = """(props) => {
    const noop = () => {};
    const form = MindmapPreview.sendForm({
        ...props,
        on: {input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop},
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
            {"target": "D-1", "body": "案 A にする", "status": "saving"},
            {
                "submitDisabled": True,
                "readOnly": True,
                "invalid": None,
                "hasCopy": False,
                "describedByStatus": True,
            },
            "",
            id="saving",
        ),
        pytest.param(
            {"target": "D-1", "body": "", "status": "saved", "count": 3},
            {
                "submitDisabled": False,
                "readOnly": False,
                "invalid": None,
                "hasCopy": False,
                "describedByStatus": True,
            },
            "レビューに追加しました（レビュー中 3 件）。",
            id="saved",
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
            "コメントを入れてから追加してください。",
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
                "target": "A-5",
                "body": "ここは言い換える",
                "status": "failed",
                "detail": "選んだ文が本文の 3 行目にありません",
            },
            {
                "submitDisabled": False,
                "readOnly": False,
                "invalid": None,
                "hasCopy": False,
                "describedByStatus": True,
            },
            "レビューに追加できませんでした。選んだ文が本文の 3 行目にありません",
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


# 添えた箇所と項目を指さない形を見て返す JavaScript（部品を作って文書に置き、× を押して on.unquote の回数も数える）
LOCATION_SCRIPT = """(props) => {
    const noop = () => {};
    let unquoteCalls = 0;
    const form = MindmapPreview.sendForm({
        ...props,
        on: {
            input: noop, save: noop, copy: noop, focus: noop, blur: noop,
            unquote: () => {
                unquoteCalls += 1;
            },
        },
    });
    document.body.append(form);
    const textarea = form.querySelector("textarea");
    const buttons = [...form.querySelectorAll("button")];
    const unquote = buttons.find(
        (button) => /×|外/.test(button.textContent + (button.getAttribute("aria-label") ?? ""))
    );
    if (unquote !== undefined) unquote.click();
    return {
        text: form.textContent,
        labelVisible: [...form.querySelectorAll("label")].some(
            (label) => label.offsetParent !== null && label.textContent.trim() !== ""
        ),
        ariaLabel: textarea.getAttribute("aria-label"),
        hasSubmit: buttons.some((button) => button.textContent.trim() === "レビューに追加"),
        rows: textarea.rows,
        unquoteCalls,
    };
}"""


@pytest.mark.parametrize(
    ("props", "expected", "expected_texts", "expected_unquote_calls"),
    [
        pytest.param(
            {
                "target": "A-005",
                "loc": {"kind": "body", "start": 3, "end": 3, "text": "受け取る人へ渡す形"},
            },
            {"labelVisible": True},
            ["本文 3 行目", "受け取る人へ渡す形"],
            1,
            id="location",
        ),
        pytest.param(
            {"target": None},
            {"labelVisible": False, "ariaLabel": "項目を指さないコメント", "hasSubmit": True},
            [],
            0,
            id="no_target",
        ),
        pytest.param(
            {"target": None, "collapsed": True},
            {"labelVisible": False, "hasSubmit": False, "rows": 1},
            [],
            0,
            id="no_target_collapsed",
        ),
    ],
)
def test_send_form_when_location_and_no_target(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected: dict[str, Any],
    expected_texts: list[str],
    expected_unquote_calls: int,
) -> None:
    """添えた箇所と項目を指さない形（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(LOCATION_SCRIPT, props)
    # 検証
    assert expected.items() <= observed.items()
    assert all(text in observed["text"] for text in expected_texts)
    assert observed["unquoteCalls"] == expected_unquote_calls


@pytest.mark.parametrize(
    ("status", "expected_saved"),
    [
        pytest.param("idle", ["案 A にする"], id="idle"),
        pytest.param("saving", [], id="saving"),
    ],
)
def test_send_form_when_ctrl_enter(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str,
    expected_saved: list[str],
) -> None:
    """Ctrl+Enter で溜め、溜めている間は溜めない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    saved = preview_page.evaluate(
        """(status) => {
            const saved = [];
            const noop = () => {};
            const form = MindmapPreview.sendForm({
                target: "D-1", body: "案 A にする", status,
                on: {
                    input: noop, unquote: noop, copy: noop, focus: noop, blur: noop,
                    save: (body) => saved.push(body),
                },
            });
            document.body.append(form);
            form.querySelector("textarea").dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: "Enter", ctrlKey: true, bubbles: true, cancelable: true,
                })
            );
            return saved;
        }""",
        status,
    )
    # 検証
    assert saved == expected_saved


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
