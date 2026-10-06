"""設定の再読み込み（利用者が config.yaml を手で直した後、配信に読み直させる）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。
再読み込みのエンドポイントと記録の取得は HTTP のクライアントで呼ぶ。
"""

from __future__ import annotations

from typing import Any

from display_settings_helpers import graph_look
from playwright.sync_api import Page
from preview_helpers import OpenPreview, ServeWorkspace, fetch_records, http_call
from workspace_fixtures import RECORD_DIR, MakeItem, write_yaml

# 再読み込みのエンドポイントのパス
RELOAD_PATH = "/api/config/reload"

# 見た目が変わるまで待つ上限ミリ秒
LOOK_TIMEOUT_MS = 10_000

# 見た目の既定として選べる値
LOOKS = ("glow", "starlight", "constellation", "deep", "dust")


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """手で直した config.yaml が検査に通れば、検査に通ったことを返し、開いている画面に新しい既定が開き直さずに当たる（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("D-1"), settings=valid_settings)
    open_preview(url, "#tab=graph")
    initial_look = graph_look(page)
    # 画面を開いた後に、config.yaml の見た目の既定を dust に書き換える
    write_yaml(root / RECORD_DIR / "config.yaml", {**valid_settings, "display": {"network_look": "dust"}})
    edited = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    result = http_call(url, RELOAD_PATH, method="POST")
    page.wait_for_function(
        "document.querySelector('.screen.graph')?.dataset.look === 'dust'",
        timeout=LOOK_TIMEOUT_MS,
    )
    # 検証
    # 再読み込みのエンドポイントが、検査に通ったことを返す
    assert result.status == 200
    assert result.json()["settings"]["display"]["network_look"] == "dust"
    # 開いている画面で、つながりに渡る見た目が開き直さずに dust になる
    assert initial_look == "deep"
    assert graph_look(page) == "dust"
    # config.yaml の中身が、手で直したままである
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == edited


def test_error_when_check_fails(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """崩した config.yaml では、違う箇所を示すエラーを返し、最後に検査に通った設定のまま表示する（異常系）。"""
    # 準備
    url, root = serve_workspace(
        make_item("D-1"),
        settings={**valid_settings, "display": {"network_look": "starlight"}},
    )
    open_preview(url, "#tab=graph")
    # 画面を開いた後に、config.yaml の見た目の既定を選べる値に無い rainbow に書き換える
    write_yaml(root / RECORD_DIR / "config.yaml", {**valid_settings, "display": {"network_look": "rainbow"}})
    broken = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    result = http_call(url, RELOAD_PATH, method="POST")
    records = fetch_records(url)
    # 検証
    # 再読み込みのエンドポイントがエラーを返し、本文に見た目の既定のキーと、選べる値が glow・starlight・constellation・deep・dust である理由がある
    assert result.status == 422
    assert result.headers["content-type"].startswith("application/problem+json")
    reasons = [
        line
        for line in result.json()["detail"].splitlines()
        if line.startswith("config.yaml: display.network_look: ")
    ]
    assert len(reasons) == 1
    assert all(look in reasons[0] for look in LOOKS)
    # 記録の取得が返す設定の見た目の既定が starlight で、違う箇所が添えられている
    assert records["settings"]["display"]["network_look"] == "starlight"
    assert any(
        line.startswith("config.yaml: display.network_look: ")
        for line in records["settings_problem"]
    )
    # 開いている画面で、つながりに渡る見た目が starlight のままである
    assert graph_look(page) == "starlight"
    # config.yaml の中身が、手で崩したままである（サーバーが書き換えていない）
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == broken
