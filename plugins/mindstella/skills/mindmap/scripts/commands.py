"""ツールごとの処理（引数 → 各機能 → 結果の辞書）。"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from builder import export_preview, validate_export_out
from checker import check_workspace
from change_detection import accept_written
from errors import (
    AdoptedOptionError,
    ArgumentError,
    ConcurrentWriteError,
    ItemNotFoundError,
    LastOptionError,
    OptionExistsError,
    OptionNotFoundError,
    SchemaMismatchError,
    WriteFailedError,
)
from graph import judge_goal, list_next_candidates, summarize_status
from history import (
    SUMMARY_MAX_LENGTH,
    Changes,
    ItemHistory,
    advance_seq,
    changes_since,
    commit_pending,
    flush_pending,
    history_limit,
    load_changes,
    load_item_history,
    make_entry,
    mark_read,
    note_pending,
    pending_view,
    removed_items,
    stack_history,
)
from ids import reserve_ids
from kinds import BODY_DIR, EDITOR, KINDS, RECORD_DIR, Kind, records_root
from migration_ops import DESTRUCTIVE_OPS, describe_step
from migrator import (
    MigrationReport,
    MigrationStep,
    apply_migration,
    plan_migration,
    record_version,
    set_values,
)
from readme import README_FILE, write_readme
from settings_update import update_settings
from store import (
    CHANGES_FILE,
    OPTIONS_OPTIONAL_STATUSES,
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
    now_utc,
    read_body,
    read_kind_items,
    remove_files,
    require_workspace,
    save_batch,
    save_change,
    write_failed,
    write_release,
    write_temp,
)
from tag_text import compact_tags
from threads import (
    create_thread,
    list_threads,
    mark_read as mark_thread_read,
    reply_thread,
    set_thread_status,
    update_thread,
    view_thread,
)
from versions import Version, parse_release_version, read_plugin_version

if TYPE_CHECKING:
    # serve が編集の保存で commands を読むため、循環を避けて型の注釈にだけ使う
    from serve import PreviewRegistry

logger = logging.getLogger(__name__)

# 前の版の形式の問題の詳細に続ける案内
MIGRATE_HINT = "（/mindstella:upgrade で今の形式に移せます）"

# `item` で渡させないキー（`body` 以外は `history.yaml` に持つキー）
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

# `item` で資料の HTML の本文を渡すキー（YAML には残さない）
HTML_BODY_INPUT_KEY = "body_html"

# HTML の本文を持てる種類
HTML_BODY_KIND: Kind = "doc"

# `item` で渡す本文のキー（どちらも YAML には残さない）
BODY_INPUT_KEYS = (BODY_INPUT_KEY, HTML_BODY_INPUT_KEY)

# 項目の中身のエラーの行に付けるファイル名の代わり
ITEM_NAME = "item"

# `values` の 1 要素が持つ、文字列で渡させるキー
VALUE_KEYS = ("file", "key", "value")

# `edit_option` の `option` に渡せるキー
OPTION_KEYS = ("content", "pros", "cons", "note", "reason", "recommended")

# 検討事項の案を採用したときに入る状態
DECIDED_STATUS = "決定済み"

# 保存待ちの編集の仮の ID（`new-{連番}`）を、振った ID に置き換える参照の場所（`related` は各要素の `to`）
REF_KEYS = ("related", "sources")

# `next_id` の `count` の上限
NEXT_ID_MAX_COUNT = 50

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
    # 書く本文（本文のパス → 本文。同じ項目を二度直すと後の本文で置き換える）
    bodies: dict[str, BodyWrite]
    # 当てた後の `history.yaml` の行（項目の ID → 行）
    history: dict[str, ItemHistory]
    # 当てた後のまとまりの記録
    changes: Changes
    # 書き込んだ後に消す本文のパス（形式を替えた資料の前の形式の本文）
    removed_bodies: list[str] = field(default_factory=list)
    # 読んだときのまとまりの記録（書き込む前と比べて、変わったときだけ書く）
    original: Changes | None = None


def validate_input_keys(kind: Kind, data: dict[str, Any], *, index: int) -> None:
    """ツールが付けるキーと、資料以外の `body_html`・両方の本文を弾く（`body_markdown` はどの種類も渡せる）。"""
    lines = [f"{ITEM_NAME}: {key}: ツールが付けるキーです" for key in RESERVED_KEYS if key in data]
    if lines:
        raise SchemaMismatchError(lines)
    if HTML_BODY_INPUT_KEY not in data:
        return
    where = f"{KINDS[kind].file}: items[{index}].{HTML_BODY_INPUT_KEY}"
    # 資料以外は HTML の本文を持てない
    if kind != HTML_BODY_KIND:
        raise SchemaMismatchError([f"{where}: 資料だけが HTML の本文を持てる"])
    # 本文は Markdown か HTML のどちらか 1 つ
    if BODY_INPUT_KEY in data:
        raise SchemaMismatchError(
            [f"{where}: {BODY_INPUT_KEY} と {HTML_BODY_INPUT_KEY} は一緒に渡せない"]
        )


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
    """指定した記号の案だけを採用にし、状態を決定済みにした新しい項目と、それまで採用していた案の記号を返す。"""
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
    return {**item, "options": switched, "status": DECIDED_STATUS}, previous


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
        added = [*options, {"key": key, **(option or {})}]
        return _apply_recommended(added, key, option or {})
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
        return _apply_recommended(options, key, option or {})
    # 採用している案は消せない
    if options[position].get("adopted") is True:
        raise AdoptedOptionError(
            f"{prefix}: 採用している案は消せません。先に adopt で採用をほかの案へ移してください"
        )
    # 案を必須にする状態の検討事項は、最後の案を消せない
    status = item.get("status")
    if len(options) == 1 and status not in OPTIONS_OPTIONAL_STATUSES:
        raise LastOptionError(
            f"{prefix}: 状態 {status} の検討事項は案を 1 つ以上持ちます。先に add で別の案を足してください"
        )
    del options[position]
    return options


def _apply_recommended(
    options: list[dict[str, Any]], key: str, option: dict[str, Any]
) -> list[dict[str, Any]]:
    """`option` が推奨の印を持つとき、印を立てる（ほかの案の印は外す）か、外した案のキーを消す。"""
    # 推奨の印を渡していない
    if "recommended" not in option:
        return options
    marked = option["recommended"] is True
    for entry in options:
        # 印を立てるときは指した案以外の、外すときは指した案の、印のキーを消す
        if marked != (entry.get("key") == key):
            entry.pop("recommended", None)
    return options


def stage_add(
    staged: Staged,
    kind: Kind,
    item: dict[str, Any],
    now: NowFn = now_utc,
    *,
    editor: str = EDITOR,
    item_id: str | None = None,
) -> tuple[Staged, dict[str, Any]]:
    """ID・日時・通し番号・本文を付けた 1 項目を、メモリの上の並びに足す。editor は足した項目の編集した人、item_id は先に予約から振った ID。"""
    validate_input_keys(kind, item, index=len(staged.items[kind]))
    # 主題でないタグは main を持たない
    if "tags" in item:
        item = {**item, "tags": compact_tags(item["tags"])}
    # 先に振った ID が無ければ予約から振り、消した項目の ID は振り直さない
    if item_id is None:
        item_id = reserve_ids(
            staged.workspace.root,
            kind,
            staged.items[kind],
            [removed["id"] for removed in removed_items(staged.changes)],
        )[0]
    timestamp = now()
    record, seq = advance_seq(staged.changes)
    # id を先頭に置く（作成日時・通し番号は history.yaml の行に持つ）
    added: dict[str, Any] = {"id": item_id}
    added.update({key: value for key, value in item.items() if key not in BODY_INPUT_KEYS})
    body = _body_write(item_id, item)
    bodies = dict(staged.bodies)
    # 本文を渡したときだけ、項目の body を `docs/{ID}.md`（資料の HTML は `docs/{ID}.html`）にして本文の書き込みを足す
    if body is not None:
        added["body"] = body.name
        bodies[body.name] = body
    row: ItemHistory = {
        "created": timestamp,
        "updated": timestamp,
        "updated_by": cast(Any, editor),
        "seq": seq,
        "added_seq": seq,
    }
    # 足した項目は変更履歴を持たず、まだまとめていない変更の足した項目に入る
    record = note_pending(record, item_id, "added")
    new_staged = replace(
        staged,
        items={**staged.items, kind: [*staged.items[kind], added]},
        touched=staged.touched | {kind},
        bodies=bodies,
        history={**staged.history, item_id: row},
        changes=record,
    )
    result = {
        "id": item_id,
        "file": f"{RECORD_DIR}/{KINDS[kind].file}",
        "body": f"{RECORD_DIR}/{body.name}" if body is not None else None,
    }
    return new_staged, result


def stage_update(
    staged: Staged,
    item_id: str,
    item: dict[str, Any],
    now: NowFn = now_utc,
    *,
    editor: str = EDITOR,
) -> tuple[Staged, dict[str, Any]]:
    """1 項目のキーを置き換え、変更履歴と通し番号を付けて、メモリの上の並びを差し替える。editor は項目と変更履歴の回の編集した人。"""
    workspace = replace(staged.workspace, items=staged.items)
    ref = find_item(workspace, item_id)
    validate_input_keys(ref.kind, item, index=ref.index)
    # 主題でないタグは main を持たない
    if "tags" in item:
        item = {**item, "tags": compact_tags(item["tags"])}
    changes = {key: value for key, value in item.items() if key not in BODY_INPUT_KEYS}
    merged, changed = merge_changes(ref.item, changes)
    timestamp = now()
    row: ItemHistory = {
        **staged.history.get(item_id, {}),
        "updated": timestamp,
        "updated_by": cast(Any, editor),
    }
    body = _body_write(item_id, item)
    previous_name = ref.item.get("body")
    bodies = dict(staged.bodies)
    removed_bodies = list(staged.removed_bodies)
    # 本文を渡したときは body を `docs/{ID}.md` か `docs/{ID}.html` にする（changed に入れるのは値が変わったときだけ）
    if body is not None and merged.get("body") != body.name:
        merged["body"] = body.name
        changed.append("body")
        # 前の body があり名前が違う（形式を替えた）: 前の形式の本文を消す書き込みにする
        if isinstance(previous_name, str):
            bodies.pop(previous_name, None)
            removed_bodies.append(previous_name)
    # 新しい名前の本文を書くので、消す本文には入れない
    if body is not None:
        removed_bodies = [name for name in removed_bodies if name != body.name]
    # 書き換える前の本文（同じ呼び出しで先に書いた本文があればそれ）
    previous_body = (
        staged.bodies[previous_name].text
        if isinstance(previous_name, str) and previous_name in staged.bodies
        else _read_item_body(workspace, ref.item)
    )
    # 本文の中身が変わったときは、渡した本文のキー（`body_markdown` か `body_html`）も changed に入れる
    if body is not None and body.text != previous_body:
        changed.append(HTML_BODY_INPUT_KEY if body.name.endswith(".html") else BODY_INPUT_KEY)
    row, record = _stack_changes(
        workspace,
        staged.changes,
        row=row,
        before_item=ref.item,
        after_item=merged,
        before_body=previous_body,
        after_body=body.text if body is not None else previous_body,
        at=timestamp,
        editor=editor,
    )
    rows = list(staged.items[ref.kind])
    rows[ref.index] = merged
    new_staged = replace(
        staged,
        items={**staged.items, ref.kind: rows},
        touched=staged.touched | {ref.kind},
        bodies={**bodies, **({body.name: body} if body is not None else {})},
        history={**staged.history, item_id: row},
        changes=record,
        removed_bodies=removed_bodies,
    )
    return new_staged, {
        "id": item_id,
        "file": f"{RECORD_DIR}/{KINDS[ref.kind].file}",
        "changed": changed,
    }


def run_update_settings(
    root: Path,
    settings: dict[str, Any],
    phase_map: dict[str, str] | None,
    target_map: dict[str, str] | None,
    category_map: dict[str, str] | None,
) -> dict[str, Any]:
    """設定のキーを置き換え、フェーズ・対象・カテゴリーを変えるときは項目の付け替えもする。"""
    return update_settings(
        root,
        settings,
        phase_map,
        target_map=target_map,
        category_map=category_map,
    )


def run_adopt(root: Path, item_id: str, key: str, now: NowFn = now_utc) -> dict[str, Any]:
    """検討事項の採用する案を切り替えて書き込む。ほかが間に書いたら 1 回だけ読み直して当て直す。"""
    try:
        previous, previous_status = _adopt_once(root, item_id, key, now)
    except ConcurrentWriteError:
        previous, previous_status = _adopt_once(root, item_id, key, now)
    return {
        "id": item_id,
        "adopted": key,
        "previous": previous,
        "status": DECIDED_STATUS,
        "previous_status": previous_status,
    }


def _adopt_once(root: Path, item_id: str, key: str, now: NowFn) -> tuple[str | None, str]:
    """読んで採用を切り替えて書き、それまで採用していた案の記号と前の状態を返す。"""
    workspace = load_workspace(root)
    timestamp = now()
    loaded = load_changes(root)
    # 外部の変更が入っていれば、先に外部の変更のまとまりにする
    record = flush_pending(loaded, "ai", timestamp)
    rows = load_item_history(root)
    ref = find_item(workspace, item_id)
    # 検討事項以外の項目は案を持たない
    if ref.kind != "decision":
        raise ItemNotFoundError(f"検討事項がありません: {item_id}")
    switched, previous = switch_adopted(ref.item, key)
    previous_status = ref.item["status"]
    row: ItemHistory = {**rows.get(item_id, {}), "updated": timestamp, "updated_by": EDITOR}
    # 本文は変えないので、前後の本文は同じ（読まない）
    row, noted = _stack_changes(
        workspace,
        record,
        row=row,
        before_item=ref.item,
        after_item=switched,
        before_body=None,
        after_body=None,
        at=timestamp,
    )
    items = list(workspace.items["decision"])
    items[ref.index] = switched
    written = save_change(
        workspace,
        Change(
            kind="decision",
            items=items,
            history={**rows, item_id: row},
            changes=dict(noted) if noted != loaded else None,
        ),
    )
    accept_written(workspace.root, written)
    return previous, previous_status


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
    try:
        options, result = _edit_option_once(root, item_id, action, key, option, now)
    except ConcurrentWriteError:
        options, result = _edit_option_once(root, item_id, action, key, option, now)
    return {
        "id": item_id,
        "file": result["file"],
        "options": options,
        "changed": "options" in result["changed"],
    }


def _edit_option_once(
    root: Path,
    item_id: str,
    action: Literal["add", "update", "remove"],
    key: str,
    option: dict[str, Any] | None,
    now: NowFn,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """読んで案の書き換えを当てて書き、新しい案の並びと更新の結果を返す。"""
    staged = _start_staged(root, now)
    ref = find_item(replace(staged.workspace, items=staged.items), item_id)
    options = apply_option_edit(ref.item, action, key, option)
    # 並びを丸ごと渡して更新を当てる（options は渡せないキーに入っていない）
    new_staged, result = stage_update(staged, item_id, {"options": options}, now)
    written = save_batch(staged.workspace, _batch_of(new_staged, staged.original))
    accept_written(staged.workspace.root, written)
    return options, result


def run_next_id(root: Path, kind: str, *, count: int = 1) -> dict[str, list[str]]:
    """種類ごとの次の ID を、予約と合わせて `count` 個振る（ファイルは書かない）。"""
    # 決めた種類でない
    if kind not in KINDS:
        raise ArgumentError("kind", f"{'・'.join(KINDS)} のどれかを渡してください")
    # 振る数が範囲の外
    if not 1 <= count <= NEXT_ID_MAX_COUNT:
        raise ArgumentError("count", f"1〜{NEXT_ID_MAX_COUNT} の整数で渡してください")
    require_workspace(root)
    typed_kind = cast(Kind, kind)
    items = read_kind_items(root, typed_kind)
    taken = [removed["id"] for removed in removed_items(load_changes(root))]
    return {"ids": reserve_ids(root.resolve(), typed_kind, items, taken, count=count)}


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
    at = now()
    loaded = load_changes(root)
    # 外部の変更が入っていれば、先に外部の変更のまとまりにする
    flushed = flush_pending(loaded, "ai", at)
    committed, change_set = commit_pending(flushed, text, at, by="ai")
    # まとめる自分の書き換えが無い: 外部の変更のまとまりだけを書く（あれば）
    if change_set is None:
        if flushed != loaded:
            _write_changes(root, flushed)
        return {
            "id": None,
            "at": None,
            "summary": None,
            "added": [],
            "changed": [],
            "removed": [],
        }
    _write_changes(root, committed)
    return {
        "id": change_set["id"],
        "at": change_set["at"],
        "summary": change_set["summary"],
        "added": change_set["added"],
        "changed": change_set["changed"],
        "removed": [
            {"id": removed["id"], "kind": removed["kind"], "title": removed["title"]}
            for removed in change_set.get("removed", [])
        ],
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


def run_write_release(root: Path, path: str, content: str) -> dict[str, Any]:
    """write-release の処理。`release/` の下に 1 ファイルを書き、書いたパスとバイト数を返す。"""
    written, size = write_release(root, path, content)
    return {"path": written, "bytes": size}


def run_export(root: Path, out: Path, now: NowFn = now_utc) -> dict[str, Any]:
    """書き出す先を確かめて配る書き出しを書き、そのパスを返す。"""
    # ワークスペースを読む前に確かめる（誤った out では何も読まず、書かない）
    resolved = validate_export_out(out)
    path = export_preview(load_workspace(root), out=resolved, built_at=now())
    return {"path": str(path)}


def run_preview_url(root: Path, previews: PreviewRegistry, *, diff: str | None = None) -> dict[str, Any]:
    """ワークスペースを確かめて配信を立て（立っていればそのまま）、URL を返す。立てたときは直下の README にも URL を書く。`diff` を渡したときは、そのまとまりの差分を開く URL にする。"""
    require_workspace(root)
    # まとまりを指すときは、配信を立てる前に記録にあるかを確かめる
    if diff is not None and all(change_set["id"] != diff for change_set in load_changes(root)["sets"]):
        raise ArgumentError("diff", f"記録に無いまとまりです: {diff}")
    url, started = previews.start(root)
    # この呼び出しで立てたときだけ、README のプレビューの節を URL にする
    if started:
        try:
            write_readme(root, preview_url=url)
        except WriteFailedError as error:
            # README を書けなくても配信は止めず、URL を返す
            logger.warning("README を書けなかった: %s", error)
    # README には時点を持たない URL を書き、返す URL にだけハッシュを付ける
    return {"url": url if diff is None else f"{url}#diff={diff}", "workspace": str(root), "started": started}


def run_readme(root: Path, previews: PreviewRegistry) -> dict[str, Any]:
    """ワークスペースを確かめ、直下の README を今の値と配っている URL で書き直す。"""
    require_workspace(root)
    url = previews.url_of(root)
    written = write_readme(root, preview_url=url)
    return {"path": str(root / README_FILE), "written": written, "preview_url": url}


def run_threads(
    root: Path, status: str | None, tag: str | None, unread: bool, awaiting: bool
) -> dict[str, Any]:
    """スレッドを絞ったキーだけの一覧を出力の形にする。"""
    # 決まった値でない状態
    if status not in (None, "open", "closed", "all"):
        raise ArgumentError("status", "open・closed・all のどれかを渡してください")
    rows = list_threads(
        load_workspace(root),
        status=cast("Literal['open', 'closed', 'all'] | None", status),
        tag=tag,
        unread=unread,
        awaiting=awaiting,
    )
    return {"items": rows}


def run_thread(
    root: Path,
    thread_id: str,
    unread_only: bool,
    *,
    lock: Callable[[], AbstractContextManager[None]],
) -> dict[str, Any]:
    """スレッド 1 件を返し、返した未読の書き込みを既読にする。未読が無ければ鍵を取らない。"""
    require_workspace(root)
    view, unread_ids = view_thread(root, thread_id, unread_only=unread_only)
    # 未読を返した: 鍵の中で既読にする
    if unread_ids:
        with lock():
            mark_thread_read(root, thread_id, unread_ids)
    return view


def run_new_thread(
    root: Path,
    body: str,
    summary: str,
    tags: list[str] | None,
    target: str | None,
    now: NowFn = now_utc,
) -> dict[str, Any]:
    """AI の書き込みを最初の 1 件にしたスレッドを立て、出力の形にする。"""
    thread_id, post_id, created = create_thread(
        load_workspace(root), body=body, summary=summary, tags=tags, target=target, now=now
    )
    return {"id": thread_id, "post": post_id, "created": created}


def run_reply(
    root: Path,
    thread_id: str,
    body: str,
    summary: str,
    take: bool,
    now: NowFn = now_utc,
) -> dict[str, Any]:
    """スレッドへ返信し、出力の形にする。"""
    require_workspace(root)
    post_id, created, taken = reply_thread(
        root, thread_id, body=body, summary=summary, take=take, now=now
    )
    return {"id": thread_id, "post": post_id, "created": created, "taken": taken}


def run_set_thread_status(
    root: Path, thread_id: str, status: str, reason: str | None, now: NowFn = now_utc
) -> dict[str, Any]:
    """書き手を AI にしてスレッドの状態を変え、出力の形にする。"""
    require_workspace(root)
    changed = set_thread_status(root, thread_id, status=status, reason=reason, author="ai", now=now)
    return {"id": thread_id, "status": status, "changed": changed}


def run_update_thread(
    root: Path,
    thread_id: str,
    summary: str | None,
    tags: list[str] | None,
    take: bool,
    now: NowFn = now_utc,
) -> dict[str, Any]:
    """スレッドの要約とタグを書き換え、出力の形にする。"""
    require_workspace(root)
    taken = update_thread(root, thread_id, summary=summary, tags=tags, take=take, now=now)
    return {"id": thread_id, "taken": taken}


def _read_item_body(workspace: Workspace, item: dict[str, Any]) -> str | None:
    """項目の `body` が指す本文を読む（`body` を持たないか、ファイルが無ければ None）。"""
    name = item.get("body")
    return read_body(workspace, name) if isinstance(name, str) else None


def _stack_changes(
    workspace: Workspace,
    record: Changes,
    *,
    row: ItemHistory,
    before_item: dict[str, Any],
    after_item: dict[str, Any],
    before_body: str | None,
    after_body: str | None,
    at: str,
    editor: str = EDITOR,
) -> tuple[ItemHistory, Changes]:
    """変更履歴の 1 回分を作って履歴の行に積み、通し番号を振った行と、新しい記録を返す。"""
    limit = history_limit(workspace.settings)
    entry = make_entry(
        before_item,
        after_item,
        before_body=before_body,
        after_body=after_body,
        seq=record["last_seq"] + 1,
        at=at,
        by=cast(Any, editor),
    )
    read_seq = record.get("read_seq")
    # 変わったものが無い: 通し番号は進めない
    if entry is None:
        return cast(ItemHistory, stack_history(dict(row), None, limit, read_seq=read_seq)), record
    # 変わった: 通し番号を振り、行の seq にして変更履歴を積む
    record, seq = advance_seq(record)
    stacked = cast(
        ItemHistory, stack_history({**row, "seq": seq}, entry, limit, read_seq=read_seq)
    )
    # 積んだ（保持する回数が 0 でない）: まだまとめていない変更に足す
    if limit > 0:
        record = note_pending(record, after_item["id"], "changed")
    return stacked, record


def _start_staged(root: Path, now: NowFn = now_utc) -> Staged:
    """ワークスペース・履歴・まとまりを読み、まだ何も当てていない `Staged` を作る（外部の変更は先にまとめる）。"""
    workspace = load_workspace(root)
    loaded = load_changes(root)
    return Staged(
        workspace=workspace,
        items=workspace.items,
        touched=frozenset(),
        bodies={},
        history=load_item_history(root),
        changes=flush_pending(loaded, "ai", now()),
        original=loaded,
    )


def _batch_of(staged: Staged, original: Changes) -> BatchChange:
    """当てた書き換えを、書き込む変更にする（履歴・まとまりは変わったときだけ書く）。"""
    rows = load_item_history(staged.workspace.root)
    return BatchChange(
        items={kind: staged.items[kind] for kind in KINDS if kind in staged.touched},
        bodies=list(staged.bodies.values()),
        history=dict(staged.history) if staged.history != rows else None,
        changes=dict(staged.changes) if staged.changes != original else None,
        removed_bodies=list(staged.removed_bodies),
    )


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
    """`item` の `body_markdown` を `docs/{ID}.md`、`body_html` を `docs/{ID}.html` に書く本文にする。"""
    markdown = item.get(BODY_INPUT_KEY)
    html = item.get(HTML_BODY_INPUT_KEY)
    if markdown is not None:
        return BodyWrite(name=f"{BODY_DIR}/{item_id}.md", text=str(markdown))
    if html is not None:
        return BodyWrite(name=f"{BODY_DIR}/{item_id}.html", text=str(html))
    # 本文を渡していない
    return None


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
                "destructive": step.op in DESTRUCTIVE_OPS or bool(step.args.get("destructive")),
                "summary": describe_step(step),
                **_step_report(report.reports, step),
            }
            for step in report.steps
        ],
        "needs_values": [asdict(value) for value in report.needs_values],
        "backup": asdict(report.backup) if report.backup is not None else None,
        "recorded": _version_text(report.recorded),
    }


def _step_report(reports: list[str], step: MigrationStep) -> dict[str, list[str]]:
    """手順が報告の行を返していれば `{"report": 行の並び}`、無ければ空の辞書を返す。"""
    prefix = f"{step.version} #{step.index}: "
    lines = [line.removeprefix(prefix) for line in reports if line.startswith(prefix)]
    return {"report": lines} if lines else {}


def _version_text(version: Version | None) -> str | None:
    """版を文字列にする。None（版を記録する前の形式・書いていない）はそのまま None。"""
    return str(version) if version is not None else None
