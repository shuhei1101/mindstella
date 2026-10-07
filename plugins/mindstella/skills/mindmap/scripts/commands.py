"""ツールごとの処理（引数 → 各機能 → 結果の辞書）。"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

from builder import export_preview, validate_export_out
from checker import check_workspace
from errors import (
    AdoptedOptionError,
    ArgumentError,
    ItemNotFoundError,
    MindmapError,
    OptionExistsError,
    OptionNotFoundError,
    SchemaMismatchError,
    WriteFailedError,
)
from graph import judge_goal, list_next_candidates, summarize_status, trace_impact
from history import (
    SUMMARY_MAX_LENGTH,
    Changes,
    advance_seq,
    changes_since,
    commit_pending,
    history_limit,
    load_changes,
    make_entry,
    mark_read,
    note_pending,
    pending_view,
    stack_history,
)
from kinds import EDITOR, KINDS, RECORD_DIR, Kind, records_root
from migration_ops import DESTRUCTIVE_OPS, describe_step
from migrator import MigrationReport, apply_migration, plan_migration, record_version, set_values
from query import SearchFilter, list_attrs, list_tags, search_items, show_item
from readme import README_FILE, write_readme
from serve import PreviewRegistry
from settings_update import update_settings
from store import (
    CHANGES_FILE,
    BatchChange,
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
    require_workspace,
    save_batch,
    save_change,
    write_failed,
    write_temp,
)
from submissions import list_pending_submissions, take_submission
from versions import Version, parse_release_version, read_plugin_version

logger = logging.getLogger(__name__)

# 前の版の形式の問題の詳細に続ける案内
MIGRATE_HINT = "（/mindstella:upgrade で今の形式に移せます）"

# `item` で渡させない、ツールが付けるキー
RESERVED_KEYS = (
    "id",
    "created",
    "updated",
    "updated_by",
    "body",
    "history",
    "history_dropped_seq",
    "seq",
    "added_seq",
)

# `item` で本文の Markdown を渡すキー（YAML には残さない）
BODY_INPUT_KEY = "body_markdown"

# 項目の中身のエラーの行に付けるファイル名の代わり
ITEM_NAME = "item"

# `values` の 1 要素が持つ、文字列で渡させるキー
VALUE_KEYS = ("file", "key", "value")

# `edit_option` の `option` に渡せるキー
OPTION_KEYS = ("content", "pros", "cons", "note", "reason")

# `batch` が `$番号` を置き換えるキー
REF_KEYS = ("parent", "depends_on", "for", "related", "sources")

# `batch` の操作ごとに持つ・持たないキー（操作 → 要るキー）。`op` は全ての操作が持つ
OPERATION_REQUIRED_KEYS = {
    "add": frozenset({"kind", "item"}),
    "update": frozenset({"id", "item"}),
    "show": frozenset({"id"}),
}

# 先に足した項目を指す番号（全体が `$` と数字だけの文字列）
REF_PATTERN = re.compile(r"^\$([0-9]+)$")

# 検討事項の ID の頭（`edit_option` が受ける ID）
DECISION_PREFIX = "D-"

# 案の書き換えの `option` を渡す引数の名前（引数の誤りに添える）
OPTION_NAME = "option"


@dataclass(frozen=True, slots=True, kw_only=True)
class Staged:
    """書き込む前にメモリの上で当てた、種類ごとの項目・本文・まとまり。"""

    # 読んだワークスペース（書き込みの前の中身。`save_batch` に渡す）
    workspace: Workspace
    # 当てた後の種類ごとの項目の並び（書き換えた種類だけでなく全て）
    items: dict[Kind, list[dict[str, Any]]]
    # 書き換えた種類
    touched: frozenset[Kind]
    # 書く本文（ファイル名 → 本文。同じ項目を二度直すと後の本文で置き換える）
    bodies: dict[str, BodyWrite]
    # 当てた後のまとまりの記録
    changes: Changes


def validate_input_keys(kind: Kind, data: dict[str, Any]) -> None:
    """ツールが付けるキーを弾く（`body_markdown` はどの種類も渡せる）。"""
    lines = [f"{ITEM_NAME}: {key}: ツールが付けるキーです" for key in RESERVED_KEYS if key in data]
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


def apply_option_edit(
    item: dict[str, Any],
    action: Literal["add", "update", "remove"],
    key: str,
    option: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """検討事項の案の並びに、記号で指した 1 つの足す・直す・消すを当てた新しい並びを返す。"""
    # option の渡し方が合わない: 足す・直すは必須、消すは渡さない、渡せるキーは決まっている
    if action in ("add", "update") and option is None:
        raise ArgumentError(OPTION_NAME, f"{action} では option を渡してください")
    if action == "remove" and option is not None:
        raise ArgumentError(OPTION_NAME, "remove では option を渡せません")
    unknown = [name for name in (option or {}) if name not in OPTION_KEYS]
    if unknown:
        raise ArgumentError(
            OPTION_NAME, f"渡せないキーです: {', '.join(unknown)}（渡せるのは {', '.join(OPTION_KEYS)}）"
        )
    options = [dict(entry) for entry in item.get("options") or []]
    position = next((index for index, entry in enumerate(options) if entry.get("key") == key), None)
    prefix = f"{item['id']} の案 {key}"
    if action == "add":
        # 同じ記号の案が既にある
        if position is not None:
            raise OptionExistsError(f"{prefix}: 同じ記号の案が既にあります")
        return [*options, {"key": key, **(option or {})}]
    # 直す・消すは、その記号の案が要る
    if position is None:
        raise OptionNotFoundError(f"{prefix}: その記号の案がありません")
    if action == "update":
        edited = options[position]
        for name, value in (option or {}).items():
            # null のキーは消し、それ以外は置き換える
            if value is None:
                edited.pop(name, None)
            else:
                edited[name] = value
        return options
    # 採用している案は消せない
    if options[position].get("adopted") is True:
        raise AdoptedOptionError(
            f"{prefix}: 採用している案は消せません。先に adopt で採用をほかの案へ移してください"
        )
    del options[position]
    return options


def resolve_refs(item: dict[str, Any], added: dict[int, str]) -> dict[str, Any]:
    """`item` の参照のキーの `$番号` を、その番号の `add` で振った ID に置き換えた新しい `item` を返す。"""
    resolved = dict(item)
    for key in REF_KEYS:
        if key not in resolved:
            continue
        value = resolved[key]
        # 配列は要素ごとに、文字列はそのまま置き換える
        if isinstance(value, list):
            resolved[key] = [_resolve_ref(key, entry, added) for entry in value]
        else:
            resolved[key] = _resolve_ref(key, value, added)
    return resolved


def stage_add(
    staged: Staged, kind: Kind, item: dict[str, Any], now: NowFn = now_utc
) -> tuple[Staged, dict[str, Any]]:
    """ID・日時・通し番号・本文を付けた 1 項目を、メモリの上の並びに足す。"""
    validate_input_keys(kind, item)
    item_id = next_id(replace(staged.workspace, items=staged.items), kind)
    timestamp = now()
    record, seq = advance_seq(staged.changes)
    # id を先頭に、created・updated・updated_by・seq・added_seq を末尾に置く
    added: dict[str, Any] = {"id": item_id}
    added.update({key: value for key, value in item.items() if key != BODY_INPUT_KEY})
    body = _body_write(item_id, item)
    bodies = dict(staged.bodies)
    # 本文を渡したときだけ（どの種類も）、項目の body を `{ID}.md` にして本文の書き込みを足す
    if body is not None:
        added["body"] = body.name
        bodies[body.name] = body
    added.update(
        {
            "created": timestamp,
            "updated": timestamp,
            "updated_by": EDITOR,
            "seq": seq,
            "added_seq": seq,
        }
    )
    # 足した項目は変更履歴を持たず、まだまとめていない変更の足した項目に入る
    record = note_pending(record, item_id, "added")
    new_staged = replace(
        staged,
        items={**staged.items, kind: [*staged.items[kind], added]},
        touched=staged.touched | {kind},
        bodies=bodies,
        changes=record,
    )
    result = {
        "id": item_id,
        "file": f"{RECORD_DIR}/{KINDS[kind].file}",
        "body": f"{RECORD_DIR}/docs/{body.name}" if body is not None else None,
    }
    return new_staged, result


def stage_update(
    staged: Staged, item_id: str, item: dict[str, Any], now: NowFn = now_utc
) -> tuple[Staged, dict[str, Any]]:
    """1 項目のキーを置き換え、変更履歴と通し番号を付けて、メモリの上の並びを差し替える。"""
    workspace = replace(staged.workspace, items=staged.items)
    ref = find_item(workspace, item_id)
    validate_input_keys(ref.kind, item)
    changes = {key: value for key, value in item.items() if key != BODY_INPUT_KEY}
    merged, changed = merge_changes(ref.item, changes)
    merged["updated"] = now()
    merged["updated_by"] = EDITOR
    body = _body_write(item_id, item)
    # 本文を渡したときは body を `{ID}.md` にする（changed に入れるのは値が変わったときだけ）
    if body is not None and merged.get("body") != body.name:
        merged["body"] = body.name
        changed.append("body")
    # 書き換える前の本文（同じ呼び出しで先に書いた本文があればそれ）
    previous_name = ref.item.get("body")
    previous_body = (
        staged.bodies[previous_name].text
        if isinstance(previous_name, str) and previous_name in staged.bodies
        else _read_item_body(workspace, ref.item)
    )
    # 本文の中身が変わったときは、`body_markdown` も changed に入れる
    if body is not None and body.text != previous_body:
        changed.append(BODY_INPUT_KEY)
    merged, record = _stack_changes(
        workspace,
        staged.changes,
        before_item=ref.item,
        after_item=merged,
        before_body=previous_body,
        after_body=body.text if body is not None else previous_body,
    )
    rows = list(staged.items[ref.kind])
    rows[ref.index] = merged
    new_staged = replace(
        staged,
        items={**staged.items, ref.kind: rows},
        touched=staged.touched | {ref.kind},
        bodies={**staged.bodies, **({body.name: body} if body is not None else {})},
        changes=record,
    )
    return new_staged, {
        "id": item_id,
        "file": f"{RECORD_DIR}/{KINDS[ref.kind].file}",
        "changed": changed,
    }


def run_add(root: Path, kind: Kind, item: dict[str, Any], now: NowFn = now_utc) -> dict[str, Any]:
    """ID・日時・本文を付けて 1 項目を足す。"""
    staged = _start_staged(root)
    new_staged, result = stage_add(staged, kind, item, now)
    save_batch(staged.workspace, _batch_of(new_staged, staged.changes))
    return result


def run_update(
    root: Path, item_id: str, item: dict[str, Any], now: NowFn = now_utc
) -> dict[str, Any]:
    """1 項目のキーを置き換え、更新日時を変える。"""
    staged = _start_staged(root)
    new_staged, result = stage_update(staged, item_id, item, now)
    save_batch(staged.workspace, _batch_of(new_staged, staged.changes))
    return result


def run_update_settings(
    root: Path,
    settings: dict[str, Any],
    phase_map: dict[str, str] | None,
    target_map: dict[str, str] | None,
    category_map: dict[str, str] | None,
) -> dict[str, Any]:
    """設定のキーを置き換え、フェーズ・対象・カテゴリーを変えるときは項目の付け替えもする。"""
    return update_settings(
        root, settings, phase_map, target_map=target_map, category_map=category_map
    )


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
    switched["updated_by"] = EDITOR
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
        workspace,
        Change(kind="decision", items=items, changes=dict(noted) if noted != record else None),
    )
    return {"id": item_id, "adopted": key, "previous": previous}


def run_edit_option(
    root: Path,
    item_id: str,
    action: Literal["add", "update", "remove"],
    key: str,
    option: dict[str, Any] | None,
    now: NowFn = now_utc,
) -> dict[str, Any]:
    """検討事項の案を 1 つ足す・直す・消す。"""
    # 検討事項の ID でない
    if not item_id.startswith(DECISION_PREFIX):
        raise ArgumentError("id", "検討事項の ID（D-）を渡してください")
    staged = _start_staged(root)
    ref = find_item(replace(staged.workspace, items=staged.items), item_id)
    options = apply_option_edit(ref.item, action, key, option)
    # 並びを丸ごと渡して更新を当てる（options は渡せないキーに入っていない）
    new_staged, result = stage_update(staged, item_id, {"options": options}, now)
    save_batch(staged.workspace, _batch_of(new_staged, staged.changes))
    return {
        "id": item_id,
        "file": result["file"],
        "options": options,
        "changed": "options" in result["changed"],
    }


def run_batch(
    root: Path, operations: list[dict[str, Any]], now: NowFn = now_utc
) -> dict[str, Any]:
    """追加・更新・取得の操作を並べた順に当て、最後に 1 回だけ書き込む。"""
    # 1 件も渡していない
    if not operations:
        raise ArgumentError("operations", "1 件以上の操作を渡してください")
    staged = _start_staged(root)
    original = staged.changes
    # `$番号`（1 始まりの add の番号）→ 振った ID、項目の ID → 最後に書いた操作の（番号, op）
    added: dict[int, str] = {}
    writers: dict[str, tuple[int, str]] = {}
    results: list[dict[str, Any]] = []
    add_count = 0
    for number, operation in enumerate(operations, start=1):
        op = str(operation.get("op"))
        try:
            _validate_operation(operation)
            if op == "add":
                staged, result = stage_add(
                    staged, operation["kind"], resolve_refs(operation["item"], added), now
                )
                add_count += 1
                added[add_count] = result["id"]
                writers[result["id"]] = (number, op)
            elif op == "update":
                item_id = _resolve_ref("id", operation["id"], added)
                staged, result = stage_update(
                    staged, item_id, resolve_refs(operation["item"], added), now
                )
                writers[item_id] = (number, op)
            else:
                result = _show_staged(staged, _resolve_ref("id", operation["id"], added))
        except MindmapError as error:
            # どの操作で起きたかをメッセージの頭に付けて、同じ種類のエラーのまま送る
            _prefix_error(error, number, op)
            raise
        results.append({"op": op, "result": result})
    # 書き換えた種類があるときだけ、1 回で書き込む
    if staged.touched:
        try:
            save_batch(staged.workspace, _batch_of(staged, original))
        except SchemaMismatchError as error:
            # 合わない箇所の項目を最後に書いた操作の番号を付ける
            writer = _schema_error_writer(error, staged, writers)
            if writer is not None:
                _prefix_error(error, *writer)
            raise
    return {"results": results}


def run_changes_since_read(root: Path) -> dict[str, Any]:
    """読んだ時点からの変更を並べ、読んだ時点を進めて書き込む。"""
    workspace = load_workspace(root)
    record = load_changes(root)
    result = changes_since(workspace, record)
    # 読んだ時点を進めた記録だけを `changes.yaml` に書く（項目は書かず、今ある違反では止めない）
    _write_changes(root, mark_read(record))
    return result


def run_commit(root: Path, summary: str, now: NowFn = now_utc) -> dict[str, Any]:
    """まだまとめていない変更を、説明つきの 1 つのまとまりにして書き込む。"""
    text = summary.strip()
    # 説明が空白だけか、長すぎる
    if not text or len(text) > SUMMARY_MAX_LENGTH:
        raise ArgumentError(
            "summary", f"前後の空白を除いて 1〜{SUMMARY_MAX_LENGTH} 文字で渡してください"
        )
    require_workspace(root)
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
        # （問題の file は `.mindstella/` から始まるので、記録のフォルダからのパスに戻して見分ける）
        relative = replace(problem, file=problem.file.removeprefix(f"{RECORD_DIR}/"))
        if is_legacy_problem(relative, workspace):
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


def run_tags(root: Path) -> dict[str, Any]:
    """タグの一覧を出力の形にする。"""
    return {"tags": list_tags(load_workspace(root))}


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
    """ワークスペースを確かめて配信を立て（立っていればそのまま）、URL を返す。立てたときは直下の README にも URL を書く。"""
    require_workspace(root)
    url, started = previews.start(root)
    # この呼び出しで立てたときだけ、README のプレビューの節を URL にする
    if started:
        try:
            write_readme(root, preview_url=url)
        except WriteFailedError as error:
            # README を書けなくても配信は止めず、URL を返す
            logger.warning("README を書けなかった: %s", error)
    return {"url": url, "workspace": str(root), "started": started}


def run_readme(root: Path, previews: PreviewRegistry) -> dict[str, Any]:
    """ワークスペースを確かめ、直下の README を今の値と配っている URL で書き直す。"""
    require_workspace(root)
    url = previews.url_of(root)
    written = write_readme(root, preview_url=url)
    return {"path": str(root / README_FILE), "written": written, "preview_url": url}


def run_submissions(root: Path) -> dict[str, Any]:
    """取り込んでいない送信を出力の形にする。"""
    pending = list_pending_submissions(load_workspace(root))
    return {"items": [asdict(submission) for submission in pending]}


def run_take_submission(root: Path, submission_id: str, now: NowFn = now_utc) -> dict[str, Any]:
    """送信 1 件を取り込み済みにし、出力の形にする。"""
    require_workspace(root)
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
) -> tuple[dict[str, Any], Changes]:
    """変更履歴の 1 回分を作って積み、通し番号を振った項目と、新しい記録を返す。"""
    limit = history_limit(workspace.settings)
    entry = make_entry(
        before_item,
        after_item,
        before_body=before_body,
        after_body=after_body,
        seq=record["last_seq"] + 1,
        at=after_item["updated"],
        by=EDITOR,
    )
    read_seq = record.get("read_seq")
    # 変わったものが無い: 通し番号は進めない
    if entry is None:
        return stack_history(after_item, None, limit, read_seq=read_seq), record
    # 変わった: 通し番号を振り、項目の seq にして変更履歴を積む
    record, seq = advance_seq(record)
    stacked = stack_history({**after_item, "seq": seq}, entry, limit, read_seq=read_seq)
    # 積んだ（保持する回数が 0 でない）: まだまとめていない変更に足す
    if limit > 0:
        record = note_pending(record, after_item["id"], "changed")
    return stacked, record


def _start_staged(root: Path) -> Staged:
    """ワークスペースとまとまりを読み、まだ何も当てていない `Staged` を作る。"""
    workspace = load_workspace(root)
    return Staged(
        workspace=workspace,
        items=workspace.items,
        touched=frozenset(),
        bodies={},
        changes=load_changes(root),
    )


def _batch_of(staged: Staged, original: Changes) -> BatchChange:
    """当てた書き換えを、書き込む変更にする（まとまりは変わったときだけ書く）。"""
    return BatchChange(
        items={kind: staged.items[kind] for kind in KINDS if kind in staged.touched},
        bodies=list(staged.bodies.values()),
        changes=dict(staged.changes) if staged.changes != original else None,
    )


def _resolve_ref(key: str, value: Any, added: dict[int, str]) -> Any:
    """全体が `$番号` の文字列を、その番号の `add` で振った ID にする（ほかの値はそのまま）。"""
    if not isinstance(value, str):
        return value
    matched = REF_PATTERN.fullmatch(value)
    if matched is None:
        return value
    # 前の add を指していない番号
    if int(matched.group(1)) not in added:
        raise ArgumentError(key, f"{value} はこの操作より前の add を指していません")
    return added[int(matched.group(1))]


def _validate_operation(operation: dict[str, Any]) -> None:
    """操作に要るキーが揃い、要らないキーが無いことを確かめる。"""
    op = operation.get("op")
    required = OPERATION_REQUIRED_KEYS.get(str(op))
    if required is None:
        raise ArgumentError("operations", f"op は add・update・show のどれかです: {op}")
    given = set(operation) - {"op"}
    missing = sorted(required - given)
    extra = sorted(given - required)
    if missing:
        raise ArgumentError("operations", f"{op} に要るキーがありません: {', '.join(missing)}")
    if extra:
        raise ArgumentError("operations", f"{op} に要らないキーがあります: {', '.join(extra)}")


def _show_staged(staged: Staged, item_id: str) -> dict[str, Any]:
    """当てた後の並びと本文で、`show` と同じ形の結果を作る。"""
    shown = show_item(replace(staged.workspace, items=staged.items), item_id)
    name = shown["item"].get("body")
    # 同じ呼び出しで先に書いた本文は、ファイルより新しい
    if isinstance(name, str) and name in staged.bodies:
        shown["body_markdown"] = staged.bodies[name].text
    return shown


def _prefix_error(error: MindmapError, number: int, op: str) -> None:
    """エラーのメッセージの頭に、何番目の操作かを付ける（同じ種類のエラーのまま）。"""
    error.args = (f"{number} 番目の操作（{op}）: {error.args[0]}", *error.args[1:])


def _schema_error_writer(
    error: SchemaMismatchError, staged: Staged, writers: dict[str, tuple[int, str]]
) -> tuple[int, str] | None:
    """スキーマに合わない最初の行の項目を、最後に書いた操作の（番号, op）を返す（見つからなければ None）。"""
    files = {spec.file: kind for kind, spec in KINDS.items()}
    for line in error.lines:
        matched = re.match(r"^(?P<file>[^:]+): items\[(?P<index>[0-9]+)\]", line)
        if matched is None or matched.group("file") not in files:
            continue
        rows = staged.items[files[matched.group("file")]]
        index = int(matched.group("index"))
        if index < len(rows) and rows[index].get("id") in writers:
            return writers[rows[index]["id"]]
    return None


def _write_changes(root: Path, record: Changes) -> None:
    """`changes.yaml` を、一時ファイルを書いてから置き換えて書く。"""
    path = records_root(root) / CHANGES_FILE
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
