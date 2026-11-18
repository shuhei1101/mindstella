"""スキーマ違反・ID の重複・参照切れ・本文のずれ・変更履歴のずれの点検（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from comments import COMMENTS_FILE, DRAFTS_FILE, load_comments, load_drafts
from errors import ItemNotFoundError, SchemaMismatchError
from history import (
    CHANGES_FILE,
    Changes,
    apply_body_diff,
    load_changes,
    load_item_history,
    removed_items,
)
from kinds import BODY_DIR, KINDS, RECORD_DIR, kind_of_id, records_root
from store import (
    Problem,
    Workspace,
    as_ids,
    find_item,
    read_body,
    related_ids,
    validate_workspace,
)
from threads import THREADS_FILE, awaiting_posts, load_threads, raw_thread_targets

# 関連の種類を表すキーの頭（`related.depends_on` など）
RELATED_PREFIX = "related."

# リストの記号・引用の `>` を除いた行の頭（フェンスの行を見分けるため）
_LINE_PREFIX = re.compile(r"^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*")

# フェンスを開く行の記号（3 つ以上のバッククォートかチルダ）
_FENCE_OPEN = re.compile(r"^(`{3,}|~{3,})")

# インラインコード（同じ数のバッククォートで囲んだ範囲）
_INLINE_CODE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")

# 画像の記法 `![…](パス)`・`![…](パス "title")`・`![…](<パス>)` のパス
_IMAGE_PATH = re.compile(r"!\[[^\]]*\]\(\s*(<[^>]*>|[^\s)]+)(?:\s+\"[^\"]*\")?\s*\)")

# スキームを持つパス（`https:`・`data:` など）
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

# （参照する側の種類, `related` の種類かキー）→ 指してよい種類。表に無い組は持たない
REF_RULES: dict[tuple[str, str], frozenset[str]] = {
    ("decision", "related.depends_on"): frozenset({"decision"}),
    ("decision", "related.parent"): frozenset({"decision"}),
    ("decision", "sources"): frozenset({"log"}),
    ("task", "related.depends_on"): frozenset({"task"}),
    ("task", "related.for"): frozenset({"decision"}),
    **{(kind, "related.see_also"): frozenset(KINDS) for kind in KINDS},
}


def check_workspace(workspace: Workspace) -> list[Problem]:
    """全ての問題をファイル名の順、同じファイルの中は拾った順に返す。"""
    problems = [
        *validate_workspace(workspace),
        *_check_duplicate_ids(workspace),
        *_check_refs(workspace),
        *_check_bodies(workspace),
        *_check_embedded_files(workspace),
        *_check_threads(workspace),
        *_check_comments(workspace),
        *_check_history(workspace),
    ]
    # ファイル名の順に並べ（sorted は安定なので、同じファイルの中は拾った順を保つ）、ワークスペースからの相対パスにする
    ordered = sorted(problems, key=lambda problem: problem.file)
    return [replace(problem, file=f"{RECORD_DIR}/{problem.file}") for problem in ordered]


def find_referrers(workspace: Workspace, item_id: str) -> list[str]:
    """1 項目を指している記録を `{ファイル名}: {指している側の ID かキーのパス}: {キー}` の行で返す（読むだけ）。"""
    lines: list[str] = []
    # 種類の順に、ほかの項目の参照のキーが指しているものを拾う
    for kind, spec in KINDS.items():
        for item in workspace.items[kind]:
            # 自分自身の参照は、消えるので指しているうちに入れない
            if item.get("id") == item_id:
                continue
            for rule_kind, key in REF_RULES:
                if rule_kind == kind and item_id in _refs_of(item, key):
                    lines.append(f"{spec.file}: {item.get('id')}: {key}")
    # レビュー中のコメントと書きかけが向けている
    lines.extend(
        f"{COMMENTS_FILE}: {comment.id}: target"
        for comment in load_comments(workspace.root).items
        if comment.target == item_id
    )
    lines.extend(
        f"{DRAFTS_FILE}: items[{index}]: target"
        for index, draft in enumerate(load_drafts(workspace.root))
        if draft.target == item_id
    )
    # 取り込み待ちのスレッドが向けている（オープンでもクローズでも。取り込み済みだけのスレッドは記録として残るので拾わない）
    lines.extend(
        f"{THREADS_FILE}: {thread.id}: target"
        for thread in load_threads(workspace.root)
        if awaiting_posts(thread) and thread.target == item_id
    )
    return lines


def _removed_ids(root: Path) -> set[str]:
    """`changes.yaml` に記録した、消した項目の ID を返す。読めない `changes.yaml` は、消した項目なしとして扱う（その問題は履歴の点検が返す）。"""
    try:
        return {removed["id"] for removed in removed_items(load_changes(root))}
    except SchemaMismatchError:
        return set()


def _check_duplicate_ids(workspace: Workspace) -> list[Problem]:
    """同じ ID を 2 つ目以降に持つ項目を `duplicate_id` にする。"""
    problems: list[Problem] = []
    seen: set[str] = set()
    for kind, spec in KINDS.items():
        for index, item in enumerate(workspace.items[kind]):
            item_id = item.get("id")
            if not isinstance(item_id, str):
                continue
            # 既に出た ID: 2 つ目以降の項目を問題にする
            if item_id in seen:
                problems.append(
                    Problem(
                        kind="duplicate_id",
                        file=spec.file,
                        id=item_id,
                        key=f"items[{index}].id",
                        detail=f"ID が重複しています: {item_id}",
                    )
                )
            seen.add(item_id)
    return problems


def _check_refs(workspace: Workspace) -> list[Problem]:
    """存在しない ID と、`REF_RULES` に合わない種類の ID を指す参照を `broken_ref` にする。"""
    existing = {kind: {item.get("id") for item in workspace.items[kind]} for kind in KINDS}
    problems: list[Problem] = []
    for kind, spec in KINDS.items():
        for item in workspace.items[kind]:
            related = item.get("related")
            # 関連は要素ごとに、種類の組で指してよい種類を引く
            for index, entry in enumerate(related if isinstance(related, list) else []):
                if not isinstance(entry, dict) or not isinstance(entry.get("to"), str):
                    continue
                allowed = REF_RULES.get((kind, f"{RELATED_PREFIX}{entry.get('type')}"))
                # その種類が持てない関連の種類
                if allowed is None:
                    detail: str | None = f"使えない関連の種類: {entry.get('type')}"
                else:
                    detail = _ref_error(entry["to"], allowed, existing)
                if detail is not None:
                    problems.append(
                        Problem(
                            kind="broken_ref",
                            file=spec.file,
                            id=item.get("id"),
                            key=f"related[{index}].to",
                            detail=detail,
                        )
                    )
            # 出典（sources）は種類の組でそのまま引く
            sources_allowed = REF_RULES.get((kind, "sources"))
            if sources_allowed is None:
                continue
            for ref in as_ids(item.get("sources")):
                detail = _ref_error(ref, sources_allowed, existing)
                if detail is not None:
                    problems.append(
                        Problem(
                            kind="broken_ref",
                            file=spec.file,
                            id=item.get("id"),
                            key="sources",
                            detail=detail,
                        )
                    )
    return problems


def _check_bodies(workspace: Workspace) -> list[Problem]:
    """指す本文が無い項目と、どこからも指されない `docs/*.md`・`docs/*.html` を拾う。"""
    problems: list[Problem] = []
    referenced: set[str] = set()
    for kind, spec in KINDS.items():
        for index, item in enumerate(workspace.items[kind]):
            body = item.get("body")
            if not isinstance(body, str):
                continue
            # 前の版の形（docs/ の無いファイル名）はスキーマの問題として拾うので、本文の有無は見ない
            if "/" not in body:
                referenced.add(f"{BODY_DIR}/{body}")
                continue
            referenced.add(body)
            # body が指す本文のファイルが無い
            if read_body(workspace, body) is None:
                problems.append(
                    Problem(
                        kind="missing_body",
                        file=spec.file,
                        id=item.get("id"),
                        key=f"items[{index}].body",
                        detail=f"本文がありません: {body}",
                    )
                )
    body_dir = records_root(workspace.root) / BODY_DIR
    # どの項目の body にも無い本文は、どこからも指されていない
    paths = [*body_dir.glob("*.md"), *body_dir.glob("*.html")] if body_dir.is_dir() else []
    for path in sorted(paths):
        if f"{BODY_DIR}/{path.name}" not in referenced:
            problems.append(
                Problem(
                    kind="orphan_body",
                    file=f"{BODY_DIR}/{path.name}",
                    id=None,
                    key=None,
                    detail="どの項目の body からも指されていません",
                )
            )
    return problems


def _refs_of(item: dict[str, Any], key: str) -> list[str]:
    """`related.{種類}` はその種類の関連の相手、それ以外はそのキーの ID の並びを返す。"""
    if key.startswith(RELATED_PREFIX):
        return related_ids(item, key.removeprefix(RELATED_PREFIX))
    return as_ids(item.get(key))


def _ref_error(ref: str, allowed: frozenset[str], existing: dict[str, set[Any]]) -> str | None:
    """参照が指してはいけない種類か、存在しない ID なら理由を返す（正しければ None）。"""
    ref_kind = kind_of_id(ref)
    # 指してよい種類でない
    if ref_kind is None or ref_kind not in allowed:
        return f"指してはいけない種類: {ref}"
    # その種類に ID が無い
    if ref not in existing[ref_kind]:
        return f"存在しない ID: {ref}"
    return None


def _check_comments(workspace: Workspace) -> list[Problem]:
    """`comments.yaml`・`drafts.yaml` のスキーマ違反を `schema` にする（向けた項目は確かめない）。"""
    problems: list[Problem] = []
    for file, load in ((COMMENTS_FILE, load_comments), (DRAFTS_FILE, load_drafts)):
        try:
            load(workspace.root)
        except SchemaMismatchError as error:
            # 読めない・合わない: `{ファイル名}: {キーのパス}: {理由}` の行を、パスと理由に分けて `schema` にする
            problems.extend(
                Problem(
                    kind="schema",
                    file=file,
                    id=None,
                    key=line.split(": ", 2)[1],
                    detail=line.split(": ", 2)[2],
                )
                for line in error.lines
            )
    return problems


def _check_embedded_files(workspace: Workspace) -> list[Problem]:
    """Markdown の本文が画像の記法で指すワークスペースの中のファイルが無いものを `missing_file` にする。"""
    problems: list[Problem] = []
    body_dir = records_root(workspace.root) / BODY_DIR
    for kind in KINDS:
        for item in workspace.items[kind]:
            body = item.get("body")
            # Markdown の本文だけを確かめる（前の版の形の body はスキーマの問題として拾う）
            if not isinstance(body, str) or not body.endswith(".md") or "/" not in body:
                continue
            markdown = read_body(workspace, body)
            # 本文が無いものは _check_bodies が missing_body にする
            if markdown is None:
                continue
            for written in embedded_paths(markdown):
                # `#`・`?` より後ろは再生位置などで、ファイルのパスに含めない
                file_part = re.split(r"[#?]", written, maxsplit=1)[0]
                if (body_dir / unquote(file_part)).is_file():
                    continue
                problems.append(
                    Problem(
                        kind="missing_file",
                        file=body,
                        id=item.get("id"),
                        key=None,
                        detail=written,
                    )
                )
    return problems


def embedded_paths(markdown: str) -> list[str]:
    """Markdown から、コードの外部の画像の記法 `![…](パス)` の相対パスを、記載した順に拾う。"""
    paths: list[str] = []
    # 開いているフェンスの記号と、閉じるのに要る数
    fence: tuple[str, int] | None = None
    # 直前の行が空行か字下げのコードの行（字下げのコードを始められる）
    code_may_start = True
    for line in markdown.split("\n"):
        stripped = _LINE_PREFIX.sub("", line, count=1)
        # フェンスの中と、フェンスを閉じる行は飛ばす
        if fence is not None:
            symbol, count = fence
            if re.fullmatch(rf"{re.escape(symbol)}{{{count},}}[ \t]*", stripped):
                fence = None
            continue
        opened = _FENCE_OPEN.match(stripped)
        # フェンスを開く行は飛ばす
        if opened is not None:
            fence = (opened[1][0], len(opened[1]))
            continue
        indented = code_may_start and re.match(r"^( {4}|\t)", line) is not None
        code_may_start = line.strip() == "" or indented
        # 字下げのコードの行と空行は飛ばす
        if indented or line.strip() == "":
            continue
        for matched in _IMAGE_PATH.finditer(_INLINE_CODE.sub("", line)):
            path = matched[1]
            # `<…>` で囲んだパスは囲みを外す
            if path.startswith("<") and path.endswith(">"):
                path = path[1:-1]
            # 絶対 URL・`/` で始まるパス・`#` だけのパスは、ワークスペースのファイルを指さない
            if _SCHEME.match(path) or path.startswith(("/", "#")):
                continue
            paths.append(path)
    return paths


def _check_threads(workspace: Workspace) -> list[Problem]:
    """`threads.yaml` のスキーマ違反を `schema`、無い項目への `target` を `broken_ref` にする。"""
    try:
        threads = load_threads(workspace.root)
    except SchemaMismatchError as error:
        # 読めない・合わない: `{ファイル名}: {キーのパス}: {理由}` の行を、パスと理由に分けて `schema` にし、読める範囲のスレッドの参照切れも拾う
        return [
            Problem(
                kind="schema",
                file=THREADS_FILE,
                id=None,
                key=line.split(": ", 2)[1],
                detail=line.split(": ", 2)[2],
            )
            for line in error.lines
        ] + _check_thread_targets(workspace, raw_thread_targets(workspace.root))
    # 項目を指すスレッドだけを確かめる
    return _check_thread_targets(
        workspace,
        [
            (thread.id, thread.target, bool(awaiting_posts(thread)))
            for thread in threads
            if thread.target is not None
        ],
    )


def _check_thread_targets(
    workspace: Workspace, targets: list[tuple[str, str, bool]]
) -> list[Problem]:
    """（スレッドの ID・向けた項目・取り込み待ちか）のうち、向けた項目が無いものを `broken_ref` にする。"""
    problems: list[Problem] = []
    removed_ids = _removed_ids(workspace.root)
    for thread_id, target, waiting in targets:
        # 取り込み待ちでないスレッドが消した項目を指す: 記録として残るので拾わない
        if not waiting and target in removed_ids:
            continue
        try:
            find_item(workspace, target)
        except ItemNotFoundError:
            # 向けた項目が無い: 参照切れにする
            problems.append(
                Problem(
                    kind="broken_ref",
                    file=THREADS_FILE,
                    id=thread_id,
                    key="target",
                    detail=f"存在しない ID: {target}",
                )
            )
    return problems


def _check_history(workspace: Workspace) -> list[Problem]:
    """`changes.yaml` のスキーマ違反・参照切れと、今の本文に当たらない変更履歴を拾う。"""
    problems: list[Problem] = []
    try:
        changes = load_changes(workspace.root)
    except SchemaMismatchError as error:
        # 読めない・合わない: 行を `schema` にして、参照切れは確かめない
        problems.extend(
            Problem(
                kind="schema",
                file=CHANGES_FILE,
                id=None,
                key=line.split(": ", 2)[1],
                detail=line.split(": ", 2)[2],
            )
            for line in error.lines
        )
    else:
        problems.extend(_missing_change_refs(workspace, changes))
    problems.extend(_stale_histories(workspace))
    return problems


def _missing_change_refs(workspace: Workspace, changes: Changes) -> list[Problem]:
    """まとまりと、まだまとめていない変更が指す ID のうち、項目が無いものを `broken_ref` にする。"""
    existing = {item.get("id") for kind in KINDS for item in workspace.items[kind]}
    # 消した項目の ID は、項目が無くても参照切れにしない
    existing.update(removed["id"] for removed in removed_items(changes))
    groups = [
        *(
            (change_set["id"], f"sets[{index}].{key}", change_set[key])
            for index, change_set in enumerate(changes["sets"])
            for key in ("added", "changed")
        ),
        *((None, f"pending.{key}", changes["pending"][key]) for key in ("added", "changed")),
    ]
    return [
        Problem(
            kind="broken_ref",
            file=CHANGES_FILE,
            id=owner,
            key=key,
            detail=f"存在しない ID: {ref}",
        )
        for owner, key, ids in groups
        for ref in ids
        if ref not in existing
    ]


def _stale_histories(workspace: Workspace) -> list[Problem]:
    """本文を持つ項目の変更履歴を今の本文へ新しい順に当て、当たらなくなる回を `stale_history` にする。"""
    problems: list[Problem] = []
    rows = load_item_history(workspace.root)
    for kind, spec in KINDS.items():
        for item in workspace.items[kind]:
            name = item.get("body")
            text = read_body(workspace, name) if isinstance(name, str) else None
            history = rows.get(str(item.get("id")), {}).get("history")
            # 本文か変更履歴が無い項目は確かめるものが無い
            if text is None or not isinstance(history, list):
                continue
            for position, entry in enumerate(history):
                # 本文を変えていない回は、本文を戻さない
                if not isinstance(entry, dict) or "body_diff" not in entry:
                    continue
                restored = apply_body_diff(text, entry["body_diff"])
                # 差分が本文に当たらない: この回より前の本文を出せない
                if restored is None:
                    problems.append(
                        Problem(
                            kind="stale_history",
                            file=spec.file,
                            id=item.get("id") if isinstance(item.get("id"), str) else None,
                            key=f"history[{position}].body_diff",
                            detail=f"本文に当たりません。この回より前の本文の差分を出せません: {name}",
                        )
                    )
                    break
                text = restored
    return problems
