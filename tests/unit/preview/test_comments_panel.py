"""screens/comments.ts（コメントの一覧：左から出すパネル。スレッドの一覧・スレッド・レビュー中の書き込みの 3 つの画面）の単体テスト。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts
from .thread_data import make_post, make_review_item, make_thread

# レビュー中の書き込み（項目あり・消えた項目で箇所が合わない・項目を指さない）
ITEM_1 = make_review_item("C-1", body="案 A にする")
ITEM_2 = make_review_item(
    "C-2",
    target="D-9",
    target_title=None,
    loc={"kind": "body", "start": 5, "end": 5, "text": "五行目"},
    body="ここは言い換える",
)
ITEM_3 = make_review_item("C-3", target=None, target_title=None, body="全体に目を通した")

# 一覧を開いている間に消した書き込み
REMOVED = make_review_item("C-4", body="消したコメント")

# 詳細パネルで消した、D-1 へのコメント
REMOVED_C2 = make_review_item("C-2", body="消した後に戻すコメント")

# スレッドへの返信（オープンの TH-1 へ）
REPLY_C5 = make_review_item("C-5", target=None, target_title=None, thread="TH-1", body="返信です")

# クローズのスレッド TH-5 への返信
REPLY_C44 = make_review_item("C-44", target=None, target_title=None, thread="TH-5", body="閉じた後の返信")

# まだ送っていない新しいスレッド（D-5 へ）
NEW_C41 = make_review_item("C-41", target="D-5", target_title=None, body="新しいスレッドの本文")

# スレッド（オープン 2 件とクローズ 1 件。最後の書き込みの日時が 01:00・02:00・03:00）
THREAD_1 = make_thread(
    "TH-1",
    summary="返信先の要約",
    tags=["画面"],
    target="D-1",
    target_title="問い",
    posts=[
        make_post("user", "最初の質問", "2026-10-12T00:30:00+00:00"),
        make_post("ai", "AI の返答", "2026-10-12T01:00:00+00:00"),
    ],
)
THREAD_2 = make_thread(
    "TH-2",
    summary="二つ目の要約",
    posts=[make_post("user", "二つ目の質問", "2026-10-12T02:00:00+00:00")],
)
THREAD_5 = make_thread(
    "TH-5",
    status="closed",
    summary="閉じた話",
    tags=["画面"],
    posts=[make_post("user", "閉じた質問", "2026-10-12T03:00:00+00:00")],
    events=[{"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T03:10:00+00:00"}],
)

# 箇所が合わない理由
STALE_REASON = "選んだ文が D-9 の本文の 5〜5 行目にありません"

# 画面を作って文書に置き、操作して、見た目と呼ばれた操作を集めて返す JavaScript
RUN_SCRIPT = """(args) => {
    const noop = () => {};
    const calls = [];
    const names = [
        "close", "review", "back", "filter", "tag", "clearTag", "compose", "openThread", "openId",
        "reply", "replyInput", "reasonOpen", "reasonInput", "setStatus", "check", "checkAll",
        "send", "open", "edit", "saveEdit", "cancelEdit", "remove", "restore", "unloc", "changeSet",
    ];
    const on = Object.fromEntries(names.map((name) => [name, (...a) => calls.push([name, ...a])]));
    const props = {
        view: "list", items: [], removed: [], threads: [], threadsError: null, filter: "open",
        tag: null, opened: null, composing: false,
        free: {
            target: null, body: "", status: "idle", label: "新しいスレッド", collapsed: false,
            on: {input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop},
        },
        reply: {body: "", status: "idle", count: null, detail: null},
        reason: {open: false, body: "", status: "idle", detail: null},
        checked: new Set(), editing: null, editingIn: "list", editError: null, editBody: null,
        stale: new Map(), result: null, selected: null, reviewFocus: null,
        titleOf: (id) => ({"D-1": "問い", "D-12": "失敗時の扱い", "T-14": "確かめる"})[id] ?? null,
        changeSetOf: (id) => ({"V-1": "1 回目の説明", "V-6": "6 回目の説明"})[id] ?? null,
        ...args.props,
        on,
    };
    props.checked = new Set(args.props.checked ?? []);
    props.stale = new Map(args.props.stale ?? []);
    const host = document.createElement("div");
    host.append(...[MindmapPreview[args.screen](props)].flat());
    document.body.append(host);
    const norm = (text) => text.replace(/\\s+/g, " ").trim();
    const buttons = () => [...host.querySelectorAll("button")];
    const find = (target) => {
        if (target.exact !== undefined) return buttons().find((b) => norm(b.textContent) === target.exact);
        if (target.text !== undefined) return buttons().find((b) => norm(b.textContent).startsWith(target.text));
        if (target.label !== undefined) return buttons().find((b) => b.getAttribute("aria-label") === target.label);
        if (target.focus !== undefined) return host.querySelector(`[data-focus="${target.focus}"]`);
        if (target.row !== undefined) {
            return [...host.querySelectorAll(`li[data-comment="${target.row}"] button`)].find(
                (b) => norm(b.textContent).includes(target.includes)
            );
        }
        return host.querySelector(target.selector);
    };
    for (const action of args.actions) {
        if (action.click !== undefined) find(action.click).click();
        if (action.type !== undefined) {
            const field = find(action.type);
            field.value = action.value;
            field.dispatchEvent(new Event("input", {bubbles: true}));
        }
        if (action.key !== undefined) {
            find(action.key).dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: action.name, ctrlKey: action.ctrl ?? false, bubbles: true, cancelable: true,
                })
            );
        }
    }
    const describeButton = (b) => ({
        text: norm(b.textContent), label: b.getAttribute("aria-label"), title: b.title,
        pressed: b.getAttribute("aria-pressed"), disabled: b.disabled,
        focus: b.getAttribute("data-focus"), classes: [...b.classList],
    });
    const probes = {};
    for (const probe of args.probes) {
        const leaf = [...host.querySelectorAll("*")].filter(
            (e) => e.children.length === 0 && e.textContent.includes(probe)
        )[0];
        probes[probe] = {present: leaf !== undefined, inButton: leaf !== undefined && leaf.closest("button") !== null};
    }
    return {
        text: norm(host.textContent),
        rootTag: host.firstElementChild === null ? null : host.firstElementChild.tagName,
        buttons: buttons().map(describeButton),
        labels: [...host.querySelectorAll("label")].map((l) => norm(l.textContent)),
        fields: [...host.querySelectorAll("textarea, input")].map((f) => ({
            tag: f.tagName, type: f.type, ariaLabel: f.getAttribute("aria-label"),
            readOnly: f.readOnly, disabled: f.disabled, checked: f.checked,
            indeterminate: f.indeterminate, maxlength: f.getAttribute("maxlength"), value: f.value,
        })),
        alerts: [...host.querySelectorAll('[role="alert"]')].map((a) => norm(a.textContent)),
        setLinks: [...host.querySelectorAll("a.setlink")].map((a) => ({
            text: norm(a.textContent), bodyClass: a.parentElement.className,
        })),
        statuses: [...host.querySelectorAll('[role="status"]')].map((s) => norm(s.textContent)),
        items: [...host.querySelectorAll("li")].map((li) => ({
            text: norm(li.textContent),
            comment: li.getAttribute("data-comment"),
            thread: (li.querySelector('[data-focus^="thread:"]') ?? li).getAttribute("data-focus"),
            buttons: [...li.querySelectorAll("button")].map(describeButton),
            checkbox: (() => {
                const box = li.querySelector('input[type="checkbox"]');
                return box === null ? null : {checked: box.checked, disabled: box.disabled};
            })(),
            alerts: [...li.querySelectorAll('[role="alert"]')].map((a) => norm(a.textContent)),
        })),
        probes,
        calls,
    };
}"""


def _run(
    preview_page: Page,
    screen: str,
    props: dict[str, Any],
    *,
    actions: list[dict[str, Any]] | None = None,
    probes: list[str] | None = None,
) -> dict[str, Any]:
    """画面を作って操作し、見た目と呼ばれた操作を返す。"""
    return preview_page.evaluate(
        RUN_SCRIPT,
        {"screen": screen, "props": props, "actions": actions or [], "probes": probes or []},
    )


def _call_names(observed: dict[str, Any]) -> list[str]:
    """呼ばれた操作の名前を呼ばれた順に返す。"""
    return [call[0] for call in observed["calls"]]


def _labels(observed: dict[str, Any]) -> list[str | None]:
    """ボタンの読み上げの名前（無ければ文字）を並びのまま返す。"""
    return [button["label"] or button["text"] for button in observed["buttons"]]


def _threads_by_focus(observed: dict[str, Any]) -> list[str]:
    """一覧の行を、並びのまま `data-focus` の値で返す。"""
    return [item["thread"] for item in observed["items"] if (item["thread"] or "").startswith("thread:")]


# --- パネル -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("view", "actions", "expected_entrance", "expected_calls", "expected_marker"),
    [
        pytest.param(
            "list",
            [{"click": {"label": "レビュー中の書き込みを確かめる（3 件）"}}],
            True,
            ["review"],
            "新しいスレッド",
            id="list",
        ),
        pytest.param(
            "thread",
            [{"click": {"label": "レビュー中の書き込みを確かめる（3 件）"}}],
            True,
            ["review"],
            "一覧へ戻る",
            id="thread",
        ),
        pytest.param("review", [], False, [], "まとめて送る", id="review"),
    ],
)
def test_comments_panel(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    view: str,
    actions: list[dict[str, Any]],
    expected_entrance: bool,
    expected_calls: list[str],
    expected_marker: str,
) -> None:
    """見出しの帯と、view ごとの中身（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {
        "view": view,
        "items": [ITEM_1, ITEM_2, ITEM_3],
        "threads": [THREAD_1],
        "opened": {"id": "TH-1", "pending": False},
        "checked": ["C-1"],
    }
    # 実行
    observed = _run(preview_page, "commentsPanel", props, actions=actions)
    # 検証
    assert observed["rootTag"] == "ASIDE"
    assert "コメント" in observed["text"]
    assert "コメントの一覧を閉じる" in _labels(observed)
    assert ("レビュー中の書き込みを確かめる（3 件）" in _labels(observed)) is expected_entrance
    assert _call_names(observed) == expected_calls
    assert expected_marker in observed["text"]


def test_comments_panel_when_no_pending(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """レビュー中が 0 件でも入口を出す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _run(preview_page, "commentsPanel", {"view": "list", "items": []})
    # 検証
    entrance = next(
        button for button in observed["buttons"] if button["label"] == "レビュー中の書き込みを確かめる（0 件）"
    )
    assert "zero" in entrance["classes"]


# --- スレッドの一覧 ---------------------------------------------------------


def test_thread_list_view(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """絞り込みの件数と、まだ送っていない新しいスレッドを先頭にした行（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {
        "threads": [THREAD_1, THREAD_2, THREAD_5],
        "items": [NEW_C41, make_review_item("C-43", target=None, target_title=None, thread="TH-1")],
        "filter": "open",
    }
    actions = [{"click": {"focus": "filter:closed"}}, {"click": {"focus": "thread:TH-2"}}]
    # 実行
    observed = _run(preview_page, "threadListView", props, actions=actions)
    # 検証
    segments = {
        button["focus"]: (button["text"].replace(" ", ""), button["pressed"])
        for button in observed["buttons"]
        if (button["focus"] or "").startswith("filter:")
    }
    assert segments == {
        "filter:open": ("オープン2", "true"),
        "filter:closed": ("クローズ1", "false"),
        "filter:all": ("すべて3", "false"),
    }
    assert _threads_by_focus(observed) == ["thread:new:C-41", "thread:TH-2", "thread:TH-1"]
    rows = {item["thread"]: item["text"] for item in observed["items"] if item["thread"]}
    assert "レビュー中" in rows["thread:new:C-41"]
    assert "レビュー中" in rows["thread:TH-1"]
    assert "レビュー中" not in rows["thread:TH-2"]
    assert [call[0] for call in observed["calls"]] == ["filter", "openThread"]
    assert observed["calls"][0] == ["filter", "closed"]
    assert "TH-2" in json.dumps(observed["calls"][1])


def test_thread_list_view_when_tag(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """タグで絞るとチップと件数を出し、まだ送っていない新しいスレッドを出さない（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {
        "threads": [THREAD_1, {**THREAD_2, "tags": ["起票"]}],
        "items": [NEW_C41],
        "tag": "画面",
    }
    actions = [{"click": {"label": "タグ「画面」の絞り込みを外す"}}]
    # 実行
    observed = _run(preview_page, "threadListView", props, actions=actions)
    # 検証
    assert "1 / 2 件" in observed["text"]
    assert _threads_by_focus(observed) == ["thread:TH-1"]
    assert observed["calls"] == [["clearTag"]]


@pytest.mark.parametrize(
    ("props", "expected_text", "expect_alert"),
    [
        pytest.param({}, "オープンのスレッドはありません。", False, id="no_threads"),
        pytest.param(
            {"filter": "closed", "tag": "起票", "threads": [THREAD_1]},
            "タグ「起票」のクローズのスレッドはありません。",
            False,
            id="no_match",
        ),
        pytest.param(
            {"threadsError": {"detail": None}},
            "スレッドを読めませんでした。サーバーが止まっています。立ち上げ直してから開いてください。",
            True,
            id="unreachable",
        ),
        pytest.param(
            {"threadsError": {"detail": "threads.yaml: 読めません"}},
            "スレッドを読めませんでした。threads.yaml: 読めません",
            True,
            id="detail",
        ),
    ],
)
def test_thread_list_view_when_empty_or_failed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected_text: str,
    expect_alert: bool,
) -> None:
    """0 件の文言と、読めない理由（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _run(preview_page, "threadListView", props)
    # 検証
    assert expected_text in observed["text"]
    assert (expected_text in " ".join(observed["alerts"])) is expect_alert


@pytest.mark.parametrize(
    ("composing", "click", "expected_calls"),
    [
        pytest.param(False, {"exact": "新しいスレッド"}, [["compose", True]], id="closed"),
        pytest.param(
            True, {"label": "新しいスレッドの入力を閉じる"}, [["compose", False]], id="composing"
        ),
    ],
)
def test_thread_list_view_when_composing(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    composing: bool,
    click: dict[str, str],
    expected_calls: list[list[Any]],
) -> None:
    """新しいスレッドの入口と入力を切り替える（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _run(
        preview_page,
        "threadListView",
        {"composing": composing},
        actions=[{"click": click}],
    )
    # 検証
    assert observed["calls"] == expected_calls
    assert any(field["ariaLabel"] == "新しいスレッド" for field in observed["fields"]) is composing


# --- スレッド ---------------------------------------------------------------

# 書き込み 3 件と記録 2 件を持つオープンのスレッド
THREAD_4 = make_thread(
    "TH-4",
    summary="四つ目の話",
    posts=[
        make_post("user", "最初の質問", "2026-10-12T00:10:00+00:00"),
        make_post("ai", "AI の返答", "2026-10-12T00:12:00+00:00"),
        make_post("user", "三つ目の書き込み", "2026-10-12T00:30:00+00:00"),
    ],
    events=[
        {"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T00:20:00+00:00"},
        {"kind": "reopened", "author": "ai", "reason": None, "created": "2026-10-12T00:29:00+00:00"},
    ],
)


def test_thread_view(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """書き込みと状態の記録を日時の順に並べ、レビュー中の返信を末尾に出す（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {
        "threads": [THREAD_4],
        "opened": {"id": "TH-4", "pending": False},
        "items": [make_review_item("C-43", target=None, target_title=None, thread="TH-4", body="返信の下書き")],
        "removed": [make_review_item("C-45", target=None, target_title=None, thread="TH-4")],
    }
    # 実行
    observed = _run(preview_page, "threadView", props)
    # 検証
    markers = [
        "最初の質問",
        "AI の返答",
        "クローズにしました",
        "オープンに戻しました",
        "三つ目の書き込み",
        "返信の下書き",
        "元に戻す",
    ]
    texts = [item["text"] for item in observed["items"]]
    positions = [next(i for i, text in enumerate(texts) if marker in text) for marker in markers]
    assert positions == sorted(set(positions))
    assert "レビュー中" in texts[positions[5]]
    assert "クローズにする" in [button["text"] for button in observed["buttons"]]
    assert "返信" in observed["labels"]
    assert any(field["tag"] == "TEXTAREA" for field in observed["fields"])


@pytest.mark.parametrize(
    ("props", "expected_buttons", "expected_texts", "expect_reply_field"),
    [
        pytest.param(
            {"threads": [THREAD_5], "opened": {"id": "TH-5", "pending": False}},
            ["オープンに戻す"],
            ["クローズにしたスレッドです。"],
            False,
            id="closed",
        ),
        pytest.param(
            {"items": [NEW_C41], "opened": {"id": "C-41", "pending": True}},
            ["D-5 へのコメントを修正", "D-5 へのコメントを削除"],
            ["レビュー中", "まだ送っていないスレッドです。"],
            False,
            id="pending",
        ),
    ],
)
def test_thread_view_when_closed_or_pending(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected_buttons: list[str],
    expected_texts: list[str],
    expect_reply_field: bool,
) -> None:
    """クローズと、まだ送っていない新しいスレッドは返信の入力を出さない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _run(preview_page, "threadView", props)
    # 検証
    labels = _labels(observed)
    assert all(name in labels for name in expected_buttons)
    assert all(text in observed["text"] for text in expected_texts)
    assert any(field["tag"] == "TEXTAREA" for field in observed["fields"]) is expect_reply_field
    # 送ったスレッドの状態を変えるボタンは、クローズでは「オープンに戻す」だけ。まだ送っていないものには出ない
    assert ("クローズにする" in labels) is False


def test_thread_view_when_change_set_link(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """書き込みのまとまりのリンクを使う側へ知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    thread = make_thread(
        "TH-1",
        posts=[make_post("ai", "[D-1 を直した](#diff=V-1)", "2026-10-12T01:00:00+00:00")],
    )
    props = {"threads": [thread], "opened": {"id": "TH-1", "pending": False}}
    actions = [{"click": {"selector": "p.post-body a.setlink"}}]
    # 実行
    observed = _run(preview_page, "threadView", props, actions=actions)
    # 検証
    assert observed["setLinks"] == [{"text": "D-1 を直した", "bodyClass": "post-body"}]
    assert observed["calls"] == [["changeSet", "V-1"]]


REASON_FIELD = 'textarea[maxlength="400"]'


@pytest.mark.parametrize(
    ("reason", "actions", "expected", "expected_call_names", "expected_call_text"),
    [
        pytest.param(
            {"open": True, "body": "", "status": "idle", "detail": None},
            [
                {"type": {"selector": REASON_FIELD}, "value": "案 A で決着"},
                {"click": {"focus": "reason-ok"}},
            ],
            {"fieldPresent": True, "closeButtons": 1},
            ["setStatus"],
            ["closed", "案 A で決着"],
            id="confirm",
        ),
        pytest.param(
            {"open": True, "body": "", "status": "idle", "detail": None},
            [{"key": {"selector": REASON_FIELD}, "name": "Escape"}],
            {"fieldPresent": True, "closeButtons": 1},
            ["reasonOpen"],
            ["false"],
            id="escape",
        ),
        pytest.param(
            {"open": True, "body": "案 A", "status": "saving", "detail": None},
            [],
            {"fieldPresent": True, "readOnly": True, "confirmDisabled": True},
            [],
            [],
            id="saving",
        ),
        pytest.param(
            {"open": True, "body": "案 A", "status": "failed", "detail": None},
            [],
            {
                "fieldPresent": True,
                "alert": "クローズにできませんでした。サーバーが止まっています。立ち上げ直してから押してください。",
            },
            [],
            [],
            id="failed_unreachable",
        ),
        pytest.param(
            {"open": True, "body": "案 A", "status": "failed", "detail": "スレッドがありません"},
            [],
            {"fieldPresent": True, "alert": "クローズにできませんでした。スレッドがありません"},
            [],
            [],
            id="failed_detail",
        ),
    ],
)
def test_thread_view_when_reason(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    reason: dict[str, Any],
    actions: list[dict[str, Any]],
    expected: dict[str, Any],
    expected_call_names: list[str],
    expected_call_text: list[str],
) -> None:
    """理由の入力と、変えられなかった理由（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {"threads": [THREAD_2], "opened": {"id": "TH-2", "pending": False}, "reason": reason}
    # 実行
    observed = _run(preview_page, "threadView", props, actions=actions)
    # 検証
    field = next((f for f in observed["fields"] if f["maxlength"] == "400"), None)
    confirm = next((b for b in observed["buttons"] if b["focus"] == "reason-ok"), None)
    summary = {
        "fieldPresent": field is not None,
        "closeButtons": sum(1 for b in observed["buttons"] if b["text"] == "クローズにする"),
    }
    assert expected.get("fieldPresent") is summary["fieldPresent"]
    assert expected.get("closeButtons", summary["closeButtons"]) == summary["closeButtons"]
    assert expected.get("readOnly", field["readOnly"]) == field["readOnly"]
    assert expected.get("confirmDisabled", confirm["disabled"]) == confirm["disabled"]
    assert expected.get("alert", "") in " ".join(observed["alerts"])
    assert "理由（任意）" in observed["labels"]
    assert _call_names(observed) == expected_call_names
    assert all(text in json.dumps(observed["calls"], ensure_ascii=False) for text in expected_call_text)


@pytest.mark.parametrize(
    ("thread", "expected_target", "expected_plain", "expected_calls"),
    [
        pytest.param(
            make_thread("TH-1", tags=["画面"], target="D-12", target_title="失敗時の扱い"),
            True,
            ["画面"],
            [["openId", "D-12"]],
            id="with_target",
        ),
        pytest.param(
            make_thread("TH-6", target="D-99"),
            False,
            ["D-99"],
            [],
            id="removed_target",
        ),
        pytest.param(make_thread("TH-7"), False, [], [], id="no_target_no_tag"),
    ],
)
def test_thread_view_when_target(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    thread: dict[str, Any],
    expected_target: bool,
    expected_plain: list[str],
    expected_calls: list[list[str]],
) -> None:
    """向けた項目とタグ（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {"threads": [thread], "opened": {"id": thread["id"], "pending": False}}
    actions = [{"click": {"focus": "target"}}] if expected_target else []
    # 実行
    observed = _run(
        preview_page, "threadView", props, actions=actions, probes=expected_plain
    )
    # 検証
    target_button = [button for button in observed["buttons"] if button["focus"] == "target"]
    assert (len(target_button) == 1) is expected_target
    assert all(
        observed["probes"][text]["present"] and not observed["probes"][text]["inButton"]
        for text in expected_plain
    )
    assert observed["calls"] == expected_calls


# --- レビュー中の書き込み ---------------------------------------------------


def _row(observed: dict[str, Any], comment_id: str) -> dict[str, Any]:
    """レビュー中の書き込みの行（`data-comment` が ID のもの）を返す。"""
    return next(item for item in observed["items"] if item["comment"] == comment_id)


def test_review_view(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """送る帯と、新しいスレッド・返信の行を描く（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {
        "items": [ITEM_1, ITEM_2, ITEM_3, REPLY_C5],
        "removed": [REMOVED],
        "threads": [THREAD_1],
        "checked": ["C-1", "C-3"],
        "stale": [["C-2", STALE_REASON]],
    }
    actions = [{"click": {"row": "C-5", "includes": "返信先の要約"}}]
    # 実行
    observed = _run(
        preview_page, "reviewView", props, actions=actions, probes=["項目を指さない"]
    )
    # 検証
    assert "レビュー中の書き込み" in observed["text"]
    assert "2 / 4 件" in observed["text"]
    send = next(button for button in observed["buttons"] if button["text"].startswith("まとめて送る"))
    assert send["text"] == "まとめて送る（2 件）"
    select_all = next(
        field for field in observed["fields"] if field["type"] == "checkbox" and field["indeterminate"]
    )
    assert select_all["indeterminate"] is True
    assert [STALE_REASON in alert for alert in _row(observed, "C-2")["alerts"]] == [True]
    assert "箇所を外す" not in [button["text"] for button in _row(observed, "C-2")["buttons"]]
    assert observed["probes"]["項目を指さない"] == {"present": True, "inButton": False}
    assert "スレッドを開く" in [button["text"] for button in _row(observed, "C-3")["buttons"]]
    reply_row = _row(observed, "C-5")
    assert "返信" in reply_row["text"]
    assert "返信先の要約" in reply_row["text"]
    assert "元に戻す" in [button["text"] for item in observed["items"] for button in item["buttons"]]
    assert _call_names(observed) == ["openThread"]
    assert "TH-1" in json.dumps(observed["calls"])


def test_review_view_when_blocked(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """クローズのスレッドへの返信は選べず、送る件数に入らない（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {
        "items": [make_review_item("C-1"), REPLY_C44],
        "threads": [THREAD_5],
        "checked": ["C-1", "C-44"],
    }
    actions = [{"click": {"row": "C-44", "includes": "スレッドを開く"}}]
    # 実行
    observed = _run(preview_page, "reviewView", props, actions=actions)
    # 検証
    blocked = _row(observed, "C-44")
    assert blocked["checkbox"] == {"checked": False, "disabled": True}
    assert "1 / 1 件" in observed["text"]
    assert "まとめて送る（1 件）" in [button["text"] for button in observed["buttons"]]
    assert "クローズのスレッドへの返信は送れません。オープンに戻すと送れます。" in blocked["text"]
    assert _call_names(observed) == ["openThread"]
    assert "TH-5" in json.dumps(observed["calls"])


def test_review_view_when_empty(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """0 件は空の状態だけ（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _run(preview_page, "reviewView", {"items": [], "removed": []})
    # 検証
    assert "レビュー中の書き込みはありません。" in observed["text"]
    assert not any(button["text"].startswith("まとめて送る") for button in observed["buttons"])


@pytest.mark.parametrize(
    ("checked", "result", "expected_text"),
    [
        pytest.param([], None, "送る書き込みにチェックを付けてください。", id="nothing_checked"),
        pytest.param(["C-1"], {"kind": "sending"}, "", id="sending"),
    ],
)
def test_review_view_when_send_disabled(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    checked: list[str],
    result: dict[str, Any] | None,
    expected_text: str,
) -> None:
    """チェック 0 件と送っている間は送れない（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {"items": [ITEM_1], "checked": checked, "result": result}
    # 実行
    observed = _run(
        preview_page,
        "reviewView",
        props,
        actions=[{"click": {"text": "まとめて送る"}}],
    )
    # 検証
    send = next(button for button in observed["buttons"] if button["text"].startswith("まとめて送る"))
    assert send["disabled"] is True
    assert "send" not in _call_names(observed)
    assert expected_text in observed["text"]


def test_review_view_when_editing_in_detail(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """詳細パネルで書き換えている行は、本文だけで描く（正常系）。"""
    # 準備
    load_preview_scripts()
    props = {"items": [ITEM_1], "editing": "C-1", "editingIn": "detail"}
    # 実行
    observed = _run(preview_page, "reviewView", props)
    # 検証
    row = _row(observed, "C-1")
    edit_names = ["D-1 へのコメントを修正", "D-1 へのコメントを削除", "キャンセル", "修正"]
    assert [b for b in row["buttons"] if (b["label"] or b["text"]) in edit_names] == []
    assert "案 A にする" in row["text"]
    assert not any(field["tag"] == "TEXTAREA" for field in observed["fields"])


@pytest.mark.parametrize(
    ("entered", "expected_text"),
    [
        pytest.param(True, "2 件を送り、Claude Code に入力しました（12:04）。", id="entered"),
        pytest.param(
            False,
            "2 件を送りましたが、Claude Code には入力できませんでした（12:04）。"
            "送った内容は保存されていて、次に話し合いを始めたときに取り込まれます。",
            id="not_entered",
        ),
    ],
)
def test_review_view_when_sent(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    entered: bool,
    expected_text: str,
) -> None:
    """送れた結果を Claude Code へ入力したかで出し分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    result = {"kind": "sent", "count": 2, "at": "2026-10-10T03:04:00+00:00", "entered": entered}
    props = {"items": [ITEM_1], "checked": ["C-1"], "result": result}
    # 実行
    observed = _run(preview_page, "reviewView", props)
    # 検証
    assert any(expected_text in status for status in observed["statuses"])


def test_review_view_when_change_set_link(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """行の本文のまとまりのリンクと、文字のままの項目の ID（正常系）。"""
    # 準備
    load_preview_scripts()
    reply = make_review_item(
        "C-6",
        target=None,
        target_title=None,
        thread="TH-1",
        body="[A-14 の書き直し](#diff=V-6) で消した行は戻して。T-14 にも関わる",
    )
    props = {"items": [reply], "threads": [THREAD_1]}
    actions = [{"click": {"selector": 'li[data-comment="C-6"] p.review-body a.setlink'}}]
    # 実行
    observed = _run(preview_page, "reviewView", props, actions=actions)
    # 検証
    row = _row(observed, "C-6")
    assert observed["setLinks"] == [{"text": "A-14 の書き直し", "bodyClass": "review-body"}]
    assert "T-14" in row["text"]
    assert "T-14" not in [button["text"] for button in row["buttons"]]
    assert observed["calls"] == [["changeSet", "V-6"]]


# --- 補助の関数 -------------------------------------------------------------

# 状態とタグで絞る例のスレッド（オープン 2 件の 1 件にタグ 画面、クローズ 1 件にタグ 画面）
VISIBLE_THREADS = [
    {**THREAD_1, "tags": ["画面"]},
    {**THREAD_2, "tags": []},
    {**THREAD_5, "tags": ["画面"]},
]


@pytest.mark.parametrize(
    ("status", "tag", "expected"),
    [
        pytest.param("open", None, ["TH-2", "TH-1"], id="open"),
        pytest.param("all", None, ["TH-5", "TH-2", "TH-1"], id="all"),
        pytest.param("all", "画面", ["TH-5", "TH-1"], id="all_tagged"),
        pytest.param("closed", "起票", [], id="closed_other_tag"),
    ],
)
def test_visible_threads(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str,
    tag: str | None,
    expected: list[str],
) -> None:
    """状態とタグで絞り、新しい順に並べる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([threads, status, tag]) => {
            const before = threads.map((thread) => thread.id);
            const shown = MindmapPreview.visibleThreads(threads, status, tag).map((thread) => thread.id);
            return {shown, untouched: threads.map((thread) => thread.id).join() === before.join()};
        }""",
        [VISIBLE_THREADS, status, tag],
    )
    # 検証
    assert result == {"shown": expected, "untouched": True}


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        pytest.param(None, {"open": 2, "closed": 1, "all": 3}, id="no_tag"),
        pytest.param("画面", {"open": 1, "closed": 1, "all": 2}, id="tagged"),
    ],
)
def test_thread_counts(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    tag: str | None,
    expected: dict[str, int],
) -> None:
    """タグで絞った件数を数える（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    counts = preview_page.evaluate(
        "([threads, tag]) => MindmapPreview.threadCounts(threads, tag)", [VISIBLE_THREADS, tag]
    )
    # 検証
    assert counts == expected


@pytest.mark.parametrize(
    ("status", "tag", "expected"),
    [
        pytest.param("open", None, ["C-41", "C-42"], id="open"),
        pytest.param("all", None, ["C-41", "C-42"], id="all"),
        pytest.param("closed", None, [], id="closed"),
        pytest.param("open", "画面", [], id="tagged"),
    ],
)
def test_pending_threads(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str,
    tag: str | None,
    expected: list[str],
) -> None:
    """返信を除き、クローズの絞り込みとタグの絞り込みでは出さない（正常系）。"""
    # 準備
    load_preview_scripts()
    items = [
        make_review_item("C-41"),
        make_review_item("C-42"),
        make_review_item("C-43", target=None, thread="TH-1"),
    ]
    # 実行
    shown = preview_page.evaluate(
        "([items, status, tag]) => MindmapPreview.pendingThreads(items, status, tag).map((item) => item.id)",
        [items, status, tag],
    )
    # 検証
    assert shown == expected


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        pytest.param(REPLY_C44, True, id="closed_thread"),
        pytest.param(REPLY_C5, False, id="open_thread"),
        pytest.param(NEW_C41, False, id="new_thread"),
        pytest.param(make_review_item("C-46", target=None, thread="TH-9"), False, id="missing_thread"),
    ],
)
def test_is_blocked_reply(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    item: dict[str, Any],
    expected: bool,
) -> None:
    """クローズのスレッドへの返信だけ真（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    blocked = preview_page.evaluate(
        "([item, threads]) => MindmapPreview.isBlockedReply(item, threads)",
        [item, [THREAD_1, THREAD_5]],
    )
    # 検証
    assert blocked is expected


def test_thread_timeline(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """日時の順に混ぜ、同じ日時は書き込みを先にする（正常系）。"""
    # 準備
    load_preview_scripts()
    thread = make_thread(
        "TH-4",
        posts=[
            make_post("user", "一つ目", "2026-10-12T00:10:00+00:00"),
            make_post("ai", "二つ目", "2026-10-12T00:30:00+00:00"),
        ],
        events=[
            {"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T00:20:00+00:00"},
            {"kind": "reopened", "author": "ai", "reason": None, "created": "2026-10-12T00:30:00+00:00"},
        ],
    )
    # 実行
    timeline = preview_page.evaluate(
        """(thread) => MindmapPreview.threadTimeline(thread).map(
            (entry) => entry.post ? ["post", entry.post.created] : ["event", entry.event.created]
        )""",
        thread,
    )
    # 検証
    assert timeline == [
        ["post", "2026-10-12T00:10:00+00:00"],
        ["event", "2026-10-12T00:20:00+00:00"],
        ["post", "2026-10-12T00:30:00+00:00"],
        ["event", "2026-10-12T00:30:00+00:00"],
    ]


# --- 行の操作の部品 ---------------------------------------------------------

# 部品の戻り値（要素・要素の配列・DocumentFragment のどれでも）を文書に置いて、その入れ物を返す関数
MOUNT_FUNCTION = """const mount = (value) => {
    const host = document.createElement("div");
    host.append(...[value].flat());
    document.body.append(host);
    return host;
};"""

# 行の右上の「修正」「削除」を描き、2 つのボタンを押して、見た目と呼ばれた ID を集める
ROW_ACTIONS_SCRIPT = (
    MOUNT_FUNCTION
    + """
({item, focus}) => {
    const calls = {edit: [], remove: []};
    const host = mount(MindmapPreview.reviewRowActions({
        item,
        focus,
        on: {edit: (id) => calls.edit.push(id), remove: (id) => calls.remove.push(id)},
    }));
    const buttons = [...host.querySelectorAll("button")];
    const buttonInfo = buttons.map((button) => ({
        label: button.getAttribute("aria-label"),
        title: button.title,
        focus: button.getAttribute("data-focus"),
    }));
    buttons.forEach((button) => button.click());
    return {buttonInfo, calls};
}"""
)


@pytest.mark.parametrize(
    ("item", "focus", "expected"),
    [
        pytest.param(
            ITEM_1,
            "detail-",
            {
                "buttonInfo": [
                    {
                        "label": "D-1 へのコメントを修正",
                        "title": "修正",
                        "focus": "detail-edit-open:C-1",
                    },
                    {
                        "label": "D-1 へのコメントを削除",
                        "title": "削除",
                        "focus": "detail-remove:C-1",
                    },
                ],
                "calls": {"edit": ["C-1"], "remove": ["C-1"]},
            },
            id="targeted_in_detail",
        ),
        pytest.param(
            ITEM_3,
            "",
            {
                "buttonInfo": [
                    {
                        "label": "項目を指さないコメントを修正",
                        "title": "修正",
                        "focus": "edit-open:C-3",
                    },
                    {
                        "label": "項目を指さないコメントを削除",
                        "title": "削除",
                        "focus": "remove:C-3",
                    },
                ],
                "calls": {"edit": ["C-3"], "remove": ["C-3"]},
            },
            id="untargeted_in_list",
        ),
    ],
)
def test_review_row_actions(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    item: dict[str, Any],
    focus: str,
    expected: dict[str, Any],
) -> None:
    """読み上げの名前と `title` と `data-focus` を付けて、押すと ID を知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(ROW_ACTIONS_SCRIPT, {"item": item, "focus": focus})
    # 検証
    assert observed == expected


# 行の本文の書き換えを描き、入力欄に入れた中身で操作して、ボタンの並びと呼ばれた引数と理由を集める
EDIT_FORM_SCRIPT = (
    MOUNT_FUNCTION
    + """
({item, body, error, typed, action}) => {
    const calls = {save: [], cancel: 0};
    const host = mount(MindmapPreview.reviewEditForm({
        item,
        body,
        error,
        focus: "",
        on: {
            saveEdit: (id, text) => calls.save.push([id, text]),
            cancelEdit: () => { calls.cancel += 1; },
        },
    }));
    const field = host.querySelector("textarea");
    const buttons = [...host.querySelectorAll("button")];
    const labels = buttons.map((button) => button.textContent.trim());
    if (typed !== null) field.value = typed;
    const named = (label) => buttons.find((button) => button.textContent.trim() === label);
    let escapePrevented = null;
    if (action === "save") named("修正").click();
    if (action === "cancel") named("キャンセル").click();
    if (action === "escape") {
        const event = new KeyboardEvent("keydown", {key: "Escape", bubbles: true, cancelable: true});
        field.dispatchEvent(event);
        escapePrevented = event.defaultPrevented;
    }
    return {
        labels,
        calls,
        escapePrevented,
        value: field.value,
        invalid: field.getAttribute("aria-invalid"),
        alerts: [...host.querySelectorAll('[role="alert"]')].map((alert) => alert.textContent),
    };
}"""
)


@pytest.mark.parametrize(
    ("typed", "action", "expected_calls", "expected_escape_prevented"),
    [
        pytest.param(
            "案 A に決める",
            "save",
            {"save": [["C-1", "案 A に決める"]], "cancel": 0},
            None,
            id="save",
        ),
        pytest.param(None, "cancel", {"save": [], "cancel": 1}, None, id="cancel"),
        pytest.param(None, "escape", {"save": [], "cancel": 1}, True, id="escape"),
    ],
)
def test_review_edit_form(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    typed: str | None,
    action: str,
    expected_calls: dict[str, Any],
    expected_escape_prevented: bool | None,
) -> None:
    """文言と、送る・捨てる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        EDIT_FORM_SCRIPT,
        {"item": ITEM_1, "body": None, "error": None, "typed": typed, "action": action},
    )
    # 検証
    assert observed["labels"] == ["キャンセル", "修正"]
    assert observed["calls"] == expected_calls
    assert observed["escapePrevented"] is expected_escape_prevented


@pytest.mark.parametrize(
    (
        "body",
        "error",
        "typed",
        "action",
        "expected_value",
        "expected_reason",
        "expected_invalid",
    ),
    [
        pytest.param(
            None,
            None,
            "   ",
            "save",
            "   ",
            "コメントを入れてから直してください。",
            "true",
            id="blank_only",
        ),
        pytest.param(
            "案 A に決める",
            "サーバーが止まっています。立ち上げ直してから直してください。",
            None,
            "none",
            "案 A に決める",
            "サーバーが止まっています。立ち上げ直してから直してください。",
            None,
            id="save_failed",
        ),
    ],
)
def test_review_edit_form_when_blank_or_error(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    body: str | None,
    error: str | None,
    typed: str | None,
    action: str,
    expected_value: str,
    expected_reason: str,
    expected_invalid: str | None,
) -> None:
    """空白だけは送らず、直せなかった理由と中身を出す（異常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        EDIT_FORM_SCRIPT,
        {
            "item": ITEM_1,
            "body": body,
            "error": error,
            "typed": typed,
            "action": action,
        },
    )
    # 検証
    assert observed["calls"]["save"] == []
    assert observed["value"] == expected_value
    assert expected_reason in "".join(observed["alerts"])
    assert observed["invalid"] == expected_invalid


# 消した行を描き、「元に戻す」を押して、見た目と呼ばれた ID を集める
REMOVED_ROW_SCRIPT = (
    MOUNT_FUNCTION
    + """
({item, focus}) => {
    const restored = [];
    const host = mount(MindmapPreview.removedReviewRow({
        item,
        focus,
        on: {restore: (id) => restored.push(id)},
    }));
    const button = [...host.querySelectorAll("button")].find(
        (candidate) => candidate.textContent.trim() === "元に戻す"
    );
    const result = {
        status: [...host.querySelectorAll('[role="status"]')].map((status) => status.textContent.trim()),
        restoreFocus: button === undefined ? null : button.getAttribute("data-focus"),
        rowClass: host.querySelector("li.row.removed") === null ? null : "row removed",
    };
    if (button !== undefined) button.click();
    result.restored = restored;
    return result;
}"""
)


def test_removed_review_row(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """消した旨と元に戻すを出し、押すと ID を知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        REMOVED_ROW_SCRIPT, {"item": REMOVED_C2, "focus": "detail-"}
    )
    # 検証
    assert observed == {
        "status": ["コメントを削除しました。"],
        "restoreFocus": "detail-restore:C-2",
        "rowClass": "row removed",
        "restored": ["C-2"],
    }
