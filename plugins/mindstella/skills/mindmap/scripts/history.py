"""項目の変更履歴の 1 回分・本文の差分・書き換えのまとまり（`changes.yaml`）・前回開いた日時（`.mindstella-opened`）。

書き込みは呼ぶ側が `save_change` などに任せる。鍵も呼ぶ側が取る。
"""

from __future__ import annotations

import difflib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

import yaml
from errors import ItemNotFoundError, SchemaMismatchError
from jsonschema import Draft202012Validator
from kinds import KINDS, Kind, records_root
from store import (
    CHANGES_FILE,
    SCHEMA_DIR,
    WHOLE_PATH,
    Workspace,
    find_item,
    format_path,
    read_body,
    remove_files,
    write_failed,
    write_temp,
)

__all__ = [
    "CHANGES_FILE",
    "CHANGES_SCHEMA",
    "DEFAULT_HISTORY_LIMIT",
    "OPENED_FILE",
    "SET_ID_PREFIX",
    "SUMMARY_MAX_LENGTH",
    "BodyDiffHunk",
    "ChangeSet",
    "Changes",
    "HistoryEntry",
    "Pending",
    "RemovedItem",
    "advance_seq",
    "apply_body_diff",
    "changes_since",
    "commit_pending",
    "diff_body",
    "history_limit",
    "load_changes",
    "make_entry",
    "mark_read",
    "note_pending",
    "note_removed",
    "pending_view",
    "removed_items",
    "stack_history",
    "touch_opened",
    "values_at_read",
]

# `SCHEMA_DIR` の下の、`changes.yaml` を検証するスキーマのファイル名
CHANGES_SCHEMA = "changes.schema.json"

# プレビューを最後に開いた日時を持つファイルの名前（`records_root` の下）
OPENED_FILE = ".mindstella-opened"

# `config.yaml` に `history_limit` が無いときの回数
DEFAULT_HISTORY_LIMIT = 5

# まとまりの ID の頭の文字
SET_ID_PREFIX = "V-"

# `commit` の `summary` の前後の空白を除いた文字数の上限
SUMMARY_MAX_LENGTH = 200

# 変更履歴の `before` に入れない、ツールが付けるキー（本文は `body_diff` で持つ）
NON_HISTORY_KEYS = frozenset(
    {"updated", "updated_by", "history", "history_dropped_seq", "seq", "added_seq", "body"}
)

# 前に本文が無かった回の、`before` に入れる本文のキー
BODY_KEY = "body"

# `pending_view` が、本文を変えたことを表すキーの名前
BODY_MARKDOWN_KEY = "body_markdown"


class BodyDiffHunk(TypedDict):
    """書き換えた後の本文のある行からの並びを、前の行の並びに置き換える 1 か所。"""

    # 書き換えた後の本文の 1 始まりの行。`now` が空のときはその行の前に差し込む
    line: int
    # その行からの今の行（改行を含まない）
    now: list[str]
    # 置き換える前の行
    before: list[str]


class HistoryEntry(TypedDict):
    """項目の `history` の 1 要素。"""

    seq: int
    at: str
    # その回を書き換えた人。このキーを入れる前に積んだ回は持たない
    by: NotRequired[Literal["ai", "user"]]
    # 変わったキー → 書き換える前の値。前に無かったキーは `None`
    before: dict[str, Any]
    # 今の本文を前の本文へ戻す行の置き換えの並び（本文が変わったときだけ）
    body_diff: NotRequired[list[BodyDiffHunk]]


class RemovedItem(TypedDict):
    """`changes.yaml` の `pending.removed`・`sets[].removed` の 1 要素。"""

    # 消した項目の ID
    id: str
    # 消した項目の種類
    kind: Kind
    # 消したときのタイトル
    title: str
    # 消したときに振った通し番号
    seq: int
    # 消した項目が持っていた `added_seq`（持たなければ 0）
    added_seq: int


class ChangeSet(TypedDict):
    """`changes.yaml` の `sets` の 1 要素。"""

    id: str
    at: str
    summary: str
    until_seq: int
    added: list[str]
    changed: list[str]
    # 消した項目。消した項目が無いまとまりはキーを持たない
    removed: NotRequired[list[RemovedItem]]


class Pending(TypedDict):
    """`changes.yaml` の `pending`。"""

    # 足した項目の ID（書き換えた順）
    added: list[str]
    # 変えた項目の ID（書き換えた順。足した項目は入れない）
    changed: list[str]
    # 消した項目（消した順）。無ければ消した項目なし
    removed: NotRequired[list[RemovedItem]]


class Changes(TypedDict):
    """`changes.yaml` の中身。書き換える関数は受け取ったものを書き換えず、新しいものを返す。"""

    last_seq: int
    sets: list[ChangeSet]
    pending: Pending
    # AI が最後に読んだ時点。`changes_since_read` を一度も呼んでいなければキーが無い
    read_seq: NotRequired[int]


def load_changes(root: Path) -> Changes:
    """`changes.yaml` を読んでスキーマと突き合わせる。無ければ空の記録を返す。"""
    path = records_root(root) / CHANGES_FILE
    # ファイルが無い: まとまり 0 件・まだまとめていない変更なしとして扱う
    if not path.is_file():
        return {"last_seq": 0, "sets": [], "pending": {"added": [], "changed": []}}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        # YAML として読めない: 全体の問題として送る
        reason = " ".join(str(error).split())
        raise SchemaMismatchError(
            [f"{CHANGES_FILE}: {WHOLE_PATH}: YAML として読めません: {reason}"]
        ) from error
    schema = json.loads((SCHEMA_DIR / CHANGES_SCHEMA).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    # スキーマに合わない: 合わない箇所ごとの行を持って送る
    if errors:
        raise SchemaMismatchError(
            [
                f"{CHANGES_FILE}: {format_path(error.absolute_path)}: {error.message}"
                for error in errors
            ]
        )
    return value


def history_limit(settings: dict[str, Any]) -> int:
    """設定の `history_limit` を返す。無ければ `DEFAULT_HISTORY_LIMIT`。"""
    return int(settings.get("history_limit", DEFAULT_HISTORY_LIMIT))


def diff_body(before: str, after: str) -> list[BodyDiffHunk]:
    """書き換えた後の本文を前の本文へ戻す、行の置き換えの並びを作る。"""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    # 突き合わせの目印に何度も現れる行（空行など）を使わない既定のまま使う: 大きな書き換えでも長くかからない
    matcher = difflib.SequenceMatcher(None, after_lines, before_lines)
    return [
        {"line": i1 + 1, "now": after_lines[i1:i2], "before": before_lines[j1:j2]}
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    ]


def apply_body_diff(text: str, hunks: list[BodyDiffHunk]) -> str | None:
    """本文に差分を後ろの箇所から当てて前の本文にする。`now` が当てる先の行と合わなければ `None`。"""
    lines = text.splitlines()
    for hunk in sorted(hunks, key=lambda entry: entry["line"], reverse=True):
        start = hunk["line"] - 1
        end = start + len(hunk["now"])
        # 当てる先の行が今の本文の範囲を出るか、`now` と違う
        if end > len(lines) or lines[start:end] != hunk["now"]:
            return None
        lines[start:end] = hunk["before"]
    return "\n".join(lines) + "\n" if lines else ""


def make_entry(
    before_item: dict[str, Any],
    after_item: dict[str, Any],
    *,
    before_body: str | None,
    after_body: str | None,
    seq: int,
    at: str,
    by: Literal["ai", "user"],
) -> HistoryEntry | None:
    """書き換える前と後の項目と本文を比べ、変わったものがあれば 1 回分を作る。"""
    keys = [
        key for key in dict.fromkeys([*before_item, *after_item]) if key not in NON_HISTORY_KEYS
    ]
    # 値が違う・消えた・足したキーを、書き換える前の値（前に無ければ None）で持つ
    before = {
        key: before_item.get(key)
        for key in keys
        if (key in before_item) != (key in after_item)
        or before_item.get(key) != after_item.get(key)
    }
    body_diff: list[BodyDiffHunk] = []
    if before_body is None and after_body is not None:
        # 本文を初めて足した回
        before[BODY_KEY] = None
    elif before_body is not None and after_body is not None and before_body != after_body:
        body_diff = diff_body(before_body, after_body)
    # 前後の body の名前が違う（資料の本文の形式を替えた）回は、前の名前を持つ
    before_name = before_item.get(BODY_KEY)
    if before_name is not None and after_item.get(BODY_KEY) not in (None, before_name):
        before[BODY_KEY] = before_name
    # 変わったキーも本文も無い
    if not before and not body_diff:
        return None
    entry: HistoryEntry = {"seq": seq, "at": at, "by": by, "before": before}
    if body_diff:
        entry["body_diff"] = body_diff
    return entry


def stack_history(
    item: dict[str, Any], entry: HistoryEntry | None, limit: int, *, read_seq: int | None
) -> dict[str, Any]:
    """項目の `history` の先頭に 1 回分を足し、保持する回数を超えた古いものを消して、消した回の最大の `seq` を `history_dropped_seq` に残した新しい項目を返す。"""
    # 保持する回数が 0: 変更履歴を持たない
    if limit == 0:
        return {
            key: value for key, value in item.items() if key not in ("history", "history_dropped_seq")
        }
    # 積むものが無い
    if entry is None:
        return item
    stacked = [entry, *item.get("history", [])]
    # 先頭から保持する回数までと、AI がまだ読んでいない回（`read_seq` より後）は消さない
    kept = [
        old
        for position, old in enumerate(stacked)
        if position < limit or (read_seq is not None and old["seq"] > read_seq)
    ]
    dropped = [old for old in stacked if old not in kept]
    result = {**item, "history": kept}
    # 消した回があれば、その最大の seq と今の history_dropped_seq の大きい方を残す
    if dropped:
        result["history_dropped_seq"] = max(
            item.get("history_dropped_seq", 0), *(old["seq"] for old in dropped)
        )
    return result


def note_pending(
    changes: Changes, item_id: str, kind: Literal["added", "changed"]
) -> Changes:
    """まだまとめていない変更に ID を足した新しい記録を返す（通し番号は進めない。進めるのは `advance_seq`）。"""
    # 消した項目の記録はそのまま引き継ぐ
    pending: Pending = {
        **changes["pending"],
        "added": list(changes["pending"]["added"]),
        "changed": list(changes["pending"]["changed"]),
    }
    # 足した項目は、変えても changed に入れない。同じ ID は二度足さない
    already = item_id in pending["added"] or (kind == "changed" and item_id in pending["changed"])
    if not already:
        pending[kind].append(item_id)
    return {**changes, "pending": pending}


def note_removed(changes: Changes, removed: RemovedItem) -> Changes:
    """`pending.added`・`pending.changed` から消した ID を除き、`pending.removed` の末尾に消した項目を足した新しい記録を返す（通し番号は進めない。進めるのは `advance_seq`）。"""
    pending = changes["pending"]
    return {
        **changes,
        "pending": {
            "added": [item_id for item_id in pending["added"] if item_id != removed["id"]],
            "changed": [item_id for item_id in pending["changed"] if item_id != removed["id"]],
            # まとめる前に足した項目も、消した ID を振り直さないために記録する
            "removed": [*pending.get("removed", []), removed],
        },
    }


def removed_items(changes: Changes) -> list[RemovedItem]:
    """`sets[].removed` と `pending.removed` の記録を、消した順（`seq` の小さい順）に並べて返す。"""
    collected = [
        removed
        for change_set in changes["sets"]
        for removed in change_set.get("removed", [])
    ]
    collected.extend(changes["pending"].get("removed", []))
    return sorted(collected, key=lambda removed: removed["seq"])


def advance_seq(changes: Changes) -> tuple[Changes, int]:
    """`last_seq` を 1 進めた新しい記録と、振った番号を返す。"""
    seq = changes["last_seq"] + 1
    return {**changes, "last_seq": seq}, seq


def commit_pending(changes: Changes, summary: str, at: str) -> tuple[Changes, ChangeSet | None]:
    """まだまとめていない変更を 1 つのまとまりにした新しい記録と、足したまとまりを返す。"""
    pending = changes["pending"]
    pending_removed = pending.get("removed", [])
    # まとめるものが無い
    if not pending["added"] and not pending["changed"] and not pending_removed:
        return changes, None
    numbers = [int(entry["id"].removeprefix(SET_ID_PREFIX)) for entry in changes["sets"]]
    change_set: ChangeSet = {
        "id": f"{SET_ID_PREFIX}{max(numbers, default=0) + 1}",
        "at": at,
        "summary": summary,
        "until_seq": changes["last_seq"],
        "added": list(pending["added"]),
        "changed": list(pending["changed"]),
    }
    # 消した項目があるときだけ、まとまりに写す
    if pending_removed:
        change_set["removed"] = list(pending_removed)
    committed: Changes = {
        **changes,
        "sets": [change_set, *changes["sets"]],
        "pending": {"added": [], "changed": []},
    }
    return committed, change_set


def pending_view(workspace: Workspace, changes: Changes) -> dict[str, Any]:
    """まだまとめていない項目を、タイトルと変えたキーつきで返し、消した項目も並べる（`pending` のツールの結果の形）。"""
    sets = changes["sets"]
    # 最後のまとまりより後の変更履歴だけが、まだまとめていない分
    floor = sets[0]["until_seq"] if sets else 0
    added = [
        {"id": item_id, "title": item["title"]}
        for item_id, item in _existing_items(workspace, changes["pending"]["added"])
    ]
    changed = []
    for item_id, item in _existing_items(workspace, changes["pending"]["changed"]):
        keys: list[str] = []
        for entry in item.get("history", []):
            if entry["seq"] <= floor:
                continue
            keys.extend(entry["before"])
            # 本文を変えた回は、本文のキーも並べる
            if "body_diff" in entry:
                keys.append(BODY_MARKDOWN_KEY)
        changed.append({"id": item_id, "title": item["title"], "keys": list(dict.fromkeys(keys))})
    removed = [
        {"id": entry["id"], "kind": entry["kind"], "title": entry["title"]}
        for entry in changes["pending"].get("removed", [])
    ]
    return {"added": added, "changed": changed, "removed": removed}


def values_at_read(
    item: dict[str, Any], body: str | None, read_seq: int
) -> tuple[dict[str, Any], list[BodyDiffHunk] | None]:
    """読んだ時点より後に変わったキーの読んだ時点の値と、今の本文を読んだ時点の本文へ戻す差分を組み立てる。"""
    # 読んだ時点より後の回（新しい順）
    entries = [entry for entry in item.get("history", []) if entry["seq"] > read_seq]
    before: dict[str, Any] = {}
    # 新しい回から重ね、同じキーは古い回の値で上書きする（最も古い回の値が読んだ時点の値）
    for entry in entries:
        before.update(entry["before"])
    # 今の項目と同じ値に戻っているキーは、変わっていないので返さない
    before = {key: value for key, value in before.items() if item.get(key) != value}
    body_diff: list[BodyDiffHunk] | None = None
    if body is not None:
        text: str | None = body
        # 本文を変えた回を新しい順に当てて、読んだ時点の本文を作る
        for entry in entries:
            if text is not None and "body_diff" in entry:
                text = apply_body_diff(text, entry["body_diff"])
        # 作れて、今の本文と違うときだけ差分にする
        if text is not None and text != body:
            body_diff = diff_body(text, body)
    return before, body_diff


def changes_since(workspace: Workspace, changes: Changes) -> dict[str, Any]:
    """AI が最後に読んだ時点より後に足した・変えた・消した項目を、`changes_since_read` の結果の形に並べる。"""
    read_seq = changes.get("read_seq")
    # 読んだ時点の記録が無い: 差分を返さない
    if read_seq is None:
        return {
            "had_read_point": False,
            "read_seq": None,
            "until_seq": changes["last_seq"],
            "added": [],
            "changed": [],
            "removed": [],
        }
    limit = history_limit(workspace.settings)
    added: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    for kind in KINDS:
        for item in workspace.items[kind]:
            # 読んだ時点より後に足した項目
            if item.get("added_seq", 0) > read_seq:
                added.append(
                    {
                        "id": item["id"],
                        "kind": kind,
                        "title": item["title"],
                        "updated_by": item.get("updated_by"),
                    }
                )
                continue
            # 読んだ時点より後に変えていない項目
            if item.get("seq", 0) <= read_seq:
                continue
            before: dict[str, Any] | None = None
            body_diff: list[BodyDiffHunk] | None = None
            # 保持する回数が 0 のときは変更履歴が無いので、前の値を組み立てない
            if limit > 0:
                name = item.get("body")
                body = read_body(workspace, name) if isinstance(name, str) else None
                before, body_diff = values_at_read(item, body, read_seq)
                # 変わったキーも本文の差分も残らない項目は返さない
                if not before and body_diff is None:
                    continue
            changed.append(
                {
                    "id": item["id"],
                    "kind": kind,
                    "title": item["title"],
                    "updated_by": item.get("updated_by"),
                    "by": _editors_since(item, read_seq) if limit > 0 else [],
                    "before": before,
                    "body_diff": body_diff,
                }
            )
    # 読んだ時点に有って、後で消した項目（読んだ後に足して消した項目は、読んだ時点にも今にも無いので返さない）
    removed = [
        {"id": entry["id"], "kind": entry["kind"], "title": entry["title"]}
        for entry in removed_items(changes)
        if entry["seq"] > read_seq and entry["added_seq"] <= read_seq
    ]
    return {
        "had_read_point": True,
        "read_seq": read_seq,
        "until_seq": changes["last_seq"],
        "added": added,
        "changed": changed,
        "removed": removed,
    }


def _editors_since(item: dict[str, Any], read_seq: int) -> list[str]:
    """読んだ時点より後の変更履歴の回を書き換えた人を、重なりなく `user`・`ai` の順で返す（`by` を持たない回は数えない）。"""
    editors = {
        entry["by"]
        for entry in item.get("history", [])
        if entry["seq"] > read_seq and "by" in entry
    }
    return [editor for editor in ("user", "ai") if editor in editors]


def mark_read(changes: Changes) -> Changes:
    """`read_seq` を `last_seq` にした新しい記録を返す。"""
    return {**changes, "read_seq": changes["last_seq"]}


def touch_opened(root: Path, now: str) -> str | None:
    """前回開いた日時を読み、今の日時に書き換えて、前の日時を返す。"""
    path = records_root(root) / OPENED_FILE
    previous = _read_opened(path)
    try:
        temp = write_temp(path, f"{now}\n")
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        remove_files([temp])
        raise write_failed(path, error) from error
    return previous


def _existing_items(workspace: Workspace, ids: list[str]) -> list[tuple[str, dict[str, Any]]]:
    """ID の並びのうち、ワークスペースに項目があるものを、ID と項目の組にする。"""
    found: list[tuple[str, dict[str, Any]]] = []
    for item_id in ids:
        try:
            found.append((item_id, find_item(workspace, item_id).item))
        except ItemNotFoundError:
            # 消えた項目は並べない（点検が参照切れとして知らせる）
            continue
    return found


def _read_opened(path: Path) -> str | None:
    """前回開いた日時のファイルの 1 行目を返す。無いか、日時として読めなければ `None`。"""
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    first = lines[0].strip() if lines else ""
    try:
        datetime.fromisoformat(first)
    except ValueError:
        return None
    return first
