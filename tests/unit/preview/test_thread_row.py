"""components/thread-row.ts（スレッドの行・状態の札・レビュー中の印・題の決め方）の単体テスト。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts
from .thread_data import make_post as _post
from .thread_data import make_thread as _thread


# AI が返信したオープンのスレッド（D-12・タグ 画面）
REPLIED = _thread(
    "TH-1",
    tags=["画面"],
    summary="D-12 の失敗時の扱いの相談",
    target="D-12",
    target_title="失敗時の扱い",
    posts=[
        _post("user", "D-12 は案 B にしたい", "2026-10-12T01:20:00+00:00"),
        _post("ai", "D-12 を案 B で決定にしました。", "2026-10-12T01:24:00+00:00"),
    ],
)

# 要約がまだ無く、最後の書き込みが利用者のスレッド
NO_SUMMARY = _thread(
    "TH-3",
    target="A-1",
    posts=[_post("user", "背景の節を 3 行にまとめてほしい\n経緯は会話ログへ", "2026-10-12T05:01:00+00:00")],
)

# クローズのスレッド
CLOSED = _thread(
    "TH-5",
    status="closed",
    summary="版の置き場所の質問",
    target="D-2",
    posts=[
        _post("user", "版はどこに書く？", "2026-10-12T02:00:00+00:00"),
        _post("ai", "config.yaml に書きます。", "2026-10-12T02:03:00+00:00"),
    ],
    events=[{"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T02:10:00+00:00"}],
)

# 項目を指さないスレッド（タグ 2 つ）
FREE = _thread(
    "TH-4",
    tags=["調査", "画面"],
    summary="移し替えの手順を画面で見られるかの質問",
    posts=[_post("ai", "資料を足しました。", "2026-10-12T00:41:00+00:00")],
)

# まだ送っていない新しいスレッドの最初の書き込み
PENDING = {
    "id": "C-41",
    "target": "D-5",
    "target_title": "写しの取り方",
    "loc": None,
    "thread": None,
    "body": "写しは git のコミットで取るほうが戻しやすいと思う",
    "created": "2026-10-12T05:10:00+00:00",
}

# 行を作って文書に置き、見た目と押した結果を集める JavaScript
ROW_SCRIPT = """(args) => {
    const calls = [];
    const row = MindmapPreview.threadRow({
        ...args.props,
        on: {
            open: (...a) => calls.push(["open", ...a]),
            tag: (...a) => calls.push(["tag", ...a]),
        },
    });
    document.body.append(row);
    const tags = [...row.querySelectorAll("button")]
        .filter((button) => (button.getAttribute("data-focus") ?? "").startsWith("tag:"));
    if (args.clickTag !== null) {
        tags.find((button) => button.textContent.includes(args.clickTag)).click();
    }
    if (args.clickRow) row.querySelector("button").click();
    return {
        text: row.textContent.replace(/\\s+/g, " "),
        hasTime: row.querySelector("time[datetime]") !== null,
        tagLabels: tags.map((button) => button.textContent.trim()),
        tagPressed: tags.map((button) => button.getAttribute("aria-pressed")),
        calls,
    };
}"""


def _observe(
    preview_page: Page, props: dict[str, Any], *, click_tag: str | None = None, click_row: bool = False
) -> dict[str, Any]:
    """行を作って見た目と押した結果を返す。"""
    return preview_page.evaluate(
        ROW_SCRIPT, {"props": props, "clickTag": click_tag, "clickRow": click_row}
    )


@pytest.mark.parametrize(
    ("props", "expected_texts", "expected_tags", "has_item_id"),
    [
        pytest.param(
            {"thread": REPLIED},
            ["オープン", "D-12 の失敗時の扱いの相談", "D-12", "AI"],
            ["画面"],
            True,
            id="replied",
        ),
        pytest.param(
            {"thread": NO_SUMMARY},
            ["オープン", "背景の節を 3 行にまとめてほしい", "あなた"],
            [],
            True,
            id="no_summary",
        ),
        pytest.param({"thread": CLOSED}, ["クローズ"], [], True, id="closed"),
        pytest.param({"thread": FREE}, ["オープン", "資料を足しました"], ["調査", "画面"], False, id="free"),
        pytest.param(
            {"thread": REPLIED, "hasPendingReply": True}, ["レビュー中"], ["画面"], True, id="pending_reply"
        ),
    ],
)
def test_thread_row(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected_texts: list[str],
    expected_tags: list[str],
    has_item_id: bool,
) -> None:
    """状態・題・向けた項目・最後の書き手・タグを描く（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, props)
    # 検証
    assert all(text in observed["text"] for text in expected_texts)
    assert observed["hasTime"] is True
    assert observed["tagLabels"] == expected_tags
    # 項目を指さないスレッドは、2 行目に項目の ID が出ない
    assert (any(f"{prefix}-" in observed["text"] for prefix in ("D", "A", "T")) is has_item_id)


def test_thread_row_when_pending(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """まだ送っていない新しいスレッドはレビュー中の札でタグを持たない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, {"pending": PENDING}, click_row=True)
    # 検証
    assert all(text in observed["text"] for text in ["レビュー中", "D-5", "あなた"])
    assert observed["tagLabels"] == []
    assert len(observed["calls"]) == 1
    name, *args = observed["calls"][0]
    assert name == "open"
    assert "C-41" in json.dumps(args)
    assert "true" in json.dumps(args)


def test_thread_row_when_tag(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """タグは行と別のボタンで、絞っているタグを押した状態にする（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, {"thread": FREE, "activeTag": "画面"}, click_tag="画面")
    # 検証
    assert observed["tagLabels"] == ["調査", "画面"]
    assert observed["tagPressed"] == ["false", "true"]
    assert observed["calls"] == [["tag", "画面"]]


@pytest.mark.parametrize(
    ("thread", "expected"),
    [
        pytest.param(REPLIED, "D-12 の失敗時の扱いの相談", id="with_summary"),
        pytest.param(NO_SUMMARY, "背景の節を 3 行にまとめてほしい", id="first_line"),
    ],
)
def test_thread_title(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, thread: dict[str, Any], expected: str
) -> None:
    """要約があれば要約、無ければ最初の書き込みの 1 行目（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    title = preview_page.evaluate("(thread) => MindmapPreview.threadTitle(thread)", thread)
    # 検証
    assert title == expected
