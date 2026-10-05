"""発言の取り込み（利用者の発言を記録し、派生の検討事項・タスクを積む）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねる書き込みを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# valid_settings の対象・カテゴリー（記録した項目に付ける）
PLACE = {"target": "mindmap", "category": "データ構造", "phase": "要件"}

# 取り込みの前からある話題のタグと、取り込みで作る新しい話題のタグ
TOPIC_TAG = "保存"
NEW_TOPIC_TAG = "通知"

# 会話の日付
TODAY = "2026-10-02"

# 取り込んだ内容の一言の説明
INTAKE_SUMMARY = "発言を取り込む"

# 納品物の資料の本文（概要・背景・最終的な構成の見出しを先に置く）
DELIVERABLE_BODY = "# 要件定義書\n\n## 概要\n\n支出を記録する。\n\n## 背景\n\n## 構成\n\n- 画面\n- データ\n"

# 検討事項に書く案（A を採用する）
OPTIONS = [
    {"key": "A", "content": "YAML", "pros": "手で読める", "cons": "大きいと遅い"},
    {"key": "B", "content": "SQLite", "pros": "速い", "cons": "手で読めない"},
]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """話題のタグを引いて使い回し、案を持つ決め事・派生の検討事項・未整理・タスク・会話ログを、1 回のまとめての書き込みで積む（正常系）。"""
    # 準備（取り込みの前から、タグ `保存` を持つメモ N-1 がある）
    root = make_workspace(make_item("N-1", tags=[TOPIC_TAG]))
    ws = {"workspace": str(root)}
    # 実行
    # 取り込みの最初に、使っているタグの一覧を引く
    tags_before = replay("tags", **ws)
    # 1 つの発言から出た記録を、1 回のまとめての書き込みで渡す（D-2 の parent と T-1 の for は、先に足す項目を指す）
    replay(
        "batch",
        **ws,
        operations=[
            {
                "op": "add",
                "kind": "decision",
                "item": {
                    "title": "保存先",
                    "status": "決定済み",
                    "answer": "YAML",
                    "reason": "手で読める",
                    # 決めたこととして足すので、選ばれた案 A を採用する
                    "options": [{**OPTIONS[0], "adopted": True}, OPTIONS[1]],
                    "tags": [TOPIC_TAG],
                    **PLACE,
                },
            },
            {
                "op": "add",
                "kind": "decision",
                "item": {
                    "title": "ファイルの分け方",
                    "status": "未決定",
                    "parent": "$1",
                    "options": OPTIONS,
                    "tags": [TOPIC_TAG],
                    **PLACE,
                },
            },
            {
                "op": "add",
                "kind": "decision",
                "item": {
                    "title": "いつか使うかも",
                    "status": "未整理",
                    "tags": [TOPIC_TAG, NEW_TOPIC_TAG],
                    **PLACE,
                },
            },
            {
                "op": "add",
                "kind": "task",
                "item": {
                    "title": "分け方の案を出す",
                    "kind": "作業",
                    "status": "未着手",
                    "for": ["$2"],
                    "tags": [TOPIC_TAG],
                    **PLACE,
                },
            },
            {
                "op": "add",
                "kind": "log",
                "item": {"title": "発言", "date": TODAY, "related": ["$1"], **PLACE},
            },
        ],
    )
    replay("commit", **ws, summary=INTAKE_SUMMARY)
    pending = replay("pending", **ws)
    tags_after = replay("tags", **ws)
    # 検証
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    tasks = read_yaml(root, "tasks.yaml")["items"]
    logs = read_yaml(root, "logs.yaml")["items"]
    # D-1 が決定済みで answer を持つ
    assert decisions["D-1"]["status"] == "決定済み"
    assert decisions["D-1"]["answer"] == "YAML"
    # D-1 が案を持ち、A だけが adopted: true である
    assert [option["key"] for option in decisions["D-1"]["options"]] == ["A", "B"]
    assert [option.get("adopted", False) for option in decisions["D-1"]["options"]] == [True, False]
    # D-2 が parent: D-1 と案を持ち、未決定である
    assert decisions["D-2"]["parent"] == "D-1"
    assert [option["key"] for option in decisions["D-2"]["options"]] == ["A", "B"]
    assert decisions["D-2"]["status"] == "未決定"
    # D-3 が未整理である
    assert decisions["D-3"]["status"] == "未整理"
    # T-1 が for: [D-2] を持つ
    assert tasks[0]["id"] == "T-1"
    assert tasks[0]["for"] == ["D-2"]
    # 会話ログ L-1 がある
    assert logs[0]["id"] == "L-1"
    # 足した全ての項目が target・category・phase を持つ
    assert [
        decisions["D-1"]["phase"],
        decisions["D-2"]["category"],
        decisions["D-3"]["target"],
    ] == [
        "要件",
        "データ構造",
        "mindmap",
    ]
    assert [tasks[0]["target"], logs[0]["category"], logs[0]["phase"]] == [
        "mindmap",
        "データ構造",
        "要件",
    ]
    # 取り込みの前のタグの一覧が `保存`（1 件）を返し、取り込んだ後のタグの一覧が `保存`（5 件）と `通知`（1 件）を返す
    assert tags_before == {"tags": [{"name": TOPIC_TAG, "count": 1, "kinds": ["note"]}]}
    assert tags_after == {
        "tags": [
            {"name": TOPIC_TAG, "count": 5, "kinds": ["decision", "task", "note"]},
            {"name": NEW_TOPIC_TAG, "count": 1, "kinds": ["decision"]},
        ]
    }
    # 足した D-1・D-2・D-3・T-1・L-1 が 1 つのまとまりに属し、そのまとまりが説明を持つ。pending が空を返す
    changes = read_yaml(root, "changes.yaml")
    assert len(changes["sets"]) == 1
    assert changes["sets"][0]["summary"] == INTAKE_SUMMARY
    assert changes["sets"][0]["added"] == ["D-1", "D-2", "D-3", "T-1", "L-1"]
    assert pending == {"added": [], "changed": []}


def test_normal_when_diagram_kept_as_doc(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """会話で出した図を、本文を持つ資料に残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    ws = {"workspace": str(root)}
    # 実行
    # 資料と会話ログを、1 回のまとめての書き込みで渡す
    replay(
        "batch",
        **ws,
        operations=[
            {
                "op": "add",
                "kind": "doc",
                "item": {
                    "title": "保存の流れ",
                    "kind": "図",
                    "deliverable": False,
                    "status": "下書き",
                    "related": ["D-1"],
                    "body_markdown": "```mermaid\nflowchart TD\n  A --> B\n```\n",
                },
            },
            {
                "op": "add",
                "kind": "log",
                "item": {"title": "図を出した", "date": TODAY, "related": ["$1"]},
            },
        ],
    )
    checked = call_tool("check", **ws)
    # 検証
    doc = read_yaml(root, "docs.yaml")["items"][0]
    # 資料 A-1 が kind: 図 と related: [D-1] を持つ
    assert doc["id"] == "A-1"
    assert doc["kind"] == "図"
    assert doc["related"] == ["D-1"]
    # docs/ に A-1 の本文の Markdown がある
    assert "flowchart TD" in (root / "docs" / "A-1.md").read_text(encoding="utf-8")
    # check が YAML と Markdown のずれを 0 件で返す
    assert checked.is_error is False
    assert checked.data["problems"] == []


def test_normal_when_off_topic_question(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """脱線した質問を、言葉は用語集に・それ以外はメモに残し、タスクにはしない（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    # 実行
    replay(
        "batch",
        **ws,
        operations=[
            {
                "op": "add",
                "kind": "term",
                "item": {"title": "検討事項", "meaning": "問いと答えの 1 件"},
            },
            {
                "op": "add",
                "kind": "note",
                "item": {"title": "他社の例", "content": "他社は DB を使う", "tags": ["脱線"]},
            },
            {
                "op": "add",
                "kind": "log",
                "item": {"title": "脱線", "date": TODAY, "related": ["$1", "$2"]},
            },
        ],
    )
    # 検証
    # 用語集 G-1 が meaning を持つ
    term = read_yaml(root, "terms.yaml")["items"][0]
    assert term["id"] == "G-1"
    assert term["meaning"] == "問いと答えの 1 件"
    # メモ N-1 がタグ 脱線 を持つ
    note = read_yaml(root, "notes.yaml")["items"][0]
    assert note["id"] == "N-1"
    assert note["tags"] == ["脱線"]
    # タスクが 0 件のままである
    assert replay("find", **ws, kind="task")["items"] == []


def test_normal_when_deliverable_doc_created(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """概要・背景・構成を先に置いた納品物の資料を作り、同じタイトルのゴールの納品物からその資料を指す（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "要件定義書"}],
        },
    }
    root = make_workspace(settings=settings)
    ws = {"workspace": str(root)}
    # 実行
    # 資料の本文は add の body_markdown で docs/ に書く
    replay(
        "add",
        **ws,
        kind="doc",
        item={
            "title": "要件定義書",
            "kind": "文書",
            "deliverable": True,
            "status": "下書き",
            "body_markdown": DELIVERABLE_BODY,
            **PLACE,
        },
    )
    # 同じタイトルの納品物があるので、行は足さず、その doc から資料 A-1 を指す（ゴールは丸ごと置き換わる）
    goal = read_yaml(root, "mindmap.yaml")["goal"]
    deliverables = [{"title": "要件定義書", "doc": "A-1"}]
    replay("update_settings", **ws, settings={"goal": {**goal, "deliverables": deliverables}})
    replay(
        "add",
        **ws,
        kind="log",
        item={"title": "要件定義書をまとめた", "date": TODAY, "related": ["A-1"]},
    )
    checked = replay("check", **ws)
    # 検証
    # goal.deliverables が「要件定義書」の 1 件だけで、その doc が A-1 である
    assert read_yaml(root, "mindmap.yaml")["goal"]["deliverables"] == [
        {"title": "要件定義書", "doc": "A-1"}
    ]
    # 資料 A-1 が deliverable: true と status: 下書き を持つ
    doc = read_yaml(root, "docs.yaml")["items"][0]
    assert doc["deliverable"] is True
    assert doc["status"] == "下書き"
    # docs/ の A-1 の本文が、概要・背景・構成の見出しを持つ
    body = (root / "docs" / "A-1.md").read_text(encoding="utf-8")
    assert [heading in body for heading in ("## 概要", "## 背景", "## 構成")] == [True] * 3
    # check が問題を 0 件で返す
    assert checked == {"ok": True, "problems": []}


def test_normal_when_task_output_kept_as_doc(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """タスクで作った成果を資料に残し、タスクの related から指して完了にする（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "要件定義書"}],
        },
    }
    root = make_workspace(
        make_item("D-1"),
        make_item("T-1", status="進行中", **{"for": ["D-1"]}),
        settings=settings,
    )
    ws = {"workspace": str(root)}
    goal_before = read_yaml(root, "mindmap.yaml")["goal"]
    # 実行
    # 成果の資料（ゴールの納品物に当たらないので deliverable: false）を足し、成果と資料が 1 対 1 で揃ったタスクを資料に結んで完了にし、会話ログを足す。3 つを 1 回のまとめての書き込みで渡す
    replay(
        "batch",
        **ws,
        operations=[
            {
                "op": "add",
                "kind": "doc",
                "item": {
                    "title": "画面の一覧",
                    "kind": "文書",
                    "deliverable": False,
                    "status": "下書き",
                    "body_markdown": "# 画面の一覧\n\n- 入力\n- 一覧\n",
                },
            },
            {
                "op": "update",
                "id": "T-1",
                "item": {"related": ["$1"], "status": "完了", "result": "画面の一覧をまとめた"},
            },
            {
                "op": "add",
                "kind": "log",
                "item": {"title": "画面の一覧ができた", "date": TODAY, "related": ["T-1", "$1"]},
            },
        ],
    )
    checked = replay("check", **ws)
    # 検証
    task = read_yaml(root, "tasks.yaml")["items"][0]
    # T-1 が完了で、related に A-1 を持つ
    assert task["status"] == "完了"
    assert task["related"] == ["A-1"]
    # 資料 A-1 が deliverable: false を持ち、docs/ に本文がある
    assert read_yaml(root, "docs.yaml")["items"][0]["deliverable"] is False
    assert "画面の一覧" in (root / "docs" / "A-1.md").read_text(encoding="utf-8")
    # goal.deliverables が呼ぶ前と同じである
    assert read_yaml(root, "mindmap.yaml")["goal"]["deliverables"] == goal_before["deliverables"]
    # check が問題を 0 件で返す
    assert checked == {"ok": True, "problems": []}
