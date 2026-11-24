"""画面からのプリセットの作成（POST /api/presets）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from workspace_fixtures import RECORD_DIR

from .fixture_types import LockDirs, MakeItem, MakeWorkspace
from .http_helpers import EventStream, http_request, send_json
from .preset_helpers import eq, read_settings, tags, with_presets

# 画面からのプリセットの作成のパス
PRESETS_PATH = "/api/presets"

# 書き換えてから知らせが届くまでを待つ上限秒数
CHANGED_WITHIN_SEC = 2


def _post(url: str, payload: dict[str, Any], **headers: str) -> Any:
    """プリセットの作成を POST する。"""
    return send_json(url, "POST", PRESETS_PATH, payload, headers=headers)


def _config_bytes(root: Path) -> bytes:
    """config.yaml の中身をそのまま読む。"""
    return (root / RECORD_DIR / "config.yaml").read_bytes()


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """プリセットを末尾に追加し、該当する件数を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", tags=tags("画面", "廃止")),
        make_item("A-2", tags=tags("画面")),
        settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}),
    )
    before = read_settings(root)
    url = serve_preview(root)
    stream = open_events(url)
    expr = {"and": [eq("画面"), eq("廃止")]}
    # 実行
    result = _post(url, {"name": "廃止する画面", "filter": expr})
    # 検証
    assert result.status == 201
    assert result.json() == {"preset": {"name": "廃止する画面", "filter": expr}, "count": 1}
    after = read_settings(root)
    assert after["presets"] == [
        {"name": "画面の設計", "filter": eq("画面")},
        {"name": "廃止する画面", "filter": expr},
    ]
    assert {key: value for key, value in after.items() if key != "presets"} == {
        key: value for key, value in before.items() if key != "presets"
    }
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True


@pytest.mark.parametrize(
    ("payload", "key"),
    [
        pytest.param({"name": "", "filter": eq("画面")}, "name", id="empty_name"),
        pytest.param({"name": "画面", "filter": {"and": []}}, "and", id="empty_and"),
        pytest.param(
            {"name": "画面", "filter": eq("画面"), "description": "説明"},
            "description",
            id="unknown_key",
        ),
    ],
)
def test_error_when_value_invalid(
    make_workspace: MakeWorkspace,
    serve_preview: Callable[[Path], str],
    payload: dict[str, Any],
    key: str,
) -> None:
    """空の名前・空の束の式・受け付けないキーは書かない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = _config_bytes(root)
    # 実行
    result = _post(url, payload)
    # 検証
    assert result.status == 400
    assert key in result.json()["detail"]
    assert _config_bytes(root) == before


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace, serve_preview: Callable[[Path], str]
) -> None:
    """別のサイトのページからは書かない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = _config_bytes(root)
    # 実行
    result = _post(
        url, {"name": "廃止する画面", "filter": eq("廃止")}, Origin="https://attacker.example"
    )
    # 検証
    assert result.status == 403
    assert _config_bytes(root) == before


def test_error_when_name_taken(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
) -> None:
    """全角半角・大文字小文字だけ違う名前も重なりとして拒む（異常系）。"""
    # 準備
    root = make_workspace(
        settings=with_presets(valid_settings, {"name": "UI の設計", "filter": eq("画面")})
    )
    url = serve_preview(root)
    before = _config_bytes(root)
    # 実行
    result = _post(url, {"name": "ｕｉ の設計", "filter": eq("廃止")})
    # 検証
    assert result.status == 409
    assert "UI の設計" in result.json()["detail"]
    assert _config_bytes(root) == before


def test_error_when_content_type_mismatch(
    make_workspace: MakeWorkspace, serve_preview: Callable[[Path], str]
) -> None:
    """JSON でない本文は読まずに書かない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = _config_bytes(root)
    # 実行
    result = http_request(
        url,
        PRESETS_PATH,
        method="POST",
        headers={"Content-Type": "text/plain"},
        body='{"name": "廃止する画面", "filter": {"field": "tags", "op": "eq", "values": ["廃止"]}}',
    )
    # 検証
    assert result.status == 415
    assert _config_bytes(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    serve_preview: Callable[[Path], str],
    lock_dirs: LockDirs,
) -> None:
    """ワークスペースのフォルダに書けないと、理由を返して何も変えない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    before = _config_bytes(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = _post(url, {"name": "廃止する画面", "filter": eq("廃止")})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert _config_bytes(root) == before


def test_error_when_config_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
) -> None:
    """今の config.yaml がスキーマに合わないと、合わない箇所を返して何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    url = serve_preview(root)
    config = root / RECORD_DIR / "config.yaml"
    config.write_text(
        config.read_text(encoding="utf-8") + "presets: 画面\n", encoding="utf-8"
    )
    before = _config_bytes(root)
    # 実行
    result = _post(url, {"name": "廃止する画面", "filter": eq("廃止")})
    # 検証
    assert result.status == 422
    assert "presets" in result.json()["detail"]
    assert _config_bytes(root) == before
