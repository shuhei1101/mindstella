"""話し合いをゴールまで進める（セットアップから取り込み・ヒアリング・リサーチ・方針転換を重ね、ゴール判定でリリースするまで）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    FREE_FORM,
    FREE_TEXTAREA,
    PILL,
    OpenPreview,
    fetch_records,
    select_text_for_pill,
)
from readme_helpers import assert_readme_commands, preview_section
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
    StartServer,
    plugin_version,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 前の版（v0.6.0 より前）の設定ファイルの名前と、今の設定ファイルの名前
LEGACY_SETTINGS_FILE = "mindmap.yaml"
SETTINGS_FILE = "config.yaml"

# 話し合いの対象・カテゴリー
TARGET = "家計簿アプリ"
CATEGORY = "機能"

# 範囲の見直しでまとめる前の、壁打ちで使うカテゴリー
IDEA_CATEGORY = "アイデア"

# 範囲の見直しで変える対象の名前
NEW_TARGET = "アプリ"

# 会話の日付
TODAY = "2026-10-02"

# 範囲の見直しの前に足す検討事項の案
SCOPE_OPTIONS = [
    {"key": "A", "content": "支出を記録する", "recommended": True},
    {"key": "B", "content": "予算を立てる"},
]

# 画面から送る回答の本文と、送る先の検討事項の案
SUBMISSION_BODY = "案 A にする"
SUBMISSION_OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]

# 資料 A-1 の 3 行の段落の本文と、2 行目の選ぶ文・その箇所へ溜める本文、項目に紐づかないコメントの本文
SUBMISSION_DOC_BODY = "最初の文\n言い換えたい文\n最後の文\n"
SUBMISSION_SENTENCE = "言い換えたい文"
SUBMISSION_LOCATION_BODY = "ここは言い換える"
SUBMISSION_FREE_BODY = "全体に目を通した"

# コメントを溜めて送る結果を待つ上限ミリ秒
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


# 取り込みで足すタスクの本文
TASK_BODY = "経緯: 会話で持ち越した\n終わり方: 比べた結果を残す\n"


def _to_field_settings(root: Path) -> None:
    """前の版の形式にするため、mindmap.yaml の playbooks を、同じ位置の field（分野の名前）に置き換える。"""
    settings = yaml.safe_load((root / LEGACY_SETTINGS_FILE).read_text(encoding="utf-8"))
    legacy = {
        ("field" if key == "playbooks" else key): ("システム開発" if key == "playbooks" else value)
        for key, value in settings.items()
    }
    (root / LEGACY_SETTINGS_FILE).write_text(
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
    # セッションの準備: 直下の README を書き直す
    replay("readme", **ws)
    # 取り込み: 決め事・派生の検討事項・タスク・会話ログを、1 回のまとめての書き込みで積む
    replay(
        "batch",
        **ws,
        operations=[
            {
                "op": "add",
                "kind": "decision",
                "item": _placed(
                    "保存先を決める",
                    "構成",
                    status="決定済み",
                    answer="YAML ファイルに保存する",
                    reason="手で読める",
                    options=[{"key": "A", "content": "YAML ファイルに保存する", "adopted": True}],
                ),
            },
            {
                "op": "add",
                "kind": "decision",
                "item": _placed(
                    "保存先のファイル分け",
                    "インターフェース",
                    status="未決定",
                    parent="$1",
                    depends_on=["$1"],
                    options=[
                        {"key": "A", "content": "種類ごとに分ける", "recommended": True},
                        {"key": "B", "content": "1 つにまとめる"},
                    ],
                ),
            },
            {
                "op": "add",
                "kind": "task",
                "item": _placed(
                    "保存先の候補を調べる",
                    "構成",
                    kind="調査",
                    status="未着手",
                    body_markdown=TASK_BODY,
                    **{"for": ["$1"]},
                ),
            },
            {
                "op": "add",
                "kind": "log",
                "item": _log("1 回目の会話", ["$1", "$2", "$3"], "保存先を決めた"),
            },
        ],
    )
    added_decisions = read_yaml(root, "decisions.yaml")["items"]
    # ヒアリング: 前提が揃った未決定を聞いて、選ばれた案を採用し、答えと理由を記録する
    candidates = replay("next", **ws)["candidates"]
    replay("adopt", **ws, id="D-2", key="A")
    replay(
        "update", **ws, id="D-2", item={"answer": "種類ごとに分ける", "reason": "探しやすい"}
    )
    replay("add", **ws, kind="log", item=_log("ヒアリング", ["D-2"], "ファイル分けを決めた"))
    # 取り込み: D-1 に案 B を、案の書き換えで足す
    replay(
        "edit_option",
        **ws,
        id="D-1",
        action="add",
        key="B",
        option={"content": "DB に保存する"},
    )
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
    (root / RECORD_DIR / "release" / "決定事項.md").write_text(
        "# 決定事項\n\n- D-1: DB に保存する\n- D-2: テーブルを種類ごとに分ける\n", encoding="utf-8"
    )
    (root / RECORD_DIR / "release" / "要件定義書.md").write_text(deliverable["body_markdown"], encoding="utf-8")
    replay(
        "add", **ws, kind="log", item=_log("ゴール判定", ["A-1"], "ゴールに届いたのでリリースした")
    )
    checked = call_tool("check", **ws)

    # 検証
    # config.yaml に、プレイブック・最上位の軸の呼び名・フェーズ・カテゴリー・ゴールが入っている
    settings = read_yaml(root, "config.yaml")
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
    # 取り込みで足したタスクが本文を持ち、show の body_markdown が書いた本文を返す
    assert replay("show", **ws, id="T-1")["body_markdown"] == TASK_BODY
    # 足した・直した項目の updated_by が、どれも ai である
    edited = [
        item
        for file_name in ("decisions.yaml", "tasks.yaml", "research.yaml", "docs.yaml", "logs.yaml")
        for item in read_yaml(root, file_name)["items"]
    ]
    assert {item["updated_by"] for item in edited} == {"ai"}
    # 足した検討事項がどれも案を 1 つ以上持ち、未決定で足した D-2 が推奨の印を 1 つ持つ
    assert all(item["options"] for item in added_decisions)
    assert [
        option["key"] for option in added_decisions[1]["options"] if option.get("recommended")
    ] == ["A"]
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
    # ヒアリングで答えた D-2 が、採用した案 A を 1 つだけ持って決定済みである
    assert [option["key"] for option in decisions["D-2"]["options"] if option.get("adopted")] == [
        "A"
    ]
    # goal の出力が「届いた」である
    assert goal["reached"] is True
    assert goal["remaining_decisions"] == []
    assert goal["remaining_deliverables"] == []
    # release/ に、確定した検討事項と納品物の資料が書き出されている
    assert "D-2" in (root / RECORD_DIR / "release" / "決定事項.md").read_text(encoding="utf-8")
    assert "支出を DB に記録する" in (root / RECORD_DIR / "release" / "要件定義書.md").read_text(
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
    # ワークスペースの直下には .mindstella/ と README.md だけがある
    assert sorted(path.name for path in root.iterdir()) == [RECORD_DIR, "README.md"]
    # 直下の README.md に、起動・接続のコマンドとスキルの呼び方の一覧があり、プレビューの節が示した URL である
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert_readme_commands(root, readme)
    assert preview_section(readme).splitlines()[1] == preview_url


def test_normal_when_resume(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """途中まで進んだワークスペースの状況と前回読んだ後の変更を読み、続きの番号で項目を足す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="見直しの問い", status="要見直し", body="D-1.md"),
        make_item("T-1", title="進めている作業", status="進行中"),
        make_item("D-2", title="次に決める問い"),
        bodies={"D-1.md": "1 行目\n2 行目\n3 行目\n"},
    )
    ws = {"workspace": str(root)}
    # 前の話し合いの終わりに前回読んだ時点を記録し、その後で D-1 のタイトルと本文を書き換えておく
    replay("changes_since_read", **ws)
    replay(
        "update",
        **ws,
        id="D-1",
        item={"title": "見直しの問い（直した）", "body_markdown": "1 行目\n直した 2 行目\n3 行目\n"},
    )
    # 実行
    # セットアップ: 既存のワークスペースの状況を読む
    status = replay("status", **ws)
    # 準備: 前回読んだ時点からの変更を読む
    read = replay("changes_since_read", **ws)
    read_again = replay("changes_since_read", **ws)
    # 読んだ直後の changes.yaml を控える（取り込みの書き込みで last_seq が進む前の状態）
    changes_after_read = read_yaml(root, "changes.yaml")
    # 取り込み: 続きの番号で、1 つの発言から出た検討事項とタスクを 1 回で足す
    batched = replay(
        "batch",
        **ws,
        operations=[
            {
                "op": "add",
                "kind": "decision",
                "item": {
                    "title": "続きで出た問い",
                    "status": "未決定",
                    "options": [{"key": "A", "content": "案 A", "recommended": True}],
                },
            },
            {
                "op": "add",
                "kind": "task",
                "item": {
                    "title": "続きの問いを調べる",
                    "kind": "調査",
                    "status": "未着手",
                    "for": ["$1"],
                },
            },
        ],
    )
    # 検証
    # status の出力に、要見直しの D-1・進行中の T-1・次の候補の D-2 がある
    assert status["needs_review"] == [{"id": "D-1", "title": "見直しの問い（直した）"}]
    assert status["in_progress"] == [{"id": "T-1", "title": "進めている作業"}]
    assert status["next"][0]["id"] == "D-2"
    # 前回読んだ時点からの変更の出力に、D-1 が変わったキー（タイトル・本文）と前の値つきである
    assert [entry["id"] for entry in read["changed"]] == ["D-1"]
    assert read["changed"][0]["before"] == {"title": "見直しの問い"}
    assert read["changed"][0]["body_diff"] is not None
    # 前回読んだ時点からの変更の出力の D-1 に、最後に編集した人 ai が載っている
    assert read["changed"][0]["updated_by"] == "ai"
    # 読んだ後、AI が最後に読んだ時点が最後の書き換えの通し番号になっており、続けてもう一度読むと変更が 0 件である
    assert changes_after_read["read_seq"] == changes_after_read["last_seq"]
    assert read_again["added"] == []
    assert read_again["changed"] == []
    # 既存の項目の ID が変わらず、取り込みの 1 回の呼び出しで足した検討事項が D-3、タスクが T-2 になっている
    assert [entry["result"]["id"] for entry in batched["results"]] == ["D-3", "T-2"]
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
    decided = make_item("D-1", status="決定済み", answer="YAML に保存する", reason="手で読める")
    root = make_legacy_workspace(
        {key: value for key, value in decided.items() if key != "options"},
        legacy_docs={"A-1": True},
        without_summary=True,
        settings_file=LEGACY_SETTINGS_FILE,
        top=True,
    )
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
        values=[
            {"file": f"{RECORD_DIR}/{SETTINGS_FILE}", "key": "summary", "value": SUMMARY_ANSWER}
        ],
    )
    recorded = call_tool("migrate", **ws, record=True)
    top_after_migration = sorted(path.name for path in root.iterdir())
    # セットアップ（2 回目）: 版の案内を出さず、状況を読む
    second_plan = replay("migrate", **ws, plan=True)
    status = replay("status", **ws)
    # セッションの準備: 直下の README を書く
    replay("readme", **ws)
    # 取り込み: 続きの番号で検討事項を足す
    added = replay(
        "add",
        **ws,
        kind="decision",
        item={
            "title": "続きで出た問い",
            "status": "未決定",
            "options": [{"key": "A", "content": "案 A", "recommended": True}],
        },
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
    first_line = (root / RECORD_DIR / "mindstella-version.ini").read_text(encoding="utf-8").splitlines()[0]
    assert first_line == plugin_version()
    # 資料 A-1 が status: 完成で done を持たず、config.yaml の summary が答えた題名である
    doc = read_yaml(root, "docs.yaml")["items"][0]
    assert doc["status"] == "完成"
    assert "done" not in doc
    settings = read_yaml(root, SETTINGS_FILE)
    assert settings["summary"] == SUMMARY_ANSWER
    # config.yaml が field を持たず、playbooks に元の分野のシステム開発の 1 件を持ち、target_label が移し替えの前と同じである
    assert "field" not in settings
    assert settings["playbooks"] == ["システム開発"]
    assert settings["target_label"] == "システム"
    # ワークスペースに mindmap.yaml が残っておらず、直下には記録のフォルダだけがある
    assert not (root / LEGACY_SETTINGS_FILE).exists()
    assert top_after_migration == [RECORD_DIR]
    # session の準備の後、直下に README.md があり、このフォルダの起動・接続のコマンドとスキルの呼び方の一覧がある
    assert_readme_commands(root, (root / "README.md").read_text(encoding="utf-8"))
    # 2 回目のセットアップが版の案内を出さず、状況と続きの推奨を出す
    assert second_plan["relation"] == "same"
    # D-1 が移し替えの前の answer を内容、reason を理由にした採用した案を 1 つ持ち、決定済みのままである
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert decision["status"] == "決定済み"
    assert decision["options"] == [
        {"key": "A", "content": "YAML に保存する", "reason": "手で読める", "adopted": True}
    ]
    # 決定済みの D-1 は次の候補に上がらない
    assert status["next"] == []
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
            "categories": [
                {"name": CATEGORY, "target": TARGET, "summary": "利用者ができること"},
                {"name": IDEA_CATEGORY, "target": TARGET, "summary": "出たアイデア"},
            ],
            "links": [],
        },
    )
    # 取り込み: 問いと発散の検討事項を積む（発散のものは アイデア のカテゴリーに置く）
    replay(
        "add",
        **ws,
        kind="decision",
        item=_placed("何を作るか", "問い", status="未決定", options=SCOPE_OPTIONS),
    )
    replay(
        "add",
        **ws,
        kind="decision",
        item=_placed(
            "使う場面の案", "発散", status="未決定", category=IDEA_CATEGORY, options=SCOPE_OPTIONS
        ),
    )
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
            "targets": [{"name": NEW_TARGET, "summary": "支出を記録する"}],
            "categories": [
                {"name": CATEGORY, "target": NEW_TARGET, "summary": "利用者ができること"}
            ],
            "goal": new_goal,
        },
        phase_map={"問い": "目的", "整理": "要件", "絞り込み": "要件", "結論": "要件"},
        target_map={TARGET: NEW_TARGET},
        category_map={IDEA_CATEGORY: CATEGORY},
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
            target=NEW_TARGET,
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
    # 取り込み: ゴールのフェーズまでの検討事項の案を採用して決定済みにし、納品物の資料を完成にする
    replay("adopt", **ws, id="D-1", key="A")
    replay("adopt", **ws, id="D-2", key="A")
    replay("update", **ws, id="D-1", item={"answer": "支出を記録する"})
    replay("update", **ws, id="D-2", item={"answer": "買い物の後に使う"})
    replay("update", **ws, id="A-1", item={"status": "完成"})
    # ゴール判定: 届いたかを確かめ、確定の後に release/ へ書き出す
    second_goal = replay("goal", **ws)
    deliverable = replay("show", **ws, id="A-1")
    replay("clear_release", **ws)
    (root / RECORD_DIR / "release" / "決定事項.md").write_text(
        "# 決定事項\n\n- D-1: 支出を記録する\n- D-2: 買い物の後に使う\n", encoding="utf-8"
    )
    (root / RECORD_DIR / "release" / "要件定義書.md").write_text(deliverable["body_markdown"], encoding="utf-8")
    checked = call_tool("check", **ws)

    # 検証
    # 最初の goal の出力が、ゴールが無いことを示す
    assert first_goal["has_goal"] is False
    assert first_goal["reached"] is None
    # config.yaml の playbooks が壁打ちとシステム開発の 2 件で、summary・target_label・goal が書き換えた値である
    settings = read_yaml(root, "config.yaml")
    assert settings["playbooks"] == ["壁打ち", "システム開発"]
    assert settings["summary"] == "家計簿アプリの要件を決める"
    assert settings["target_label"] == "機能"
    assert settings["goal"]["phase"] == "要件"
    # 付け替えの前に足した D-1・D-2 のフェーズが、どちらも書き換えた後の phases のどれかである
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    assert {decisions["D-1"]["phase"], decisions["D-2"]["phase"]} <= set(settings["phases"])
    # D-1・D-2 の対象・カテゴリーが、書き換えた後の targets・categories のどれかである
    assert {decisions["D-1"]["target"], decisions["D-2"]["target"]} <= {
        entry["name"] for entry in settings["targets"]
    }
    assert {decisions["D-1"]["category"], decisions["D-2"]["category"]} <= {
        entry["name"] for entry in settings["categories"]
    }
    # 付け替えた D-1・D-2 の updated_by が ai である
    assert [decisions[item_id]["updated_by"] for item_id in ("D-1", "D-2")] == ["ai", "ai"]
    # D-1・D-2 が採用した案を 1 つ持って決定済みである
    for item_id in ("D-1", "D-2"):
        assert decisions[item_id]["status"] == "決定済み"
        assert [o["key"] for o in decisions[item_id]["options"] if o.get("adopted")] == ["A"]
    # goal.deliverables の納品物が、取り込みで作った資料を doc で指している
    assert settings["goal"]["deliverables"] == [{"title": "要件定義書", "doc": "A-1"}]
    # 2 回目の goal の出力が「届いた」である
    assert second_goal["reached"] is True
    # release/ に、確定した検討事項と納品物の資料が書き出されている
    assert "D-2" in (root / RECORD_DIR / "release" / "決定事項.md").read_text(encoding="utf-8")
    assert "支出を記録する" in (root / RECORD_DIR / "release" / "要件定義書.md").read_text(encoding="utf-8")
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
    """プレビューで溜めてまとめて送ったコメントを、Claude Code を立ち上げ直した後の話し合いの最初に取り込む（正常系）。"""
    # 準備
    # 案 A・B を持つ未決定の検討事項 D-1 と、3 行の段落の本文を持つ資料 A-1 を持つワークスペース（版のファイルはプラグインと同じ版）
    root = make_workspace(
        make_item("D-1", title="見せ方", options=SUBMISSION_OPTIONS),
        make_item("A-1"),
        bodies={"A-1.md": SUBMISSION_DOC_BODY},
        raw_files={"mindstella-version.ini": f"{plugin_version()}\n"},
    )
    ws = {"workspace": str(root)}
    first_server = start_server()
    # 実行
    # 1 回目の立ち上げ: セットアップが既存のワークスペースの状況を読み、プレビューの URL を示す
    first_status = first_server.call("status", **ws)
    served = first_server.call("preview_url", **ws)
    assert served.data is not None
    # 示された URL をブラウザで開き、D-1 の詳細パネルでコメントを溜める
    open_preview(served.data["url"], "#tab=decisions&id=D-1")
    page.wait_for_selector(DETAIL_TEXTAREA)
    page.fill(DETAIL_TEXTAREA, SUBMISSION_BODY)
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=SEND_TIMEOUT_MS)
    # A-1 の詳細パネルで、本文の 2 行目の文を選んで箇所を添えたコメントを溜める
    open_preview(served.data["url"], "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    select_text_for_pill(page, "aside.panel .md", SUBMISSION_SENTENCE)
    page.click(PILL)
    page.fill(DETAIL_TEXTAREA, SUBMISSION_LOCATION_BODY)
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=SEND_TIMEOUT_MS)
    # コメントのボタンから一覧を開き、項目に紐づかないコメントを溜めてチェックを外し、まとめて送る
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.fill(FREE_TEXTAREA, SUBMISSION_FREE_BODY)
    page.locator(FREE_FORM).get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} li[data-comment='C-3']", timeout=SEND_TIMEOUT_MS)
    page.locator(f"{COMMENTS_PANEL} li[data-comment='C-3'] input.row-check").uncheck()
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .send-band .send-msg.sent", timeout=SEND_TIMEOUT_MS)
    # Claude Code を閉じる（MCP サーバーが止まる）
    first_server.close_stdin()
    first_server.wait_exit()
    # 立ち上げ直し: 同じワークスペースを渡した新しい MCP サーバーで、セットアップの後に取り込みを再生する
    second_server = start_server()
    second_status = second_server.call("status", **ws)
    pending = second_server.call("submissions", **ws)
    assert pending.data is not None
    # 取り込みのステップ: D-1 への送信の本文から採用する案を A にして決定済みにし、会話ログに本文を残す
    adopted = second_server.call("adopt", **ws, id="D-1", key="A")
    updated = second_server.call(
        "update", **ws, id="D-1", item={"status": "決定済み", "answer": "表で見せる"}
    )
    first_logged = second_server.call(
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
    first_taken = second_server.call("take_submission", **ws, id=pending.data["items"][0]["id"])
    # A-1 の箇所を持つ送信は、本文の 2 行目と選んだ文を添えて会話ログに残し、取り込み済みにする
    second_logged = second_server.call(
        "add",
        **ws,
        kind="log",
        item={
            "title": "画面から届いた意見（A-1 の箇所）",
            "date": TODAY,
            "related": ["A-1"],
            "body_markdown": f"A-1 の本文の 2 行目「{SUBMISSION_SENTENCE}」へ: {SUBMISSION_LOCATION_BODY}",
        },
    )
    second_taken = second_server.call("take_submission", **ws, id=pending.data["items"][1]["id"])
    again = second_server.call("submissions", **ws)
    checked = second_server.call("check", **ws)
    # 検証
    assert first_status.is_error is False
    assert second_status.is_error is False
    assert [item["target"] for item in pending.data["items"]] == ["D-1", "A-1"]
    assert [item["body"] for item in pending.data["items"]] == [
        SUBMISSION_BODY,
        SUBMISSION_LOCATION_BODY,
    ]
    assert pending.data["items"][1]["loc"] == {
        "kind": "body",
        "start": 2,
        "end": 2,
        "text": SUBMISSION_SENTENCE,
    }
    for result in (adopted, updated, first_logged, first_taken, second_logged, second_taken):
        assert result.is_error is False, result.text
    # D-1 の採用する案が A で、決定済みである
    decision = read_yaml(root, "decisions.yaml")["items"][0]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["A"]
    assert decision["status"] == "決定済み"
    # 会話ログに、D-1 への送信の本文と、A-1 の箇所を添えた送信の本文が残っている
    assert SUBMISSION_BODY in (root / RECORD_DIR / "docs" / "L-1.md").read_text(encoding="utf-8")
    location_log = (root / RECORD_DIR / "docs" / "L-2.md").read_text(encoding="utf-8")
    assert SUBMISSION_LOCATION_BODY in location_log
    assert SUBMISSION_SENTENCE in location_log
    # チェックを外した項目に紐づかないコメントは送信に無く、コメントの一覧に残っている
    assert [item["body"] for item in read_yaml(root, "submissions.yaml")["items"]] == [
        SUBMISSION_BODY,
        SUBMISSION_LOCATION_BODY,
    ]
    assert [item["body"] for item in read_yaml(root, "comments.yaml")["items"]] == [
        SUBMISSION_FREE_BODY
    ]
    # 送信が取り込み済みで、取り込みのツールをもう一度呼ぶと 0 件を返す
    assert all(item["taken"] is not None for item in read_yaml(root, "submissions.yaml")["items"])
    assert again.data == {"items": []}
    # check が問題を 0 件で返す
    assert checked.data is not None
    assert checked.data["problems"] == []
