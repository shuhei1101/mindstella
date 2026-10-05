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

# 資料 A-1 の本文と、2 行目を指す箇所（選んだ文は「言い換えたい文」）
BODY = "最初の文\n言い換えたい文\n最後の文\n"
SECOND_LINE = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

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


def test_normal_when_location_and_no_target(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """箇所を持つ送信と、項目を指さない送信を、箇所と項目なしを添えて拾い、記録してから取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": BODY})
    no_target = {
        key: value
        for key, value in make_submission("S-2", body="全体に目を通した").items()
        if key != "target"
    }
    write_submissions(
        root,
        make_submission("S-1", target="A-1", body="ここは言い換える", loc=SECOND_LINE),
        no_target,
    )
    ws = {"workspace": str(root)}
    # 実行
    # 準備のステップ: 取り込んでいない送信を読む
    pending = replay("submissions", **ws)["items"]
    # 取り込みのステップ: 箇所の送信は本文の行の範囲と選んだ文を添えて会話ログに残し、取り込み済みにする
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた意見（A-1 の箇所）",
            "date": "2026-10-04",
            "related": ["A-1"],
            "body_markdown": "A-1 の本文の 2 行目「言い換えたい文」へ: ここは言い換える",
        },
    )
    replay("take_submission", **ws, id=pending[0]["id"])
    # 項目を指さない送信は、発言と同じく会話ログに残し、取り込み済みにする
    replay(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた意見（項目を指さない）",
            "date": "2026-10-04",
            "body_markdown": "全体に目を通した",
        },
    )
    replay("take_submission", **ws, id=pending[1]["id"])
    after = replay("submissions", **ws)
    # 検証
    assert [(item["target"], item["target_title"], item["loc"], item["body"]) for item in pending] == [
        ("A-1", "A-1の題", SECOND_LINE, "ここは言い換える"),
        (None, None, None, "全体に目を通した"),
    ]
    first_log = (root / "docs" / "L-1.md").read_text(encoding="utf-8")
    assert "2 行目「言い換えたい文」" in first_log
    assert "ここは言い換える" in first_log
    assert "全体に目を通した" in (root / "docs" / "L-2.md").read_text(encoding="utf-8")
    assert all(item["taken"] is not None for item in read_yaml(root, "submissions.yaml")["items"])
    assert after == {"items": []}
