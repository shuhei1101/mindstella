"""commands.py（ツールごとの処理）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import builder
import commands
from errors import (
    ArgumentError,
    ItemNotFoundError,
    OptionNotFoundError,
    SchemaMismatchError,
    WorkspaceNotFoundError,
)
from export_helpers import (
    external_template,
    make_fetch,
    make_responses,
    write_preview_dir,
)
from fixture_types import (
    MakeItem,
    MakeLegacyWorkspace,
    MakeSubmission,
    MakeWorkspace,
    PatchPluginVersion,
    SnapshotTree,
    WriteSubmissions,
)
from query import SearchFilter

# now の代わりに返す日時
FIXED_NOW = "2026-10-02T08:00:00+00:00"

# 送信の取り込みで now の代わりに返す日時
SUBMISSION_NOW = "2026-10-04T03:00:00+00:00"

# make_item が項目に入れる既定の日時
DEFAULT_TIMESTAMP = "2026-10-01T00:00:00+00:00"


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _submission_now() -> str:
    """送信の取り込みで、今の日時の代わりに決めた日時を返す。"""
    return SUBMISSION_NOW


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML を読んで、項目の並びを返す。"""
    data = yaml.safe_load((root / file_name).read_text(encoding="utf-8"))
    return data["items"]


class _FakeRegistry:
    """start の呼び出しを控え、決めた URL を返す偽の配信の台帳。"""

    def __init__(self) -> None:
        """start に渡されたワークスペースを控える入れ物を作る。"""
        self.started: list[Path] = []

    def start(self, root: Path) -> tuple[str, bool]:
        """渡されたワークスペースを控えて、決めた URL と今立てたことを返す。"""
        self.started.append(root)
        return "http://127.0.0.1:1/", True


def test_validate_input_keys() -> None:
    """渡せるキーだけなら何もしない（正常系）。"""
    # 実行
    result = commands.validate_input_keys("decision", {"title": "t", "body_markdown": "b"})
    # 検証
    assert result is None


@pytest.mark.parametrize("key", ["id", "created", "updated", "body"])
def test_validate_input_keys_when_reserved(key: str) -> None:
    """ツールが付けるキーを弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        commands.validate_input_keys("decision", {key: "x"})
    assert key in exc_info.value.lines[0]


def test_validate_input_keys_when_body_not_allowed() -> None:
    """本文を持てない種類への body_markdown を弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        commands.validate_input_keys("task", {"body_markdown": "b"})
    assert "body_markdown" in exc_info.value.lines[0]


def test_merge_changes() -> None:
    """置き換え・消す・同じ値を見分ける（正常系）。"""
    # 準備
    item = {"id": "D-1", "status": "未決定", "weight": "大", "lead": "l"}
    changes = {"status": "決定済み", "weight": None, "lead": "l", "answer": "a"}
    # 実行
    merged, changed = commands.merge_changes(item, changes)
    # 検証
    assert merged == {"id": "D-1", "status": "決定済み", "lead": "l", "answer": "a"}
    assert changed == ["status", "weight", "answer"]
    assert item == {"id": "D-1", "status": "未決定", "weight": "大", "lead": "l"}


def test_switch_adopted() -> None:
    """採用を切り替え、前の記号を返す（正常系）。"""
    # 準備
    item = {
        "options": [
            {"key": "A", "content": "案 A", "adopted": True},
            {"key": "B", "content": "案 B", "adopted": False},
        ]
    }
    # 実行
    switched, previous = commands.switch_adopted(item, "B")
    # 検証
    assert switched["options"] == [
        {"key": "A", "content": "案 A", "adopted": False},
        {"key": "B", "content": "案 B", "adopted": True},
    ]
    assert previous == "A"
    assert item["options"][0]["adopted"] is True


def test_switch_adopted_when_none_adopted() -> None:
    """採用が無ければ前の記号は None を返す（正常系）。"""
    # 準備
    item = {
        "options": [
            {"key": "A", "content": "案 A", "adopted": False},
            {"key": "B", "content": "案 B", "adopted": False},
        ]
    }
    # 実行
    switched, previous = commands.switch_adopted(item, "A")
    # 検証
    assert switched["options"] == [
        {"key": "A", "content": "案 A", "adopted": True},
        {"key": "B", "content": "案 B", "adopted": False},
    ]
    assert previous is None


def test_switch_adopted_when_option_missing() -> None:
    """無い記号は切り替えない（異常系）。"""
    # 準備
    item = {
        "options": [
            {"key": "A", "content": "案 A", "adopted": True},
            {"key": "B", "content": "案 B", "adopted": False},
        ]
    }
    # 実行・検証
    with pytest.raises(OptionNotFoundError) as exc_info:
        commands.switch_adopted(item, "Z")
    message = str(exc_info.value)
    assert "Z" in message
    assert "A" in message
    assert "B" in message


def test_run_init(tmp_path: Path, valid_settings: dict[str, Any], scripts_dir: Path) -> None:
    """作ったワークスペースとファイルを返す（正常系）。"""
    # 準備
    root = tmp_path / "ws"
    plugin_version = (scripts_dir.parents[2] / "version.ini").read_text(encoding="utf-8")
    # 実行
    payload = commands.run_init(root, valid_settings)
    # 検証
    assert payload["workspace"] == str(root)
    assert len(payload["files"]) == 11
    assert (root / "mindstella-version.ini").read_text(
        encoding="utf-8"
    ) == f"{plugin_version.splitlines()[0]}\n"


def test_run_add(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """本文つきの検討事項を足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    item = {"title": "問い", "status": "未決定", "body_markdown": "## 経緯\n"}
    # 実行
    payload = commands.run_add(root, "decision", item, now=_fixed_now)
    # 検証
    assert payload == {"id": "D-2", "file": "decisions.yaml", "body": "docs/D-2.md"}
    added = _read_items(root, "decisions.yaml")[1]
    assert added["created"] == FIXED_NOW
    assert added["updated"] == FIXED_NOW
    assert added["body"] == "D-2.md"
    assert "body_markdown" not in added
    assert (root / "docs" / "D-2.md").read_text(encoding="utf-8") == "## 経緯\n"


def test_run_add_when_no_body(make_workspace: MakeWorkspace) -> None:
    """本文が無ければ body を付けない（正常系）。"""
    # 準備
    root = make_workspace()
    item = {"title": "作業", "kind": "作業", "status": "未着手"}
    # 実行
    payload = commands.run_add(root, "task", item, now=_fixed_now)
    # 検証
    assert payload == {"id": "T-1", "file": "tasks.yaml", "body": None}
    assert "body" not in _read_items(root, "tasks.yaml")[0]


def test_run_update(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """キーを置き換えて更新日時を変える（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", lead="l", weight="大"))
    # 実行
    payload = commands.run_update(root, "D-1", {"answer": "a", "weight": None}, now=_fixed_now)
    # 検証
    assert payload == {
        "id": "D-1",
        "file": "decisions.yaml",
        "changed": ["answer", "weight"],
    }
    updated = _read_items(root, "decisions.yaml")[0]
    assert updated["answer"] == "a"
    assert "weight" not in updated
    assert updated["lead"] == "l"
    assert updated["created"] == DEFAULT_TIMESTAMP
    assert updated["updated"] == FIXED_NOW


def test_run_adopt(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """切り替えて書き込む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            options=[
                {"key": "A", "content": "案 A", "adopted": True},
                {"key": "B", "content": "案 B", "adopted": False},
            ],
        )
    )
    # 実行
    payload = commands.run_adopt(root, "D-1", "B", now=_fixed_now)
    # 検証
    assert payload == {"id": "D-1", "adopted": "B", "previous": "A"}
    options = _read_items(root, "decisions.yaml")[0]["options"]
    assert options[0]["adopted"] is False
    assert options[1]["adopted"] is True


def test_run_adopt_when_not_decision(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """検討事項でない ID は切り替えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("T-1"))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="T-1"):
        commands.run_adopt(root, "T-1", "A", now=_fixed_now)


def test_run_check(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """問題が無ければ ok（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    payload = commands.run_check(root)
    # 検証
    assert payload == {"ok": True, "problems": []}


def test_run_check_when_problems(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """問題があれば ok が偽（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", depends_on=["D-9"]))
    # 実行
    payload = commands.run_check(root)
    # 検証
    assert payload["ok"] is False
    assert len(payload["problems"]) == 1


def test_run_check_when_legacy_format(make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """前の版の形式の問題に /mindstella:upgrade を案内する（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True})
    # 実行
    payload = commands.run_check(root)
    # 検証
    assert payload["ok"] is False
    details = [problem["detail"] for problem in payload["problems"] if problem["id"] == "A-1"]
    assert details != []
    assert all(
        detail.endswith("（/mindstella:upgrade で今の形式に移せます）") for detail in details
    )


def test_run_impact(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """影響を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("D-2", title="依存する問い", depends_on=["D-1"])
    )
    # 実行
    payload = commands.run_impact(root, "D-1")
    # 検証
    assert payload == {
        "id": "D-1",
        "affected": [
            {
                "id": "D-2",
                "title": "依存する問い",
                "status": "未決定",
                "via": [],
                "key": "depends_on",
            }
        ],
    }


def test_run_next(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """候補を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    # 実行
    payload = commands.run_next(root, None)
    # 検証
    assert payload == {
        "candidates": [
            {
                "id": "D-1",
                "title": "最初の問い",
                "phase": None,
                "weight": None,
                "followers": 0,
            }
        ]
    }


def test_run_next_when_limit_invalid(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """1 未満の limit は引数の誤り（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行・検証
    with pytest.raises(ArgumentError, match="limit"):
        commands.run_next(root, 0)


def test_run_status(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """状況を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="見直しの問い", status="要見直し"))
    # 実行
    payload = commands.run_status(root)
    # 検証
    assert payload["needs_review"] == [{"id": "D-1", "title": "見直しの問い"}]
    assert {"in_progress", "resumable", "waiting", "on_hold", "next"} <= set(payload)


def test_run_find(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """検索結果を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    # 実行
    payload = commands.run_find(root, SearchFilter())
    # 検証
    assert payload == {
        "items": [{"id": "D-1", "kind": "decision", "title": "最初の問い", "status": "未決定"}]
    }


def test_run_show(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """1 件を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    payload = commands.run_show(root, "D-1")
    # 検証
    assert set(payload) == {"item", "kind", "body_markdown", "referenced_by"}


def test_run_attrs(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """属性名を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", attrs={"担当": "自分"}))
    # 実行
    payload = commands.run_attrs(root)
    # 検証
    assert payload == {"attrs": [{"name": "担当", "count": 1, "kinds": ["decision"]}]}


def test_run_goal(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """判定を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", phase="目的", status="未決定"))
    # 実行
    payload = commands.run_goal(root)
    # 検証
    assert payload["reached"] is False
    assert {
        "goal_phase",
        "phases",
        "remaining_decisions",
        "remaining_deliverables",
    } <= set(payload)


def test_run_migrate(
    make_legacy_workspace: MakeLegacyWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """手順を並べて出力の形にする（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    patch_plugin_version("v0.3.0")
    # 実行
    payload = commands.run_migrate(
        root, plan=True, record=False, values=None, from_version=None, to_version=None
    )
    # 検証
    assert payload["workspace_version"] is None
    assert payload["plugin_version"] == "v0.3.0"
    assert payload["relation"] == "older"
    assert payload["steps"][0] == {
        "version": "v0.3.0",
        "index": 1,
        "op": "rename_key",
        "destructive": False,
        "summary": "docs.yaml の items[].done を status に名前を変える",
    }
    assert payload["needs_values"] == [
        {"file": "mindmap.yaml", "key": "summary", "description": "話し合いの題名"}
    ]
    assert payload["backup"] is None


def test_run_migrate_when_values(
    make_legacy_workspace: MakeLegacyWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """values の値を入れて並べ直す（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    patch_plugin_version("v0.3.0")
    values = [{"file": "mindmap.yaml", "key": "summary", "value": "題名"}]
    # 実行
    payload = commands.run_migrate(
        root, plan=False, record=False, values=values, from_version=None, to_version=None
    )
    # 検証
    assert payload["steps"] == []
    assert payload["needs_values"] == []
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == "題名"


@pytest.mark.parametrize(
    ("kwargs", "expected_argument"),
    [
        pytest.param({"plan": True, "record": True}, "plan", id="plan_and_record"),
        pytest.param({"to_version": "0.3"}, "to_version", id="version_form"),
        pytest.param(
            {"from_version": "v0.3.0", "to_version": "v0.2.0"}, "to_version", id="reversed"
        ),
        pytest.param({"values": [{"file": "mindmap.yaml"}]}, "values", id="values_form"),
    ],
)
def test_run_migrate_when_argument_invalid(
    make_legacy_workspace: MakeLegacyWorkspace,
    patch_plugin_version: PatchPluginVersion,
    snapshot_tree: SnapshotTree,
    kwargs: dict[str, Any],
    expected_argument: str,
) -> None:
    """一緒に使わない引数・版の形の誤り・形の違う values は引数の誤り（異常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    patch_plugin_version("v0.3.0")
    before = snapshot_tree(root)
    arguments: dict[str, Any] = {
        "plan": False,
        "record": False,
        "values": None,
        "from_version": None,
        "to_version": None,
    }
    arguments.update(kwargs)
    # 実行・検証
    with pytest.raises(ArgumentError, match=expected_argument):
        commands.run_migrate(root, **arguments)
    assert snapshot_tree(root) == before


def test_run_clear_release(make_workspace: MakeWorkspace) -> None:
    """release/ の中を消し、消したものを返す（正常系）。"""
    # 準備
    root = make_workspace()
    (root / "release" / "古い資料.md").write_text("古い\n", encoding="utf-8")
    # 実行
    payload = commands.run_clear_release(root)
    # 検証
    assert payload == {"removed": ["古い資料.md"]}


def _patch_export_offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """配る書き出しを、通信せず小さな雛形と取る中身を差し込んだものに差し替える。"""
    # 差し替える前の本物を控える
    real_export = builder.export_preview
    scripts = [("marked", b"/* marked */")]
    preview_dir = tmp_path / "preview"
    write_preview_dir(preview_dir, external_template(scripts))
    fetch, _calls = make_fetch(make_responses(scripts))

    def _export_offline(workspace: Any, **kwargs: Any) -> Path:
        """雛形のフォルダと取る関数だけを差し替えて、本物の書き出しを呼ぶ。"""
        return real_export(workspace, **{**kwargs, "preview_dir": preview_dir, "fetch": fetch})

    # 書き出しのモジュールの関数と、ツールの処理が名前で取り込んだ関数の両方を差し替える
    monkeypatch.setattr(builder, "export_preview", _export_offline)
    monkeypatch.setattr(commands, "export_preview", _export_offline, raising=False)


def test_run_export(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """配る書き出しを書いてそのパスを返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    _patch_export_offline(monkeypatch, tmp_path)
    # 実行
    payload = commands.run_export(root, out, now=_fixed_now)
    # 検証
    assert payload == {"path": str(out)}
    assert out.exists()


def test_run_export_when_out_invalid(tmp_path: Path) -> None:
    """.html で終わらない out はワークスペースを読む前に弾く（異常系）。"""
    # 準備
    root = tmp_path / "空のフォルダ"
    root.mkdir()
    # 実行・検証
    with pytest.raises(ArgumentError, match="out"):
        commands.run_export(root, root / "配る.txt", now=_fixed_now)


def test_run_preview_url(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """台帳の結果を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    previews = _FakeRegistry()
    # 実行
    payload = commands.run_preview_url(root, previews=previews)
    # 検証
    assert payload == {"url": "http://127.0.0.1:1/", "workspace": str(root), "started": True}
    assert previews.started == [root]


def test_run_preview_url_when_not_workspace(tmp_path: Path) -> None:
    """ワークスペースでなければ配信を立てない（異常系）。"""
    # 準備
    previews = _FakeRegistry()
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError):
        commands.run_preview_url(tmp_path, previews=previews)
    assert previews.started == []


def test_run_submissions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """取り込んでいない送信を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    no_target = make_submission("S-3", body="全体に目を通した")
    del no_target["target"]
    write_submissions(
        root,
        make_submission("S-1", taken="2026-10-03T00:00:00+00:00"),
        make_submission("S-2", body="案 A にする"),
        no_target,
    )
    # 実行
    payload = commands.run_submissions(root)
    # 検証
    assert payload == {
        "items": [
            {
                "id": "S-2",
                "target": "D-1",
                "target_title": "最初の問い",
                "loc": None,
                "body": "案 A にする",
                "sent": DEFAULT_TIMESTAMP,
            },
            {
                "id": "S-3",
                "target": None,
                "target_title": None,
                "loc": None,
                "body": "全体に目を通した",
                "sent": DEFAULT_TIMESTAMP,
            },
        ]
    }


def test_run_take_submission(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """取り込んだ日時を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    # 実行
    payload = commands.run_take_submission(root, "S-1", now=_submission_now)
    # 検証
    assert payload == {"id": "S-1", "taken": SUBMISSION_NOW, "already": False}
