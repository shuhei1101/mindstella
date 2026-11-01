"""components/thread-post.ts（スレッドの書き込み・状態の記録・レビュー中の返信と、Markdown の本文の中の項目の ID・まとまりのリンク）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadMdmark, LoadPreviewScripts

# 利用者の書き込み
USER_POST = {
    "id": "TH-1-1",
    "author": "user",
    "body": "案 B にしたい",
    "created": "2026-10-12T01:20:00+00:00",
}

# 記録にある D-12 と、記録に無い D-99 を含む 2 行の AI の書き込み
AI_POST = {
    "id": "TH-1-2",
    "author": "ai",
    "body": "D-12 を案 B に決めました。\nD-99 は記録にありません。",
    "created": "2026-10-12T01:24:00+00:00",
}

# まだ送っていない、スレッドへの返信
PENDING_REPLY = {
    "id": "C-43",
    "target": None,
    "target_title": None,
    "loc": None,
    "thread": "TH-1",
    "body": "了解です",
    "created": "2026-10-12T05:20:00+00:00",
}

# 書き込みを作って文書に置き、見た目と押した結果を集める JavaScript
POST_SCRIPT = """(props) => {
    const calls = [];
    const item = MindmapPreview.threadPost({
        titles: (id) => (id === "D-12" ? "失敗時の扱い" : null),
        ...props,
        on: {
            openId: (...a) => calls.push(["openId", ...a]),
            edit: (...a) => calls.push(["edit", ...a]),
            saveEdit: (...a) => calls.push(["saveEdit", ...a]),
            cancelEdit: (...a) => calls.push(["cancelEdit", ...a]),
            remove: (...a) => calls.push(["remove", ...a]),
        },
    });
    document.body.append(item);
    const buttons = [...item.querySelectorAll("button")];
    const named = (name) => buttons.find((button) => button.getAttribute("aria-label") === name);
    const idButton = buttons.find((button) => button.textContent.trim() === "D-12");
    if (idButton !== undefined) idButton.click();
    for (const name of ["TH-1 への返信を修正", "TH-1 への返信を削除"]) {
        const button = named(name);
        if (button !== undefined) button.click();
    }
    return {
        classes: [...item.classList],
        text: item.textContent.replace(/\\s+/g, " "),
        html: item.innerHTML,
        hasTime: item.querySelector("time[datetime]") !== null,
        idButtonTitle: idButton === undefined ? null : idButton.title,
        unknownIdIsButton: buttons.some((button) => button.textContent.trim() === "D-99"),
        buttonNames: buttons.map(
            (button) => button.getAttribute("aria-label") ?? button.textContent.trim()
        ),
        hasField: item.querySelector("textarea") !== null,
        alerts: [...item.querySelectorAll('[role="alert"]')].map((alert) => alert.textContent),
        calls,
    };
}"""


def _observe(preview_page: Page, props: dict[str, Any]) -> dict[str, Any]:
    """書き込みを作って見た目と押した結果を返す。"""
    return preview_page.evaluate(POST_SCRIPT, props)


@pytest.mark.parametrize(
    ("post", "expected_classes", "expected_head", "expected_calls"),
    [
        pytest.param(USER_POST, {"post", "user"}, "あなた", [], id="user"),
        pytest.param(AI_POST, {"post", "ai"}, "AI", [["openId", "D-12"]], id="ai"),
    ],
)
def test_thread_post(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    post: dict[str, Any],
    expected_classes: set[str],
    expected_head: str,
    expected_calls: list[list[str]],
) -> None:
    """書き手ごとの書き込みと、記録にある ID のリンク（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    observed = _observe(preview_page, {"post": post})
    # 検証
    assert expected_classes <= set(observed["classes"])
    assert expected_head in observed["text"]
    assert observed["hasTime"] is True
    assert observed["calls"] == expected_calls


def test_thread_post_when_known_and_unknown_id(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_mdmark: LoadMdmark
) -> None:
    """記録にある ID はタイトルつきのボタン、記録に無い ID は文字のまま。改行を保つ（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    observed = _observe(preview_page, {"post": AI_POST})
    # 検証
    assert observed["idButtonTitle"] == "失敗時の扱い"
    assert observed["unknownIdIsButton"] is False
    assert "D-99" in observed["text"]
    assert "\n" in observed["html"] or "<br" in observed["html"]


@pytest.mark.parametrize(
    ("event", "expected_text", "reason_visible"),
    [
        pytest.param(
            {"kind": "closed", "author": "user", "reason": "案 A で決着", "created": "2026-10-12T02:10:00+00:00"},
            "あなたがクローズにしました",
            True,
            id="user_closed",
        ),
        pytest.param(
            {"kind": "reopened", "author": "user", "reason": None, "created": "2026-10-12T02:20:00+00:00"},
            "あなたがオープンに戻しました",
            False,
            id="user_reopened",
        ),
        pytest.param(
            {"kind": "closed", "author": "ai", "reason": None, "created": "2026-10-12T02:30:00+00:00"},
            "AI がクローズにしました",
            False,
            id="ai_closed",
        ),
        pytest.param(
            {"kind": "reopened", "author": "ai", "reason": None, "created": "2026-10-12T02:40:00+00:00"},
            "AI がオープンに戻しました",
            False,
            id="ai_reopened",
        ),
    ],
)
def test_thread_post_when_event(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    event: dict[str, Any],
    expected_text: str,
    reason_visible: bool,
) -> None:
    """状態の記録の書き手・日時・理由（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, {"event": event})
    # 検証
    assert expected_text in observed["text"]
    assert observed["hasTime"] is True
    assert ("案 A で決着" in observed["text"]) is reason_visible


@pytest.mark.parametrize(
    ("props", "expected_buttons", "expect_field", "expected_alert", "expected_calls"),
    [
        pytest.param(
            {"pending": PENDING_REPLY},
            ["TH-1 への返信を修正", "TH-1 への返信を削除"],
            False,
            None,
            [["edit", "C-43"], ["remove", "C-43"]],
            id="default",
        ),
        pytest.param(
            {"pending": PENDING_REPLY, "editing": True},
            ["キャンセル", "修正"],
            True,
            None,
            [],
            id="editing",
        ),
        pytest.param(
            {"pending": PENDING_REPLY, "editing": True, "editError": "直せませんでした"},
            ["キャンセル", "修正"],
            True,
            "直せませんでした",
            [],
            id="edit_error",
        ),
    ],
)
def test_thread_post_when_pending(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected_buttons: list[str],
    expect_field: bool,
    expected_alert: str | None,
    expected_calls: list[list[str]],
) -> None:
    """レビュー中の書き込みの印・修正・削除と、書き換えている形（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, props)
    # 検証
    assert "レビュー中" in observed["text"]
    assert observed["buttonNames"] == expected_buttons
    assert observed["hasField"] is expect_field
    assert observed["alerts"] == ([] if expected_alert is None else [expected_alert])
    assert observed["calls"] == expected_calls


# まとまりのリンク・外のリンクを含む本文を `postBody` で描き、リンクを押したときの結果を集める JavaScript
POST_BODY_SCRIPT = """(useTitles) => {
    const calls = [];
    const titles = (id) => (useTitles && (id === "A-14" || id === "D-12") ? id + "の題" : null);
    const changeSets = (id) => (id === "V-6" ? "V-6 の説明" : null);
    const body = MindmapPreview.postBody({
        body: "[A-14 の書き直し](#tab=docs&diff=V-6) と D-12。[古い](#diff=V-99)。[外](https://example.com)",
        titles,
        changeSets,
        className: "post-body",
        on: {
            openId: (...a) => calls.push(["openId", ...a]),
            changeSet: (...a) => calls.push(["changeSet", ...a]),
        },
    });
    document.body.append(body);
    const links = [...body.querySelectorAll("a.setlink")];
    const hashBefore = location.hash;
    const click = new MouseEvent("click", {bubbles: true, cancelable: true});
    if (links.length > 0) links[0].dispatchEvent(click);
    return {
        classes: [...body.classList],
        text: body.textContent,
        links: links.map((link) => ({
            text: link.textContent,
            href: link.getAttribute("href"),
            title: link.title,
            focus: link.getAttribute("data-focus"),
            hasButton: link.querySelector("button") !== null,
        })),
        otherLinks: [...body.querySelectorAll("a:not(.setlink)")].map((link) => link.getAttribute("href")),
        idButtons: [...body.querySelectorAll("button.idlink")].map((button) => button.textContent),
        defaultPrevented: click.defaultPrevented,
        hashChanged: location.hash !== hashBefore,
        calls,
    };
}"""


@pytest.mark.parametrize(
    ("use_titles", "expected_id_buttons"),
    [
        pytest.param(True, ["D-12"], id="with_titles"),
        pytest.param(False, [], id="without_titles"),
    ],
)
def test_post_body(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    use_titles: bool,
    expected_id_buttons: list[str],
) -> None:
    """項目の ID のボタンとまとまりのリンクを描き分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    observed = preview_page.evaluate(POST_BODY_SCRIPT, use_titles)
    # 検証
    assert "post-body" in observed["classes"]
    assert observed["links"] == [
        {
            "text": "A-14 の書き直し",
            "href": "#diff=V-6",
            "title": "V-6 の説明",
            "focus": "post-set:V-6",
            "hasButton": False,
        }
    ]
    # 記録に無いまとまりのリンクは `a` を持たず、文言だけが出る
    assert "古い" in observed["text"]
    assert "#diff=V-99" not in observed["text"]
    assert observed["otherLinks"] == ["https://example.com"]
    assert observed["idButtons"] == expected_id_buttons
    assert observed["defaultPrevented"] is True
    assert observed["hashChanged"] is False
    assert observed["calls"] == [["changeSet", "V-6"]]


# 見出し・改行 1 つの段落・セルに ID を持つ表・インラインコードの ID・補足の囲みを持つ本文
MARKDOWN_POST_BODY = (
    "## 結果\n\nD-1 は A。\n2 行目\n\n| 列 |\n| --- |\n| D-1 |\n\n`D-1`\n\n> [!NOTE]\n> 補足の文\n"
)

# Markdown の本文を `postBody` で描き、ブロックと項目の ID のボタンの状態を集める JavaScript
MARKDOWN_POST_BODY_SCRIPT = """(source) => {
    const body = MindmapPreview.postBody({
        body: source,
        titles: (id) => (id === "D-1" ? id + "の題" : null),
        changeSets: () => null,
        className: "post-body",
        on: {openId: () => {}, changeSet: () => {}},
    });
    document.body.append(body);
    const title = body.querySelector("div.markdown-alert > p.markdown-alert-title");
    return {
        classes: [...body.classList],
        heading: body.querySelector("h2")?.textContent ?? null,
        hardBreak: body.querySelector("p br") !== null,
        tableInWrap: body.querySelector(".md-table-wrap > table") !== null,
        noteIcon: title?.firstElementChild?.outerHTML === MindmapPreview.icon("note").outerHTML,
        paragraphButtons: [...body.querySelectorAll("p > button.idlink")].map((b) => b.textContent),
        cellButtons: [...body.querySelectorAll("td button.idlink")].map((b) => b.textContent),
        codeText: body.querySelector("code")?.textContent ?? null,
        codeButtons: body.querySelectorAll("code button").length,
        colSizes: [...body.querySelectorAll("th, td")].map((cell) => cell.getAttribute("data-col-size")),
    };
}"""


def test_post_body_when_markdown(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_mdmark: LoadMdmark
) -> None:
    """本文を Markdown として描き、段落の中の改行を保ち、コードの中の ID はボタンにしない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    observed = preview_page.evaluate(MARKDOWN_POST_BODY_SCRIPT, MARKDOWN_POST_BODY)
    # 検証
    assert {"post-body", "mdmark"} <= set(observed["classes"])
    assert observed["heading"] == "結果"
    assert observed["hardBreak"] is True
    assert observed["tableInWrap"] is True
    assert observed["noteIcon"] is True
    assert observed["paragraphButtons"] == ["D-1"]
    assert observed["cellButtons"] == ["D-1"]
    assert observed["codeText"] == "D-1"
    assert observed["codeButtons"] == 0
    # 表の列の幅の見せ方は書き込みには当てない
    assert observed["colSizes"] == [None, None]


def test_post_body_when_library_missing(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """mdmark が読めなければ文字のまま改行を保つ（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        """(source) => {
            const body = MindmapPreview.postBody({
                body: source,
                titles: (id) => (id === "D-1" ? id + "の題" : null),
                changeSets: () => null,
                className: "post-body",
                on: {openId: () => {}, changeSet: () => {}},
            });
            document.body.append(body);
            return {
                classes: [...body.classList],
                text: body.textContent,
                alerts: body.querySelectorAll('[role="alert"]').length,
                buttons: body.querySelectorAll("button").length,
                strongs: body.querySelectorAll("strong").length,
            };
        }""",
        "**D-1**\n2 行目",
    )
    # 検証
    assert "post-body" in observed["classes"]
    assert observed["text"] == "**D-1**\n2 行目"
    assert (observed["alerts"], observed["buttons"], observed["strongs"]) == (0, 0, 0)


# まとまりのリンクを含む書き込みを作り、リンクを押したときの結果を集める JavaScript
CHANGE_SET_POST_SCRIPT = """(props) => {
    const calls = [];
    const item = MindmapPreview.threadPost({
        titles: () => null,
        changeSets: (id) => (id === "V-6" ? "V-6 の説明" : null),
        ...props,
        on: {
            openId: (...a) => calls.push(["openId", ...a]),
            changeSet: (...a) => calls.push(["changeSet", ...a]),
            edit: (...a) => calls.push(["edit", ...a]),
            saveEdit: (...a) => calls.push(["saveEdit", ...a]),
            cancelEdit: (...a) => calls.push(["cancelEdit", ...a]),
            remove: (...a) => calls.push(["remove", ...a]),
        },
    });
    document.body.append(item);
    const links = [...item.querySelectorAll(".post-body a.setlink")];
    if (links.length > 0) links[0].click();
    return {linkCount: links.length, calls};
}"""


@pytest.mark.parametrize(
    "props",
    [
        pytest.param(
            {
                "post": {
                    "id": "TH-1-2",
                    "author": "ai",
                    "body": "[A-14 の書き直し](#diff=V-6)",
                    "created": "2026-10-12T01:24:00+00:00",
                }
            },
            id="post",
        ),
        pytest.param({"pending": {**PENDING_REPLY, "body": "[A-14 の書き直し](#diff=V-6)"}}, id="pending"),
    ],
)
def test_thread_post_when_change_set_link(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    props: dict[str, Any],
) -> None:
    """書き込みとレビュー中の書き込みのまとまりのリンク（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    observed = preview_page.evaluate(CHANGE_SET_POST_SCRIPT, props)
    # 検証
    assert observed["linkCount"] == 1
    assert observed["calls"] == [["changeSet", "V-6"]]
