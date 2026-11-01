"""項目の検索・1 件の表示と参照元・属性名とタグの一覧（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from errors import ArgumentError
from kinds import KINDS, Kind, id_number
from store import Workspace, as_ids, body_format, dump_yaml, find_item, read_body
from tag_text import normalize_tag, similar_tags, tag_name

# 参照元として拾うキーとその並び
REFERENCE_KEYS = ("depends_on", "parent", "for", "related", "sources")

# `find` が 1 ページに返す既定の件数
DEFAULT_LIMIT = 20

# `find` の `limit` に渡せる件数の上限
MAX_LIMIT = 80

# `find` が返せる項目の名前とその並び（`include`・`exclude` に渡せる名前）
FIELD_NAMES = (
    "title",
    "status",
    "tags",
    "chars",
    "target",
    "category",
    "phase",
    "attrs",
    "updated",
    "extra",
    "body",
)

# `view` ごとに返す項目の名前
VIEW_FIELDS: dict[str, tuple[str, ...]] = {
    "brief": FIELD_NAMES[:4],
    "standard": FIELD_NAMES[:9],
    "full": FIELD_NAMES,
}

# `extra` に入れないキー（名前を持つ項目に当たるキー）
NAMED_ITEM_KEYS = (
    "id",
    "title",
    "status",
    "tags",
    "target",
    "category",
    "phase",
    "attrs",
    "updated",
    "body",
)

# Markdown の表に列として出さない項目の名前
SECTION_FIELDS = ("extra", "body", "body_format")

# スレッドをタグの一覧の種類に並べるときの名前
THREAD_KIND = "thread"

# 切り詰めたときの案内に並べる引数の名前とその並び
NARROWING_ARGUMENTS = ("tags", "kind", "status", "phase", "category", "text")

# 続きの値に入れる条件の指紋の長さ（16 進の文字数）
FINGERPRINT_CHARS = 16


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchFilter:
    """`find` の引数をまとめた条件。None の条件は絞らない。"""

    # 文字の欄に含まれる文字
    text: str | None = None
    kind: Kind | None = None
    status: str | None = None
    target: str | None = None
    category: str | None = None
    phase: str | None = None
    # 属性名と値（値が None ならその属性を持つことだけ）
    attrs: list[tuple[str, str | None]] = field(default_factory=list)
    # 全てを持つ項目に絞るタグ（AND。空なら絞らない）
    tags: tuple[str, ...] = ()
    # いずれかを持つ項目に絞るタグ（OR。空なら絞らない）
    any_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchHit:
    """`find` の条件に合った 1 項目と、その文字数。"""

    kind: Kind
    item: dict[str, Any]
    # 項目の文字数（`item_chars`）
    chars: int


def search_items(workspace: Workspace, search_filter: SearchFilter) -> list[SearchHit]:
    """条件の全てに合う項目を、文字数を添えて並べて返す。"""
    needle = search_filter.text.lower() if search_filter.text is not None else None
    matched: list[tuple[Kind, dict[str, Any]]] = []
    for kind, item in _iter_sorted_items(workspace):
        # 種類で絞る
        if search_filter.kind is not None and kind != search_filter.kind:
            continue
        if not _matches_fields(item, search_filter):
            continue
        # 文字で絞る（項目の全ての文字列の値が対象）
        if needle is not None and not _contains_text(item, needle):
            continue
        matched.append((kind, item))
    # タグで絞ったときは、渡したタグを主題として持つ項目を先に置く（安定な並べ替え）
    wanted = {normalize_tag(tag) for tag in (*search_filter.tags, *search_filter.any_tags)}
    if wanted:
        matched.sort(key=lambda pair: 0 if wanted & _main_tags(pair[1]) else 1)
    return [
        SearchHit(kind=kind, item=item, chars=item_chars(workspace, item))
        for kind, item in matched
    ]


def item_chars(workspace: Workspace, item: dict[str, Any]) -> int:
    """項目を YAML に書き出した文字数と、本文のファイルの文字数の和を返す。"""
    chars = len(dump_yaml(item))
    body_name = item.get("body")
    # 本文が無い・読めないときは YAML の文字数だけ
    text = read_body(workspace, body_name) if isinstance(body_name, str) else None
    if text is not None:
        chars += len(text)
    return chars


def resolve_fields(
    view: Literal["brief", "standard", "full"],
    *,
    include: Sequence[str],
    exclude: Sequence[str],
) -> tuple[str, ...]:
    """`view` の項目に `include` を加え、`exclude` を外した名前を `FIELD_NAMES` の順で返す。"""
    overlapped = [name for name in include if name in exclude]
    if overlapped:
        raise ArgumentError(
            "include", f"exclude と同じ名前は渡せません（{'・'.join(overlapped)}）"
        )
    chosen = (set(VIEW_FIELDS[view]) | set(include)) - set(exclude)
    return tuple(name for name in FIELD_NAMES if name in chosen)


def build_row(workspace: Workspace, hit: SearchHit, fields: tuple[str, ...]) -> dict[str, Any]:
    """当たった項目を、選んだ項目の名前だけを持つ結果の 1 行にする。"""
    item = hit.item
    row: dict[str, Any] = {"id": item.get("id"), "kind": hit.kind}
    for name in fields:
        if name == "tags":
            tags = item.get("tags")
            row["tags"] = list(tags) if isinstance(tags, list) else []
        elif name == "attrs":
            attrs = item.get("attrs")
            row["attrs"] = attrs if isinstance(attrs, dict) else {}
        elif name == "chars":
            row["chars"] = hit.chars
        elif name == "extra":
            row["extra"] = {
                key: value for key, value in item.items() if key not in NAMED_ITEM_KEYS
            }
        elif name == "body":
            body_name = item.get("body")
            row["body"] = read_body(workspace, body_name) if isinstance(body_name, str) else None
            row["body_format"] = body_format(body_name)
        else:
            row[name] = item.get(name)
    return row


def count_tags(hits: Sequence[SearchHit]) -> list[dict[str, Any]]:
    """当たった項目が使っているタグを、正規化した表記ごとに数える（件数の多い順）。"""
    counts: dict[str, int] = {}
    for hit in hits:
        tags = hit.item.get("tags")
        if not isinstance(tags, list):
            continue
        # 1 つの項目が同じタグを表記を変えて 2 回持っても 1 件と数える
        for name in _normalized_tags(tags):
            counts[name] = counts.get(name, 0) + 1
    return [
        {"tag": name, "count": counts[name]}
        for name in sorted(counts, key=lambda name: (-counts[name], name))
    ]


def render_find_markdown(result: dict[str, Any]) -> str:
    """`find` の結果の辞書を Markdown の本文にする。"""
    lines = [f"全 {result['total']} 件・合計 {result['total_chars']} 文字"]
    # 件数だけ: タグごとの件数の表を続けて返す
    if "tag_counts" in result:
        lines += ["", "| タグ | 件数 |", "| --- | --- |"]
        lines += [
            f"| {_markdown_cell(entry['tag'])} | {entry['count']} |"
            for entry in result["tag_counts"]
        ]
        return "\n".join(lines) + "\n"
    rows: list[dict[str, Any]] = result.get("items", [])
    if rows:
        columns = [key for key in rows[0] if key not in SECTION_FIELDS]
        lines += [
            "",
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        lines += [
            "| " + " | ".join(_render_cell(column, row.get(column)) for column in columns) + " |"
            for row in rows
        ]
        # extra・本文は表の後に項目ごとのセクションで書く
        for row in rows:
            if "extra" not in row and "body" not in row:
                continue
            lines += ["", f"## {row.get('id')} {row.get('title') or ''}".rstrip()]
            if "extra" in row:
                lines += ["", "```yaml", dump_yaml(row["extra"]).rstrip("\n"), "```"]
            if row.get("body") is not None:
                lines += ["", row["body"].rstrip("\n")]
    tail: list[str] = []
    if result.get("next_cursor") is not None:
        tail.append(f"next_cursor: {result['next_cursor']}")
    if result.get("hint") is not None:
        tail.append(result["hint"])
    if result.get("omitted"):
        tail.append(f"省いた項目: {'・'.join(result['omitted'])}（view か include で取れる）")
    if tail:
        lines += ["", *tail]
    return "\n".join(lines) + "\n"


def _render_cell(column: str, value: Any) -> str:
    """表の 1 セルの文字にする（タグ・属性は `、` で区切り、None は空）。"""
    if value is None:
        return ""
    if column == "tags" and isinstance(value, list):
        names: list[str] = []
        for entry in value:
            name = tag_name(entry)
            if name is None:
                continue
            is_main = isinstance(entry, dict) and entry.get("main") is True
            names.append(f"{name} [main]" if is_main else name)
        return _markdown_cell("、".join(names))
    if column == "attrs" and isinstance(value, dict):
        return _markdown_cell("、".join(f"{key}={item}" for key, item in value.items()))
    return _markdown_cell(str(value))


def _markdown_cell(text: str) -> str:
    """セルの `|` と改行をエスケープする。"""
    return text.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _main_tags(item: dict[str, Any]) -> set[str]:
    """項目が主題として持つタグの正規化した名前を返す。"""
    tags = item.get("tags")
    if not isinstance(tags, list):
        return set()
    return {
        normalize_tag(entry["name"])
        for entry in tags
        if isinstance(entry, dict) and entry.get("main") is True and isinstance(entry.get("name"), str)
    }


def parse_attr(text: str) -> tuple[str, str | None]:
    """`--attr` の `名前=値`・`名前` を名前と値に分ける（`=` が無ければ値は None）。"""
    name, separator, value = text.partition("=")
    # `=` が無い: その属性を持つことだけを条件にする
    if not separator:
        return name, None
    return name, value


def show_item(workspace: Workspace, item_id: str) -> dict[str, Any]:
    """1 項目の全てのキー・種類・本文・参照元をまとめる。"""
    ref = find_item(workspace, item_id)
    body_name = ref.item.get("body")
    # body があるときだけ本文を読み、形式に合う側に入れる
    text = read_body(workspace, body_name) if isinstance(body_name, str) else None
    body_kind = body_format(body_name)
    return {
        "item": ref.item,
        "kind": ref.kind,
        "body_markdown": text if body_kind == "markdown" else None,
        "body_html": text if body_kind == "html" else None,
        "body_format": body_kind,
        "referenced_by": list_referrers(workspace, item_id),
    }


def list_referrers(workspace: Workspace, item_id: str) -> list[dict[str, str]]:
    """その ID を `REFERENCE_KEYS` のどれかで指す項目を、キーごとに 1 行で返す。"""
    referrers: list[dict[str, str]] = []
    for _, item in _iter_sorted_items(workspace):
        for key in REFERENCE_KEYS:
            # 同じ項目が複数のキーで指すときは、キーごとに行を分ける
            if item_id in as_ids(item.get(key)):
                referrers.append({"id": item["id"], "key": key})
    return referrers


def list_attrs(workspace: Workspace) -> list[dict[str, Any]]:
    """全ての項目の `attrs` の名前ごとに、持つ項目の数と種類を数える。"""
    counts: dict[str, int] = {}
    kinds_by_name: dict[str, set[Kind]] = {}
    for kind, item in _iter_sorted_items(workspace):
        attrs = item.get("attrs")
        if not isinstance(attrs, dict):
            continue
        for name in attrs:
            counts[name] = counts.get(name, 0) + 1
            kinds_by_name.setdefault(name, set()).add(kind)
    return [
        {
            "name": name,
            "count": counts[name],
            # 種類の並びは KINDS の順
            "kinds": [kind for kind in KINDS if kind in kinds_by_name[name]],
        }
        for name in sorted(counts)
    ]


def list_tags(workspace: Workspace, thread_tags: list[list[str]]) -> list[dict[str, Any]]:
    """項目とスレッドが使っているタグを、正規化した表記ごとに持つ数と種類を数える（件数の多い順）。"""
    counts: dict[str, int] = {}
    kinds_by_name: dict[str, set[str]] = {}
    for kind, item in _iter_sorted_items(workspace):
        tags = item.get("tags")
        if not isinstance(tags, list):
            continue
        # 1 つの項目が同じタグを表記を変えて 2 回持っても 1 件と数える
        for name in _normalized_tags(tags):
            counts[name] = counts.get(name, 0) + 1
            kinds_by_name.setdefault(name, set()).add(kind)
    for tags in thread_tags:
        for name in _normalized_tags(tags):
            counts[name] = counts.get(name, 0) + 1
            kinds_by_name.setdefault(name, set()).add(THREAD_KIND)
    return [
        {
            "name": name,
            "count": counts[name],
            # 種類の並びは KINDS の順で、スレッドは最後
            "kinds": [kind for kind in (*KINDS, THREAD_KIND) if kind in kinds_by_name[name]],
        }
        for name in sorted(counts, key=lambda name: (-counts[name], name))
    ]


def list_stray_tags(
    workspace: Workspace, search_filter: SearchFilter
) -> list[tuple[str, list[str]]]:
    """条件の `tags`・`any_tags` のうち、どの項目も使っていないタグを、近い使われているタグを添えて返す。"""
    used: set[str] = set()
    for _, item in _iter_sorted_items(workspace):
        tags = item.get("tags")
        if isinstance(tags, list):
            used.update(_normalized_tags(tags))
    stray: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for tag in (*search_filter.tags, *search_filter.any_tags):
        name = normalize_tag(tag)
        # 使われているタグと、既に拾ったタグは除く
        if name in used or name in seen:
            continue
        seen.add(name)
        stray.append((tag, similar_tags(tag, used)))
    return stray


def _normalized_tags(tags: list[Any]) -> set[str]:
    """`tags` の名前を正規化し、重なりを除く。"""
    names = (tag_name(entry) for entry in tags)
    return {normalize_tag(name) for name in names if name is not None}


def page_results(
    results: list[Any],
    search_filter: SearchFilter,
    *,
    limit: int,
    cursor: str | None,
    stray_tags: list[tuple[str, list[str]]] | None = None,
) -> dict[str, Any]:
    """検索結果を続きの値の位置から件数だけ切り出し、全体の件数・次の続きの値・絞り込みの案内を添える。"""
    # 続きの値があれば読んだ位置を取り出す（無ければ最初のページ）
    offset = _decode_cursor(cursor, search_filter) if cursor is not None else 0
    items = results[offset : offset + limit]
    # 切り出した後ろに結果が残るときだけ、次の位置を続きの値にする
    has_next = offset + limit < len(results)
    return {
        "items": items,
        "total": len(results),
        "next_cursor": _encode_cursor(offset + limit, search_filter) if has_next else None,
        "hint": build_hint(
            len(results), len(items), search_filter, has_next=has_next, stray_tags=stray_tags
        ),
    }


def build_hint(
    total: int,
    returned: int,
    search_filter: SearchFilter,
    *,
    has_next: bool,
    stray_tags: list[tuple[str, list[str]]] | None = None,
) -> str | None:
    """切り詰めたときは絞り込める引数、0 件のときは外せる条件を案内する文を組み立てる。"""
    given = _given_arguments(search_filter)
    # 条件を渡したのに 0 件: 渡した条件の引数を並べて外すよう案内する
    if total == 0 and given:
        hint = f"合う項目がありません。{'・'.join(given)} のどれかを外して探してください"
        # どの項目も使っていないタグは、近い使われているタグを案内する
        for tag, similar in stray_tags or []:
            nearest = "・".join(similar) if similar else "近いタグなし"
            hint += f" {tag} はどの項目も使っていないタグです（近いタグ: {nearest}）"
        return hint
    # 続きがある: まだ渡していない絞り込みの引数と続きの読み方を案内する
    if has_next:
        remaining = [name for name in NARROWING_ARGUMENTS if name not in given]
        if not remaining:
            return "next_cursor で続きを読んでください"
        return (
            f"全 {total} 件のうち {returned} 件を返しました。"
            f"{'・'.join(remaining)} で絞るか、next_cursor で続きを読んでください"
        )
    return None


def _given_arguments(search_filter: SearchFilter) -> list[str]:
    """渡した条件の引数の名前を返す（属性は `attr`）。"""
    given: list[str] = []
    for name in ("text", "kind", "status", "tags", "any_tags", "target", "category", "phase"):
        # 文字列の条件は None、タグの条件は空のタプルが渡していない印
        if getattr(search_filter, name) not in (None, ()):
            given.append(name)
    if search_filter.attrs:
        given.append("attr")
    return given


def _filter_fingerprint(search_filter: SearchFilter) -> str:
    """条件を短い文字列にする（同じ条件なら同じ値）。"""
    text = json.dumps(asdict(search_filter), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:FINGERPRINT_CHARS]


def _encode_cursor(offset: int, search_filter: SearchFilter) -> str:
    """読んだ位置と条件を、不透明な文字列（末尾の `=` なしの URL 安全な Base64）にする。"""
    payload = json.dumps({"o": offset, "f": _filter_fingerprint(search_filter)})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str, search_filter: SearchFilter) -> int:
    """続きの値から読んだ位置を取り出し、今の条件と同じ条件で作られたかを確かめる。"""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (binascii.Error, ValueError) as error:
        raise ArgumentError("cursor", "読めない続きの値です") from error
    # 位置が 0 以上の整数で、指紋が文字列の辞書でなければ読めない値
    offset = payload.get("o") if isinstance(payload, dict) else None
    fingerprint = payload.get("f") if isinstance(payload, dict) else None
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ArgumentError("cursor", "読めない続きの値です")
    if not isinstance(fingerprint, str):
        raise ArgumentError("cursor", "読めない続きの値です")
    # 前のページと違う条件で渡した
    if fingerprint != _filter_fingerprint(search_filter):
        raise ArgumentError("cursor", "前のページと同じ条件で渡してください")
    return offset


def _iter_sorted_items(workspace: Workspace) -> Iterator[tuple[Kind, dict[str, Any]]]:
    """種類の順・連番の小さい順に項目を返す。"""
    for kind in KINDS:
        yield from (
            (kind, item)
            for item in sorted(
                workspace.items[kind], key=lambda item: id_number(str(item.get("id", "")))
            )
        )


def _matches_fields(item: dict[str, Any], search_filter: SearchFilter) -> bool:
    """状態・対象・カテゴリー・フェーズ・タグ・属性の条件に合うか。"""
    for name in ("status", "target", "category", "phase"):
        wanted = getattr(search_filter, name)
        if wanted is not None and item.get(name) != wanted:
            return False
    item_tags = item.get("tags")
    # タグは渡した側も項目の側も正規化して比べる
    tags = _normalized_tags(item_tags) if isinstance(item_tags, list) else set()
    # tags: 渡したタグを全て持つか
    if not all(normalize_tag(tag) in tags for tag in search_filter.tags):
        return False
    # any_tags: 渡したタグのどれかを持つか（渡していなければ絞らない）
    if search_filter.any_tags and not any(
        normalize_tag(tag) in tags for tag in search_filter.any_tags
    ):
        return False
    attrs = item.get("attrs")
    item_attrs = attrs if isinstance(attrs, dict) else {}
    for name, value in search_filter.attrs:
        # 名前が無い属性は合わない
        if name not in item_attrs:
            return False
        # 値の指定があるときは文字列にして一致を見る
        if value is not None and str(item_attrs[name]) != value:
            return False
    return True


def _contains_text(value: Any, needle: str) -> bool:
    """値の中の文字列（配列・辞書の値をたどる）に文字が含まれるか。"""
    # 文字列: 小文字にして含むか
    if isinstance(value, str):
        return needle in value.lower()
    # 配列は要素を、辞書は値をたどる（辞書のキーは見ない）
    if isinstance(value, list):
        return any(_contains_text(element, needle) for element in value)
    if isinstance(value, dict):
        return any(_contains_text(element, needle) for element in value.values())
    return False
