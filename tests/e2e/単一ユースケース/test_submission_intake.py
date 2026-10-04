"""送信の取り込み（`session` が話し合いの最初に、プレビューから届いた送信を記録して取り込み済みにする）の E2E テスト。

モデルを呼ばず、準備が連ねる取り込んでいない送信の一覧・`adopt`・`add`（会話ログ）・取り込み済みにするを、決めた引数で順に再生する。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from conftest import Replay
from workspace_fixtures import (
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteSubmissions,
)

# 取り込む送信の本文
SUBMISSION_BODY = "案 A にする"

# 決める検討事項の案
OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """取り込んでいない送信を拾い、記録してから取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    write_submissions(root, make_submission("S-1", target="D-1", body=SUBMISSION_BODY))
    ws = {"workspace": str(root)}
    # 実行
    # 準備のステップ: 取り込んでいない送信を読む
    pending = replay("submissions", **ws)["items"]
    # 取り込みのステップ: 送信の本文を記録する（案 A を採用して決定済みにし、会話ログに本文を残す）
    replay("adopt", **ws, id="D-1", key="A")
    replay("update", **ws, id="D-1", item={"status": "決定済み", "answer": "表で見せる"})
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた回答",
            "date": "2026-10-04",
            "related": ["D-1"],
            "body_markdown": SUBMISSION_BODY,
        },
    )
    # 記録した後に、その送信を取り込み済みにする
    replay("take_submission", **ws, id=pending[0]["id"])
    after = replay("submissions", **ws)
    # 検証
    assert [(item["target"], item["body"]) for item in pending] == [("D-1", SUBMISSION_BODY)]
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["A"]
    assert decision["status"] == "決定済み"
    log_body = (root / "docs" / "L-1.md").read_text(encoding="utf-8")
    assert SUBMISSION_BODY in log_body
    assert read_yaml(root, "submissions.yaml")["items"][0]["taken"] is not None
    assert after == {"items": []}


def test_normal_when_no_submissions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    snapshot_tree: SnapshotTree,
) -> None:
    """送信が無ければ、一覧が 0 件を返し、ワークスペースは何も変わらない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    before = snapshot_tree(root)
    # 実行
    pending = replay("submissions", workspace=str(root))
    # 検証
    assert pending == {"items": []}
    assert snapshot_tree(root) == before
