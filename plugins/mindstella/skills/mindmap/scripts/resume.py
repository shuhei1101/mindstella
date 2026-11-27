"""MindStella のセッションの SessionStart のフックが呼ぶ再開の状況と、その注入文を組み立てる（何も書かない）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2
import yaml
from history import Changes, load_changes, load_item_history, merge_item_history, removed_items
from kinds import KINDS, id_number
from read_point import load_migration_report, load_read_seq
from store import Workspace, load_workspace
from threads import awaiting_posts, load_threads

# `changed`・`removed`・`needs_review`・`in_progress` のそれぞれの上限
SUMMARY_LIMIT = 20

# SessionStart の注入文のプロンプトファイル
PROMPT_FILE = Path(__file__).resolve().parents[3] / "content" / "prompts" / "session-start.yaml"


def summarize_resume(root: Path, source: str, *, state_root: Path | None = None) -> dict[str, Any]:
    """再開の状況の応答の辞書を組み立てる（前回参照した時点も移し替えの報告も書き換えない）。"""
    workspace = load_workspace(root)
    record = load_changes(root)
    read_seq = load_read_seq(root, state_root=state_root)
    changed, removed = _changes_after(workspace, record, read_seq)
    needs_review = _rows(workspace.items["decision"], "要見直し")
    in_progress = _rows(workspace.items["task"], "進行中")
    awaiting = sum(1 for thread in load_threads(root) if awaiting_posts(thread))
    # 利用者がプレビューで案を選んだ検討事項（件数だけ。中身は user_choices で取得する）
    chosen = sum(1 for item in workspace.items["decision"] if "user_choice" in item)
    status: dict[str, Any] = {
        # startup だけを起動、それ以外（resume・clear・compact）を再開にする
        "trigger": "startup" if source == "startup" else "resume",
        "awaiting_threads": awaiting,
        "user_choices": chosen,
    }
    for key, rows in (
        ("changed", changed),
        ("removed", removed),
        ("needs_review", needs_review),
        ("in_progress", in_progress),
    ):
        status[key] = rows[:SUMMARY_LIMIT]
        status[f"{key}_more"] = max(len(rows) - SUMMARY_LIMIT, 0)
    status["flow"] = workspace.settings.get("flow")
    status["migration"] = load_migration_report(root, state_root=state_root)
    status["until_seq"] = record["last_seq"]
    status["context"] = render_context(status)
    return status


def render_context(status: dict[str, Any], *, prompt_file: Path = PROMPT_FILE) -> str:
    """プロンプトファイルの `lang` の本文のうち `when` が真の部品を、並び順に描いて空行でつなぐ。"""
    prompt = yaml.safe_load(prompt_file.read_text(encoding="utf-8"))
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined, autoescape=False, keep_trailing_newline=True
    )
    lang = prompt["lang"]
    rendered: list[str] = []
    for part in prompt["parts"]:
        when = part.get("when")
        # 条件を持ち、偽: この部品を使わない
        if when is not None and not env.compile_expression(_expression_of(when))(**status):
            continue
        text = next(entry["text"] for entry in part["texts"] if entry["lang"] == lang)
        rendered.append(env.from_string(text).render(**status).strip())
    return "\n\n".join(rendered)


def _expression_of(when: str) -> str:
    """`when` の `{{ 式 }}` から式を取り出す（括弧の無い式はそのまま）。"""
    stripped = when.strip()
    if stripped.startswith("{{") and stripped.endswith("}}"):
        return stripped[2:-2].strip()
    return stripped


def _changes_after(
    workspace: Workspace, record: Changes, read_seq: int | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """前回参照した時点より後に足した・変えた項目と、後で削除した項目を返す（時点が無ければどちらも空）。"""
    if read_seq is None:
        return [], []
    rows = load_item_history(workspace.root)
    merged = [
        (kind, merge_item_history(item, rows)) for kind in KINDS for item in workspace.items[kind]
    ]
    added = [(kind, item) for kind, item in merged if item.get("added_seq", 0) > read_seq]
    updated = [
        (kind, item)
        for kind, item in merged
        if item.get("added_seq", 0) <= read_seq and item.get("seq", 0) > read_seq
    ]
    changed = [
        {
            "id": item["id"],
            "kind": kind,
            "title": item["title"],
            "updated_by": item.get("updated_by"),
        }
        for kind, item in [*added, *updated]
    ]
    removed = [
        {"id": entry["id"], "kind": entry["kind"], "title": entry["title"]}
        for entry in removed_items(record)
        if entry["seq"] > read_seq and entry["added_seq"] <= read_seq
    ]
    return changed, removed


def _rows(items: list[dict[str, Any]], status: str) -> list[dict[str, str]]:
    """その状態の項目を、連番の順に `{id, title}` で返す。"""
    return [
        {"id": item["id"], "title": str(item.get("title", ""))}
        for item in sorted(items, key=lambda item: id_number(item["id"]))
        if item.get("status") == status
    ]
