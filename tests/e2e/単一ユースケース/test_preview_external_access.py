"""プレビューを外から見る（待ち受けのポート・許可するホスト名・起動と終了のフックを設定し、外の入口の内側で開いたプレビューで記録を読み、コメントを送る）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、外の入口（トンネル・リバースプロキシ）の代わりに、外のホスト名の Host と Origin を付けて
配信のポートへ渡す転送を置く。その転送を通して実際のブラウザで開く。描画のライブラリは CDN から読む。
外の入口のサービスそのものと、その認証は確かめない。
"""

from __future__ import annotations

import signal
import socket
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml
from external_access_helpers import (
    HOOK_SETTLE_SEC,
    ForwardProxy,
    free_port,
    read_hook_lines,
    read_settled_hook_lines,
    recording_hook,
)
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    OpenPreview,
    row_ids,
)
from workspace_fixtures import RECORD_DIR, MakeItem, MakeWorkspace, StartServer

# 許可するホスト名を渡す環境変数と、許可するホスト名（外の入口のホスト名）
ALLOWED_HOSTS_ENV = "MINDSTELLA_ALLOWED_HOSTS"
EXTERNAL_HOST = "preview.example.test"

# 起動時と終了時のフックを渡す環境変数
START_HOOK_ENV = "MINDSTELLA_PREVIEW_START_HOOK"
STOP_HOOK_ENV = "MINDSTELLA_PREVIEW_STOP_HOOK"

# 配信が画面を返すパス
PAGE_PATH = "/mindstella.html"

# 検討事項の表を開くハッシュと、D-1 の詳細パネルを開くハッシュ
TABLE_HASH = "#tab=decisions&view=table"
DETAIL_HASH = "#tab=decisions&id=D-1"

# 書くコメント
COMMENT_BODY = "案 A にする"

# 結果が画面に出るまで待つ上限ミリ秒
RESULT_TIMEOUT_MS = 10_000

# 端末の別のアドレスへのつなぎを待つ上限秒数
CONNECT_TIMEOUT_SEC = 1

# コメントの一覧の送る帯と、その結果
SEND_BAND = f"{COMMENTS_PANEL} .send-band"
BAND_RESULT = f"{SEND_BAND} .send-msg"

# 外へ出る経路を調べるために向ける、文書用のアドレス（UDP は何も送らず、経路だけを引く）
PROBE_ADDRESS = ("192.0.2.1", 9)


def _non_loopback_address() -> str | None:
    """この端末の、127.0.0.1 以外の IPv4 アドレスを返す。外へ出る経路が無ければ None。"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(PROBE_ADDRESS)
        except OSError:
            # 外へ出る経路が無い端末
            return None
        address = str(probe.getsockname()[0])
    return None if address.startswith("127.") else address


def test_normal_when_port_fixed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """ポートを固定して許可するホスト名を設定すると、外のホスト名で開いた画面に記録が出て、コメントを送れる（正常系）。"""
    # 準備
    port = free_port()
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "preview": {"port": port}})
    server = start_server(extra_env={ALLOWED_HOSTS_ENV: EXTERNAL_HOST})
    # 実行（スキルの手順どおりに、プレビューの URL を取る）
    served = server.call("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    listen_url = str(served.data["url"])
    # 実行（外の入口を通して開き、D-1 を表で読んで、詳細パネルからコメントを書いて送る）
    with ForwardProxy(upstream_port=port, external_host=EXTERNAL_HOST) as gateway:
        open_preview(f"{gateway.url}{PAGE_PATH}", TABLE_HASH)
        page.wait_for_selector("table.grid tbody tr")
        shown_ids = row_ids(page)
        page.evaluate("hash => { location.hash = hash }", DETAIL_HASH)
        page.wait_for_selector(DETAIL_TEXTAREA)
        page.fill(DETAIL_TEXTAREA, COMMENT_BODY)
        page.get_by_role("button", name="レビューに追加").click()
        page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=RESULT_TIMEOUT_MS)
        page.click(COMMENTS_BUTTON)
        page.wait_for_selector(f"{COMMENTS_PANEL}.open")
        page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").click()
        page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=RESULT_TIMEOUT_MS)
    # 検証
    # 配信の待ち受けは 127.0.0.1 の、設定したポートだけで、端末の別のアドレスからはつながらない
    assert listen_url == f"http://127.0.0.1:{port}{PAGE_PATH}"
    other_address = _non_loopback_address()
    if other_address is not None:
        with pytest.raises(OSError, match=r"."):
            socket.create_connection((other_address, port), timeout=CONNECT_TIMEOUT_SEC)
    # 外のホスト名で開いた画面に D-1 がある
    assert shown_ids == ["D-1"]
    # 送ったコメントが、ワークスペースの送信に残る
    submissions = yaml.safe_load(
        (root / RECORD_DIR / "submissions.yaml").read_text(encoding="utf-8")
    )["items"]
    assert [(item["target"], item["body"]) for item in submissions] == [("D-1", COMMENT_BODY)]


def test_normal_when_hooks_set(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
) -> None:
    """起動時と終了時のフックを設定すると、配信を立てたときと止めるときに、ポートとワークスペースの名前を受け取って呼ばれる（正常系）。"""
    # 準備
    start_record = tmp_path / "start-hook.txt"
    stop_record = tmp_path / "stop-hook.txt"
    root = make_workspace(make_item("D-1"), name="家計簿")
    server = start_server(
        extra_env={
            ALLOWED_HOSTS_ENV: EXTERNAL_HOST,
            START_HOOK_ENV: recording_hook(start_record),
            STOP_HOOK_ENV: recording_hook(stop_record),
        }
    )
    # 実行（配信を立て、Claude Code を閉じる代わりに、標準入力は開いたまま SIGTERM を送る）
    served = server.call("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    port = urlsplit(str(served.data["url"])).port
    started_lines = read_hook_lines(start_record)
    server.process.send_signal(signal.SIGTERM)
    exit_code = server.wait_exit()
    stopped_lines = read_settled_hook_lines(stop_record)
    # 検証
    # 起動時のフックが 1 回、配信のポートとワークスペースのフォルダの名前を受け取って呼ばれている
    assert started_lines == [f"{port} 家計簿"]
    assert read_settled_hook_lines(start_record) == [f"{port} 家計簿"]
    # 終了時のフックが 1 回、起動時と同じポートとワークスペースの名前を受け取って呼ばれている
    assert stopped_lines == [f"{port} 家計簿"]
    # MCP サーバーのプロセスが残っていない
    assert exit_code == 0
    assert server.process.poll() == 0


def test_error_when_port_in_use(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
) -> None:
    """設定したポートを別のプロセスが使っていると、待ち受けを立てられない理由を示すエラーが返り、フックは呼ばれない（異常系）。"""
    # 準備
    record = tmp_path / "start-hook.txt"
    server = start_server(extra_env={START_HOOK_ENV: recording_hook(record)})
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupier:
        occupier.bind(("127.0.0.1", 0))
        occupier.listen()
        port = int(occupier.getsockname()[1])
        root = make_workspace(
            make_item("D-1"), settings={**valid_settings, "preview": {"port": port}}
        )
        # 実行
        served = server.call("preview_url", workspace=str(root))
        # 検証
        # プレビューの URL の取得がエラーを返し、本文に待ち受けを立てられない理由とポートがある
        assert served.is_error is True
        assert served.text.startswith("エラー: ")
        assert "プレビューの配信を立てられません" in served.text
        assert str(port) in served.text
        # 設定したポートを先に待ち受けていた側が、そのまま待ち受けている
        with socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT_SEC):
            pass
    # 起動時のフックが呼ばれていない（呼ばれるなら届くはずの間だけ待つ）
    time.sleep(HOOK_SETTLE_SEC)
    assert not record.exists()
