"""ツールごとの処理（引数 → 各機能 → 結果の辞書）。"""

from __future__ import annotations

import os
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from builder import export_preview, validate_export_out
from checker import check_workspace
from errors import (
    ArgumentError,
    ItemNotFoundError,
    OptionNotFoundError,
    SchemaMismatchError,
    WorkspaceNotFoundError,
)
from graph import judge_goal, list_next_candidates, summarize_status, trace_impact
from history import (
    SUMMARY_MAX_LENGTH,
    Changes,
    commit_pending,
    history_limit,
    load_changes,
    make_entry,
    note_pending,
    pending_view,
    stack_history,
)
from kinds import KINDS, SETTINGS_FILE, Kind
from migration_ops import DESTRUCTIVE_OPS, describe_step
from migrator import MigrationReport, apply_migration, plan_migration, record_version, set_values
from query import SearchFilter, list_attrs, search_items, show_item
from serve import PreviewRegistry
from settings_update import update_settings
from store import (
    CHANGES_FILE,
    BodyWrite,
    Change,
    NowFn,
    Workspace,
    clear_release,
    create_workspace,
    dump_yaml,
    find_item,
    is_legacy_problem,
    load_workspace,
    next_id,
    now_utc,
    read_body,
    remove_files,
    save_change,
    write_failed,
    write_temp,
)
from submissions import list_pending_submissions, take_submission
from versions import Version, parse_release_version, read_plugin_version

# 前の版の形式の問題の詳細に続ける案内
MIGRATE_HINT = "（/mindstella:upgrade で今の形式に移せます）"

# `item` で渡させない、ツールが付けるキー
RESERVED_KEYS = ("id", "created", "updated", "body", "history", "history_dropped_seq")

# `item` で本文の Markdown を渡すキー（YAML には残さない）
BODY_INPUT_KEY = "body_markdown"

# 項目の中身のエラーの行に付けるファイル名の代わり
ITEM_NAME = "item"

# `values` の 1 要素が持つ、文字列で渡させるキー
VALUE_KEYS = ("file", "key", "value")


def validate_input_keys(kind: Kind, data: dict[str, Any]) -> None:
    """ツールが付けるキーと、本文を持てない種類への `body_markdown` を弾く。"""
    lines = [f"{ITEM_NAME}: {key}: ツールが付けるキーです" for key in RESERVED_KEYS if key in data]
    # 本文を持てない種類に本文を渡した
    if BODY_INPUT_KEY in data and not KINDS[kind].has_body:
        lines.append(f"{ITEM_NAME}: {BODY_INPUT_KEY}: この種類は本文を持てません")
    if lines:
        raise SchemaMismatchError(lines)


def merge_changes(
    item: dict[str, Any], changes: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """渡したキーを値ごと置き換え、`None` のキーを消した新しい項目と、変わったキーを返す。"""
    merged = dict(item)
    changed: list[str] = []
    for key, value in changes.items():
        # 値が None: キーがあれば消す
        if value is None:
            if key in merged:
                del merged[key]
                changed.append(key)
        # 元の値と違う（新しいキーを含む）: 置き換える（新しいキーは末尾に足される）
        elif key not in merged or merged[key] != value:
            merged[key] = value
            changed.append(key)
    return merged, changed


def switch_adopted(item: dict[str, Any], key: str) -> tuple[dict[str, Any], str | None]:
    """指定した記号の案だけを採用にした新しい項目と、それまで採用していた案の記号を返す。"""
    options = [option for option in item.get("options") or [] if isinstance(option, dict)]
    keys = [str(option.get("key")) for option in options]
    # 検討事項がその記号の案を持たない
    if key not in keys:
        raise OptionNotFoundError(f"案がありません: {key}（持っている案: {', '.join(keys)}）")
    # それまで採用していた最初の案の記号を控える
    previous = next(
        (str(option["key"]) for option in options if option.get("adopted") is True), None
    )
    switched = [{**option, "adopted": str(option.get("key")) == key} for option in options]
    return {**item, "options": switched}, previous


def run_init(root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """`settings` でワークスペースを作る。"""
    files = create_workspace(root, settings, version=str(read_plugin_version()))
    return {"workspace": str(root.resolve()), "files": files}


def run_add(root: Path, kind: Kind, item: dict[str, Any], now: NowFn = now_utc) -> dict[str, Any]:
    """ID・日時・本文を付けて 1 項目を足す。"""
    workspace = load_workspace(root)
    changes = load_changes(root)
    validate_input_keys(kind, item)
    item_id = next_id(workspace, kind)
    timestamp = now()
    # id を先頭に、created・updated を末尾に置く
    added: dict[str, Any] = {"id": item_id}
    added.update({key: value for key, value in item.items() if key != BODY_INPUT_KEY})
    body = _body_write(item_id, item)
    # 本文を渡したときだけ、項目の body を `{ID}.md` にする
    if body is not None:
        added["body"] = body.name
    added["created"] = timestamp
    added["updated"] = timestamp
    # 足した項目は変更履歴を持たず、まだまとめていない変更の足した項目に入る
    noted = note_pending(changes, item_id, "added")
    save_change(
        workspace,
        Change(kind=kind, items=[*workspace.items[kind], added], body=body, changes=dict(noted)),
    )
    return {
        "id": item_id,
        "file": KINDS[kind].file,
        "body": f"docs/{body.name}" if body is not None else None,
    }


def run_update(
    root: Path, item_id: str, item: dict[str, Any], now: NowFn = now_utc
) -> dict[str, Any]:
    """1 項目のキーを置き換え、更新日時を変える。"""
    workspace = load_workspace(root)
    record = load_changes(root)
    ref = find_item(workspace, item_id)
    validate_input_keys(ref.kind, item)
    changes = {key: value for key, value in item.items() if key != BODY_INPUT_KEY}
    merged, changed = merge_changes(ref.item, changes)
    merged["updated"] = now()
    body = _body_write(item_id, item)
    # 本文を渡したときは body を `{ID}.md` にする（changed に入れるのは値が変わったときだけ）
    if body is not None and merged.get("body") != body.name:
        merged["body"] = body.name
        changed.append("body")
    # 書き換える前の本文（本文を変えないときは、後の本文も同じ）
    previous_body = _read_item_body(workspace, ref.item)
    # 本文の中身が変わったときは、`body_markdown` も changed に入れる
    if body is not None and body.text != previous_body:
        changed.append(BODY_INPUT_KEY)
    merged, noted = _stack_changes(
        workspace,
        record,
        before_item=ref.item,
        after_item=merged,
        before_body=previous_body,
        after_body=body.text if body is not None else previous_body,
    )
    items = list(workspace.items[ref.kind])
    items[ref.index] = merged
    save_change(
        workspace,
        Change(kind=ref.kind, items=items, body=body, changes=dict(noted) if noted else None),
    )
    return {"id": item_id, "file": KINDS[ref.kind].file, "changed": changed}


def run_update_settings(
    root: Path, settings: dict[str, Any], phase_map: dict[str, str] | None
) -> dict[str, Any]:
    """設定のキーを置き換え、フェーズを変えるときは項目のフェーズも付け替える。"""
    return update_settings(root, settings, phase_map)


def run_adopt(root: Path, item_id: str, key: str, now: NowFn = now_utc) -> dict[str, Any]:
    """検討事項の採用する案を切り替えて書き込む。"""
    workspace = load_workspace(root)
    record = load_changes(root)
    ref = find_item(workspace, item_id)
    # 検討事項以外の項目は案を持たない
    if ref.kind != "decision":
        raise ItemNotFoundError(f"検討事項がありません: {item_id}")
    switched, previous = switch_adopted(ref.item, key)
    switched["updated"] = now()
    # 本文は変えないので、前後の本文は同じ（読まない）
    switched, noted = _stack_changes(
        workspace,
        record,
        before_item=ref.item,
        after_item=switched,
        before_body=None,
        after_body=None,
    )
    items = list(workspace.items["decision"])
    items[ref.index] = switched
    save_change(
        workspace, Change(kind="decision", items=items, changes=dict(noted) if noted else None)
    )
    return {"id": item_id, "adopted": key, "previous": previous}


def run_commit(root: Path, summary: str, now: NowFn = now_utc) -> dict[str, Any]:
    """まだまとめていない変更を、説明つきの 1 つのまとまりにして書き込む。"""
    text = summary.strip()
    # 説明が空白だけか、長すぎる
    if not text or len(text) > SUMMARY_MAX_LENGTH:
        raise ArgumentError(
            "summary", f"前後の空白を除いて 1〜{SUMMARY_MAX_LENGTH} 文字で渡してください"
        )
    _require_workspace(root)
    committed, change_set = commit_pending(load_changes(root), text, now())
    # まとめる書き換えが無い: 何も書かない
    if change_set is None:
        return {"id": None, "at": None, "summary": None, "added": [], "changed": []}
    _write_changes(root, committed)
    return {
        "id": change_set["id"],
        "at": change_set["at"],
        "summary": change_set["summary"],
        "added": change_set["added"],
        "changed": change_set["changed"],
    }


def run_pending(root: Path) -> dict[str, Any]:
    """まだまとめていない変更を、出力の形にする。"""
    workspace = load_workspace(root)
    return pending_view(workspace, load_changes(root))


def run_check(root: Path) -> dict[str, Any]:
    """点検して、問題の有無と問題の並びを返す。前の版の形式の問題には /mindstella:upgrade を案内する。"""
    workspace = load_workspace(root)
    problems = check_workspace(workspace)
    rows = []
    for problem in problems:
        row = asdict(problem)
        # 前の版の形式から来た問題: 詳細に移し替えのスキルでの移し方を続ける
        if is_legacy_problem(problem, workspace):
            row["detail"] += MIGRATE_HINT
        rows.append(row)
    return {"ok": not problems, "problems": rows}


def run_impact(root: Path, item_id: str) -> dict[str, Any]:
    """影響を出力の形にする。"""
    affected = trace_impact(load_workspace(root), item_id)
    return {"id": item_id, "affected": [asdict(row) for row in affected]}


def run_next(root: Path, limit: int | None) -> dict[str, Any]:
    """次の候補を出力の形にする。"""
    # 件数の上限は 1 以上
    if limit is not None and limit < 1:
        raise ArgumentError("limit", "1 以上を渡してください")
    candidates = list_next_candidates(load_workspace(root), limit=limit)
    return {"candidates": [asdict(candidate) for candidate in candidates]}


def run_status(root: Path) -> dict[str, Any]:
    """再開時の状況を出力の形にする。"""
    return asdict(summarize_status(load_workspace(root)))


def run_goal(root: Path) -> dict[str, Any]:
    """ゴールに届いたかの判定を出力の形にする（届いていなくてもツールのエラーにしない）。"""
    return asdict(judge_goal(load_workspace(root)))


def run_find(root: Path, search_filter: SearchFilter) -> dict[str, Any]:
    """引数から作った条件で探し、検索結果を出力の形にする。"""
    return {"items": search_items(load_workspace(root), search_filter)}


def run_show(root: Path, item_id: str) -> dict[str, Any]:
    """1 項目の表示を出力の形にする。"""
    return show_item(load_workspace(root), item_id)


def run_attrs(root: Path) -> dict[str, Any]:
    """属性名の一覧を出力の形にする。"""
    return {"attrs": list_attrs(load_workspace(root))}


def run_migrate(
    root: Path,
    *,
    plan: bool,
    record: bool,
    values: list[dict[str, Any]] | None,
    from_version: str | None,
    to_version: str | None,
) -> dict[str, Any]:
    """`plan`・`values`・`record` で分けて移し替えの処理を呼び、結果を出力の形にする。"""
    # 一緒に使わない引数は、先に見つけた方の名前を持って弾く
    given = [
        name
        for name, passed in (("plan", plan), ("values", values is not None), ("record", record))
        if passed
    ]
    if len(given) > 1:
        raise ArgumentError(given[0], f"{'・'.join(given)} は一緒に使えません")
    assignments = _parse_values(values) if values is not None else None
    parsed_from = _parse_version("from_version", from_version)
    parsed_to = _parse_version("to_version", to_version)
    # 書く先の版が、当てる起点の版より前
    if parsed_from is not None and parsed_to is not None and parsed_to < parsed_from:
        raise ArgumentError("to_version", f"from_version より前の版は渡せません: {to_version}")

    versions = {"from_version": parsed_from, "to_version": parsed_to}
    if plan:
        report = plan_migration(root, **versions)
    elif assignments is not None:
        # 値を入れてから並べ直す（手順は当てないので steps は空）
        set_values(root, assignments)
        report = replace(plan_migration(root, **versions), steps=[])
    elif record:
        # 版を書いてから並べ直す（手順は当てないので steps は空）
        recorded = record_version(root, to_version=parsed_to)
        report = replace(plan_migration(root, **versions), steps=[], recorded=recorded)
    else:
        report = apply_migration(root, **versions)
    return _migration_payload(report)


def run_clear_release(root: Path) -> dict[str, Any]:
    """`release/` の中身を消し、消したものを返す。"""
    return {"removed": clear_release(root)}


def run_export(root: Path, out: Path, now: NowFn = now_utc) -> dict[str, Any]:
    """書き出す先を確かめて配る書き出しを書き、そのパスを返す。"""
    # ワークスペースを読む前に確かめる（誤った out では何も読まず、書かない）
    resolved = validate_export_out(out)
    path = export_preview(load_workspace(root), out=resolved, built_at=now())
    return {"path": str(path)}


def run_preview_url(root: Path, previews: PreviewRegistry) -> dict[str, Any]:
    """ワークスペースを確かめて配信を立て（立っていればそのまま）、URL を返す。"""
    _require_workspace(root)
    url, started = previews.start(root)
    return {"url": url, "workspace": str(root), "started": started}


def run_submissions(root: Path) -> dict[str, Any]:
    """取り込んでいない送信を出力の形にする。"""
    pending = list_pending_submissions(load_workspace(root))
    return {"items": [asdict(submission) for submission in pending]}


def run_take_submission(root: Path, submission_id: str, now: NowFn = now_utc) -> dict[str, Any]:
    """送信 1 件を取り込み済みにし、出力の形にする。"""
    _require_workspace(root)
    taken, already = take_submission(root, submission_id, now=now)
    return {"id": submission_id, "taken": taken, "already": already}


def _read_item_body(workspace: Workspace, item: dict[str, Any]) -> str | None:
    """項目の `body` が指す本文を読む（`body` を持たないか、ファイルが無ければ None）。"""
    name = item.get("body")
    return read_body(workspace, name) if isinstance(name, str) else None


def _stack_changes(
    workspace: Workspace,
    record: Changes,
    *,
    before_item: dict[str, Any],
    after_item: dict[str, Any],
    before_body: str | None,
    after_body: str | None,
) -> tuple[dict[str, Any], Changes | None]:
    """変更履歴の 1 回分を作って積んだ項目と、まとまりが変わったときの新しい記録（変わらなければ None）を返す。"""
    limit = history_limit(workspace.settings)
    entry = make_entry(
        before_item,
        after_item,
        before_body=before_body,
        after_body=after_body,
        seq=record["last_seq"] + 1,
        at=after_item["updated"],
    )
    stacked = stack_history(after_item, entry, limit)
    # 積んだ（保持する回数が 0 でなく、変わったものがある）: まだまとめていない変更に足す
    if entry is not None and limit > 0:
        return stacked, note_pending(record, after_item["id"], "changed", stacked=True)
    return stacked, None


def _write_changes(root: Path, record: Changes) -> None:
    """`changes.yaml` を、一時ファイルを書いてから置き換えて書く。"""
    path = root / CHANGES_FILE
    try:
        temp = write_temp(path, dump_yaml(record))
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えられなかった: 書いた一時ファイルを残さない
        remove_files([temp])
        raise write_failed(path, error) from error


def _require_workspace(root: Path) -> None:
    """`mindmap.yaml` が無いフォルダはワークスペースではないので、無ければ送る。"""
    if not (root / SETTINGS_FILE).is_file():
        raise WorkspaceNotFoundError(f"ワークスペースがありません: {root}")


def _body_write(item_id: str, item: dict[str, Any]) -> BodyWrite | None:
    """`item` に `body_markdown` があれば、`docs/{ID}.md` に書く本文にする。"""
    text = item.get(BODY_INPUT_KEY)
    # 本文を渡していない
    if text is None:
        return None
    return BodyWrite(name=f"{item_id}.md", text=str(text))


def _parse_version(argument: str, text: str | None) -> Version | None:
    """`from_version`・`to_version` を版にする（渡していなければ None）。"""
    if text is None:
        return None
    try:
        return parse_release_version(text)
    except ValueError as error:
        raise ArgumentError(argument, str(error)) from error


def _parse_values(values: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """`values` の要素を、ファイル・キーのパス・値の組にする。"""
    assignments: list[tuple[str, str, str]] = []
    for entry in values:
        # 要素が `file`・`key`・`value` を文字列で持たない
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(name), str) for name in VALUE_KEYS
        ):
            raise ArgumentError("values", "要素は file・key・value を文字列で持ってください")
        assignments.append((entry["file"], entry["key"], entry["value"]))
    return assignments


def _migration_payload(report: MigrationReport) -> dict[str, Any]:
    """移し替えの結果を、出力の辞書にする（版は文字列、手順は 1 行の説明つき）。"""
    return {
        "workspace_version": _version_text(report.workspace_version),
        "plugin_version": str(report.plugin_version),
        "relation": report.relation,
        "steps": [
            {
                "version": str(step.version),
                "index": step.index,
                "op": step.op,
                "destructive": step.op in DESTRUCTIVE_OPS,
                "summary": describe_step(step),
            }
            for step in report.steps
        ],
        "needs_values": [asdict(value) for value in report.needs_values],
        "backup": asdict(report.backup) if report.backup is not None else None,
        "recorded": _version_text(report.recorded),
    }


def _version_text(version: Version | None) -> str | None:
    """版を文字列にする。None（版を記録する前の形式・書いていない）はそのまま None。"""
    return str(version) if version is not None else None
