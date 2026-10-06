"""スキーマ違反・ID の重複・参照切れ・本文のずれ・設定に無いフェーズ・変更履歴のずれの点検（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from comments import COMMENTS_FILE, DRAFTS_FILE, load_comments, load_drafts
from errors import ItemNotFoundError, SchemaMismatchError
from history import CHANGES_FILE, Changes, apply_body_diff, load_changes
from kinds import BODY_DIR, KINDS, RECORD_DIR, SETTINGS_FILE, kind_of_id, records_root
from store import Problem, Workspace, as_ids, find_item, read_body, validate_workspace
from submissions import SUBMISSIONS_FILE, load_submissions

# 設定の納品物の資料を指すキー（`REF_RULES` の参照する側の種類に使う）
SETTINGS_KIND = "settings"
DELIVERABLE_DOC_KEY = "goal.deliverables[].doc"

# （参照する側の種類, キー）→ 指してよい種類。表に無い組はそのキーを持たない
REF_RULES: dict[tuple[str, str], frozenset[str]] = {
    ("decision", "depends_on"): frozenset({"decision"}),
    ("decision", "parent"): frozenset({"decision"}),
    ("decision", "sources"): frozenset({"log"}),
    ("task", "depends_on"): frozenset({"task"}),
    ("task", "for"): frozenset({"decision"}),
    **{(kind, "related"): frozenset(KINDS) for kind in KINDS},
    (SETTINGS_KIND, DELIVERABLE_DOC_KEY): frozenset({"doc"}),
}


def check_workspace(workspace: Workspace) -> list[Problem]:
    """全ての問題をファイル名の順、同じファイルの中は拾った順に返す。"""
    problems = [
        *validate_workspace(workspace),
        *_check_duplicate_ids(workspace),
        *_check_refs(workspace),
        *_check_bodies(workspace),
        *_check_submissions(workspace),
        *_check_comments(workspace),
        *_check_phases(workspace),
        *_check_history(workspace),
    ]
    # ファイル名の順に並べ（sorted は安定なので、同じファイルの中は拾った順を保つ）、ワークスペースからの相対パスにする
    ordered = sorted(problems, key=lambda problem: problem.file)
    return [replace(problem, file=f"{RECORD_DIR}/{problem.file}") for problem in ordered]


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
            for (rule_kind, key), allowed in REF_RULES.items():
                if rule_kind != kind:
                    continue
                for ref in as_ids(item.get(key)):
                    detail = _ref_error(ref, allowed, existing)
                    if detail is not None:
                        problems.append(
                            Problem(
                                kind="broken_ref",
                                file=spec.file,
                                id=item.get("id"),
                                key=key,
                                detail=detail,
                            )
                        )
    allowed_docs = REF_RULES[(SETTINGS_KIND, DELIVERABLE_DOC_KEY)]
    for index, deliverable in enumerate(_deliverables(workspace.settings)):
        for ref in as_ids(deliverable.get("doc")):
            detail = _ref_error(ref, allowed_docs, existing)
            if detail is not None:
                problems.append(
                    Problem(
                        kind="broken_ref",
                        file=SETTINGS_FILE,
                        id=None,
                        key=f"goal.deliverables[{index}].doc",
                        detail=detail,
                    )
                )
    return problems


def _check_bodies(workspace: Workspace) -> list[Problem]:
    """指す本文が無い項目と、どこからも指されない `docs/*.md` を拾う。"""
    problems: list[Problem] = []
    referenced: set[str] = set()
    for kind, spec in KINDS.items():
        for index, item in enumerate(workspace.items[kind]):
            body = item.get("body")
            if not isinstance(body, str):
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
                        detail=f"本文がありません: {BODY_DIR}/{body}",
                    )
                )
    body_dir = records_root(workspace.root) / BODY_DIR
    # どの項目の body にも無い本文は、どこからも指されていない
    for path in sorted(body_dir.glob("*.md")) if body_dir.is_dir() else []:
        if path.name not in referenced:
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


def _check_phases(workspace: Workspace) -> list[Problem]:
    """項目の `phase` と設定の `goal.phase` のうち、設定の `phases` に無いものを `unknown_phase` にする。"""
    settings = workspace.settings
    phases = settings.get("phases")
    known = set(phases) if isinstance(phases, list) else set()
    problems: list[Problem] = []
    goal = settings.get("goal")
    # ゴールのフェーズが phases に無い
    if isinstance(goal, dict) and goal.get("phase") not in known:
        problems.append(
            Problem(
                kind="unknown_phase",
                file=SETTINGS_FILE,
                id=None,
                key="goal.phase",
                detail=str(goal.get("phase")),
            )
        )
    for kind, spec in KINDS.items():
        for index, item in enumerate(workspace.items[kind]):
            phase = item.get("phase")
            # フェーズを持ち、phases に無い
            if phase is not None and phase not in known:
                problems.append(
                    Problem(
                        kind="unknown_phase",
                        file=spec.file,
                        id=item.get("id") if isinstance(item.get("id"), str) else None,
                        key=f"items[{index}].phase",
                        detail=str(phase),
                    )
                )
    return problems


def _deliverables(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """設定のゴールの納品物のうち、辞書のものを取り出す。"""
    goal = settings.get("goal")
    deliverables = goal.get("deliverables") if isinstance(goal, dict) else None
    if not isinstance(deliverables, list):
        return []
    return [deliverable for deliverable in deliverables if isinstance(deliverable, dict)]


def _check_submissions(workspace: Workspace) -> list[Problem]:
    """`submissions.yaml` のスキーマ違反を `schema`、無い項目への `target` を `broken_ref` にする。"""
    try:
        submissions = load_submissions(workspace.root)
    except SchemaMismatchError as error:
        # 読めない・合わない: `{ファイル名}: {キーのパス}: {理由}` の行を、パスと理由に分けて `schema` にする
        return [
            Problem(
                kind="schema",
                file=SUBMISSIONS_FILE,
                id=None,
                key=line.split(": ", 2)[1],
                detail=line.split(": ", 2)[2],
            )
            for line in error.lines
        ]
    problems: list[Problem] = []
    for submission in submissions:
        # 項目に紐づかない送信は確かめるものが無い
        if submission.target is None:
            continue
        try:
            find_item(workspace, submission.target)
        except ItemNotFoundError:
            # 向けた項目が無い: 参照切れにする
            problems.append(
                Problem(
                    kind="broken_ref",
                    file=SUBMISSIONS_FILE,
                    id=submission.id,
                    key="target",
                    detail=f"存在しない ID: {submission.target}",
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
    for kind, spec in KINDS.items():
        for item in workspace.items[kind]:
            name = item.get("body")
            text = read_body(workspace, name) if isinstance(name, str) else None
            history = item.get("history")
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
