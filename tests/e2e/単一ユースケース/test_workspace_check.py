"""ワークスペースの点検（スキルが参照切れと YAML と本文のずれを洗い出す）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)


def test_normal_when_clean(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """整った記録は、問題が無いと返る（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"]),
        bodies={"D-1.md": "本文\n"},
    )
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"ok": True, "problems": []}


def test_normal_when_problems_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """参照切れ・本文の無い項目（調査とメモ）・項目の無い本文を、全て出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", depends_on=["D-9"]),
        make_item("R-1", body="R-1.md"),
        make_item("N-1", body="N-1.md"),
        bodies={"X-1.md": "どこからも指されない本文\n"},
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["ok"] is False
    problems = {
        (row["kind"], row["file"], row["id"], row["key"]): row for row in payload["problems"]
    }
    assert set(problems) == {
        ("broken_ref", ".mindstella/decisions.yaml", "D-1", "depends_on"),
        ("missing_body", ".mindstella/research.yaml", "R-1", "items[0].body"),
        ("missing_body", ".mindstella/notes.yaml", "N-1", "items[0].body"),
        ("orphan_body", ".mindstella/docs/X-1.md", None, None),
    }
    broken = problems[("broken_ref", ".mindstella/decisions.yaml", "D-1", "depends_on")]
    assert "D-9" in broken["detail"]
    assert snapshot_tree(root) == before


def test_normal_when_unknown_phase(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """項目の phase と goal.phase が設定の phases に無ければ、設定に無いフェーズとして全て出す（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件"],
        "goal": {"phase": "結論", "summary": "まとめる", "deliverables": []},
    }
    root = make_workspace(make_item("D-1", phase="発散"), settings=settings)
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    # ツールのエラーにせず、ok が偽の結果を返す
    assert result.is_error is False
    payload = result.data
    assert payload["ok"] is False
    # D-1 の phase の発散と、goal.phase の結論が、設定の phases に無い旨を出す
    unknown = {
        (row["file"], row["id"], row["key"], row["detail"])
        for row in payload["problems"]
        if row["kind"] == "unknown_phase"
    }
    assert unknown == {
        (".mindstella/decisions.yaml", "D-1", "items[0].phase", "発散"),
        (".mindstella/config.yaml", None, "goal.phase", "結論"),
    }
    # ワークスペースの全てのファイルの中身が、点検を呼ぶ前と同じである
    assert snapshot_tree(root) == before


def _without_options(item: dict[str, Any]) -> dict[str, Any]:
    """案のキーを持たない検討事項にする。"""
    return {key: value for key, value in item.items() if key != "options"}


def test_normal_when_options_and_status_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """案と状態の合わない検討事項だけを全て出し、案が要らない状態の検討事項は出さない（正常系）。"""
    # 準備
    option_a = {"key": "A", "content": "案 A"}
    option_b = {"key": "B", "content": "案 B"}
    root = make_workspace(
        _without_options(make_item("D-1", status="未決定")),
        make_item("D-2", status="決定済み", options=[option_a, option_b]),
        make_item("D-3", status="未決定", options=[{**option_a, "adopted": True}, option_b]),
        _without_options(make_item("D-4", status="未整理")),
        _without_options(make_item("D-5", status="対象外")),
        _without_options(make_item("D-6", status="取り下げ")),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    # ツールのエラーにせず、ok が偽の結果を返す
    assert result.is_error is False
    payload = result.data
    assert payload["ok"] is False
    # 問題が D-1・D-2・D-3 の 3 件だけで、D-4・D-5・D-6 は出ない
    problems = payload["problems"]
    assert [(row["kind"], row["id"]) for row in problems] == [
        ("decision_state", "D-1"),
        ("decision_state", "D-2"),
        ("decision_state", "D-3"),
    ]
    # D-1 が案を持たない旨、D-2 が決定済みなのに採用した案を持たない旨、D-3 が採用した案を持つのに未決定である旨が出る
    assert "案を 1 つ以上持つ" in problems[0]["detail"]
    assert "決定済みなのに採用した案を持たない" in problems[1]["detail"]
    assert "採用した案 A を持つのに未決定" in problems[2]["detail"]
    # ワークスペースの全てのファイルの中身が、点検を呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_removed_item_in_change_set(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """過去のまとまりが消した項目の ID を持っていても、参照切れにしない（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    for tool, arguments in (
        ("add", {"kind": "note", "item": {"title": "メモ", "content": "中身"}}),
        ("commit", {"summary": "メモを足す"}),
        ("remove", {"id": "N-1"}),
        ("commit", {"summary": "メモを消す"}),
    ):
        step = call_tool(tool, **ws, **arguments)
        assert step.is_error is False, step.text
    # 実行
    result = call_tool("check", **ws)
    # 検証
    # 点検のツールが成功を返し、問題が無い旨がある
    assert result.is_error is False
    assert result.data == {"ok": True, "problems": []}


def test_normal_when_html_body_problems_found(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """HTML の本文の、指す本文が無い資料と、どこからも指されない本文のファイルを出す（正常系）。"""
    # 準備（A-1 の本文のファイルを消し、どの資料も指さない HTML の本文 A-9 を置く）
    root = make_workspace(
        make_item("A-1", body="A-1.html"),
        make_item("A-2", body="A-2.html"),
        bodies={
            "A-1.html": "<p>一覧の画面</p>\n",
            "A-2.html": "<p>詳細の画面</p>\n",
            "A-9.html": "<p>どの項目も指さない画面</p>\n",
        },
    )
    (root / RECORD_DIR / "docs" / "A-1.html").unlink()
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["ok"] is False
    problems = {
        (row["kind"], row["file"], row["id"], row["key"]) for row in payload["problems"]
    }
    # A-1 の「指す本文が無い」問題が 1 件、A-9 の「どこからも指されない」問題が 1 件あり、A-2 には問題が無い
    assert problems == {
        ("missing_body", ".mindstella/docs.yaml", "A-1", "items[0].body"),
        ("orphan_body", ".mindstella/docs/A-9.html", None, None),
    }


def test_normal_when_threads_problems_found(
    make_workspace: MakeWorkspace,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """スレッドの、存在しない項目を指す参照切れとスキーマ違反を出し、消した項目を指す取り込み済みのスレッドは出さない（正常系）。"""
    # 準備（メモ N-1 を足して commit し、消してもう一度 commit する）
    root = make_workspace()
    ws = {"workspace": str(root)}
    for tool, arguments in (
        ("add", {"kind": "note", "item": {"title": "メモ", "content": "中身"}}),
        ("commit", {"summary": "メモを足す"}),
        ("remove", {"id": "N-1"}),
        ("commit", {"summary": "メモを消す"}),
    ):
        step = call_tool(tool, **ws, **arguments)
        assert step.is_error is False, step.text
    taken_at = "2026-10-12T00:30:00+00:00"
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1"), target="D-9"),
        make_thread(
            "TH-2",
            make_post("TH-2-1", read=True, taken=taken_at),
            status="closed",
            target="N-1",
            events=[
                {
                    "kind": "closed",
                    "author": "user",
                    "reason": None,
                    "created": "2026-10-12T01:00:00+00:00",
                }
            ],
        ),
        make_thread("TH-3", make_post("TH-3-1"), status="waiting"),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", **ws)
    # 検証
    # 点検のツールがエラーにせず、ok が偽の結果を返す
    assert result.is_error is False
    assert result.data is not None
    assert result.data["ok"] is False
    problems = result.data["problems"]
    broken = [row for row in problems if row["kind"] == "broken_ref"]
    # スレッドの最初の書き込みが存在しない D-9 を指す旨が、参照切れとしてある
    assert [(row["file"], row["id"]) for row in broken] == [(".mindstella/threads.yaml", "TH-1")]
    assert "D-9" in broken[0]["detail"]
    # 消した N-1 を指すクローズのスレッドは出ない
    assert all("N-1" not in row["detail"] for row in problems)
    # 状態がオープンでもクローズでもないスレッドが、スキーマ違反としてある
    schema = [row for row in problems if row["kind"] == "schema"]
    assert len(schema) == 1
    assert schema[0]["file"] == ".mindstella/threads.yaml"
    assert "waiting" in schema[0]["detail"]
    # ワークスペースの全てのファイルの中身が、点検を呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_unknown_tag(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """項目とスレッドのタグが語彙に無ければ、ツールのエラーにせず、無いタグを返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["通知"]),
        settings={**valid_settings, "tags": [{"name": "保存"}]},
    )
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    # 点検のツールがツールのエラーにせず、ok が偽の結果を返す
    assert result.is_error is False
    assert result.data["ok"] is False
    # D-1 のタグ 通知、TH-1 のタグ 起票 が語彙に無い旨がある
    unknown = {
        (row["file"], row["id"], row["detail"])
        for row in result.data["problems"]
        if row["kind"] == "unknown_tag"
    }
    assert unknown == {
        (f"{RECORD_DIR}/decisions.yaml", "D-1", "通知"),
        (f"{RECORD_DIR}/threads.yaml", "TH-1", "起票"),
    }
    # ワークスペースの全てのファイルの中身が、点検を呼ぶ前と同じである
    assert snapshot_tree(root) == before
