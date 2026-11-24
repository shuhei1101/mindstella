"""絞り込みのプリセットのタグの式の検証・項目への当てはめと件数の計算と、`config.yaml` の `presets` の作成・更新・削除。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from errors import ArgumentError, PresetNameTakenError, PresetNotFoundError, SchemaMismatchError, SettingsInvalidError
from kinds import KINDS
from settings_update import save_settings
from store import Workspace, build_mismatch_error, check_settings, load_workspace
from tag_text import normalize_tag, tag_name

# 設定のプリセットの並びのキー
PRESETS_KEY = "presets"

# 束のキー
BUNDLE_KEYS = ("and", "or", "not")

# 条件が持てるキー
CONDITION_KEYS = ("field", "op", "values", "match")

# 条件の比べ方
CONDITION_OPS = ("eq", "ne")

# 条件の `match` の値
MATCH_VALUES = ("any", "all")

# 束の入れ子の深さの上限（最上位の束を 1 レイヤーとする）
MAX_LAYERS = 3

# プリセットの名前の字数の上限
MAX_NAME_LENGTH = 40

# 画面からの作成の要求の本文が持てるキー
PREVIEW_BODY_KEYS = ("name", "filter")


@dataclass(frozen=True, slots=True, kw_only=True)
class PresetChanges:
    """`update_preset` で置き換える値。None のキーは今の値を保つ。"""

    # 変更後の名前
    new_name: str | None = None
    # 変更後の説明。空の文字列で説明を削除する
    description: str | None = None
    # 変更後のタグの式
    expr: dict[str, Any] | None = None
    # 移す先の並び順（1 始まり）
    position: int | None = None


def validate_preset_filter(expr: dict[str, Any]) -> list[str]:
    """タグの式を確認し、合わない箇所の `{キーのパス}: {理由}` を返却する。"""
    lines: list[str] = []
    _validate_node(expr, "filter", 0, lines)
    return lines


def _validate_node(node: object, path: str, layers: int, lines: list[str]) -> None:
    """式の 1 つの要素（条件か束）を確認し、合わない箇所の行を追加する。`layers` は親までの束の数。"""
    # オブジェクトでない: 条件にも束にもならない
    if not isinstance(node, dict):
        lines.append(f"{path}: 条件か束のオブジェクトにしてください")
        return
    bundle_keys = [key for key in node if key in BUNDLE_KEYS]
    # 束のキーを持たない: 条件として確認する
    if not bundle_keys:
        _validate_condition(node, path, lines)
        return
    # 束がほかのキーも持つ: 束は 1 つのキーだけを持つ
    if len(node) != 1:
        lines.append(f"{path}: 束は and・or・not のどれか 1 つのキーだけを持ちます")
        return
    key = bundle_keys[0]
    child_path = f"{path}.{key}"
    # 束の入れ子が上限を超える
    if layers + 1 > MAX_LAYERS:
        lines.append(f"{child_path}: 入れ子が {MAX_LAYERS} レイヤーを超えます")
        return
    value = node[key]
    # not: 1 つの要素を持つ
    if key == "not":
        _validate_node(value, child_path, layers + 1, lines)
        return
    # and・or が並びでない
    if not isinstance(value, list):
        lines.append(f"{child_path}: 並びにしてください")
        return
    # 空の束
    if not value:
        lines.append(f"{child_path}: 空の束です")
        return
    for index, child in enumerate(value):
        _validate_node(child, f"{child_path}[{index}]", layers + 1, lines)


def _validate_condition(node: dict[str, Any], path: str, lines: list[str]) -> None:
    """条件を確認し、合わない箇所の行を追加する。"""
    for key in node:
        # 決めたキーのほか（case_sensitive など）は受け付けない
        if key not in CONDITION_KEYS:
            lines.append(f"{path}.{key}: 受け付けないキーです")
    if node.get("field") != "tags":
        lines.append(f"{path}.field: tags にしてください")
    op = node.get("op")
    if op not in CONDITION_OPS:
        lines.append(f"{path}.op: 受け付けない比べ方です: {op}")
    values = node.get("values")
    if not isinstance(values, list) or not values or not all(
        isinstance(value, str) and value for value in values
    ):
        lines.append(f"{path}.values: 1 つ以上のタグの並びにしてください")
    # match を持つ
    if "match" in node:
        # ne: match を持たない
        if op == "ne":
            lines.append(f"{path}.match: ne は match を持ちません")
        # eq: any か all に限る
        elif node["match"] not in MATCH_VALUES:
            lines.append(f"{path}.match: any か all にしてください")


def matches_preset(tags: list[str], expr: dict[str, Any]) -> bool:
    """項目のタグの名前が、検証を通ったタグの式に合うかを返却する。"""
    names = {normalize_tag(tag) for tag in tags}
    return _matches(names, expr)


def _matches(names: set[str], node: dict[str, Any]) -> bool:
    """正規化したタグの名前の集合が、式の要素に合うかを返却する。"""
    if "and" in node:
        return all(_matches(names, child) for child in node["and"])
    if "or" in node:
        return any(_matches(names, child) for child in node["or"])
    if "not" in node:
        return not _matches(names, node["not"])
    values = {normalize_tag(value) for value in node["values"]}
    # ne: 選んだタグをどれも持たない（タグの無い項目も合う）
    if node["op"] == "ne":
        return not (names & values)
    # eq の all: 全てを持つ
    if node.get("match") == "all":
        return values <= names
    # eq の any: どれかを持つ（タグの無い項目は合わない）
    return bool(names & values)


def preset_counts(workspace: Workspace) -> dict[str, int]:
    """設定の `presets` ごとに、全ての種類の項目のうち式に合う数を返却する。構造の崩れたプリセットは含めない。"""
    item_tags = [_item_tags(item) for kind in KINDS for item in workspace.items[kind]]
    counts: dict[str, int] = {}
    for entry in _presets_of(workspace.settings):
        name = entry.get("name")
        expr = entry.get("filter")
        # 手で修正して構造の崩れたプリセット: 数えない（点検がスキーマの問題として返却する）
        if not isinstance(name, str) or not isinstance(expr, dict) or validate_preset_filter(expr):
            continue
        counts[name] = sum(1 for tags in item_tags if matches_preset(tags, expr))
    return counts


def create_preset(
    root: Path, *, name: str, description: str | None = None, expr: dict[str, Any]
) -> dict[str, Any]:
    """名前と式を確認し、`presets` の末尾に追加して書き込み、該当する件数を返却する。"""
    workspace = load_workspace(root)
    _require_valid(name=name, expr=expr)
    presets = _presets_of(workspace.settings)
    taken = _find_index(presets, name)
    # 名前が重なる: 書き込まずに送出する
    if taken is not None:
        raise PresetNameTakenError(presets[taken]["name"])
    entry = _build_entry(name, description, expr)
    files = save_settings(workspace, {**workspace.settings, PRESETS_KEY: [*presets, entry]})
    count = _count_after_write(root, name)
    return {"preset": _public(entry), "count": count, "warnings": _warnings(name, count), "files": files}


def create_preset_from_preview(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """画面からの要求の本文を確認して `create_preset` を呼び、保存したプリセットと件数を返却する。"""
    # 名前と式のほかのキーは受け付けない
    unknown = [key for key in body if key not in PREVIEW_BODY_KEYS]
    if unknown:
        raise SettingsInvalidError("、".join(f"{key}: 知らないキーです" for key in unknown))
    raw_name = body.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    # 名前が無い・空白だけ・長すぎる
    if not 1 <= len(name) <= MAX_NAME_LENGTH:
        raise SettingsInvalidError(f"name: 1 字以上 {MAX_NAME_LENGTH} 字以内にしてください")
    expr = body.get("filter")
    # 式がオブジェクトでない
    if not isinstance(expr, dict):
        raise SettingsInvalidError("filter: タグの式のオブジェクトを渡してください")
    lines = validate_preset_filter(expr)
    # 式が構造に合わない
    if lines:
        raise SettingsInvalidError("、".join(lines))
    # 崩れた config.yaml の上には書き足さない
    _, problems = check_settings(root)
    if problems:
        raise build_mismatch_error(problems)
    created = create_preset(root, name=name, expr=expr)
    return {"preset": {"name": created["preset"]["name"], "filter": created["preset"]["filter"]}, "count": created["count"]}


def update_preset(root: Path, *, name: str, changes: PresetChanges) -> dict[str, Any]:
    """指定したキーだけを置き換え、`position` で並びを移して書き込み、該当する件数を返却する。"""
    # 置き換える値が 1 つも無い: 引数の誤り
    if (
        changes.new_name is None
        and changes.description is None
        and changes.expr is None
        and changes.position is None
    ):
        raise ArgumentError("update_preset", "new_name・description・filter・position のどれかを渡してください")
    workspace = load_workspace(root)
    presets = _presets_of(workspace.settings)
    index = _require_index(presets, name)
    current = presets[index]
    new_name = changes.new_name if changes.new_name is not None else current["name"]
    expr = changes.expr if changes.expr is not None else current["filter"]
    _require_valid(name=new_name, expr=expr)
    if changes.position is not None and changes.position < 1:
        raise SchemaMismatchError(["position: 1 以上にしてください"])
    # 名前を変える: ほかのプリセットと重ならない
    if changes.new_name is not None:
        taken = _find_index(presets, new_name)
        if taken is not None and taken != index:
            raise PresetNameTakenError(presets[taken]["name"])
    description = current.get("description") if changes.description is None else changes.description
    entry = _build_entry(new_name, description or None, expr)
    rest = [preset for position, preset in enumerate(presets) if position != index]
    # 並び: 指定が無ければ今の位置、数を超える値は末尾
    target = index if changes.position is None else min(changes.position - 1, len(rest))
    updated = [*rest[:target], entry, *rest[target:]]
    files = save_settings(workspace, {**workspace.settings, PRESETS_KEY: updated})
    count = _count_after_write(root, new_name)
    return {
        "preset": _public(entry),
        "position": target + 1,
        "count": count,
        "warnings": _warnings(new_name, count),
        "files": files,
    }


def delete_preset(root: Path, *, name: str) -> dict[str, Any]:
    """該当したプリセットを除いて書き込む。最後の 1 件なら `presets` のキーごと除く。"""
    workspace = load_workspace(root)
    presets = _presets_of(workspace.settings)
    index = _require_index(presets, name)
    deleted = presets[index]
    remaining = [preset for position, preset in enumerate(presets) if position != index]
    # 残りがある: 元の位置に並びを配置する。無い: キーごと除く
    if remaining:
        settings = {**workspace.settings, PRESETS_KEY: remaining}
    else:
        settings = {key: value for key, value in workspace.settings.items() if key != PRESETS_KEY}
    files = save_settings(workspace, settings)
    return {"deleted": _public(deleted), "remaining": len(remaining), "files": files}


def _presets_of(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """設定のプリセットの並びを返却する。無いか並びでなければ空。"""
    presets = settings.get(PRESETS_KEY)
    if not isinstance(presets, list):
        return []
    return [entry for entry in presets if isinstance(entry, dict)]


def _item_tags(item: dict[str, Any]) -> list[str]:
    """項目のタグの名前を返却する。"""
    tags = item.get("tags")
    if not isinstance(tags, list):
        return []
    return [name for name in (tag_name(entry) for entry in tags) if name is not None]


def _find_index(presets: list[dict[str, Any]], name: str) -> int | None:
    """NFKC と大文字小文字をそろえて名前が重なるプリセットの位置を返却する。"""
    normalized = normalize_tag(name)
    for index, entry in enumerate(presets):
        current = entry.get("name")
        if isinstance(current, str) and normalize_tag(current) == normalized:
            return index
    return None


def _require_index(presets: list[dict[str, Any]], name: str) -> int:
    """名前に該当するプリセットの位置を返却する。無ければ送出する。"""
    index = _find_index(presets, name)
    if index is None:
        names = [entry["name"] for entry in presets if isinstance(entry.get("name"), str)]
        raise PresetNotFoundError(name, names)
    return index


def _require_valid(*, name: str, expr: dict[str, Any]) -> None:
    """名前の字数と式を確認し、合わなければ送出する。"""
    lines: list[str] = []
    if not 1 <= len(name) <= MAX_NAME_LENGTH:
        lines.append(f"name: 1 字以上 {MAX_NAME_LENGTH} 字以内にしてください")
    lines.extend(validate_preset_filter(expr))
    if lines:
        raise SchemaMismatchError(lines)


def _build_entry(name: str, description: str | None, expr: dict[str, Any]) -> dict[str, Any]:
    """`config.yaml` に書き込むプリセットを作る。説明が無ければキーを持たない。"""
    entry: dict[str, Any] = {"name": name}
    if description:
        entry["description"] = description
    entry["filter"] = expr
    return entry


def _public(entry: dict[str, Any]) -> dict[str, Any]:
    """結果に返却するプリセット（説明が無ければ null）。"""
    return {"name": entry["name"], "description": entry.get("description"), "filter": entry["filter"]}


def _count_after_write(root: Path, name: str) -> int:
    """書き込んだ後のワークスペースで、そのプリセットに該当する件数を数える。"""
    return preset_counts(load_workspace(root)).get(name, 0)


def _warnings(name: str, count: int) -> list[str]:
    """件数が 0 のとき、どの項目にも該当しない旨の 1 行を返却する。"""
    if count == 0:
        return [f"どの項目にも該当しません: {name}"]
    return []
