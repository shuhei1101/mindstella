"""設定の既定の書き換え（PUT /api/config/display）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import LockDirs, MakeWorkspace
from .http_helpers import EventStream, http_request, send_json

# 既定の書き換えのパス
DISPLAY_PATH = "/api/config/display"

# 書き換えてから知らせが届くまでを待つ上限秒数
CHANGED_WITHIN_SEC = 2

# 用語集を除いた 6 種類
KINDS_WITHOUT_TERMS = ["decisions", "tasks", "research", "docs", "notes", "logs"]


def _put(url: str, payload: dict[str, Any], **headers: str) -> Any:
    """既定の書き換えを PUT する。"""
    return send_json(url, "PUT", DISPLAY_PATH, payload, headers=headers)


def _read_settings(root: Path) -> dict[str, Any]:
    """ワークスペースの config.yaml を読む。"""
    return yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """見た目の既定と表示する種類の既定を書き、ほかのキーを残す（正常系）。"""
    # 準備
    root = make_workspace()
    before = _read_settings(root)
    url = serve_preview(root)
    stream = open_events(url)
    # 実行
    result = _put(url, {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS})
    # 検証
    assert result.status == 200
    assert result.json()["display"]["network_look"] == "glow"
    after = _read_settings(root)
    assert after["display"] == {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS}
    assert {key: value for key, value in after.items() if key != "display"} == before
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True


def test_error_when_value_invalid(
    make_workspace: MakeWorkspace, serve_preview: Callable[[Path], str]
) -> None:
    """選べない見た目は書かない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = (root / "config.yaml").read_bytes()
    # 実行
    result = _put(url, {"network_look": "rainbow", "visible_kinds": KINDS_WITHOUT_TERMS})
    # 検証
    assert result.status == 400
    detail = result.json()["detail"]
    assert "network_look" in detail
    assert "glow" in detail
    assert (root / "config.yaml").read_bytes() == before


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace, serve_preview: Callable[[Path], str]
) -> None:
    """別のサイトのページからは書かない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = (root / "config.yaml").read_bytes()
    # 実行
    result = _put(
        url,
        {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS},
        Origin="https://attacker.example",
    )
    # 検証
    assert result.status == 403
    assert (root / "config.yaml").read_bytes() == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    serve_preview: Callable[[Path], str],
    lock_dirs: LockDirs,
) -> None:
    """ワークスペースのフォルダに書けないと、理由を返して何も変えない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = (root / "config.yaml").read_bytes()
    lock_dirs(root)
    # 実行
    result = _put(url, {"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert (root / "config.yaml").read_bytes() == before
    assert http_request(url, "/api/records").status == 200
