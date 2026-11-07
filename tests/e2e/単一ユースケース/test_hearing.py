"""ヒアリング（前提が揃った未決定を、検討事項ごとにスレッドを立てて聞き、スレッドで届いた答えを記録する）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
利用者の回答は、サーバーの配信の `POST /api/comments` と `POST /api/comments/send` で再生する。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from preview_helpers import send_user_reply
from workspace_fixtures import MakeItem, MakeWorkspace

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 検討事項が持つ案
OPTIONS = [
    {"key": "A", "content": "YAML", "pros": "手で読める", "cons": "大きいと遅い"},
    {"key": "B", "content": "種類ごとに分ける", "pros": "探しやすい", "cons": "ファイルが増える"},
]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """前提が揃った未決定に推奨の印を記録してから聞き、選ばれた案を採用して答えと理由を書き、依存していた問いが次の候補に上がる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", options=OPTIONS),
        make_item("D-2", options=OPTIONS),
        make_item("D-3", depends_on=["D-1"]),
    )
    ws = {"workspace": str(root)}
    # 実行
    before = replay("next", **ws)["candidates"]
    # 聞く前に、D-1・D-2 の推奨する案 A に推奨の印を立てる
    replay("edit_option", **ws, id="D-1", action="update", key="A", option={"recommended": True})
    replay("edit_option", **ws, id="D-2", action="update", key="A", option={"recommended": True})
    asked = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    # 検討事項ごとに、その検討事項を向けたスレッドを立てて、案の表と推奨を質問の書式で聞く
    question = {
        item_id: replay(
            "new_thread",
            **ws,
            body=f"## {item_id} の保存の形\n\n| 案 | 内容 |\n| --- | --- |\n| A | YAML |\n| B | 種類ごとに分ける |\n\n推奨: A",
            summary=f"{item_id} の保存の形を聞いた。返事待ち",
            target=item_id,
        )["id"]
        for item_id in ("D-1", "D-2")
    }
    # 利用者がそれぞれのスレッドへ回答を送る
    url = replay("preview_url", **ws)["url"]
    send_user_reply(url, question["D-1"], "A にする")
    send_user_reply(url, question["D-2"], "B にする")
    # 取り込み待ちのスレッドを読み、選ばれた案を採用する
    awaiting = [item["id"] for item in replay("threads", **ws, awaiting=True)["items"]]
    answers = {
        thread_id: [post["body"] for post in replay("thread", **ws, id=thread_id)["posts"]]
        for thread_id in awaiting
    }
    # 利用者が選んだ案（D-1 は案 A、D-2 は案 B）を採用して決定済みにし、答えと理由を書く
    replay("adopt", **ws, id="D-1", key="A")
    replay("adopt", **ws, id="D-2", key="B")
    replay("update", **ws, id="D-1", item={"answer": "YAML", "reason": "手で読める"})
    replay("update", **ws, id="D-2", item={"answer": "種類ごとに分ける", "reason": "探しやすい"})
    replay(
        "add",
        **ws,
        kind="log",
        item={"title": "ヒアリング", "date": "2026-10-02", "related": ["D-1", "D-2"]},
    )
    for item_id, thread_id in question.items():
        replay("reply", **ws, id=thread_id, body=f"{item_id} を決めました", summary=f"{item_id} が決まった")
    after = replay("next", **ws)["candidates"]
    # 検証
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    # next の候補に D-1・D-2 があり、D-3 が無い
    assert [candidate["id"] for candidate in before] == ["D-1", "D-2"]
    # 聞く前に、D-1・D-2 は案 A だけが推奨の印を持つ
    for item_id in ("D-1", "D-2"):
        assert [option.get("recommended") for option in asked[item_id]["options"]] == [True, None]
    # D-1・D-2 が決定済みで answer と reason を持つ
    assert [decisions["D-1"]["status"], decisions["D-1"]["answer"], decisions["D-1"]["reason"]] == [
        "決定済み",
        "YAML",
        "手で読める",
    ]
    assert [decisions["D-2"]["status"], decisions["D-2"]["answer"], decisions["D-2"]["reason"]] == [
        "決定済み",
        "種類ごとに分ける",
        "探しやすい",
    ]
    # D-1 は案 A、D-2 は案 B だけが adopted: true である
    assert [o["key"] for o in decisions["D-1"]["options"] if o.get("adopted")] == ["A"]
    assert [o["key"] for o in decisions["D-2"]["options"] if o.get("adopted")] == ["B"]
    # 書き込みの後の next の候補に D-3 がある
    assert [candidate["id"] for candidate in after] == ["D-3"]
    # D-1・D-2 それぞれを向けた AI のスレッドがあり、最初の書き込みが案の表と推奨を持つ
    threads = {item["id"]: item for item in read_yaml(root, "threads.yaml")["items"]}
    for item_id, thread_id in question.items():
        assert threads[thread_id]["target"] == item_id
        assert threads[thread_id]["posts"][0]["author"] == "ai"
        assert "推奨: A" in threads[thread_id]["posts"][0]["body"]
        # 最後の書き込みが、検討事項の ID を含む AI の返信である
        assert threads[thread_id]["posts"][-1]["author"] == "ai"
        assert item_id in threads[thread_id]["posts"][-1]["body"]
    assert sorted(awaiting) == sorted(question.values())
    assert answers[question["D-1"]] == ["A にする"]
    assert answers[question["D-2"]] == ["B にする"]
    # 取り込み待ちのスレッドの一覧が 0 件を返す
    assert replay("threads", **ws, awaiting=True) == {"items": []}
    # 会話ログが 1 件足されている
    assert [item["id"] for item in read_yaml(root, "logs.yaml")["items"]] == ["L-1"]
