"""設定の再読み込み（POST /api/config/reload）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from workspace_fixtures import RECORD_DIR, write_yaml

from .fixture_types import MakeWorkspace
from .http_helpers import EventStream, http_request

# 再読み込みのパス
RELOAD_PATH = "/api/config/reload"

# 再読み込みしてから知らせが届くまでを待つ上限秒数
CHANGED_WITHIN_SEC = 2


def test_normal(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """手で直した config.yaml が検査に通れば、新しい設定を使い知らせる（正常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    stream = open_events(url)
    write_yaml(
        root / RECORD_DIR / "config.yaml", {**valid_settings, "display": {"network_look": "dust"}}
    )
    # 実行
    result = http_request(url, RELOAD_PATH, method="POST")
    # 検証
    assert result.status == 200
    assert result.json()["settings"]["display"]["network_look"] == "dust"
    records = http_request(url, "/api/records").json()
    assert records["settings"]["display"]["network_look"] == "dust"
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True


def test_error_when_check_fails(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
) -> None:
    """崩れた config.yaml では、最後に通った設定のまま違う箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"network_look": "starlight"}})
    url = serve_preview(root)
    write_yaml(
        root / RECORD_DIR / "config.yaml",
        {**valid_settings, "display": {"network_look": "rainbow"}},
    )
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    result = http_request(url, RELOAD_PATH, method="POST")
    # 検証
    assert result.status == 422
    assert result.headers["content-type"].startswith("application/problem+json")
    assert any(
        line.startswith("config.yaml: display.network_look: ")
        for line in result.json()["detail"].splitlines()
    )
    records = http_request(url, "/api/records").json()
    assert records["settings"]["display"]["network_look"] == "starlight"
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == before
