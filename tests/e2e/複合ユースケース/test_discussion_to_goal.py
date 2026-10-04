"""話し合いをゴールまで進める（セットアップから取り込み・ヒアリング・リサーチ・方針転換を重ね、ゴール判定でリリースするまで）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from playwright.sync_api import Page
from preview_helpers import OpenPreview, fetch_records
from workspace_fixtures import (
    REPO_ROOT,
    CallTool,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
    StartServer,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 話し合いの対象・カテゴリー
TARGET = "家計簿アプリ"
CATEGORY = "機能"

# 会話の日付
TODAY = "2026-10-02"

# 画面から送る回答の本文と、送る先の検討事項の案
SUBMISSION_BODY = "案 A にする"
SUBMISSION_OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]

# 詳細パネルの送信の入力欄・結果・送るボタンと、送信の結果を待つ上限ミリ秒
SEND_TEXTAREA = "aside.panel form.send textarea"
SEND_MESSAGE = "aside.panel form.send .send-msg"
SEND_BUTTON = "aside.panel form.send button[type=submit]"
SEND_TIMEOUT_MS = 10_000

# 移し替えの点検で聞かれる題名に利用者が答える内容
SUMMARY_ANSWER = "要件出しのスキルを設計する"

# 新しい話し合いで /mindstella:setup が決める設定（プレイブック: システム開発、ゴール: インターフェースまで）
SETTINGS: dict[str, Any] = {
    "summary": "家計簿アプリの要件を決める",
    "playbooks": ["システム開発"],
    "target_label": "システム",
    "phases": ["目的", "要件", "構成", "インターフェース", "コンテンツ"],
    "targets": [{"name": TARGET, "summary": "支出を記録する"}],
    "categories": [{"name": CATEGORY, "target": TARGET, "summary": "利用者ができること"}],
    "goal": {
        "phase": "インターフェース",
        "summary": "インターフェースまで決まる",
        "deliverables": [{"title": "要件定義書", "doc": "A-1"}],
    },
    "links": [],
}


def _plugin_version() -> str:
    """プラグインの版（plugins/mindstella/version.ini の 1 行目）を返す。"""
    version_file = REPO_ROOT / "plugins" / "mindstella" / "version.ini"
    return version_file.read_text(encoding="utf-8").splitlines()[0]


def _to_field_settings(root: Path) -> None:
    """前の版の形式にするため、mindmap.yaml の playbooks を、同じ位置の field（分野の名前）に置き換える。"""
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    legacy = {
        ("field" if key == "playbooks" else key): ("システム開発" if key == "playbooks" else value)
        for key, value in settings.items()
    }
    (root / "mindmap.yaml").write_text(
        yaml.safe_dump(legacy, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _placed(title: str, phase: str, **keys: Any) -> dict[str, Any]:
    """対象・カテゴリー・フェーズを付けた項目の中身を作る。"""
    return {"title": title, "target": TARGET, "category": CATEGORY, "phase": phase, **keys}


def _log(title: str, related: list[str], summary: str) -> dict[str, Any]:
    """会話ログの項目の中身を作る。"""
    return {"title": title, "date": TODAY, "related": related, "body_markdown": summary}


def test_normal_when_new_discussion(
    tmp_path: Path,
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """セットアップから、取り込み・ヒアリング・リサーチ・方針転換・ゴール判定を通してゴールまで進める（正常系）。"""
    # 準備
    root = tmp_path / "workspace"
    ws = {"workspace": str(root)}

    # 実行
    # セットアップ: 新しいワークスペースを作る
    replay("init", **ws, settings=SETTINGS)
    # 取り込み: 決め事・派生の検討事項・タスク・会話ログを積む
    replay(
        "add",
        **ws,
        kind="decision",
        item=_placed(
            "保存先を決める",
            "構成",
            status="決定済み",
            answer="YAML ファイルに保存する",
            reason="手で読める",
            options=[
                {"key": "A", "content": "YAML ファイルに保存する", "adopted": True},
                {"key": "B", "content": "DB に保存する"},
            ],
        ),
    )
    replay(
        "add",
        **ws,
        kind="decision",
        item=_placed(
            "保存先のファイル分け",
            "インターフェース",
            status="未決定",
            parent="D-1",
            depends_on=["D-1"],
        ),
    )
    replay(
        "add",
        **ws,
        kind="task",
        item=_placed(
            "保存先の候補を調べる", "構成", kind="調査", status="未着手", **{"for": ["D-1"]}
        ),
    )
    replay(
        "add", **ws, kind="log", item=_log("1 回目の会話", ["D-1", "D-2", "T-1"], "保存先を決めた")
    )
    # ヒアリング: 前提が揃った未決定を聞いて、答えを記録する
    candidates = replay("next", **ws)["candidates"]
    replay("update", **ws, id="D-2", item={"status": "決定済み", "answer": "種類ごとに分ける"})
    replay("add", **ws, kind="log", item=_log("ヒアリング", ["D-2"], "ファイル分けを決めた"))
    # リサーチ: 調査を検討事項に繋ぎ、タスクを完了にする
    replay(
        "add",
        **ws,
        kind="research",
        item=_placed(
            "保存先の候補の比較",
            "構成",
            question="YAML と DB のどちらが手で直しやすいか",
            conclusion="YAML",
            confidence="高",
            angles=["可読性", "手で直せるか"],
            related=["D-1"],
        ),
    )
    replay("update", **ws, id="T-1", item={"status": "完了", "result": "比較を調査 R-1 に書いた"})
    replay("add", **ws, kind="log", item=_log("リサーチ", ["R-1", "T-1"], "候補を比べた"))
    # 方針転換: 採用する案を切り替え、影響を要見直しにして見直しのタスクを積む
    replay("adopt", **ws, id="D-1", key="B")
    affected = replay("impact", **ws, id="D-1")["affected"]
    replay("update", **ws, id="D-1", item={"answer": "DB に保存する", "reason": "検索しやすい"})
    replay(
        "update", **ws, id="D-2", item={"status": "要見直し", "reason": "保存先が DB に変わった"}
    )
    replay(
        "add",
        **ws,
        kind="task",
        item=_placed(
            "ファイル分けを見直す",
            "インターフェース",
            kind="作業",
            status="未着手",
            **{"for": ["D-2"]},
        ),
    )
    replay(
        "add", **ws, kind="log", item=_log("方針転換", ["D-1", "D-2", "T-2"], "保存先を DB にした")
    )
    # 取り込み: 要見直しを決め直し、見直しのタスクを完了する
    replay(
        "update",
        **ws,
        id="D-2",
        item={"status": "決定済み", "answer": "テーブルを種類ごとに分ける"},
    )
    replay("update", **ws, id="T-2", item={"status": "完了", "result": "テーブルの分け方を決めた"})
    # 納品物の資料を作る
    replay(
        "add",
        **ws,
        kind="doc",
        item=_placed(
            "要件定義書",
            "要件",
            kind="文書",
            deliverable=True,
            status="完成",
            body_markdown="# 要件定義書\n\n支出を DB に記録する。",
        ),
    )
    # プレビュー: 配信の URL を示す
    preview_url = replay("preview_url", **ws)["url"]
    # ゴール判定: 届いたかを確かめ、確定の後に release/ へ書き出す
    goal = replay("goal", **ws)
    deliverable = replay("show", **ws, id="A-1")
    replay("clear_release", **ws)
    (root / "release" / "決定事項.md").write_text(
        "# 決定事項\n\n- D-1: DB に保存する\n- D-2: テーブルを種類ごとに分ける\n", encoding="utf-8"
    )
    (root / "release" / "要件定義書.md").write_text(deliverable["body_markdown"], encoding="utf-8")
    replay(
        "add", **ws, kind="log", item=_log("ゴール判定", ["A-1"], "ゴールに届いたのでリリースした")
    )
    checked = call_tool("check", **ws)

    # 検証
    # mindmap.yaml に、プレイブック・最上位の軸の呼び名・フェーズ・カテゴリー・ゴールが入っている
    settings = read_yaml(root, "mindmap.yaml")
    assert settings["playbooks"] == ["システム開発"]
    assert settings["target_label"] == "システム"
    assert settings["phases"] == SETTINGS["phases"]
    assert settings["categories"][0]["name"] == CATEGORY
    assert settings["goal"]["phase"] == "インターフェース"
    # 取り込みで足した検討事項・派生の検討事項（parent を持つ）・タスク・会話ログがある
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    tasks = {item["id"]: item for item in read_yaml(root, "tasks.yaml")["items"]}
    assert decisions["D-2"]["parent"] == "D-1"
    assert tasks["T-1"]["for"] == ["D-1"]
    assert len(read_yaml(root, "logs.yaml")["items"]) == 5
    # ヒアリングで聞いた候補は D-2 だけだった
    assert [candidate["id"] for candidate in candidates] == ["D-2"]
    # リサーチで足した調査が、元の検討事項と related でつながっている
    assert read_yaml(root, "research.yaml")["items"][0]["related"] == ["D-1"]
    # D-1 の採用する案が B で、D-2 が決め直されて決定済み、D-2 の見直しのタスクが完了である
    adopted = [option["key"] for option in decisions["D-1"]["options"] if option.get("adopted")]
    assert adopted == ["B"]
    assert [item["id"] for item in affected] == ["D-2", "T-1"]
    assert decisions["D-2"]["status"] == "決定済み"
    assert tasks["T-2"]["status"] == "完了"
    # goal の出力が「届いた」である
    assert goal["reached"] is True
    assert goal["remaining_decisions"] == []
    assert goal["remaining_deliverables"] == []
    # release/ に、確定した検討事項と納品物の資料が書き出されている
    assert "D-2" in (root / "release" / "決定事項.md").read_text(encoding="utf-8")
    assert "支出を DB に記録する" in (root / "release" / "要件定義書.md").read_text(
        encoding="utf-8"
    )
    # check が参照切れと、YAML と Markdown のずれを 0 件で返す
    assert checked.is_error is False
    assert checked.data["problems"] == []
    # サーバーが配るプレビューの記録が、最後の編集を含んでいる。ワークスペースに preview.html は書き出されていない
    records = fetch_records(preview_url)
    assert records["decisions"] == read_yaml(root, "decisions.yaml")["items"]
    assert records["logs"] == read_yaml(root, "logs.yaml")["items"]
    assert not (root / "preview.html").exists()


def test_normal_when_resume(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """途中まで進んだワークスペースの状況を読み、続きの番号で項目を足す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="見直しの問い", status="要見直し"),
        make_item("T-1", title="進めている作業", status="進行中"),
        make_item("D-2", title="次に決める問い"),
    )
    ws = {"workspace": str(root)}
    # 実行
    # セットアップ: 既存のワークスペースの状況を読む
    status = replay("status", **ws)
    # 取り込み: 続きの番号で検討事項を足す
    added = replay(
        "add", **ws, kind="decision", item={"title": "続きで出た問い", "status": "未決定"}
    )
    # 検証
    # status の出力に、要見直しの D-1・進行中の T-1・次の候補の D-2 がある
    assert status["needs_review"] == [{"id": "D-1", "title": "見直しの問い"}]
    assert status["in_progress"] == [{"id": "T-1", "title": "進めている作業"}]
    assert status["next"][0]["id"] == "D-2"
    # 既存の項目の ID が変わらず、取り込みで足した検討事項が D-3 になっている
    assert added["id"] == "D-3"
    ids = [item["id"] for item in read_yaml(root, "decisions.yaml")["items"]]
    assert ids == ["D-1", "D-2", "D-3"]


def test_normal_when_resume_older_version(
    make_legacy_workspace: MakeLegacyWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """古い版のワークスペースを移し替えてから、状況を読み、続きの番号で項目を足す（正常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1"), legacy_docs={"A-1": True}, without_summary=True)
    _to_field_settings(root)
    before = snapshot_tree(root)
    ws = {"workspace": str(root)}
    # 実行
    # セットアップ: 版を比べて古いと分かり、どのファイルも書き換えずに移し替えのスキルを案内して止まる
    first_plan = call_tool("migrate", **ws, plan=True)
    unchanged_after_setup = snapshot_tree(root)
    # 移し替え: 手順を当て、点検で聞かれる題名を入れ、版を書き換える
    applied = call_tool("migrate", **ws)
    checked_before_set = call_tool("check", **ws)
    call_tool(
        "migrate",
        **ws,
        values=[{"file": "mindmap.yaml", "key": "summary", "value": SUMMARY_ANSWER}],
    )
    recorded = call_tool("migrate", **ws, record=True)
    # セットアップ（2 回目）: 版の案内を出さず、状況を読む
    second_plan = replay("migrate", **ws, plan=True)
    status = replay("status", **ws)
    # 取り込み: 続きの番号で検討事項を足す
    added = replay(
        "add", **ws, kind="decision", item={"title": "続きで出た問い", "status": "未決定"}
    )
    checked = call_tool("check", **ws)
    # 検証
    # 最初のセットアップが、どのファイルも書き換えずに移し替えのスキルを案内する
    assert first_plan.data["relation"] == "older"
    assert unchanged_after_setup == before
    assert applied.is_error is False
    assert checked_before_set.data["ok"] is False
    assert recorded.is_error is False
    # 移し替えの後、mindstella-version.ini の 1 行目がプラグインの版である
    plugin_version = (REPO_ROOT / "plugins" / "mindstella" / "version.ini").read_text(
        encoding="utf-8"
    )
    first_line = (root / "mindstella-version.ini").read_text(encoding="utf-8").splitlines()[0]
    assert first_line == plugin_version.splitlines()[0]
    # 資料 A-1 が status: 完成で done を持たず、mindmap.yaml の summary が答えた題名である
    doc = read_yaml(root, "docs.yaml")["items"][0]
    assert doc["status"] == "完成"
    assert "done" not in doc
    settings = read_yaml(root, "mindmap.yaml")
    assert settings["summary"] == SUMMARY_ANSWER
    # mindmap.yaml が field を持たず、playbooks に元の分野のシステム開発の 1 件を持ち、target_label が移し替えの前と同じである
    assert "field" not in settings
    assert settings["playbooks"] == ["システム開発"]
    assert settings["target_label"] == "システム"
    # 2 回目のセットアップが版の案内を出さず、状況と続きの推奨を出す
    assert second_plan["relation"] == "same"
    assert status["next"][0]["id"] == "D-1"
    # 既存の項目の ID が変わらず、取り込みで足した検討事項が D-2 になっている
    assert added["id"] == "D-2"
    ids = [item["id"] for item in read_yaml(root, "decisions.yaml")["items"]]
    assert ids == ["D-1", "D-2"]
    # check が問題を 0 件で返す
    assert checked.is_error is False
    assert checked.data["problems"] == []


def test_normal_when_scope_widened(
    tmp_path: Path,
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """ゴールを決めずに始め、範囲を広げて題名・ゴール・プレイブックを書き換え、書き換えたゴールまで進める（正常系）。"""
    # 準備
    root = tmp_path / "workspace"
    ws = {"workspace": str(root)}
    new_phases = ["目的", "発散", "要件", "構成", "インターフェース", "コンテンツ"]
    new_goal = {
        "phase": "要件",
        "summary": "要件が決まる",
        "deliverables": [{"title": "要件定義書"}],
    }

    # 実行
    # セットアップ: 壁打ちのプレイブックを選び、ゴールを決めずに作る
    replay(
        "init",
        **ws,
        settings={
            "summary": "家計簿アプリについて壁打ちする",
            "description": "家計簿アプリで何を作るかを壁打ちして整理する話し合い。",
            "playbooks": ["壁打ち"],
            "target_label": "テーマ",
            "phases": ["問い", "発散", "整理", "絞り込み", "結論"],
            "targets": [{"name": TARGET, "summary": "支出を記録する"}],
            "categories": [{"name": CATEGORY, "target": TARGET, "summary": "利用者ができること"}],
            "links": [],
        },
    )
    # 取り込み: 問いと発散の検討事項を積む
    replay("add", **ws, kind="decision", item=_placed("何を作るか", "問い", status="未決定"))
    replay("add", **ws, kind="decision", item=_placed("使う場面の案", "発散", status="未決定"))
    # ゴール判定: ゴールが無いことを示す
    first_goal = replay("goal", **ws)
    # 範囲の見直し: システム開発を足し、フェーズの対応を確かめて付け替え、題名・最上位の軸の呼び名・ゴールを書き換える
    replay(
        "update_settings",
        **ws,
        settings={
            "summary": "家計簿アプリの要件を決める",
            "playbooks": ["壁打ち", "システム開発"],
            "phases": new_phases,
            "target_label": "機能",
            "goal": new_goal,
        },
        phase_map={"問い": "目的", "整理": "要件", "絞り込み": "要件", "結論": "要件"},
    )
    replay("add", **ws, kind="log", item=_log("範囲の見直し", ["D-1", "D-2"], "要件まで決める"))
    # 取り込み: 納品物の資料を作って、同じタイトルのゴールの納品物から指す
    replay(
        "add",
        **ws,
        kind="doc",
        item=_placed(
            "要件定義書",
            "要件",
            kind="文書",
            deliverable=True,
            status="下書き",
            body_markdown="# 要件定義書\n\n支出を記録する。",
        ),
    )
    replay(
        "update_settings",
        **ws,
        settings={"goal": {**new_goal, "deliverables": [{"title": "要件定義書", "doc": "A-1"}]}},
    )
    # 取り込み: ゴールのフェーズまでの検討事項を決定済みにし、納品物の資料を完成にする
    replay("update", **ws, id="D-1", item={"status": "決定済み", "answer": "支出を記録する"})
    replay("update", **ws, id="D-2", item={"status": "決定済み", "answer": "買い物の後に使う"})
    replay("update", **ws, id="A-1", item={"status": "完成"})
    # ゴール判定: 届いたかを確かめ、確定の後に release/ へ書き出す
    second_goal = replay("goal", **ws)
    deliverable = replay("show", **ws, id="A-1")
    replay("clear_release", **ws)
    (root / "release" / "決定事項.md").write_text(
        "# 決定事項\n\n- D-1: 支出を記録する\n- D-2: 買い物の後に使う\n", encoding="utf-8"
    )
    (root / "release" / "要件定義書.md").write_text(deliverable["body_markdown"], encoding="utf-8")
    checked = call_tool("check", **ws)

    # 検証
    # 最初の goal の出力が、ゴールが無いことを示す
    assert first_goal["has_goal"] is False
    assert first_goal["reached"] is None
    # mindmap.yaml の playbooks が壁打ちとシステム開発の 2 件で、summary・target_label・goal が書き換えた値である
    settings = read_yaml(root, "mindmap.yaml")
    assert settings["playbooks"] == ["壁打ち", "システム開発"]
    assert settings["summary"] == "家計簿アプリの要件を決める"
    assert settings["target_label"] == "機能"
    assert settings["goal"]["phase"] == "要件"
    # 付け替えの前に足した D-1・D-2 のフェーズが、どちらも書き換えた後の phases のどれかである
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    assert {decisions["D-1"]["phase"], decisions["D-2"]["phase"]} <= set(settings["phases"])
    # goal.deliverables の納品物が、取り込みで作った資料を doc で指している
    assert settings["goal"]["deliverables"] == [{"title": "要件定義書", "doc": "A-1"}]
    # 2 回目の goal の出力が「届いた」である
    assert second_goal["reached"] is True
    # release/ に、確定した検討事項と納品物の資料が書き出されている
    assert "D-2" in (root / "release" / "決定事項.md").read_text(encoding="utf-8")
    assert "支出を記録する" in (root / "release" / "要件定義書.md").read_text(encoding="utf-8")
    # check が問題を 0 件で返す
    assert checked.is_error is False
    assert checked.data["problems"] == []


def test_normal_when_submission_from_preview(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """プレビューの詳細パネルから送った回答を、Claude Code を立ち上げ直した後の話し合いの最初に取り込む（正常系）。"""
    # 準備
    # 案 A・B を持つ未決定の検討事項 D-1 を持つワークスペース（版のファイルはプラグインと同じ版）
    root = make_workspace(
        make_item("D-1", title="見せ方", options=SUBMISSION_OPTIONS),
        raw_files={"mindstella-version.ini": f"{_plugin_version()}\n"},
    )
    ws = {"workspace": str(root)}
    first_server = start_server()
    # 実行
    # 1 回目の立ち上げ: セットアップが既存のワークスペースの状況を読み、プレビューの URL を示す
    first_status = first_server.call("status", **ws)
    served = first_server.call("preview_url", **ws)
    assert served.data is not None
    # 示された URL をブラウザで開き、D-1 の詳細パネルから回答を送る
    open_preview(served.data["url"], "#tab=decisions&id=D-1")
    page.wait_for_selector(SEND_TEXTAREA)
    page.fill(SEND_TEXTAREA, SUBMISSION_BODY)
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.sent", timeout=SEND_TIMEOUT_MS)
    # Claude Code を閉じる（MCP サーバーが止まる）
    first_server.close_stdin()
    first_server.wait_exit()
    # 立ち上げ直し: 同じワークスペースを渡した新しい MCP サーバーで、セットアップの後に取り込みを再生する
    second_server = start_server()
    second_status = second_server.call("status", **ws)
    pending = second_server.call("submissions", **ws)
    assert pending.data is not None
    # 取り込みのステップ: 本文から D-1 の採用する案を A にして決定済みにし、会話ログに本文を残す
    adopted = second_server.call("adopt", **ws, id="D-1", key="A")
    updated = second_server.call(
        "update", **ws, id="D-1", item={"status": "決定済み", "answer": "表で見せる"}
    )
    logged = second_server.call(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた回答",
            "date": TODAY,
            "related": ["D-1"],
            "body_markdown": SUBMISSION_BODY,
        },
    )
    # 記録した後に、その送信を取り込み済みにする
    taken = second_server.call("take_submission", **ws, id=pending.data["items"][0]["id"])
    again = second_server.call("submissions", **ws)
    checked = second_server.call("check", **ws)
    # 検証
    assert first_status.is_error is False
    assert second_status.is_error is False
    assert [item["target"] for item in pending.data["items"]] == ["D-1"]
    assert [item["body"] for item in pending.data["items"]] == [SUBMISSION_BODY]
    for result in (adopted, updated, logged, taken):
        assert result.is_error is False, result.text
    # D-1 の採用する案が A で、決定済みである
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["A"]
    assert decision["status"] == "決定済み"
    # 会話ログに送信の本文が残っている
    assert SUBMISSION_BODY in (root / "docs" / "L-1.md").read_text(encoding="utf-8")
    # 送信が取り込み済みで、取り込みのツールをもう一度呼ぶと 0 件を返す
    assert read_yaml(root, "submissions.yaml")["items"][0]["taken"] is not None
    assert again.data == {"items": []}
    # check が問題を 0 件で返す
    assert checked.data is not None
    assert checked.data["problems"] == []
