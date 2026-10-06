"""項目へコメントする（サーバーが配るプレビューの詳細パネルで、開いている項目へのコメントを書き、送らずにレビュー中として溜める）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    OpenPreview,
    click_item_ball,
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

# 未決定の検討事項 D-1 の案
OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]

# 溜める本文
BODY = "案 A にする"

# 溜めずにパネルを閉じる書きかけの本文
DRAFT_BODY = "案 B も見たい"

# 一覧の画面で印を見るときの、D-1 と A-1 の本文（D-1 の 2 行目を指すコメントを付ける）
LIST_BODY = "最初の文\n言い換えたい文\n"

# D-1 の本文の 2 行目を指す箇所
SECOND_LINE = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 検討事項のボードを開くハッシュ
BOARD_HASH = "#tab=decisions&view=board"

# 印を置く場所ごとに、項目の ID → 読み上げの文字を返す（`root` の中だけを見る）
MARKS_SCRIPT = """(root) => Object.fromEntries(
    [...document.querySelectorAll(`${root} [data-comment-target]`)]
        .filter((place) => place.querySelector('.cmk') !== null)
        .map((place) => [place.dataset.commentTarget, place.querySelector('.cmk .sr-only').textContent])
)"""

# つながりの、見せている名前の横の印の読み上げの文字を全て返す
GRAPH_MARKS_SCRIPT = """() => [...document.querySelectorAll('.g3-marks .cmk')]
    .filter((mark) => mark.style.visibility !== 'hidden')
    .map((mark) => mark.querySelector('.sr-only').textContent)
    .sort()"""

# つながりの、見せている印のうち、キャンバスの中央から横・縦に [dx, dy] px 以内にある印の読み上げの文字を返す（選んで寄った玉は中央に来る）
CENTER_MARKS_SCRIPT = """([dx, dy]) => {
    const canvas = document.getElementById('graph-canvas').getBoundingClientRect();
    const cx = canvas.left + canvas.width / 2;
    const cy = canvas.top + canvas.height / 2;
    return [...document.querySelectorAll('.g3-marks .cmk')]
        .filter((mark) => mark.style.visibility !== 'hidden')
        .filter((mark) => {
            const box = mark.getBoundingClientRect();
            return Math.abs((box.left + box.right) / 2 - cx) <= dx && Math.abs((box.top + box.bottom) / 2 - cy) <= dy;
        })
        .map((mark) => mark.querySelector('.sr-only').textContent);
}"""

# 選んで寄った玉の名前の横の印を探す範囲（キャンバスの中央から横・縦に離れてよい px）
CENTER_WINDOW = [110, 60]

# 玉を選んだ後、さらに寄る 1 回のホイールの量と、寄り終わるまで待つミリ秒
WHEEL_IN_DELTA = -200
ZOOM_SETTLE_MS = 3_000

# 全体を表示した距離で、印が出ないことを確かめるまで待つミリ秒（玉が広がる時間より長く）
FIT_SETTLE_MS = 2_500

# 画面に結果が出るまで待つ上限ミリ秒
RESULT_TIMEOUT_MS = 10_000

# 閉じるときに保つ書きかけが、ファイルに届くまで待つミリ秒
DRAFT_FLUSH_WAIT_MS = 600


def _open_detail(page: Page, open_preview: OpenPreview, url: str) -> None:
    """検討事項 D-1 の詳細パネルを開き、コメントの入力欄が出るのを待つ。"""
    open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector(DETAIL_TEXTAREA)


def _read_comments(root: Any) -> list[dict[str, Any]]:
    """ワークスペースのレビュー中のコメントを読む（ファイルが無ければ 0 件）。"""
    path = root / RECORD_DIR / "comments.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """詳細パネルでコメントを溜めると、レビュー中のコメントとして残り、入力欄が空になる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"], BOARD_HASH)
    # 実行（ボードの D-1 のカードを押して詳細パネルを開き、コメントを溜める）
    page.click('.board button.card[data-id="D-1"]')
    page.wait_for_selector(DETAIL_TEXTAREA)
    assert page.locator('.board button.card[data-id="D-1"] .cmk').count() == 0
    page.fill(DETAIL_TEXTAREA, BODY)
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=RESULT_TIMEOUT_MS)
    # 検証
    comments = _read_comments(root)
    assert [(item["target"], item["body"]) for item in comments] == [("D-1", BODY)]
    assert not (root / RECORD_DIR / "submissions.yaml").exists()
    assert page.inner_text(DETAIL_MESSAGE) == "レビューに追加しました（レビュー中 1 件）。"
    assert page.input_value(DETAIL_TEXTAREA) == ""
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before
    # 画面を開き直さずに、ボードの D-1 のカードの右端に「コメント 1 件」の印が出る
    mark = '.board button.card[data-id="D-1"] .c-meta > .cmk-place > .cmk'
    page.wait_for_selector(mark, timeout=RESULT_TIMEOUT_MS)
    assert page.inner_text(f"{mark} .sr-only") == "コメント 1 件"
    assert page.eval_on_selector(
        '.board button.card[data-id="D-1"] .c-meta', "m => m.lastElementChild.matches('.cmk-place')"
    )


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文が空だと溜めず、本文が要る旨を出す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行
    page.fill(DETAIL_TEXTAREA, "   ")
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.empty", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert _read_comments(root) == []
    assert "コメントを入れてから追加してください。" in page.inner_text(DETAIL_MESSAGE)


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """サーバーを止めてから溜めると、溜められなかった旨を出し、入力した本文を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    server = start_server()
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 開いた後にサーバーを止める
    server.close_stdin()
    server.wait_exit()
    # 実行
    page.fill(DETAIL_TEXTAREA, BODY)
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.failed", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert "レビューに追加できませんでした" in page.inner_text(DETAIL_MESSAGE)
    assert page.input_value(DETAIL_TEXTAREA) == BODY
    assert _read_comments(root) == []


def test_normal_when_draft_restored_after_restart(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """溜めずにパネルを閉じた書きかけを、サーバーを立ち上げ直した後の新しい URL で開いた入力欄へ戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    first_server = start_server()
    served = first_server.call("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行（書きかけを入れて溜めずにパネルを閉じる）
    page.fill(DETAIL_TEXTAREA, DRAFT_BODY)
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    page.wait_for_timeout(DRAFT_FLUSH_WAIT_MS)
    # サーバーを止めて立て直し、新しい URL で開く
    first_server.close_stdin()
    first_server.wait_exit()
    second_server = start_server()
    restarted = second_server.call("preview_url", workspace=str(root))
    assert restarted.data is not None
    _open_detail(page, open_preview, restarted.data["url"])
    # 検証
    assert restarted.data["url"] != served.data["url"]
    assert page.input_value(DETAIL_TEXTAREA) == DRAFT_BODY
    assert _read_comments(root) == []


def test_normal_when_marks_shown_in_lists(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """コメントを書いた項目に、ボード・マップ・表・つながりで件数の印が出る（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2"),
        make_item("T-1"),
        make_item("A-1", body="A-1.md"),
        bodies={"D-1.md": LIST_BODY, "A-1.md": LIST_BODY},
    )
    write_comments(
        root,
        make_comment("C-1", target="D-1"),
        make_comment("C-2", target="D-1", loc=SECOND_LINE),
        make_comment("C-3", target="T-1"),
        make_comment("C-4", target="A-1"),
        {key: value for key, value in make_comment("C-5").items() if key != "target"},
    )
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    # 実行・検証（検討事項のボード・マップ・表）
    open_preview(served.data["url"], BOARD_HASH)
    page.wait_for_selector(".board button.card")
    assert page.evaluate(MARKS_SCRIPT, ".board") == {"D-1": "コメント 2 件"}
    page.click('.segment button[data-view="map"]')
    page.wait_for_selector("#decision-map .map-node.n-item")
    assert page.evaluate(MARKS_SCRIPT, "#decision-map") == {"D-1": "コメント 2 件"}
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid tbody tr")
    assert page.evaluate(MARKS_SCRIPT, "table.grid") == {"D-1": "コメント 2 件"}
    # 実行・検証（タスクのボードと表）
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".board button.card")
    assert page.evaluate(MARKS_SCRIPT, ".board") == {"T-1": "コメント 1 件"}
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid tbody tr")
    assert page.evaluate(MARKS_SCRIPT, "table.grid") == {"T-1": "コメント 1 件"}
    # 実行・検証（資料のカードと表）
    page.click('nav.tabbar a[data-tab="docs"]')
    page.wait_for_selector(".doc-grid button.card")
    assert page.evaluate(MARKS_SCRIPT, ".doc-grid") == {"A-1": "コメント 1 件"}
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid tbody tr")
    assert page.evaluate(MARKS_SCRIPT, "table.grid") == {"A-1": "コメント 1 件"}
    # 実行・検証（つながり。全体を表示した距離では、どの玉にも印が出ない）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    page.wait_for_timeout(FIT_SETTLE_MS)
    assert page.evaluate(GRAPH_MARKS_SCRIPT) == []
    # 実行・検証（玉を選んで名前が読める距離までホイールで寄ると、D-1・T-1・A-1 の名前の右に印が出る。D-2 には出ない）
    expected = {"D-1": ["コメント 2 件"], "T-1": ["コメント 1 件"], "A-1": ["コメント 1 件"], "D-2": []}
    for item_id, spoken in expected.items():
        click_item_ball(page, item_id)
        page.wait_for_selector("aside.panel.open")
        box = page.locator("#graph-canvas").bounding_box()
        assert box is not None
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.wheel(0, WHEEL_IN_DELTA)
        page.wait_for_timeout(ZOOM_SETTLE_MS)
        assert page.evaluate(CENTER_MARKS_SCRIPT, CENTER_WINDOW) == spoken, item_id
    # コメントのボタンの件数は、項目を指さないコメントを含めた 5 件
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "5"
