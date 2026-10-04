"""E2E テストの共通 fixture（ワークスペースと MCP サーバーの起動は tests/workspace_fixtures.py）。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from playwright.sync_api import Page
from preview_helpers import OpenPreview, ServePreview
from workspace_fixtures import CallTool, MakeWorkspace

# スキルの手順が連ねるツールの呼び出しを再生する関数（ツールの名前と引数を渡し、結果の JSON を返す）
type Replay = Callable[..., dict[str, Any]]


@pytest.fixture
def replay(call_tool: CallTool) -> Replay:
    """スキルの手順どおりに MCP のツールを呼び、結果の JSON のオブジェクトを返す関数を返す。"""

    def _replay(tool: str, **arguments: Any) -> dict[str, Any]:
        """ツールを呼び、エラーが返ったら本文を添えて失敗させ、構造化の結果を返す。"""
        result = call_tool(tool, **arguments)
        assert result.is_error is False, result.text
        assert result.data is not None
        return result.data

    return _replay


@pytest.fixture
def read_yaml() -> Callable[[Path, str], Any]:
    """ワークスペースの YAML を読んで中身を返す関数を返す。"""

    def _read(root: Path, file_name: str) -> Any:
        """ワークスペースの下の YAML を読む。"""
        return yaml.safe_load((root / file_name).read_text(encoding="utf-8"))

    return _read


# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 20_000


@pytest.fixture
def serve_preview(make_workspace: MakeWorkspace, call_tool: CallTool) -> ServePreview:
    """項目と設定と本文を渡して作成を済ませたワークスペースを作り、`preview_url` が返した配信の URL を返す関数を返す。"""

    def _serve(
        *items: dict[str, Any],
        settings: dict[str, Any] | None = None,
        bodies: dict[str, str] | None = None,
    ) -> str:
        """スキルと同じく `preview_url` を実際に呼んで配信を立てる。失敗したら本文を添えて止める。"""
        root = make_workspace(*items, settings=settings, bodies=bodies)
        result = call_tool("preview_url", workspace=str(root))
        assert result.is_error is False, result.text
        assert result.data is not None
        return str(result.data["url"])

    return _serve


@pytest.fixture
def open_preview(page: Page) -> OpenPreview:
    """配信の URL を実際のブラウザでハッシュ付きで開き、画面が描き終わるまで待つ関数を返す。"""

    def _open(
        url: str, hash_text: str = "", *, width: int | None = None, height: int = 800
    ) -> Page:
        """幅を指定したときはその大きさにしてから開き、本文の領域に中身が入るのを待つ。"""
        if width is not None:
            page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{url}{hash_text}")
        page.wait_for_selector("main#main > *", state="attached", timeout=RENDER_TIMEOUT_MS)
        # 文字（Web フォント）の読み込みで行の高さが変わる前に、画面を操作し始めない
        page.evaluate("document.fonts.ready.then(() => true)")
        return page

    return _open
