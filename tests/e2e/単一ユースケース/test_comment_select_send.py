"""コメントを選んで送る（コメントの一覧でレビュー中のコメントを確かめ、直し・消し・足して、チェックしたものだけをまとめて送る）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    FREE_FORM,
    FREE_TEXTAREA,
    OpenPreview,
)
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeComment,
    MakeItem,
    MakeWorkspace,
    StartServer,
    WriteComments,
)

# 資料 A-1 の本文（2 行目を指すコメントを付ける）
BODY = "最初の文\n言い換えたい文\n最後の文\n"

# 2 行目を指す箇所
SECOND_LINE = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 画面の高さを超える長さの本文（段落 1〜60 を空行で区切る。段落 k は k 番目の段落で、行は 2k - 1）
LONG_BODY = "\n\n".join(f"段落 {number}" for number in range(1, 61)) + "\n"

# 長い本文の終わり近く（段落 58 は 115 行目）を指す箇所
NEAR_END = {"kind": "body", "start": 115, "end": 115, "text": "段落 58"}

# 縮めた後の A-1 の本文（3 行）
SHORT_BODY = "1 行目\n2 行目\n3 行目\n"

# 詳細パネルを別画面として積み、開くときに履歴へ積む幅（これ以下）
NARROW_WIDTH = 800

# 結果が画面に出るまで待つ上限ミリ秒
RESULT_TIMEOUT_MS = 10_000

# コメントの一覧の送る帯の結果とボタン、行
BAND_RESULT = f"{COMMENTS_PANEL} .send-band .send-msg"
SEND_BAND = f"{COMMENTS_PANEL} .send-band"


def _serve(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    write_comments: WriteComments,
    *items: dict[str, Any],
    comments: tuple[dict[str, Any], ...],
    bodies: dict[str, str] | None = None,
) -> tuple[str, Path]:
    """項目とレビュー中のコメントを持つワークスペースを作り、配信の URL とワークスペースのフォルダを返す。"""
    root = make_workspace(*items, bodies=bodies)
    write_comments(root, *comments)
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    return str(served.data["url"]), root


def _row(comment_id: str) -> str:
    """コメントの行の選択子を返す。"""
    return f"{COMMENTS_PANEL} li[data-comment='{comment_id}']"


def _open_list(page: Page) -> None:
    """トップバーのコメントのボタンで一覧を開き、開き終わるのを待つ。"""
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.wait_for_function(
        "document.querySelector('aside.comments-panel').getBoundingClientRect().x === 0"
    )


def _read(root: Path, name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML の items を読む（ファイルが無ければ 0 件）。"""
    path = root / RECORD_DIR / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


# 検討事項のボードを開くハッシュと、ボードの D-1 のカードのコメントの印の読み上げの文字
BOARD_HASH = "#tab=decisions&view=board"
D1_MARK = '.board button.card[data-id="D-1"] .cmk .sr-only'


def _wait_d1_mark(page: Page, spoken: str | None) -> None:
    """ボードの D-1 のカードの印の読み上げの文字が、渡した文字（印が無いなら None）になるのを待つ。"""
    page.wait_for_function(
        """(spoken) => {
            const mark = document.querySelector('.board button.card[data-id="D-1"] .cmk .sr-only');
            return (mark === null ? null : mark.textContent) === spoken;
        }""",
        arg=spoken,
        timeout=RESULT_TIMEOUT_MS,
    )


def _without_target(comment: dict[str, Any]) -> dict[str, Any]:
    """向けた項目のキーを持たない（項目を指さない）コメントにする。"""
    return {key: value for key, value in comment.items() if key != "target"}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """一覧で項目に紐づかないコメントを足し、それだけチェックを外して送ると、残りが取り込んでいない送信になる（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_comments,
        make_item("D-1"),
        make_item("A-1"),
        comments=(
            make_comment("C-1", target="D-1", body="案 A にする"),
            make_comment("C-2", target="A-1", body="ここは言い換える", loc=SECOND_LINE),
        ),
        bodies={"A-1.md": BODY},
    )
    open_preview(url, BOARD_HASH)
    # 実行
    _open_list(page)
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} input.row-check", "cs => cs.map(c => c.checked)"
    ) == [True, True]
    # 送る前は、ボードの D-1 のカードにコメントの印（件数 1）がある
    assert page.inner_text(D1_MARK) == "コメント 1 件"
    page.fill(FREE_TEXTAREA, "全体に目を通した")
    page.locator(FREE_FORM).get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(_row("C-3"), timeout=RESULT_TIMEOUT_MS)
    page.locator(f"{_row('C-3')} input.row-check").uncheck()
    page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=RESULT_TIMEOUT_MS)
    # 検証
    submissions = _read(root, "submissions.yaml")
    assert [(item.get("target"), item["body"]) for item in submissions] == [
        ("D-1", "案 A にする"),
        ("A-1", "ここは言い換える"),
    ]
    assert submissions[1]["loc"] == SECOND_LINE
    assert all(item["taken"] is None for item in submissions)
    assert [(item.get("target"), item["body"]) for item in _read(root, "comments.yaml")] == [
        (None, "全体に目を通した")
    ]
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-3"]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    # 画面を開き直さずに、ボードの D-1 のカードから印が消える
    _wait_d1_mark(page, None)
    assert page.locator('.board button.card[data-id="D-1"] .cmk').count() == 0


def test_normal_when_jump_to_location(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """一覧の行を押すと、A-1 の詳細パネルを開いて箇所までスクロールして示し、戻る操作で一覧へ戻る（正常系。パネルを開くときに履歴へ積む幅 900px 以下）。"""
    # 準備
    url, _ = _serve(
        make_workspace,
        call_tool,
        write_comments,
        make_item("A-1"),
        comments=(make_comment("C-1", target="A-1", body="終わり近くの意見", loc=NEAR_END),),
        bodies={"A-1.md": LONG_BODY},
    )
    open_preview(url, width=NARROW_WIDTH)
    _open_list(page)
    # 実行
    page.click(f"{_row('C-1')} button.row-target")
    page.wait_for_selector("aside.panel.open .md .loc-hit")
    # 検証（詳細パネルが開き、箇所の行が画面の中にあり、示されている）
    assert page.inner_text("aside.panel .panel-kind") == "資料 A-1"
    box = page.locator("aside.panel .md .loc-hit").bounding_box()
    assert box is not None
    assert 0 <= box["y"] < page.evaluate("innerHeight")
    assert page.inner_text("aside.panel .md .loc-hit") == "段落 58"
    # 実行（ブラウザの戻る操作）
    page.go_back()
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    # 検証（一覧に戻る）
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert "id=" not in page.evaluate("location.hash")


def test_normal_when_edit_remove_restore(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """一覧で本文を直し、別のコメントを消して戻すと、2 件が残り、開き直しても同じ 2 件が出る（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_comments,
        make_item("D-1"),
        comments=(
            make_comment("C-1", target="D-1", body="案 A にする"),
            make_comment("C-2", target="D-1", body="案 B も見たい"),
        ),
    )
    open_preview(url, BOARD_HASH)
    _open_list(page)
    assert page.inner_text(D1_MARK) == "コメント 2 件"
    # 実行（書き換える）
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを直す").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "案 A に決める")
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="直す").click()
    page.wait_for_function(
        "document.querySelector(\"li[data-comment='C-1'] .review-body\")?.textContent === '案 A に決める'",
        timeout=RESULT_TIMEOUT_MS,
    )
    # 実行（消す）
    page.locator(_row("C-2")).get_by_role("button", name="D-1 へのコメントを削除").click()
    page.wait_for_selector(f"{_row('C-2')}.removed", timeout=RESULT_TIMEOUT_MS)
    # 検証（消した後は、ボードの D-1 のカードの件数が 1）
    _wait_d1_mark(page, "コメント 1 件")
    # 実行（戻す）
    page.get_by_role("button", name="元に戻す").click()
    page.wait_for_selector(f"{_row('C-2')} button.row-target", timeout=RESULT_TIMEOUT_MS)
    # 検証（戻した後は件数が 2）
    _wait_d1_mark(page, "コメント 2 件")
    assert [(item["id"], item["body"]) for item in _read(root, "comments.yaml")] == [
        ("C-1", "案 A に決める"),
        ("C-2", "案 B も見たい"),
    ]
    # 開き直しても同じ 2 件が出る
    page.reload()
    page.wait_for_selector("main#main > *", state="attached")
    _open_list(page)
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .review-body", "bodies => bodies.map(b => b.textContent)"
    ) == ["案 A に決める", "案 B も見たい"]


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """サーバーを止めてからまとめて送ると、送れなかった旨を出し、2 件をチェックしたまま一覧に残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(
        root,
        make_comment("C-1", target="D-1", body="案 A にする"),
        make_comment("C-2", target="D-1", body="案 B も見たい"),
    )
    server = start_server()
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"])
    _open_list(page)
    # 一覧を開いた後にサーバーを止める
    server.close_stdin()
    server.wait_exit()
    # 実行
    page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.failed", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert "送れませんでした" in page.inner_text(BAND_RESULT)
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} input.row-check", "cs => cs.map(c => c.checked)"
    ) == [True, True]
    assert not (root / RECORD_DIR / "submissions.yaml").exists()
    assert len(_read(root, "comments.yaml")) == 2


def test_error_when_nothing_checked(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """ただ 1 件のチェックを外すと、まとめて送るを押せなくなる（異常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_comments,
        make_item("D-1"),
        comments=(make_comment("C-1", target="D-1", body="案 A にする"),),
    )
    open_preview(url)
    _open_list(page)
    # 実行
    page.locator(f"{_row('C-1')} input.row-check").uncheck()
    # 検証
    assert page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").is_disabled()
    assert not (root / RECORD_DIR / "submissions.yaml").exists()


def test_error_when_location_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """溜めた後に本文が縮んで箇所が合わなくなると、どれも送らず理由を出し、箇所を外せば送れる（異常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_comments,
        make_item("D-1"),
        make_item("A-1"),
        comments=(
            make_comment(
                "C-1",
                target="A-1",
                body="5 行目への意見",
                loc={"kind": "body", "start": 5, "end": 5, "text": "5 行目"},
            ),
            make_comment("C-2", target="D-1", body="案 A にする"),
        ),
        bodies={"A-1.md": "1 行目\n2 行目\n3 行目\n4 行目\n5 行目\n"},
    )
    open_preview(url)
    _open_list(page)
    # 溜めた後に、Claude Code が A-1 の本文を 3 行に書き換えた形にする
    (root / RECORD_DIR / "docs" / "A-1.md").write_text(SHORT_BODY, encoding="utf-8")
    # 実行（まとめて送る）
    page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.stale", timeout=RESULT_TIMEOUT_MS)
    # 検証（何も送らず、A-1 への行に理由が出る）
    assert not (root / RECORD_DIR / "submissions.yaml").exists()
    assert len(_read(root, "comments.yaml")) == 2
    assert page.locator(f"{_row('C-1')} .row-stale").count() == 1
    assert page.locator(f"{_row('C-2')} .row-stale").count() == 0
    # 実行（箇所を外してもう一度送る）
    page.get_by_role("button", name="箇所を外す").click()
    page.wait_for_function(
        "!document.querySelector(\"li[data-comment='C-1'] .row-stale\")", timeout=RESULT_TIMEOUT_MS
    )
    page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=RESULT_TIMEOUT_MS)
    # 検証（2 件が送信になり、A-1 への送信は箇所を持たない）
    submissions = _read(root, "submissions.yaml")
    assert [(item["target"], item["body"]) for item in submissions] == [
        ("A-1", "5 行目への意見"),
        ("D-1", "案 A にする"),
    ]
    assert submissions[0].get("loc") is None
