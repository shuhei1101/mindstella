"""プレビューを開く（`session` がサーバーが配るプレビューの URL を示し、記録の書き換えを開いている画面へ反映する）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、示された URL を実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_PANEL,
    THREAD_HEADING,
    THREAD_POSTS,
    OpenInEmptyContext,
    OpenPreview,
    open_thread,
    row_ids,
)
from readme_helpers import preview_section
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    McpServer,
    SnapshotTree,
    StartServer,
    WriteThreads,
)

if TYPE_CHECKING:
    from conftest import Replay

# 書き換えが画面に出るまで待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 配信のページの路（`preview_url` が返す URL の終わり）
PAGE_PATH = "/mindstella.html"

# 詳細パネルの HTML の本文の枠
BODY_FRAME = "aside.panel iframe.html-frame[data-html-body]"

# 枠の中の文書の本文の文を返す
FRAME_TEXT_SCRIPT = "(frame) => frame.contentDocument?.body?.textContent ?? ''"

# 書き換えの見張りが基準を取るのを待つミリ秒
WATCH_START_MS = 500

# 札が出るまで待つ上限ミリ秒
CHIP_TIMEOUT_MS = 10_000

# 表の行ごとに、印の class（印が無ければ null）を読む
ROW_MARKS_SCRIPT = """rows => Object.fromEntries(rows.map(
    r => [r.dataset.id, r.querySelector('.row-open + .df-mark')?.className ?? null]
))"""

# 足す検討事項
NEW_DECISION = {
    "title": "新しい問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "options": [{"key": "A", "content": "案 A"}],
}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """プレビューの URL を示され、開くと今の記録が出る。ワークスペースに preview.html は書き出されない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    url = served.data["url"]
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert url.startswith("http://127.0.0.1:")
    assert url.endswith(PAGE_PATH)
    assert row_ids(page) == ["D-1"]
    assert not (root / "preview.html").exists()
    # 直下の README.md のプレビューの節が、示した URL である
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert preview_section(readme).splitlines()[1] == url


def test_normal_when_rewritten(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """記録を書き換えると、再読み込みの操作をせずに、開いている画面が描き直される（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"], "#tab=decisions&view=table")
    page.wait_for_selector("table.grid tbody tr")
    opened_url = page.url
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    assert added.is_error is False, added.text
    page.wait_for_function(
        "document.querySelectorAll('table.grid tbody tr').length === 2", timeout=UPDATE_TIMEOUT_MS
    )
    # 検証
    assert row_ids(page) == ["D-1", "D-2"]
    assert page.url == opened_url
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"


def test_error_when_config_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """config.yaml がスキーマに合わないと、違う箇所を示すエラーが返り、配信は立たない（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"network_look": "rainbow"}})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    again = call_tool("preview_url", workspace=str(root))
    # 検証
    # プレビューの URL の取得がエラーを返し、本文に見た目の既定のキーと、選べる値が示される
    assert result.is_error is True
    assert any(
        line.startswith("config.yaml: display.network_look: ")
        and all(look in line for look in ("glow", "starlight", "constellation", "deep", "dust"))
        for line in result.text.splitlines()
    )
    # 配信が立っていないので、呼び直しても URL を返さず同じエラーになる
    assert again.is_error is True
    assert "config.yaml: display.network_look: " in again.text
    # config.yaml の中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_html_body_rewritten(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """HTML の本文のファイルだけを書き換えると、再読み込みの操作をせずに、開いている詳細パネルの本文が描き直される（正常系）。"""
    # 準備（本文を HTML で持ち、段落「一覧の画面」を持つ資料 A-1 の詳細パネルを開いておく）
    root = make_workspace(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": "<p>一覧の画面</p>\n"}
    )
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"], "#tab=docs&id=A-1")
    page.wait_for_selector(f"{BODY_FRAME}[data-rendered]", state="attached", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_timeout(WATCH_START_MS)
    opened_url = page.url
    # 実行（docs.yaml は書き換えず、本文のファイルだけを書き換える）
    (root / RECORD_DIR / "docs" / "A-1.html").write_text("<p>絞り込みの画面</p>\n", encoding="utf-8")
    page.wait_for_function(
        f"document.querySelector('{BODY_FRAME}')?.contentDocument?.body?.textContent.includes('絞り込みの画面') === true",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証
    text = page.eval_on_selector(BODY_FRAME, FRAME_TEXT_SCRIPT)
    assert "絞り込みの画面" in text
    assert "一覧の画面" not in text
    # 描き直した後も、開いていた画面と URL のハッシュが変わらない
    assert page.url == opened_url
    assert page.get_attribute('nav.tabbar a[data-tab="docs"]', "aria-current") == "page"


def test_normal_when_link_to_change_set(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    open_in_empty_context: OpenInEmptyContext,
) -> None:
    """記録を直して commit した後、その id を diff に渡して得た URL が、そのまとまりの差分の表示で開く（正常系）。"""
    # 準備（まとまり V-1 を持つワークスペース）
    root = make_workspace(make_item("D-1"), make_item("D-2"))
    ws = str(root)
    replay("update", workspace=ws, id="D-2", item={"body_markdown": "D-2 の本文を直した\n"})
    replay("commit", workspace=ws, summary="D-2 を直す")
    # 実行（D-1 を直してまとめ、そのまとまりを指す URL を取る）
    replay("update", workspace=ws, id="D-1", item={"body_markdown": "D-1 の本文を直した\n"})
    committed = replay("commit", workspace=ws, summary="D-1 を直す")
    link = str(replay("preview_url", workspace=ws, diff=committed["id"])["url"])
    # 検証（リンクが 127.0.0.1 の画面を指し、ハッシュが V-2 を持つ）
    parts = urlsplit(link)
    assert committed["id"] == "V-2"
    assert parts.hostname == "127.0.0.1"
    assert parts.path == PAGE_PATH
    assert parse_qs(parts.fragment)["diff"] == ["V-2"]
    # 実行（端末の保存領域が空のブラウザでリンクを開き、検討事項の表へ移る）
    opened = open_in_empty_context(link)
    opened.wait_for_selector(".df-chip", timeout=CHIP_TIMEOUT_MS)
    opened.click('nav.tabbar a[data-tab="decisions"]')
    opened.click('.segment button[data-view="table"]')
    opened.wait_for_selector("table.grid tbody tr")
    # 検証（V-2 の説明の札が出て、D-1 に変更の印が付き、D-2 には付かない）
    assert opened.inner_text(".df-chip-t").endswith("D-1 を直す")
    marks = opened.eval_on_selector_all("table.grid tbody tr", ROW_MARKS_SCRIPT)
    assert marks == {"D-1": "df-mark df-chg", "D-2": None}


# 足す会話ログの日付
LOG_DATE = "2026-10-02"


def _call(server: McpServer, tool: str, **arguments: Any) -> dict[str, Any]:
    """MCP サーバーでツールを呼び、エラーが返ったら本文を添えて失敗させ、構造化の結果を返す。"""
    result = server.call(tool, **arguments)
    assert result.is_error is False, result.text
    assert result.data is not None
    return result.data


def test_normal_when_body_link_written_to_record(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_in_empty_context: OpenInEmptyContext,
) -> None:
    """記録の本文に直したまとまりを書くと、ポートを含まないリンクになり、配信を別のポートで立て直しても開ける（正常系）。"""
    # 準備（D-1 と D-2 を持ち、まとまり V-1 を 1 つ持つ）
    root = make_workspace(make_item("D-1"), make_item("D-2"))
    ws = str(root)
    first = start_server()
    _call(first, "update", workspace=ws, id="D-2", item={"body_markdown": "D-2 の本文を直した\n"})
    _call(first, "commit", workspace=ws, summary="D-2 を直す")
    # 実行（D-1 を直してまとめ、V-2 を指すリンクを本文に書いた会話ログを足してまとめる）
    _call(first, "update", workspace=ws, id="D-1", item={"body_markdown": "D-1 の本文を直した\n"})
    set_id = str(_call(first, "commit", workspace=ws, summary="D-1 を直す")["id"])
    added = _call(
        first,
        "add",
        workspace=ws,
        kind="log",
        item={
            "title": "D-1 を直した",
            "date": LOG_DATE,
            "body_markdown": f"[D-1 を直したところ](#diff={set_id})\n",
        },
    )
    _call(first, "commit", workspace=ws, summary="会話ログを足す")
    old_port = urlsplit(str(_call(first, "preview_url", workspace=ws)["url"])).port
    # 検証（足した会話ログの本文のリンクの先が #diff=V-2 で、ホストとポートを含まない）
    body = (root / RECORD_DIR / "docs" / f"{added['id']}.md").read_text(encoding="utf-8")
    assert set_id == "V-2"
    assert f"(#diff={set_id})" in body
    assert "127.0.0.1" not in body
    assert "http" not in body
    # 実行（配信を止め、前のポートを塞いだまま別のポートで立て直し、会話ログの詳細パネルを開く）
    first.stop()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupier:
        occupier.bind(("127.0.0.1", old_port))
        occupier.listen()
        second = start_server()
        new_url = str(_call(second, "preview_url", workspace=ws)["url"])
        # 検証（立て直した配信のポートが、立て直す前と違う）
        assert urlsplit(new_url).port != old_port
        opened = open_in_empty_context(f"{new_url}#tab=logs&id={added['id']}")
        opened.wait_for_selector("aside.panel.open .md a")
        # 実行（本文の V-2 を指すリンクを押す）
        opened.locator("aside.panel .md a", has_text="D-1 を直したところ").click()
        opened.wait_for_selector(".df-chip", timeout=CHIP_TIMEOUT_MS)
        # 検証（V-2 の説明の札が出て、会話ログの詳細パネルが開いたまま）
        assert opened.inner_text(".df-chip-t").endswith("D-1 を直す")
        assert opened.locator("aside.panel.open").count() == 1
        assert parse_qs(urlsplit(opened.url).fragment)["id"] == [added["id"]]
        # 実行（検討事項の表へ移る）
        opened.click('nav.tabbar a[data-tab="decisions"]')
        opened.click('.segment button[data-view="table"]')
        opened.wait_for_selector("table.grid tbody tr")
        # 検証（D-1 に変更の印が付き、D-2 には付かない）
        marks = opened.eval_on_selector_all("table.grid tbody tr", ROW_MARKS_SCRIPT)
        assert marks == {"D-1": "df-mark df-chg", "D-2": None}


def test_normal_when_thread_link_written(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    start_server: StartServer,
    open_in_empty_context: OpenInEmptyContext,
) -> None:
    """スレッドに直したまとまりを書くと、ポートを含まないリンクになり、配信を別のポートで立て直しても開ける（正常系）。"""
    # 準備（D-1 と D-2 を持ち、まとまり V-1 を 1 つ持つ。D-1 へのスレッドの書き込みは利用者の `D-1 を直してほしい` だけで、取り込み待ち）
    root = make_workspace(make_item("D-1"), make_item("D-2"))
    ws = str(root)
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="D-1 を直してほしい", created="2026-10-12T01:00:00+00:00"),
            summary="D-1 を直してほしい",
            target="D-1",
        ),
    )
    first = start_server()
    _call(first, "update", workspace=ws, id="D-2", item={"body_markdown": "D-2 の本文を直した\n"})
    _call(first, "commit", workspace=ws, summary="D-2 を直す")
    # 実行（取り込み待ちのスレッドを読み、D-1 を直してまとめ、V-2 を指すリンクを書いた返信を足す）
    awaiting = _call(first, "threads", workspace=ws, awaiting=True)["items"]
    _call(first, "thread", workspace=ws, id="TH-1")
    _call(first, "update", workspace=ws, id="D-1", item={"body_markdown": "D-1 の本文を直した\n"})
    set_id = str(_call(first, "commit", workspace=ws, summary="D-1 を直す")["id"])
    _call(
        first,
        "reply",
        workspace=ws,
        id="TH-1",
        body=f"D-1 を直しました。[D-1 を直したところ](#diff={set_id})",
        summary="D-1 を直した",
    )
    old_port = urlsplit(str(_call(first, "preview_url", workspace=ws)["url"])).port
    # 検証（足した返信の本文が (#diff=V-2) で終わるリンクを持ち、ホストとポートを含まない）
    threads = yaml.safe_load((root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8"))["items"]
    reply = threads[0]["posts"][-1]
    assert [item["id"] for item in awaiting] == ["TH-1"]
    assert set_id == "V-2"
    assert reply["author"] == "ai"
    assert reply["body"].rstrip().endswith(f"(#diff={set_id})")
    assert "127.0.0.1" not in reply["body"]
    assert "http" not in reply["body"]
    # 実行（配信を止め、前のポートを塞いだまま別のポートで立て直し、コメントの一覧から D-1 へのスレッドを開く）
    first.stop()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupier:
        occupier.bind(("127.0.0.1", old_port))
        occupier.listen()
        second = start_server()
        new_url = str(_call(second, "preview_url", workspace=ws)["url"])
        # 検証（立て直した配信のポートが、立て直す前と違う）
        assert urlsplit(new_url).port != old_port
        opened = open_in_empty_context(f"{new_url}#tab=decisions&view=table")
        opened.wait_for_selector("table.grid tbody tr")
        open_thread(opened, "TH-1")
        opened.wait_for_selector(f"{THREAD_POSTS}:nth-child(2) .post-body a.setlink")
        # 実行（AI の返信の V-2 を指すリンクを押す）
        opened.locator(f"{THREAD_POSTS}:nth-child(2) .post-body a.setlink").click()
        opened.wait_for_selector(".df-chip", timeout=CHIP_TIMEOUT_MS)
        # 検証（V-2 の説明の札が出て、D-1 に変更の印が付き、D-2 には付かず、D-1 へのスレッドの画面が開いたまま）
        assert opened.inner_text(".df-chip-t").endswith("D-1 を直す")
        marks = opened.eval_on_selector_all("table.grid tbody tr", ROW_MARKS_SCRIPT)
        assert marks == {"D-1": "df-mark df-chg", "D-2": None}
        assert opened.locator(f"{COMMENTS_PANEL}.open").count() == 1
        assert opened.locator(THREAD_HEADING).count() == 1
        assert parse_qs(urlsplit(opened.url).fragment)["diff"] == [set_id]
