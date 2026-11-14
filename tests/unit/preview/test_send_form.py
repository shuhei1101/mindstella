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
        on: {input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop, toggle: noop},
    });
    document.body.append(form);
    const textarea = form.querySelector("textarea");
    const submit = form.querySelector('button[type="submit"]');
    const status = form.querySelector('[role="status"]');
    const buttonNames = [...form.querySelectorAll("button")].map(
        (button) => button.getAttribute("aria-label") ?? button.textContent.trim()
    );
    return {
        submitDisabled: submit.disabled,
        readOnly: textarea.readOnly,
        invalid: textarea.getAttribute("aria-invalid"),
        hasCopy: buttonNames.includes("本文をコピー"),
        describedByStatus: status !== null && textarea.getAttribute("aria-describedby") === status.id,
        statusText: status === null ? "" : status.textContent,
        submitButton: {
            text: submit.textContent.trim(),
            label: submit.getAttribute("aria-label"),
            title: submit.getAttribute("title"),
            sameRowAsTextarea: submit.parentElement === textarea.parentElement,
        },
    };
}"""

# アイコンだけの「レビューに追加」のボタンの属性（状態によらず同じ）
EXPECTED_SUBMIT_BUTTON = {
    "text": "",
    "label": "レビューに追加",
    "title": "レビューに追加（Ctrl+Enter）",
    "sameRowAsTextarea": True,
}


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
    submit_button = observed.pop("submitButton")
    assert observed == expected
    assert expected_text in status_text
    assert submit_button == EXPECTED_SUBMIT_BUTTON


# 添えた箇所と項目を指さない形を見て返す JavaScript（部品を作って文書に置き、× を押して on.unquote の回数も数える）
LOCATION_SCRIPT = """(props) => {
    const noop = () => {};
    let unquoteCalls = 0;
    const form = MindmapPreview.sendForm({
        ...props,
        on: {
            input: noop, save: noop, copy: noop, focus: noop, blur: noop, toggle: noop,
            unquote: () => {
                unquoteCalls += 1;
            },
        },
    });
    document.body.append(form);
    const textarea = form.querySelector("textarea");
    const buttons = [...form.querySelectorAll("button")];
    const unquote = buttons.find((button) => button.getAttribute("aria-label") === "箇所を外す");
    if (unquote !== undefined) unquote.click();
    return {
        text: form.textContent,
        labelVisible: [...form.querySelectorAll("label")].some(
            (label) => label.offsetParent !== null && label.textContent.trim() !== ""
        ),
        ariaLabel: textarea.getAttribute("aria-label"),
        hasSubmit: buttons.some((button) => button.getAttribute("aria-label") === "レビューに追加"),
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
            {"labelVisible": True, "rows": 1},
            ["本文 3 行目", "受け取る人へ渡す形"],
            1,
            id="location",
        ),
        pytest.param(
            {"target": None},
            {
                "labelVisible": False,
                "ariaLabel": "項目を指さないコメント",
                "hasSubmit": True,
                "rows": 1,
            },
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
                    input: noop, unquote: noop, copy: noop, focus: noop, blur: noop, toggle: noop,
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


# 開閉のボタンと閉じた形を見て返す JavaScript（部品を作って文書に置き、開閉のボタンを押して on.toggle に渡った値を集める）
OPEN_SCRIPT = """(props) => {
    const noop = () => {};
    const toggled = [];
    const form = MindmapPreview.sendForm({
        ...props,
        on: {
            input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop,
            toggle: (open) => toggled.push(open),
        },
    });
    document.body.append(form);
    const toggle = form.querySelector("button[aria-expanded]");
    const body = form.querySelector(".send-body");
    if (toggle !== null) toggle.click();
    return {
        hasToggle: toggle !== null,
        expanded: toggle === null ? null : toggle.getAttribute("aria-expanded"),
        label: toggle === null ? null : toggle.getAttribute("aria-label"),
        controlsBody: toggle !== null && body !== null && toggle.getAttribute("aria-controls") === body.id,
        bodyHidden: body === null ? null : body.hidden,
        hasDraftMark: form.querySelector(".send-head")?.textContent.includes("書きかけ") ?? false,
        toggled,
    };
}"""


@pytest.mark.parametrize(
    ("props", "expected"),
    [
        pytest.param(
            {"target": "D-022", "open": True},
            {
                "hasToggle": True,
                "expanded": "true",
                "label": "コメントの入力を閉じる",
                "controlsBody": True,
                "bodyHidden": False,
                "hasDraftMark": False,
                "toggled": [False],
            },
            id="open",
        ),
        pytest.param(
            {"target": "D-022", "open": False},
            {
                "hasToggle": True,
                "expanded": "false",
                "label": "コメントの入力を開く",
                "controlsBody": True,
                "bodyHidden": True,
                "hasDraftMark": False,
                "toggled": [True],
            },
            id="closed",
        ),
        pytest.param(
            {"target": "D-022", "open": False, "body": "案 A にする"},
            {
                "hasToggle": True,
                "expanded": "false",
                "label": "コメントの入力を開く",
                "controlsBody": True,
                "bodyHidden": True,
                "hasDraftMark": True,
                "toggled": [True],
            },
            id="closed_with_draft",
        ),
        pytest.param(
            {"target": None},
            {
                "hasToggle": False,
                "expanded": None,
                "label": None,
                "controlsBody": False,
                "bodyHidden": None,
                "hasDraftMark": False,
                "toggled": [],
            },
            id="no_target",
        ),
    ],
)
def test_send_form_when_open(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """開閉のボタンと閉じた形（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(OPEN_SCRIPT, props)
    # 検証
    assert observed == expected


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


# 音声入力の状態を見て返す JavaScript（マイク・×・✓ と結果の行の属性を集める）
VOICE_OBSERVE_SCRIPT = """(props) => {
    const noop = () => {};
    const on = {
        input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop, toggle: noop,
        voiceStart: noop, voiceCancel: noop, voiceDone: noop, voiceBlocked: noop,
    };
    const form = (props.thread ? MindmapPreview.replyForm : MindmapPreview.sendForm)({...props, on});
    document.body.append(form);
    const byLabel = (label) => form.querySelector(`button[aria-label="${label}"]`);
    const describe = (button) => {
        if (button === null) {
            return null;
        }
        const describedBy = button.getAttribute("aria-describedby");
        return {
            text: button.textContent.trim(),
            disabled: button.disabled,
            ariaDisabled: button.getAttribute("aria-disabled"),
            title: button.getAttribute("title"),
            description: describedBy === null ? null : document.getElementById(describedBy)?.textContent.trim(),
        };
    };
    const mic = byLabel("音声で入力");
    const submit = form.querySelector('button[type="submit"]');
    const status = form.querySelector('[role="status"]');
    const hidden = status === null ? [] : [...status.querySelectorAll('[aria-hidden="true"]')];
    return {
        mic: describe(mic),
        micBeforeSubmit: mic !== null && submit !== null
            && Boolean(mic.compareDocumentPosition(submit) & Node.DOCUMENT_POSITION_FOLLOWING),
        submit: submit !== null,
        cancel: describe(byLabel("キャンセル")),
        done: describe(byLabel("文字起こし") ?? byLabel("文字起こし中")),
        readOnly: form.querySelector("textarea").readOnly,
        textareaHidden: form.querySelector("textarea").hidden,
        wave: (() => {
            const wave = form.querySelector(".send-wave");
            return wave === null ? null : {
                ariaHidden: wave.getAttribute("aria-hidden"),
                levels: [...wave.querySelectorAll("i")].map((bar) => bar.style.getPropertyValue("--lv")),
            };
        })(),
        statusText: status === null ? "" : status.textContent,
        hiddenText: hidden.map((node) => node.textContent.trim()).join(""),
        spokenText: status === null ? "" : [...status.childNodes]
            .filter((node) => !(node instanceof Element && node.getAttribute("aria-hidden") === "true"))
            .map((node) => node.textContent.trim()).join(""),
        cancelDisabled: byLabel("キャンセル")?.disabled ?? null,
        doneDisabled: (byLabel("文字起こし") ?? byLabel("文字起こし中"))?.disabled ?? null,
    };
}"""

# 音声入力のボタンを押して、呼ばれたコールバックを返す JavaScript
VOICE_EVENTS_SCRIPT = """({props, press, caret}) => {
    const calls = [];
    const noop = () => {};
    const on = {
        input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop, toggle: noop,
        voiceStart: () => calls.push(["voiceStart"]),
        voiceCancel: () => calls.push(["voiceCancel"]),
        voiceDone: (input) => calls.push(["voiceDone", input]),
        voiceBlocked: () => calls.push(["voiceBlocked"]),
    };
    const form = MindmapPreview.sendForm({...props, on});
    document.body.append(form);
    const textarea = form.querySelector("textarea");
    if (caret !== null) {
        textarea.setSelectionRange(caret, caret);
    }
    form.querySelector(`button[aria-label="${press}"]`).click();
    return calls;
}"""


@pytest.mark.parametrize(
    ("props", "expected"),
    [
        pytest.param(
            {"target": "D-1", "voice": "idle"},
            {
                "mic": {"text": "", "disabled": False, "ariaDisabled": None, "title": "音声で入力", "description": None},
                "micBeforeSubmit": True,
                "submit": True,
                "cancel": None,
                "done": None,
                "readOnly": False,
                "textareaHidden": False,
                "wave": None,
            },
            id="idle",
        ),
        pytest.param(
            {"target": "D-1", "voice": "disabled", "voiceReason": "文字起こしのサービスが起動していないため、音声で入力できません。"},
            {
                "mic": {
                    "text": "",
                    "disabled": False,
                    "ariaDisabled": "true",
                    "title": "文字起こしのサービスが起動していないため、音声で入力できません。",
                    "description": "文字起こしのサービスが起動していないため、音声で入力できません。",
                },
                "submit": True,
                "cancel": None,
                "done": None,
            },
            id="disabled",
        ),
        pytest.param(
            {"target": "D-1", "voice": "recording", "elapsed": 72, "levels": [0.2, 0.8]},
            {
                "mic": None,
                "submit": False,
                "cancel": {"text": "", "disabled": False, "ariaDisabled": None, "title": "キャンセル（録音を破棄）", "description": None},
                "done": {"text": "", "disabled": False, "ariaDisabled": None, "title": "文字起こし", "description": None},
                "readOnly": True,
                "textareaHidden": True,
                "wave": {"ariaHidden": "true", "levels": ["0.2", "0.8"]},
                "hiddenText": "1:12",
                "spokenText": "録音中",
            },
            id="recording",
        ),
        pytest.param(
            {"target": "D-1", "voice": "transcribing", "body": "確認: "},
            {"mic": None, "submit": False, "readOnly": True, "cancelDisabled": True, "doneDisabled": True},
            id="transcribing",
        ),
        pytest.param(
            {"target": "D-1", "status": "sent", "entered": False},
            {"statusText": "送信しました。Claude Code へは入力していません。"},
            id="sent",
        ),
        pytest.param(
            {"target": "D-1", "status": "inserted", "body": "確認: 案 A にする"},
            {"statusText": "文字起こしの結果を挿入しました。"},
            id="inserted",
        ),
        pytest.param(
            {"target": "D-1", "status": "reviewed"},
            {"statusText": "文字起こしの結果をレビュー中に追加しました。"},
            id="reviewed",
        ),
    ],
)
def test_send_form_when_voice(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """音声入力の状態ごとのボタンと結果の行（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(VOICE_OBSERVE_SCRIPT, props)
    # 検証
    assert {key: observed[key] for key in expected} == expected


@pytest.mark.parametrize(
    ("props", "press", "caret", "expected"),
    [
        pytest.param({"target": "D-1", "voice": "idle"}, "音声で入力", None, [["voiceStart"]], id="start"),
        pytest.param({"target": "D-1", "voice": "recording"}, "キャンセル", None, [["voiceCancel"]], id="cancel"),
        pytest.param(
            {"target": "D-1", "voice": "recording", "body": "確認: "},
            "文字起こし",
            4,
            [["voiceDone", {"body": "確認: ", "start": 4, "end": 4}]],
            id="done",
        ),
        pytest.param(
            {"target": "D-1", "voice": "disabled", "voiceReason": "理由"},
            "音声で入力",
            None,
            [["voiceBlocked"]],
            id="blocked",
        ),
    ],
)
def test_send_form_when_voice_events(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    press: str,
    caret: int | None,
    expected: list[list[Any]],
) -> None:
    """音声入力のボタンのコールバック（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    calls = preview_page.evaluate(VOICE_EVENTS_SCRIPT, {"props": props, "press": press, "caret": caret})
    # 検証
    assert calls == expected
