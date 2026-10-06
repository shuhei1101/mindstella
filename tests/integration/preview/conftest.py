"""プレビューの結合テストの共通 fixture。

MCP サーバーが `preview_url` で配る URL を開き、ハッシュで画面を指す。
描画のライブラリと文字は、配信元（jsDelivr・Google Fonts）から読む。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page
from preview_history_helpers import build_history_workspace
from preview_fixture_types import (
    BODY_WITH_DIAGRAM,
    MAIN_SELECTOR,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from workspace_fixtures import (
    CallTool,
    MakeComment,
    MakeItem,
    MakeWorkspace,
    WriteComments,
    WriteDrafts,
)

# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 15_000


@pytest.fixture
def write_preview(make_workspace: MakeWorkspace, call_tool: CallTool) -> WritePreview:
    """項目と設定を渡してワークスペースを作り、`preview_url` が返した配信の URL を返す関数を返す。"""

    def _write(
        *items: dict[str, Any],
        settings: dict[str, Any] | None = None,
        bodies: dict[str, str] | None = None,
    ) -> str:
        """ワークスペースを作って配信を立てる。`preview_url` が失敗したらテストを止める。"""
        root = make_workspace(*items, settings=settings, bodies=bodies)
        result = call_tool("preview_url", workspace=str(root))
        assert result.is_error is False, result.text
        assert result.data is not None
        return str(result.data["url"])

    return _write


@pytest.fixture
def write_review_preview(
    make_workspace: MakeWorkspace,
    write_comments: WriteComments,
    write_drafts: WriteDrafts,
    call_tool: CallTool,
) -> WriteReviewPreview:
    """項目・レビュー中のコメント・書きかけを持つワークスペースを作り、配信の URL とワークスペースのフォルダを返す関数を返す。"""

    def _write(
        *items: dict[str, Any],
        comments: tuple[dict[str, Any], ...] = (),
        drafts: tuple[dict[str, Any], ...] = (),
        bodies: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> tuple[str, Path]:
        """ワークスペースを作って配信を立てる。`preview_url` が失敗したらテストを止める。"""
        root = make_workspace(*items, settings=settings, bodies=bodies)
        if comments:
            write_comments(root, *comments)
        if drafts:
            write_drafts(root, *drafts)
        result = call_tool("preview_url", workspace=str(root))
        assert result.is_error is False, result.text
        assert result.data is not None
        return str(result.data["url"]), root

    return _write


@pytest.fixture
def write_history_preview(make_workspace: MakeWorkspace, call_tool: CallTool) -> WriteReviewPreview:
    """変更履歴つきのワークスペース（まとまり V-1・V-2 とまとめていない変更）を作り、配信の URL とフォルダを返す関数を返す。"""

    def _write(*, pending: bool = True, history_limit: int | None = None) -> tuple[str, Path]:
        """実際のツールで履歴を積んだワークスペースを作って配信を立てる。"""
        root = build_history_workspace(
            make_workspace, call_tool, pending=pending, history_limit=history_limit
        )
        result = call_tool("preview_url", workspace=str(root))
        assert result.is_error is False, result.text
        assert result.data is not None
        return str(result.data["url"]), root

    return _write


@pytest.fixture
def sample_settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """カテゴリー 2 つ・納品物 1 つを持つ設定を返す（概要の進み具合・納品物のチェックリスト用）。"""
    return {
        **valid_settings,
        "categories": [
            {"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"},
            {"name": "画面", "target": "mindmap", "summary": "プレビューの画面"},
        ],
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "YAML のスキーマ", "doc": "A-1"}],
        },
    }


@pytest.fixture
def sample_items(make_item: MakeItem) -> list[dict[str, Any]]:
    """全ての種類を 1 件以上持ち、状態・前提・案・本文がそろった項目を返す。"""
    return [
        make_item(
            "D-1",
            status="決定済み",
            phase="目的",
            category="データ構造",
            target="mindmap",
            answer="種類ごとに分ける",
        ),
        make_item(
            "D-2",
            status="未決定",
            phase="要件",
            category="データ構造",
            target="mindmap",
            depends_on=["D-1"],
            weight="大",
            lead="キーをどう持つか",
        ),
        make_item(
            "D-3",
            status="要見直し",
            phase="要件",
            category="画面",
            target="mindmap",
            body="D-3.md",
            options=[
                {"key": "A", "content": "表で見せる", "pros": "並べやすい", "adopted": True},
                {"key": "B", "content": "カードで見せる", "cons": ["数が多いと長い"]},
            ],
        ),
        make_item("D-4", status="保留", phase="構成", category="画面", depends_on=["D-2"]),
        make_item("D-5", status="未決定", phase="構成", category="画面", depends_on=["D-1"]),
        make_item("T-1", status="進行中", **{"for": ["D-2"]}),
        make_item("T-2", status="未着手"),
        make_item("T-3", status="完了"),
        make_item("R-1", confidence="高", conclusion="結論の文"),
        make_item("A-1", deliverable=True, status="完成", kind="文書"),
        make_item("A-2", deliverable=False, status="下書き", body="A-2.md"),
        make_item("G-1", meaning="用語の意味"),
        make_item("N-1", content="メモの中身"),
        make_item("L-1", date="2026-10-01"),
    ]


@pytest.fixture
def sample_bodies() -> dict[str, str]:
    """サンプルの項目が指す本文（`docs/` のファイル名 → 本文）。"""
    return {
        "D-3.md": BODY_WITH_DIAGRAM,
        "A-1.md": "# 納品物の本文\n",
        "A-2.md": "下書きの本文\n",
    }


@pytest.fixture
def write_sample_preview(
    write_preview: WritePreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> WriteSamplePreview:
    """サンプルの記録を配る URL を返す関数を返す。"""

    def _write() -> str:
        """サンプルの項目・設定・本文のワークスペースを作って配信を立てる。"""
        return write_preview(*sample_items, settings=sample_settings, bodies=sample_bodies)

    return _write


@pytest.fixture
def write_commented_preview(
    write_review_preview: WriteReviewPreview,
    make_comment: MakeComment,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> WriteReviewPreview:
    """サンプルの記録に、項目ごとの件数が違うレビュー中のコメントを足した配信の URL とフォルダを返す関数を返す。

    件数は D-2 が 2、D-3 が 1（箇所を指す）、T-1・A-1・A-2・R-1 が 1 で、D-1・D-4・D-5 は 0。項目を指さないコメントが 1 件ある。
    """

    def _write() -> tuple[str, Path]:
        """サンプルの記録とコメントのワークスペースを作って配信を立てる。"""
        return write_review_preview(
            *sample_items,
            settings=sample_settings,
            bodies=sample_bodies,
            comments=(
                make_comment("C-1", target="D-2"),
                make_comment("C-2", target="D-2"),
                make_comment(
                    "C-3",
                    target="D-3",
                    loc={"kind": "body", "start": 3, "end": 3, "text": "本文の段落"},
                ),
                make_comment("C-4", target="T-1"),
                make_comment("C-5", target="A-1"),
                make_comment("C-6", target="A-2"),
                make_comment("C-7", target="R-1"),
                {key: value for key, value in make_comment("C-8").items() if key != "target"},
            ),
        )

    return _write


@pytest.fixture
def open_preview(page: Page) -> OpenPreview:
    """配信の URL をハッシュ付きで開き、画面が描き終わるまで待つ関数を返す。"""

    def _open(url: str, hash_text: str = "") -> Page:
        """配信の URL にハッシュを付けて開き、本文の領域に中身が入るのを待つ。"""
        page.goto(f"{url}{hash_text}")
        page.wait_for_selector(f"{MAIN_SELECTOR} > *", state="attached", timeout=RENDER_TIMEOUT_MS)
        return page

    return _open
