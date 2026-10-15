"""スレッドとレビュー中の書き込みの画面向けデータ（サーバーが返す形）を作る、単体テストの補助。"""

from __future__ import annotations

from typing import Any

# 書き込みを作るときの既定の日時
DEFAULT_CREATED = "2026-10-12T01:00:00+00:00"


def make_post(
    author: str, body: str, created: str = DEFAULT_CREATED, *, seen: bool | None = None
) -> dict[str, Any]:
    """スレッドの書き込み 1 件（画面へ返す形）を作る。利用者の既読 `seen` は渡したときだけ持つ。"""
    post: dict[str, Any] = {"id": "x", "author": author, "body": body, "created": created}
    # seen を渡さない: キーを持たない書き込みにする
    if seen is not None:
        post["seen"] = seen
    return post


def make_thread(thread_id: str, **overrides: Any) -> dict[str, Any]:
    """スレッド 1 件（画面へ返す形）を作る。オープン・タグなし・要約なし・項目を指さないのが既定。"""
    thread: dict[str, Any] = {
        "id": thread_id,
        "status": "open",
        "tags": [],
        "summary": None,
        "target": None,
        "target_title": None,
        "loc": None,
        "posts": [make_post("user", f"{thread_id}の最初の書き込み")],
        "events": [],
    }
    thread.update(overrides)
    return thread


def make_review_item(item_id: str, **overrides: Any) -> dict[str, Any]:
    """レビュー中の書き込み 1 件（画面へ返す形）を作る。項目 D-1 への新しいスレッドの最初の書き込みが既定。"""
    item: dict[str, Any] = {
        "id": item_id,
        "target": "D-1",
        "target_title": "問い",
        "loc": None,
        "thread": None,
        "body": f"{item_id}の本文",
        "created": "2026-10-05T03:00:00+00:00",
    }
    item.update(overrides)
    return item
