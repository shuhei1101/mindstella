"""設定の更新（`update_settings`）の引数の確かめ・設定の置き換え・フェーズ・対象・カテゴリー・タグの付け替え・まとめた書き込み。"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

import yaml

from errors import (
    ArgumentError,
    SchemaMismatchError,
    SettingsInvalidError,
    UnmappedPhaseError,
    UnmappedTagError,
    UnmappedTargetError,
)
from kinds import EDITOR, KINDS, RECORD_DIR, SETTINGS_FILE, Kind, records_root
from store import (
    WHOLE_PATH,
    Change,
    NowFn,
    Workspace,
    build_mismatch_error,
    check_settings,
    dump_yaml,
    format_path,
    load_display_validator,
    load_workspace,
    loses_content_on_rewrite,
    now_utc,
    remove_files,
    validate_workspace,
    write_failed,
    write_temp,
)
from vocabulary import tag_names

# スレッドのファイル名（無ければスレッド 0 件）
THREADS_FILE = "threads.yaml"

# `update_settings` の `settings` に渡せるキー
EDITABLE_KEYS = (
    "summary",
    "description",
    "playbooks",
    "phases",
    "target_label",
    "goal",
    "targets",
    "categories",
    "tags",
    "links",
    "history_limit",
    "display",
)

# 値が `null` のときに消してよい任意のキー
REMOVABLE_KEYS = ("description", "goal", "tags", "links", "history_limit", "display")

# 表示の既定の書き換えの本文に必須のキー
DISPLAY_KEYS = ("network_look", "visible_kinds")

# `phase_map` の引数の名前（引数の誤りに添える）
PHASE_MAP_ARGUMENT = "phase_map"

# 付け替えたキーを `remapped` に並べる順
REMAP_KEY_ORDER = ("phase", "target", "category", "tags")

# `target_map`・`category_map` の引数の名前（引数の誤りに添える）
TARGET_MAP_ARGUMENT = "target_map"
CATEGORY_MAP_ARGUMENT = "category_map"

# `tag_map` の引数の名前（引数の誤りに添える）
TAG_MAP_ARGUMENT = "tag_map"


@dataclass(frozen=True, slots=True, kw_only=True)
class PhaseRemap:
    """フェーズ・対象・カテゴリー・タグのどれかを付け替えた 1 項目（タグはスレッドも）の 1 キー。"""

    # 項目かスレッドの ID
    id: str
    # 付け替えたキー
    key: Literal["phase", "target", "category", "tags"]
    # 前の名前
    from_value: str
    # 後の名前（タグを外したときは None）
    to_value: str | None


def validate_settings_input(
    settings: dict[str, Any],
    phase_map: dict[str, str] | None,
    current_phases: list[str],
    *,
    target_map: dict[str, str] | None,
    category_map: dict[str, str] | None,
    tag_map: dict[str, str | None] | None = None,
    current: dict[str, Any],
) -> None:
    """`settings` のキーと `phase_map`・`target_map`・`category_map`・`tag_map` の渡し方を、書き換える前に確かめる。"""
    lines = _settings_key_lines(settings)
    # 書き換えられないキー・消せないキーの null・空の settings
    if lines:
        raise SchemaMismatchError(lines)
    # phase_map を渡している: フェーズの対応を確かめる
    if phase_map is not None:
        # phases を渡さずに phase_map だけを渡した
        if "phases" not in settings:
            raise ArgumentError(PHASE_MAP_ARGUMENT, "`settings` に `phases` を渡していません")
        new_phases = settings["phases"]
        for old_phase in phase_map:
            # 古いフェーズでないか、新しい phases にも残るフェーズ: 対応を渡せない
            if old_phase not in current_phases or old_phase in new_phases:
                raise ArgumentError(
                    PHASE_MAP_ARGUMENT,
                    f"{old_phase} は、今の `phases` にあって新しい `phases` に無いフェーズではありません",
                )
        # 対応の値が新しい phases に無い
        unmapped = [(old, new) for old, new in phase_map.items() if new not in new_phases]
        if unmapped:
            raise UnmappedPhaseError(unmapped)
    # 対象・カテゴリーの対応を、それぞれの名前の一覧で同じように確かめる
    for argument, mapping, key in (
        (TARGET_MAP_ARGUMENT, target_map, "targets"),
        (CATEGORY_MAP_ARGUMENT, category_map, "categories"),
    ):
        # 対応を渡していない: 確かめることが無い
        if mapping is None:
            continue
        # 対象・カテゴリーを渡さずに対応だけを渡した
        if key not in settings:
            raise ArgumentError(argument, f"`settings` に `{key}` を渡していません")
        new_names = _names(settings[key])
        current_names = _names(current.get(key))
        for old_name in mapping:
            # 古い名前でないか、新しい設定にも残る名前: 対応を渡せない
            if old_name not in current_names or old_name in new_names:
                raise ArgumentError(
                    argument,
                    f"{old_name} は、今の `{key}` にあって新しい `{key}` に無い名前ではありません",
                )
        # 対応の値が新しい設定に無い
        unmapped_names = [
            f"{argument}: {old}: {new}" for old, new in mapping.items() if new not in new_names
        ]
        if unmapped_names:
            raise UnmappedTargetError(unmapped_names)
    # タグの対応: 対象・カテゴリーと同じく確かめ、値が None の対応は外す対応として通す
    if tag_map is not None:
        _validate_tag_map(tag_map, settings, current)


def _validate_tag_map(
    tag_map: dict[str, str | None], settings: dict[str, Any], current: dict[str, Any]
) -> None:
    """`tag_map` が、語彙を置き換えるときの、今の語彙にあって新しい語彙に無いタグから新しい語彙のタグ（か外す）への対応かを確かめる。"""
    # タグの語彙を渡さずに対応だけを渡した
    if "tags" not in settings:
        raise ArgumentError(TAG_MAP_ARGUMENT, "`settings` に `tags` を渡していません")
    new_names = _names(settings["tags"])
    current_names = _names(current.get("tags"))
    for old_name in tag_map:
        # 古いタグでないか、新しい語彙にも残るタグ: 対応を渡せない
        if old_name not in current_names or old_name in new_names:
            raise ArgumentError(
                TAG_MAP_ARGUMENT,
                f"{old_name} は、今の `tags` にあって新しい `tags` に無いタグではありません",
            )
    # 対応の値（外す対応の None を除く）が新しい語彙に無い
    unmapped = [
        (f"{TAG_MAP_ARGUMENT}[{old}]", new)
        for old, new in tag_map.items()
        if new is not None and new not in new_names
    ]
    if unmapped:
        raise UnmappedTagError(unmapped)


def merge_settings(
    current: dict[str, Any], settings: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """今の設定に渡したキーを当て、置き換えた設定と、値が変わった・消えたキーの名前を返す。"""
    # キーの並びを保つため、今の設定の写しに当てる
    merged = dict(current)
    changed: list[str] = []
    for key, value in settings.items():
        # null: キーを消す（元から無ければ変わらない）
        if value is None:
            if key in merged:
                del merged[key]
                changed.append(key)
            continue
        # 前と値が違う（無かったキーを含む）ものだけを変わったキーにする
        if key not in merged or merged[key] != value:
            changed.append(key)
        merged[key] = value
    return merged, changed


def remap_phases(
    workspace: Workspace,
    settings: dict[str, Any],
    phase_map: dict[str, str],
    now: NowFn = now_utc,
) -> tuple[list[Change], list[PhaseRemap], dict[str, Any]]:
    """新しい phases に無いフェーズを持つ項目と goal.phase を、対応で付け替える。"""
    phases = settings.get("phases", [])
    changes: list[Change] = []
    remapped: list[PhaseRemap] = []
    unmapped: list[tuple[str, str]] = []
    for kind in KINDS:
        items = [dict(item) for item in workspace.items[kind]]
        remapped_here = False
        for item in items:
            phase = item.get("phase")
            # フェーズを持たないか、新しい phases にある項目は触らない
            if not isinstance(phase, str) or phase in phases:
                continue
            # 対応が無い: 残るものとして控える
            if phase not in phase_map:
                unmapped.append((str(item.get("id")), phase))
                continue
            # 対応がある: フェーズと更新日時を置き換える
            item["phase"] = phase_map[phase]
            item["updated"] = now()
            item["updated_by"] = EDITOR
            remapped.append(
                PhaseRemap(
                    id=item["id"], key="phase", from_value=phase, to_value=phase_map[phase]
                )
            )
            remapped_here = True
        # 付け替えた項目がある種類だけ、並び全体を変更にする
        if remapped_here:
            changes.append(Change(kind=kind, items=items))
    new_settings = dict(settings)
    goal = new_settings.get("goal")
    if isinstance(goal, dict) and goal.get("phase") not in phases:
        goal_phase = goal.get("phase")
        if goal_phase in phase_map:
            # ゴールのフェーズにも対応がある: 置き換える
            new_settings["goal"] = {**goal, "phase": phase_map[goal_phase]}
        else:
            # 対応が無い: 残るものとして控える
            unmapped.append(("goal", str(goal_phase)))
    if unmapped:
        raise UnmappedPhaseError(unmapped)
    return changes, remapped, new_settings


def remap_names(
    items: dict[Kind, list[dict[str, Any]]],
    settings: dict[str, Any],
    target_map: dict[str, str],
    category_map: dict[str, str],
    now: NowFn = now_utc,
) -> tuple[dict[Kind, list[dict[str, Any]]], list[PhaseRemap], dict[str, Any]]:
    """新しい targets・categories に無い名前を持つ項目とカテゴリーの target を、対応で付け替える。"""
    targets = _names(settings.get("targets"))
    categories = _names(settings.get("categories"))
    unmapped: list[str] = []
    new_settings = dict(settings)
    # カテゴリーの target が新しい targets に無ければ、対応で付け替える
    if isinstance(settings.get("categories"), list):
        new_categories: list[Any] = []
        for category in settings["categories"]:
            target = category.get("target") if isinstance(category, dict) else None
            if isinstance(target, str) and target not in targets:
                if target in target_map:
                    category = {**category, "target": target_map[target]}
                else:
                    # 対応が無い: 残るものとして控える
                    unmapped.append(f"categories[{category.get('name')}]: target: {target}")
            new_categories.append(category)
        new_settings["categories"] = new_categories
    remapped: list[PhaseRemap] = []
    new_items: dict[Kind, list[dict[str, Any]]] = {}
    for kind in KINDS:
        rows: list[dict[str, Any]] = []
        for original in items[kind]:
            item = dict(original)
            renamed = False
            for key, names, mapping in (
                ("target", targets, target_map),
                ("category", categories, category_map),
            ):
                value = item.get(key)
                # 持たないか、新しい設定にある名前は触らない
                if not isinstance(value, str) or value in names:
                    continue
                if value in mapping:
                    # 対応がある: 置き換える
                    item[key] = mapping[value]
                    remapped.append(
                        PhaseRemap(
                            id=str(item.get("id")), key=key, from_value=value, to_value=mapping[value]
                        )
                    )
                    renamed = True
                else:
                    # 対応が無い: 残るものとして控える
                    unmapped.append(f"{item.get('id')}: {key}: {value}")
            # 付け替えた項目だけ更新日時を変える
            if renamed:
                item["updated"] = now()
                item["updated_by"] = EDITOR
            rows.append(item)
        new_items[kind] = rows
    if unmapped:
        raise UnmappedTargetError(unmapped)
    return new_items, remapped, new_settings


def remap_tags(
    items: dict[Kind, list[dict[str, Any]]],
    threads: list[dict[str, Any]],
    settings: dict[str, Any],
    tag_map: dict[str, str | None],
    now: NowFn = now_utc,
    *,
    replaced: bool,
) -> tuple[dict[Kind, list[dict[str, Any]]], list[dict[str, Any]], list[PhaseRemap]]:
    """新しい語彙に無いタグを、対応で項目とスレッドの `tags` から付け替えるか外す。"""
    # 語彙を置き換えないときはタグを確かめない
    if not replaced:
        return items, threads, []
    names = tag_names(settings)
    remapped: list[PhaseRemap] = []
    unmapped: list[tuple[str, str]] = []
    new_items: dict[Kind, list[dict[str, Any]]] = {}
    for kind in KINDS:
        rows: list[dict[str, Any]] = []
        for original in items[kind]:
            item = dict(original)
            owner = str(item.get("id"))
            before = len(remapped)
            if isinstance(item.get("tags"), list):
                item["tags"] = _remap_tag_list(
                    item["tags"], names, tag_map, owner, remapped, unmapped
                )
            # タグを付け替えた項目だけ更新日時と編集した人を書く
            if len(remapped) > before:
                item["updated"] = now()
                item["updated_by"] = EDITOR
            rows.append(item)
        new_items[kind] = rows
    new_threads: list[dict[str, Any]] = []
    for original in threads:
        thread = dict(original)
        if isinstance(thread.get("tags"), list):
            thread["tags"] = _remap_tag_list(
                thread["tags"], names, tag_map, str(thread.get("id")), remapped, unmapped
            )
        new_threads.append(thread)
    # 対応の無いタグが残る
    if unmapped:
        raise UnmappedTagError(unmapped)
    return new_items, new_threads, remapped


def _remap_tag_list(
    tags: list[Any],
    names: frozenset[str],
    tag_map: dict[str, str | None],
    owner: str,
    remapped: list[PhaseRemap],
    unmapped: list[tuple[str, str]],
) -> list[Any]:
    """1 つの `tags` を前から見て、語彙にあるタグは残し、無いタグは対応で付け替えるか外す。"""
    result: list[Any] = []
    for tag in tags:
        # 文字列でない要素と、語彙にあるタグはそのまま残す
        if not isinstance(tag, str) or tag in names:
            result.append(tag)
            continue
        # 語彙に無く対応も無い: 残るものとして控える（タグは残す）
        if tag not in tag_map:
            unmapped.append((owner, tag))
            result.append(tag)
            continue
        new_tag = tag_map[tag]
        remapped.append(PhaseRemap(id=owner, key="tags", from_value=tag, to_value=new_tag))
        # 外す対応ではなく、置き換えた先がまだ無いときだけ足す
        if new_tag is not None and new_tag not in tags and new_tag not in result:
            result.append(new_tag)
    return result


def save_settings(
    workspace: Workspace,
    settings: dict[str, Any],
    changes: list[Change],
    *,
    threads: list[dict[str, Any]] | None = None,
) -> list[str]:
    """設定と、付け替えた種類の項目の並び（とスレッド）を、検証してから全て書き換えるか、どれも書き換えない。"""
    # 書き戻すと中身を失う形のファイルには書かない
    for change in changes:
        if loses_content_on_rewrite(workspace, change.kind):
            file_name = KINDS[change.kind].file
            current = [p for p in validate_workspace(workspace) if p.file == file_name]
            raise build_mismatch_error(current, workspace)
    # 書き換えた後のワークスペース全体を検証する
    raw = {
        **workspace.raw,
        SETTINGS_FILE: settings,
        **{KINDS[change.kind].file: {"items": change.items} for change in changes},
    }
    changed = replace(workspace, raw=raw)
    problems = validate_workspace(changed)
    if problems:
        raise build_mismatch_error(problems, changed)

    # 置き換える順（種類のファイル → スレッド → 設定）に、書く先と中身を並べる
    targets = [(KINDS[change.kind].file, {"items": change.items}) for change in changes]
    if threads is not None:
        targets.append((THREADS_FILE, {"items": threads}))
    targets.append((SETTINGS_FILE, settings))
    # 一時ファイルを先に全て書き、置き換える前の中身を控える
    temps: list[tuple[Path, Path]] = []
    previous: dict[Path, bytes] = {}
    for file_name, data in targets:
        path = records_root(workspace.root) / file_name
        try:
            previous[path] = path.read_bytes()
            temps.append((write_temp(path, dump_yaml(data)), path))
        except OSError as error:
            remove_files([temp for temp, _ in temps])
            raise write_failed(path, error) from error
    # 順に置き換え、失敗したら置き換えたファイルを控えに戻す
    replaced: list[Path] = []
    for temp, path in temps:
        try:
            os.replace(temp, path)
        except OSError as error:
            for done in replaced:
                done.write_bytes(previous[done])
            remove_files([leftover for leftover, _ in temps])
            raise write_failed(path, error) from error
        replaced.append(path)
    # config.yaml を先頭に、種類のファイル、最後にスレッドの順で返す
    return [
        f"{RECORD_DIR}/{name}"
        for name in (
            SETTINGS_FILE,
            *(KINDS[change.kind].file for change in changes),
            *([THREADS_FILE] if threads is not None else []),
        )
    ]


def update_settings(
    root: Path,
    settings: dict[str, Any],
    phase_map: dict[str, str] | None,
    now: NowFn = now_utc,
    *,
    target_map: dict[str, str] | None = None,
    category_map: dict[str, str] | None = None,
    tag_map: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """引数を確かめ、設定を置き換えてフェーズ・対象・カテゴリー・タグを付け替え、まとめて書く。"""
    workspace = load_workspace(root)
    current_phases = workspace.settings.get("phases", [])
    validate_settings_input(
        settings,
        phase_map,
        current_phases,
        target_map=target_map,
        category_map=category_map,
        tag_map=tag_map,
        current=workspace.settings,
    )
    merged, changed = merge_settings(workspace.settings, settings)
    # 書き換えのたびに確かめるので、phases に無いフェーズが残れば止まる
    phase_changes, phase_remapped, phased_settings = remap_phases(
        workspace, merged, phase_map or {}, now
    )
    items = {**workspace.items, **{change.kind: change.items for change in phase_changes}}
    # 書き換えのたびに確かめるので、新しい設定に無い対象・カテゴリーが残れば止まる
    items, name_remapped, remapped_settings = remap_names(
        items, phased_settings, target_map or {}, category_map or {}, now
    )
    # 語彙を置き換える・消すときは、新しい語彙に無いタグが残れば止まる
    thread_items = _read_thread_items(root)
    items, new_threads, tag_remapped = remap_tags(
        items,
        thread_items,
        remapped_settings,
        tag_map or {},
        now,
        replaced="tags" in settings,
    )
    # 対応で goal.phase だけが変わったときも goal を変わったキーに入れる
    if phased_settings.get("goal") != merged.get("goal") and "goal" not in changed:
        changed.append("goal")
    # 対応でカテゴリーの target だけが変わったときも categories を変わったキーに入れる
    if remapped_settings.get("categories") != merged.get("categories") and "categories" not in changed:
        changed.append("categories")
    # 付け替えた項目がある種類だけを、種類の順に変更にする
    changes = [
        Change(kind=kind, items=items[kind])
        for kind in KINDS
        if items[kind] != workspace.items[kind]
    ]
    # タグを付け替えたスレッドがあるときだけ、スレッドも一緒に書く
    threads = new_threads if new_threads != thread_items else None
    files = save_settings(workspace, remapped_settings, changes, threads=threads)
    # 種類の順（スレッドは最後）・並びの順・同じ項目の中は phase・target・category・tags の順に並べる
    positions = {
        item["id"]: (kind_order, index)
        for kind_order, kind in enumerate(KINDS)
        for index, item in enumerate(items[kind])
    }
    positions.update(
        {thread["id"]: (len(KINDS), index) for index, thread in enumerate(new_threads)}
    )
    ordered = sorted(
        [*phase_remapped, *name_remapped, *tag_remapped],
        key=lambda remap: (*positions[remap.id], REMAP_KEY_ORDER.index(remap.key)),
    )
    return {
        "changed": changed,
        "remapped": [
            {"id": remap.id, "key": remap.key, "from": remap.from_value, "to": remap.to_value}
            for remap in ordered
        ],
        "files": files,
    }


def update_display(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """要求の本文の `network_look`・`visible_kinds` で `config.yaml` の `display` だけを丸ごと置き換える。"""
    # 本文に 2 つのキーがあるか
    for key in DISPLAY_KEYS:
        if key not in body:
            raise SettingsInvalidError(f"{key}: 渡してください")
    # 2 つのキーだけにした値を、設定のスキーマの display と突き合わせる
    display = {key: body[key] for key in DISPLAY_KEYS}
    found = sorted(
        load_display_validator().iter_errors(display), key=lambda error: list(error.absolute_path)
    )
    if found:
        raise SettingsInvalidError(
            "、".join(f"{format_path(error.absolute_path)}: {error.message}" for error in found)
        )
    # 崩れた config.yaml の上には書き足さない
    _, problems = check_settings(root)
    if problems:
        raise build_mismatch_error(problems)
    # 読んだ設定の display を置き換える（キーの並びは保ち、無ければ末尾に足す）
    workspace = load_workspace(root)
    settings = {**workspace.settings, "display": display}
    # 変更履歴にも書き換えのまとまりにも入れず、設定だけを書く
    save_settings(workspace, settings, [])
    return {"display": display}


def _read_thread_items(root: Path) -> list[dict[str, Any]]:
    """`threads.yaml` の `items` を読む（無いか、読めないか、スレッドの並びでなければ空）。"""
    path = records_root(root) / THREADS_FILE
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    items = value.get("items") if isinstance(value, dict) else None
    # スレッドの並びの辞書だけを返す
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _settings_key_lines(settings: dict[str, Any]) -> list[str]:
    """`settings` が空か、書き換えられないキー・消せないキーの null・名前の重なったタグの語彙を持つときの、問題ごとの行を返す。"""
    # 何も渡していない
    if not settings:
        return [f"{SETTINGS_FILE}: {WHOLE_PATH}: 1 つ以上のキーを渡してください"]
    lines: list[str] = []
    for key, value in settings.items():
        # 書き換えられないキー
        if key not in EDITABLE_KEYS:
            lines.append(f"{SETTINGS_FILE}: {key}: このツールでは書き換えられません")
        # 必須のキーを null で消そうとした
        elif value is None and key not in REMOVABLE_KEYS:
            lines.append(f"{SETTINGS_FILE}: {key}: null で消せません")
    lines.extend(_duplicated_tag_lines(settings.get("tags")))
    return lines


def _duplicated_tag_lines(tags: Any) -> list[str]:
    """タグの語彙の名前の重なりごとの行を返す（同じ名前は 1 行）。"""
    if not isinstance(tags, list):
        return []
    seen: set[str] = set()
    duplicated: list[str] = []
    for entry in tags:
        name = entry.get("name") if isinstance(entry, dict) else None
        # 名前が 2 回目以降に出たとき、まだ挙げていなければ重なりにする
        if isinstance(name, str) and name in seen and name not in duplicated:
            duplicated.append(name)
        if isinstance(name, str):
            seen.add(name)
    return [
        f"{SETTINGS_FILE}: tags: 同じ名前のタグが重なっています: {name}" for name in duplicated
    ]


def _names(entries: Any) -> set[str]:
    """`targets`・`categories` の要素の `name` を集める（形が合わない要素は飛ばす）。"""
    if not isinstance(entries, list):
        return set()
    return {
        entry["name"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
