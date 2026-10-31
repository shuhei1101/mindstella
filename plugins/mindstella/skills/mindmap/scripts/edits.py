"""プレビューで利用者が溜めた保存待ちの編集（`edits.yaml`）を読み書きし、まとめて保存するときに項目と設定へ当てる。鍵は呼ぶ側が取る。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from checker import find_referrers
from comments import read_validated
from commands import (
    BODY_INPUT_KEY,
    HTML_BODY_INPUT_KEY,
    OPTION_KEYS,
    REF_KEYS,
    Staged,
    apply_option_edit,
    stage_add,
    stage_update,
    switch_adopted,
)
from errors import (
    EditConflictError,
    EditInvalidError,
    EditNotFoundError,
    EditsBlockedError,
    ItemNotFoundError,
    MindmapError,
)
from history import (
    RemovedItem,
    advance_seq,
    commit_pending,
    load_changes,
    note_removed,
    removed_items,
)
from kinds import KINDS, SETTINGS_FILE, Kind, records_root
from settings_update import (
    EDITABLE_KEYS,
    REMOVABLE_KEYS,
    SettingsStage,
    stage_settings,
)
from store import (
    EDITS_FILE,
    BatchChange,
    NowFn,
    Workspace,
    dump_yaml,
    find_item,
    kind_required_keys,
    load_key_validator,
    load_workspace,
    next_id,
    now_utc,
    read_body,
    remove_files,
    require_workspace,
    save_batch,
    validate_workspace,
    write_failed,
    write_temp,
)

# `SCHEMA_DIR` の下の保存待ちの編集のスキーマのファイル名
EDITS_SCHEMA = "edits.schema.json"

# 編集の ID の頭（`E-{連番}`）
EDIT_ID_PREFIX = "E"

# 追加する項目の仮の ID の頭（`new-{連番}`）
NEW_ID_PREFIX = "new"

# 設定の編集の向け先
SETTINGS_TARGET = "settings"

# 編集の種類
EDIT_OPS = (
    "set",
    "option-add",
    "option-edit",
    "option-remove",
    "adopt",
    "item-add",
    "item-remove",
    "setting",
)

# 付け替えの対応を持てる設定のキー → まとめて保存が `stage_settings` に渡す引数の名前
MAPPABLE_SETTING_KEYS = {
    "phases": "phase_map",
    "targets": "target_map",
    "categories": "category_map",
}

# `set`・`item-add` の `value` に渡せないキー（案は `option-*`・`adopt` で編集する）
UNEDITABLE_KEYS = frozenset(
    {
        "id",
        "created",
        "updated",
        "updated_by",
        "history",
        "history_dropped_seq",
        "seq",
        "added_seq",
        "options",
    }
)

# 保存で書いた項目の編集した人
USER_EDITOR = "user"

# 保存の前にまだまとめていない変更があるとき、先に作るまとまりの説明
AI_PENDING_SUMMARY = "まとめる前の AI の書き換え"

# 利用者の編集をまとめたまとまりの説明
USER_EDIT_SUMMARY = "画面からの編集"

# 項目の本文を編集するキー
BODY_KEY = "body"

# 検討事項の種類
DECISION_KIND: Kind = "decision"

# 採用を外したときに決定済みから戻す状態
UNDECIDED_STATUS = "未決定"
DECIDED_STATUS = "決定済み"

# `item-add` の `key`（YAML のファイル名の頭）→ 種類
KIND_BY_STEM: dict[str, Kind] = {Path(spec.file).stem: kind for kind, spec in KINDS.items()}

type EditOp = Literal[
    "set",
    "option-add",
    "option-edit",
    "option-remove",
    "adopt",
    "item-add",
    "item-remove",
    "setting",
]

type BlockedReason = Literal["changed", "missing", "referenced", "invalid"]


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingEdit:
    """`edits.yaml` の 1 件。"""

    id: str
    # 項目の ID・追加する項目の仮の ID（`new-{連番}`）・`settings`
    target: str
    op: EditOp
    # 項目のキー・案の記号・種類・設定のキー。`item-remove` は None
    key: str | None
    # 編集した後の値
    value: Any
    # 最初に溜めたときの元の値。`option-add`・`item-add` は None
    before: Any
    # 項目への編集で、最初に溜めた時点のその項目の `updated`。`item-add`・`setting` は None
    base: str | None
    # 最初に溜めた日時
    created: str
    # `setting` の付け替えの対応（書かないときは None）
    map: dict[str, str | None] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class EditFile:
    """`edits.yaml` の中身。"""

    # 最後に振った編集の連番（無ければ 0）
    seq: int
    # 最後に振った仮の ID の連番（無ければ 0）
    new_seq: int
    # 連番の小さい順の編集
    items: list[PendingEdit]


@dataclass(frozen=True, slots=True, kw_only=True)
class BlockedEdit:
    """保存の 409 の `blocked[]` の 1 件。"""

    id: str
    reason: BlockedReason
    # 利用者に出す日本語の理由
    detail: str
    # `referenced` のとき、消す項目を指している項目の ID
    refs: list[str] = field(default_factory=list)


def load_edits(root: Path) -> EditFile:
    """`edits.yaml` を読み、スキーマと突き合わせて `EditFile` にする。"""
    value = read_validated(records_root(root) / EDITS_FILE, EDITS_SCHEMA)
    # ファイルが無い
    if value is None:
        return EditFile(seq=0, new_seq=0, items=[])
    items = [
        PendingEdit(
            id=item["id"],
            target=item["target"],
            op=item["op"],
            key=item.get("key"),
            value=item.get("value"),
            before=item.get("before"),
            base=item.get("base"),
            created=item["created"],
            map=item.get("map"),
        )
        for item in value["items"]
    ]
    return EditFile(
        seq=value["seq"],
        new_seq=value["new_seq"],
        items=sorted(items, key=lambda edit: _number_of(edit.id)),
    )


def list_edits(root: Path) -> dict[str, Any]:
    """保存待ちの編集を、控え（`base`・`map`）を除いて溜めた順に並べ、件数を添えた読み取りの形にする。"""
    require_workspace(root)
    edits = load_edits(root).items
    return {
        "items": [
            {
                "id": edit.id,
                "target": edit.target,
                "op": edit.op,
                "key": edit.key,
                "value": edit.value,
                "before": edit.before,
                "created": edit.created,
            }
            for edit in edits
        ],
        "count": len(edits),
    }


def add_edit(root: Path, data: dict[str, Any], now: NowFn = now_utc) -> tuple[dict[str, Any], bool]:
    """1 件の編集を確かめ、新しく溜めるか同じ編集を書き換えるか外して、`edits.yaml` を書く。"""
    op, target, key, value, mapping = _parse_edit_input(data)
    workspace = load_workspace(root)
    edit_file = load_edits(root)
    pending = edit_file.items
    # 向け先と、溜めた編集との食い違いを確かめる
    kind = _check_target(workspace, pending, op, target, key, value)
    if op in ("set", "item-add"):
        _check_values(kind, op, key, value)
    if op == "setting":
        _check_setting(key, value)
    # 同じ編集があるか探す
    existing = next((edit for edit in pending if _is_same_edit(edit, op, target, key)), None)
    new_seq = edit_file.new_seq
    seq = edit_file.seq
    # 足す項目の仮の ID: 省いたときは新しく振る
    if op == "item-add" and target is None:
        new_seq += 1
        target = f"{NEW_ID_PREFIX}-{new_seq}"
    if op == "setting":
        target = SETTINGS_TARGET
    draft = PendingEdit(
        id="", target=target, op=op, key=key, value=value, before=None, base=None, created=""
    )
    current = _current_value(workspace, draft)
    # 今の値に戻した編集は外す（溜めた編集が無ければ何も溜めない）
    if op in ("set", "option-edit", "adopt", "setting") and _is_current(op, value, current):
        kept = [edit for edit in pending if edit is not existing]
        _write_edits(root, EditFile(seq=seq, new_seq=new_seq, items=kept))
        return {"id": None, "target": target, "count": len(kept)}, False
    if existing is not None:
        # 同じ編集は値だけを書き換え、ID・元の値・更新日時の控え・溜めた日時は最初のまま
        changed = replace(existing, key=key, value=value, map=mapping)
        items = [changed if edit is existing else edit for edit in pending]
        _write_edits(root, EditFile(seq=seq, new_seq=new_seq, items=items))
        return {"id": existing.id, "target": target, "count": len(items)}, False
    seq += 1
    edit = PendingEdit(
        id=f"{EDIT_ID_PREFIX}-{seq}",
        target=target,
        op=op,
        key=key,
        value=value,
        before=current,
        base=_base_of(workspace, op, target),
        created=now(),
        map=mapping,
    )
    items = [*pending, edit]
    _write_edits(root, EditFile(seq=seq, new_seq=new_seq, items=items))
    return {"id": edit.id, "target": target, "count": len(items)}, True


def delete_edit(root: Path, edit_id: str) -> dict[str, Any]:
    """1 件の編集を外す。足した案を外すときはその案の採用の編集も、足した項目を外すときはその項目への編集も一緒に外す。"""
    edit_file = load_edits(root)
    found = next((edit for edit in edit_file.items if edit.id == edit_id), None)
    if found is None:
        raise EditNotFoundError(f"編集がありません: {edit_id}")
    removed = [found]
    # 足した案を外すときは、その案を採用する切り替えも外す
    if found.op == "option-add":
        removed.extend(
            edit
            for edit in edit_file.items
            if edit.op == "adopt" and edit.target == found.target and edit.value == found.key
        )
    # 足した項目を外すときは、その項目へのほかの編集も外す
    if found.op == "item-add":
        removed.extend(
            edit for edit in edit_file.items if edit is not found and edit.target == found.target
        )
    removed_ids = {edit.id for edit in removed}
    kept = [edit for edit in edit_file.items if edit.id not in removed_ids]
    _write_edits(root, replace(edit_file, items=kept))
    return {"removed": [edit.id for edit in removed], "count": len(kept)}


def save_edits(root: Path, now: NowFn = now_utc) -> dict[str, Any]:
    """保存待ちの編集を全て確かめてメモリの上で当て、まとまりにして 1 回で書く。1 件でも書き込めなければ何も書かない。"""
    workspace = load_workspace(root)
    edit_file = load_edits(root)
    if not edit_file.items:
        raise EditInvalidError("保存待ちの編集がありません")
    # 削除を溜めた項目へのほかの編集は当てずに捨てる（確かめもしない）
    removing = {edit.target for edit in edit_file.items if edit.op == "item-remove"}
    live = [
        edit for edit in edit_file.items if edit.op == "item-remove" or edit.target not in removing
    ]
    blocked = _find_blocked(workspace, live)
    # まだまとめていない AI の変更は、先に別のまとまりにする
    record, _ = commit_pending(load_changes(root), AI_PENDING_SUMMARY, now())
    staged = Staged(
        workspace=workspace,
        items=workspace.items,
        touched=frozenset(),
        bodies={},
        changes=record,
    )
    blocked_ids = {entry.id for entry in blocked}
    runnable = [edit for edit in live if edit.id not in blocked_ids]
    staged, settings_stage, mapping, invalid = _apply_edits(staged, runnable, now=now)
    blocked = [*blocked, *invalid]
    staged, referenced = _remove_items(staged, runnable)
    blocked = [*blocked, *referenced]
    blocked = [*blocked, *_validation_blocked(staged, settings_stage, runnable, mapping)]
    if blocked:
        order = {edit.id: index for index, edit in enumerate(edit_file.items)}
        ordered = sorted(
            {entry.id: entry for entry in blocked}.values(), key=lambda entry: order[entry.id]
        )
        raise EditsBlockedError(
            f"{len(ordered)} 件の編集を書き込めないため、何も保存していません。", blocked=ordered
        )
    # 利用者の変更を 1 つのまとまりにする
    at = now()
    record, change_set = commit_pending(staged.changes, USER_EDIT_SUMMARY, at)
    settings_written = settings_stage is not None and (
        settings_stage.settings != workspace.settings
    )
    touched = set(staged.touched)
    if settings_stage is not None:
        touched.update(
            kind for kind in KINDS if settings_stage.items[kind] != workspace.items[kind]
        )
    save_batch(
        workspace,
        BatchChange(
            items={kind: staged.items[kind] for kind in KINDS if kind in touched},
            bodies=list(staged.bodies.values()),
            changes=dict(record),
            removed_bodies=list(staged.removed_bodies),
            settings=settings_stage.settings if settings_written and settings_stage else None,
            edits=_edit_dict(EditFile(seq=edit_file.seq, new_seq=edit_file.new_seq, items=[])),
        ),
    )
    return {
        "set": change_set["id"] if change_set is not None else None,
        "at": at,
        "added": [{"temp": temp, "id": item_id} for temp, item_id in mapping.items()],
        "changed": list(change_set["changed"]) if change_set is not None else [],
        "removed": [entry["id"] for entry in (change_set.get("removed", []) if change_set else [])],
        "settings": list(settings_stage.changed) if settings_stage is not None else [],
    }


def _parse_edit_input(
    data: dict[str, Any],
) -> tuple[EditOp, str | None, str | None, Any, dict[str, str | None] | None]:
    """本文から `op`・`target`・`key`・`value`・`map` を取り出し、`op` ごとに要るキーと `map` の渡し方を確かめる。"""
    op = data.get("op")
    if op not in EDIT_OPS:
        raise EditInvalidError(f"op: {'・'.join(EDIT_OPS)} のどれかを渡してください")
    target = data.get("target")
    key = data.get("key")
    if target is not None and (not isinstance(target, str) or not target):
        raise EditInvalidError("target: 空でない文字列を渡してください")
    if key is not None and not isinstance(key, str):
        raise EditInvalidError("key: 文字列を渡してください")
    # 向け先の要る編集
    if op not in ("item-add", "setting") and target is None:
        raise EditInvalidError(f"target: {op} には項目の ID を渡してください")
    if op != "item-remove" and key is None:
        raise EditInvalidError(f"key: {op} には key を渡してください")
    if op in ("set", "option-add", "option-edit", "adopt", "item-add", "setting") and (
        "value" not in data
    ):
        raise EditInvalidError(f"value: {op} には value を渡してください")
    value = data.get("value")
    if op in ("option-add", "option-edit", "item-add") and not isinstance(value, dict):
        raise EditInvalidError("value: オブジェクトを渡してください")
    if op in ("option-add", "option-edit"):
        unknown = [name for name in value if name not in OPTION_KEYS]
        if unknown:
            raise EditInvalidError(f"value: 渡せないキーです: {'、'.join(unknown)}")
    if op == "adopt" and value is not None and not isinstance(value, str):
        raise EditInvalidError("value: 採用する案の記号か null を渡してください")
    mapping = data.get("map")
    if mapping is not None:
        _check_map(op, key, mapping)
    return op, target, key, value, mapping


def _check_map(op: str, key: str | None, mapping: Any) -> None:
    """`map` が、渡せる `op`・`key` で、値の型が合うかを確かめる。"""
    if op != "setting" or key not in MAPPABLE_SETTING_KEYS:
        raise EditInvalidError("map: phases・targets・categories の設定の編集だけが渡せます")
    if not isinstance(mapping, dict) or not all(isinstance(name, str) for name in mapping):
        raise EditInvalidError("map: 古い値 → 新しい値のオブジェクトを渡してください")
    for new in mapping.values():
        if not isinstance(new, str):
            raise EditInvalidError("map: 値は文字列にしてください")


def _check_target(
    workspace: Workspace,
    pending: list[PendingEdit],
    op: EditOp,
    target: str | None,
    key: str | None,
    value: Any,
) -> Kind | None:
    """向け先の項目・仮の ID・案があるか、溜めた編集と食い違わないかを確かめ、項目の種類を返す。"""
    if op == "setting":
        return None
    if op == "item-add":
        # 種類（YAML のファイル名の頭）
        if key not in KIND_BY_STEM:
            raise EditInvalidError(f"key: {'・'.join(KIND_BY_STEM)} のどれかを渡してください")
        if target is not None and not any(
            edit.op == "item-add" and edit.target == target for edit in pending
        ):
            raise EditNotFoundError(f"追加する項目がありません: {target}")
        return KIND_BY_STEM[key]
    if target is None:
        raise EditInvalidError("target: 項目の ID を渡してください")
    if target.startswith(f"{NEW_ID_PREFIX}-"):
        raise EditInvalidError(
            f"target: 追加する項目 {target} は item-add の value を書き換えてください"
        )
    try:
        ref = find_item(workspace, target)
    except ItemNotFoundError as error:
        raise EditNotFoundError(str(error)) from error
    # 削除を溜めた項目へは、削除以外の編集を溜めない
    if op != "item-remove" and any(
        edit.op == "item-remove" and edit.target == target for edit in pending
    ):
        raise EditConflictError(f"{target} は削除を溜めているため、編集を溜められません")
    if op in ("option-add", "option-edit", "option-remove", "adopt"):
        symbols = _option_symbols(ref.item, pending, target)
        # 足す案の記号が既にある
        if op == "option-add" and key in symbols:
            raise EditConflictError(f"{target} に案 {key} が既にあります")
        checked = value if op == "adopt" else key
        if op != "option-add" and checked is not None and checked not in symbols:
            raise EditNotFoundError(f"案がありません: {target} の案 {checked}")
    return ref.kind


def _option_symbols(item: dict[str, Any], pending: list[PendingEdit], target: str) -> set[str]:
    """項目の案の記号と、溜めた案の追加の記号を集める。"""
    symbols = {str(option.get("key")) for option in item.get("options") or []}
    symbols.update(
        str(edit.key) for edit in pending if edit.op == "option-add" and edit.target == target
    )
    return symbols


def _check_values(kind: Kind | None, op: EditOp, key: str | None, value: Any) -> None:
    """`set`・`item-add` の値を、その種類のスキーマのキーの型で確かめる。"""
    if kind is None or (key is None and op == "set"):
        raise EditInvalidError("key: 項目の種類とキーを渡してください")
    if op == "set":
        values = {key: value}
    else:
        values = value
        title = values.get("title")
        if not isinstance(title, str) or not title.strip():
            raise EditInvalidError("title: タイトルを書いてください")
    for name, entry in values.items():
        if name in UNEDITABLE_KEYS:
            raise EditInvalidError(f"{name}: 編集できないキーです")
        # 本文は文字列で渡す（ファイル名は保存のときに決まる）
        if name == BODY_KEY:
            if not isinstance(entry, str):
                raise EditInvalidError("body: 文字列を渡してください")
            continue
        validator = load_key_validator(kind, name)
        if validator is None:
            raise EditInvalidError(f"{name}: この種類にないキーです")
        # null はそのキーを消す編集（必須のキーは消せない）
        if entry is None:
            if name in kind_required_keys(kind):
                raise EditInvalidError(f"{name}: 消せないキーです")
            continue
        found = sorted(validator.iter_errors(entry), key=lambda error: error.message)
        if found:
            raise EditInvalidError(f"{name}: {found[0].message}")
        if name == "title" and not entry.strip():
            raise EditInvalidError("title: タイトルを書いてください")


def _check_setting(key: str | None, value: Any) -> None:
    """設定のキーが書き換えられるものか、null で消せるキーかを確かめる。"""
    if key not in EDITABLE_KEYS:
        raise EditInvalidError(f"key: {key} は書き換えられない設定のキーです")
    if value is None and key not in REMOVABLE_KEYS:
        raise EditInvalidError(f"value: {key} は null で消せません")


def _is_same_edit(edit: PendingEdit, op: str, target: str | None, key: str | None) -> bool:
    """溜めた編集が、これから溜める編集と同じ向け先・種類・キーかを返す。"""
    if op == "setting":
        return edit.op == op and edit.key == key
    if edit.op != op or edit.target != target:
        return False
    # 採用の切り替えと追加する項目は、キーが違っても 1 件にまとめる
    return op in ("adopt", "item-add") or edit.key == key


def _is_current(op: str, value: Any, current: Any) -> bool:
    """編集した後の値が、今のワークスペースの値と同じ（元の値に戻した）かを返す。"""
    if op == "option-edit":
        return isinstance(current, dict) and all(
            current.get(name) == entry for name, entry in value.items()
        )
    return bool(value == current)


def _current_value(workspace: Workspace, edit: PendingEdit) -> Any:
    """編集の向け先の今のワークスペースの値を返す（元の値の控えと、元に戻したかの判定に使う）。"""
    if edit.op == "setting":
        return workspace.settings.get(str(edit.key))
    if edit.op not in ("set", "option-edit", "adopt"):
        return None
    try:
        item = find_item(workspace, edit.target).item
    except ItemNotFoundError:
        return None
    if edit.op == "set":
        if edit.key == BODY_KEY:
            name = item.get("body")
            return read_body(workspace, name) if isinstance(name, str) else None
        return item.get(str(edit.key))
    options = item.get("options") or []
    if edit.op == "adopt":
        return next(
            (option.get("key") for option in options if option.get("adopted") is True), None
        )
    option = next((entry for entry in options if entry.get("key") == edit.key), None)
    if option is None:
        return None
    return {name: entry for name, entry in option.items() if name not in ("key", "adopted")}


def _base_of(workspace: Workspace, op: str, target: str) -> str | None:
    """項目への編集のとき、その項目の今の `updated` を返す（`item-add`・`setting` は None）。"""
    if op in ("item-add", "setting"):
        return None
    updated = find_item(workspace, target).item.get("updated")
    return updated if isinstance(updated, str) else None


def _find_blocked(workspace: Workspace, edits: list[PendingEdit]) -> list[BlockedEdit]:
    """当てる前に分かる、溜めた後の書き換え（`changed`）と項目の消失（`missing`）の編集を溜めた順に返す。"""
    blocked: list[BlockedEdit] = []
    for edit in edits:
        if edit.op == "item-add":
            continue
        if edit.op == "setting":
            # 溜めたときの設定の値と、今の値が違う
            if workspace.settings.get(str(edit.key)) != edit.before:
                blocked.append(
                    BlockedEdit(
                        id=edit.id,
                        reason="changed",
                        detail=f"溜めた後に設定 {edit.key} が書き換わっています",
                    )
                )
            continue
        try:
            item = find_item(workspace, edit.target).item
        except ItemNotFoundError:
            blocked.append(
                BlockedEdit(id=edit.id, reason="missing", detail=f"項目がありません: {edit.target}")
            )
            continue
        # 溜めた時点の更新日時と違う
        if edit.base is not None and item.get("updated") != edit.base:
            blocked.append(
                BlockedEdit(
                    id=edit.id,
                    reason="changed",
                    detail=f"溜めた後に {edit.target} が書き換わっています",
                )
            )
    return blocked


def _apply_edits(
    staged: Staged, edits: list[PendingEdit], *, now: NowFn
) -> tuple[Staged, SettingsStage | None, dict[str, str], list[BlockedEdit]]:
    """設定 → 項目の追加 → キー・案・採用の順に、編集をメモリの上で当てる。当てられなかった編集は `invalid` で返す。"""
    invalid: list[BlockedEdit] = []
    settings_stage: SettingsStage | None = None
    workspace = staged.workspace
    # 設定
    setting_edits = [edit for edit in edits if edit.op == "setting"]
    if setting_edits:
        settings_stage, failed = _stage_settings_guarded(workspace, setting_edits, now)
        invalid.extend(failed)
    if settings_stage is not None:
        staged = replace(
            staged,
            workspace=replace(workspace, settings=settings_stage.settings),
            items=settings_stage.items,
            touched=staged.touched
            | {kind for kind in KINDS if settings_stage.items[kind] != workspace.items[kind]},
        )
    # 項目の追加（仮の ID の連番の順）
    adds = sorted(
        (edit for edit in edits if edit.op == "item-add"), key=lambda edit: _number_of(edit.target)
    )
    mapping = _predict_ids(staged, adds)
    for edit in adds:
        item = _resolve_temp_refs(_body_input(dict(edit.value)), mapping)
        try:
            staged, _ = stage_add(
                staged, KIND_BY_STEM[str(edit.key)], item, now, editor=USER_EDITOR
            )
        except MindmapError as error:
            invalid.append(_invalid(edit, error))
    # 項目ごとにまとめて、キー・案・採用を当てる
    groups: dict[str, list[PendingEdit]] = {}
    for edit in edits:
        if edit.op in ("set", "option-add", "option-edit", "option-remove", "adopt"):
            groups.setdefault(edit.target, []).append(edit)
    for target, group in groups.items():
        staged, failed = _apply_item_edits(staged, target, group, now)
        invalid.extend(failed)
    # 参照のキーの指す先があるか（追加した項目も含めて確かめる）
    invalid.extend(_missing_refs(staged, edits, mapping, {entry.id for entry in invalid}))
    return staged, settings_stage, mapping, invalid


def _stage_settings_guarded(
    workspace: Workspace, edits: list[PendingEdit], now: NowFn
) -> tuple[SettingsStage | None, list[BlockedEdit]]:
    """設定の編集を 1 回で当てる。当てられなければ 1 件ずつ試して、当てられない編集を挙げる。"""
    def attempt(group: list[PendingEdit]) -> SettingsStage:
        """渡した設定の編集をまとめて当てる。"""
        maps: dict[str, dict[str, Any]] = {}
        for edit in group:
            if edit.map is not None:
                maps[MAPPABLE_SETTING_KEYS[str(edit.key)]] = edit.map
        return stage_settings(
            workspace,
            {str(edit.key): edit.value for edit in group},
            editor=USER_EDITOR,
            now=now,
            **maps,
        )

    try:
        return attempt(edits), []
    except MindmapError as error:
        failed: list[BlockedEdit] = []
        # 1 件ずつ試して、当てられない編集を挙げる
        for edit in edits:
            try:
                attempt([edit])
            except MindmapError as single:
                failed.append(_invalid(edit, single))
        # どの 1 件でも当てられる: 組み合わせの誤りなので全てを挙げる
        if not failed:
            return None, [_invalid(edit, error) for edit in edits]
        failed_ids = {entry.id for entry in failed}
        rest = [edit for edit in edits if edit.id not in failed_ids]
        if not rest:
            return None, failed
        try:
            return attempt(rest), failed
        except MindmapError as combined:
            return None, [*failed, *(_invalid(edit, combined) for edit in rest)]


def _apply_item_edits(
    staged: Staged, target: str, group: list[PendingEdit], now: NowFn
) -> tuple[Staged, list[BlockedEdit]]:
    """1 項目へのキー・案・採用の編集を溜めた順に当てて、1 回の更新にする。"""
    ref = find_item(replace(staged.workspace, items=staged.items), target)
    working = dict(ref.item)
    body: str | None = None
    failed: list[BlockedEdit] = []
    applied: list[PendingEdit] = []
    for edit in group:
        try:
            if edit.op == "set":
                if edit.key == BODY_KEY:
                    body = edit.value
                elif edit.value is None:
                    working.pop(str(edit.key), None)
                else:
                    working[str(edit.key)] = edit.value
            elif edit.op == "adopt":
                working = _adopt(working, edit.value)
            else:
                action = {"option-add": "add", "option-edit": "update", "option-remove": "remove"}[
                    edit.op
                ]
                option = None if edit.op == "option-remove" else edit.value
                working["options"] = apply_option_edit(working, action, str(edit.key), option)  # type: ignore[arg-type]
        except MindmapError as error:
            failed.append(_invalid(edit, error))
            continue
        applied.append(edit)
    if not applied:
        return staged, failed
    changes: dict[str, Any] = {
        name: entry for name, entry in working.items() if ref.item.get(name) != entry
    }
    changes.update({name: None for name in ref.item if name not in working})
    if body is not None:
        html = str(ref.item.get("body", "")).endswith(".html")
        changes[HTML_BODY_INPUT_KEY if html else BODY_INPUT_KEY] = body
    try:
        staged, _ = stage_update(staged, target, changes, now, editor=USER_EDITOR)
    except MindmapError as error:
        failed.extend(_invalid(edit, error) for edit in applied)
    return staged, failed


def _adopt(item: dict[str, Any], key: str | None) -> dict[str, Any]:
    """採用する案を切り替える。`None` は採用を外し、決定済みなら未決定に戻す。"""
    if key is not None:
        switched, _ = switch_adopted(item, key)
        return switched
    options = [
        {name: entry for name, entry in option.items() if name != "adopted"}
        for option in item.get("options") or []
    ]
    status = UNDECIDED_STATUS if item.get("status") == DECIDED_STATUS else item.get("status")
    return {**item, "options": options, "status": status}


def _predict_ids(staged: Staged, adds: list[PendingEdit]) -> dict[str, str]:
    """追加する項目に振られる ID を、仮の ID の順に求める（参照の置き換えに先に使う）。"""
    workspace = replace(staged.workspace, items=staged.items)
    taken = [entry["id"] for entry in removed_items(staged.changes)]
    next_numbers: dict[Kind, int] = {}
    mapping: dict[str, str] = {}
    for edit in adds:
        kind = KIND_BY_STEM[str(edit.key)]
        if kind not in next_numbers:
            next_numbers[kind] = int(next_id(workspace, kind, taken=taken).split("-", 1)[1])
        mapping[edit.target] = f"{KINDS[kind].prefix}-{next_numbers[kind]}"
        next_numbers[kind] += 1
    return mapping


def _resolve_temp_refs(item: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """参照のキーの値の仮の ID を、振った ID に置き換える。"""
    resolved = dict(item)
    for key in REF_KEYS:
        value = resolved.get(key)
        if isinstance(value, list):
            resolved[key] = [mapping.get(entry, entry) for entry in value]
        elif isinstance(value, str):
            resolved[key] = mapping.get(value, value)
    return resolved


def _body_input(item: dict[str, Any]) -> dict[str, Any]:
    """追加する項目の `body`（本文の文字列）を、`body_markdown` の入力にする。"""
    if BODY_KEY not in item:
        return item
    return {
        **{name: entry for name, entry in item.items() if name != BODY_KEY},
        BODY_INPUT_KEY: item[BODY_KEY],
    }


def _missing_refs(
    staged: Staged, edits: list[PendingEdit], mapping: dict[str, str], skip: set[str]
) -> list[BlockedEdit]:
    """参照のキーの値が、記録に無い項目を指している編集を挙げる。"""
    existing = {item["id"] for kind in KINDS for item in staged.items[kind]}
    blocked: list[BlockedEdit] = []
    for edit in edits:
        if edit.id in skip:
            continue
        if edit.op == "set" and edit.key in REF_KEYS:
            values = {str(edit.key): edit.value}
        elif edit.op == "item-add":
            values = _resolve_temp_refs(dict(edit.value), mapping)
        else:
            continue
        for name, entry in values.items():
            if name not in REF_KEYS:
                continue
            ids = entry if isinstance(entry, list) else [entry]
            missing = [ref for ref in ids if isinstance(ref, str) and ref not in existing]
            if missing:
                blocked.append(
                    BlockedEdit(
                        id=edit.id,
                        reason="invalid",
                        detail=f"{name}: {'、'.join(missing)} が記録にありません",
                    )
                )
                break
    return blocked


def _remove_items(staged: Staged, edits: list[PendingEdit]) -> tuple[Staged, list[BlockedEdit]]:
    """項目の削除を当てる。同じ保存で指す側が残る項目は消さず、指している項目を挙げる。"""
    removals = [edit for edit in edits if edit.op == "item-remove"]
    if not removals:
        return staged, []
    removed_ids = {edit.target for edit in removals}
    # 消す項目を除いた後の並びで、ほかの記録が指しているかを見る
    remaining = {
        kind: [item for item in staged.items[kind] if item["id"] not in removed_ids]
        for kind in KINDS
    }
    after = replace(staged.workspace, items=remaining)
    blocked: list[BlockedEdit] = []
    for edit in removals:
        referrers = find_referrers(after, edit.target)
        if referrers:
            refs = list(dict.fromkeys(line.split(": ")[1] for line in referrers))
            blocked.append(
                BlockedEdit(
                    id=edit.id,
                    reason="referenced",
                    detail=f"{'、'.join(refs)} が {edit.target} を指しているため削除できません",
                    refs=refs,
                )
            )
            continue
        staged = _remove_staged(staged, edit.target)
    return staged, blocked


def _remove_staged(staged: Staged, item_id: str) -> Staged:
    """1 項目をメモリの上の並びと本文から消し、消した項目をまだまとめていない変更に記録する。"""
    workspace = replace(staged.workspace, items=staged.items)
    ref = find_item(workspace, item_id)
    record, seq = advance_seq(staged.changes)
    removed: RemovedItem = {
        "id": item_id,
        "kind": ref.kind,
        "title": ref.item["title"],
        "seq": seq,
        "added_seq": ref.item.get("added_seq", 0),
    }
    record = note_removed(record, removed)
    rows = [row for index, row in enumerate(staged.items[ref.kind]) if index != ref.index]
    name = ref.item.get("body")
    removed_bodies = list(staged.removed_bodies)
    # 本文を持ち、`docs/` にそのファイルがあるときだけ、本文も消す
    if isinstance(name, str) and read_body(workspace, name) is not None:
        removed_bodies.append(name)
    return replace(
        staged,
        items={**staged.items, ref.kind: rows},
        touched=staged.touched | {ref.kind},
        changes=record,
        removed_bodies=removed_bodies,
    )


def _validation_blocked(
    staged: Staged,
    settings_stage: SettingsStage | None,
    edits: list[PendingEdit],
    mapping: dict[str, str],
) -> list[BlockedEdit]:
    """当てた後の記録をスキーマと案・状態の決まりに通し、合わない箇所を引き起こした編集に紐づけて挙げる。"""
    raw: dict[str, Any] = dict(staged.workspace.raw)
    for kind in staged.touched:
        raw[KINDS[kind].file] = {"items": staged.items[kind]}
    if settings_stage is not None:
        raw[SETTINGS_FILE] = settings_stage.settings
    problems = validate_workspace(replace(staged.workspace, items=staged.items, raw=raw))
    touched_files = {KINDS[kind].file for kind in staged.touched}
    if settings_stage is not None:
        touched_files.add(SETTINGS_FILE)
    blocked: list[BlockedEdit] = []
    for problem in problems:
        if problem.file not in touched_files:
            continue
        for edit in edits:
            if _causes(edit, problem.id, problem.file, mapping):
                blocked.append(
                    BlockedEdit(
                        id=edit.id,
                        reason="invalid",
                        detail=f"{problem.key}: {problem.detail}",
                    )
                )
    return blocked


def _causes(edit: PendingEdit, item_id: str | None, file: str, mapping: dict[str, str]) -> bool:
    """スキーマに合わない箇所（ファイルと項目の ID）を、この編集が引き起こしたかを返す。"""
    if file == SETTINGS_FILE:
        return edit.op == "setting"
    if edit.op == "setting" or item_id is None:
        return False
    return mapping.get(edit.target, edit.target) == item_id


def _invalid(edit: PendingEdit, error: MindmapError) -> BlockedEdit:
    """当てられなかった編集を、エラーの理由つきの `invalid` にする。"""
    detail = str(error)
    if error.lines:
        detail = f"{detail}: {'、'.join(error.lines)}"
    return BlockedEdit(id=edit.id, reason="invalid", detail=detail)


def _number_of(identifier: str) -> int:
    """`E-3`・`new-2` の形の ID の連番を返す。"""
    return int(identifier.rsplit("-", 1)[1])


def _edit_dict(edit_file: EditFile) -> dict[str, Any]:
    """保存待ちの編集のファイルを YAML に書く辞書にする（`map` は持つときだけ書く）。"""
    items: list[dict[str, Any]] = []
    for edit in edit_file.items:
        entry: dict[str, Any] = {
            "id": edit.id,
            "target": edit.target,
            "op": edit.op,
            "key": edit.key,
            "value": edit.value,
            "before": edit.before,
            "base": edit.base,
            "created": edit.created,
        }
        if edit.map is not None:
            entry["map"] = edit.map
        items.append(entry)
    return {"seq": edit_file.seq, "new_seq": edit_file.new_seq, "items": items}


def _write_edits(root: Path, edit_file: EditFile) -> None:
    """`edits.yaml` を一時ファイルに書いてから置き換える。"""
    path = records_root(root) / EDITS_FILE
    try:
        temp = write_temp(path, dump_yaml(_edit_dict(edit_file)))
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えられなかった: 書いた一時ファイルを残さない
        remove_files([temp])
        raise write_failed(path, error) from error
