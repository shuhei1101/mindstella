"""レビュー中のコメント（`comments.yaml`）と書きかけ（`drafts.yaml`）を読み書きし、チェックしたコメントを送信へ移す。鍵は呼ぶ側が取る。"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from errors import (
    CommentConflictError,
    CommentInvalidError,
    CommentNotFoundError,
    ItemNotFoundError,
    SchemaMismatchError,
    WriteFailedError,
)
from kinds import records_root
from locations import Location, check_location, location_to_dict, parse_location
from store import (
    SCHEMA_DIR,
    WHOLE_PATH,
    NowFn,
    Workspace,
    dump_yaml,
    find_item,
    format_path,
    load_workspace,
    now_utc,
    remove_files,
    write_failed,
    write_temp,
)
from submissions import MAX_BODY_CHARS, SUBMISSIONS_FILE, append_submissions

logger = logging.getLogger(__name__)

# ワークスペースのレビュー中のコメントのファイル名（無ければ 0 件）
COMMENTS_FILE = "comments.yaml"

# ワークスペースの書きかけのファイル名（無ければ 0 件）
DRAFTS_FILE = "drafts.yaml"

# `SCHEMA_DIR` の下のレビュー中のコメントと書きかけのスキーマのファイル名
COMMENTS_SCHEMA = "comments.schema.json"
DRAFTS_SCHEMA = "drafts.schema.json"

# コメントの ID の頭の文字（項目の種類と送信の頭の文字と重ならない）
COMMENT_ID_PREFIX = "C"

# コメントの ID の形（`C-{連番}`）
COMMENT_ID_PATTERN = re.compile(rf"^{COMMENT_ID_PREFIX}-(\d+)$")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewComment:
    """`comments.yaml` の 1 件。"""

    id: str
    # 向けた項目の ID（項目に紐づかないコメントは None）
    target: str | None
    # 選んだ箇所
    loc: Location | None
    # 前後の空白を除いた本文
    body: str
    # 溜めた日時
    created: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommentFile:
    """`comments.yaml` の中身。"""

    # 最後に振った連番（無ければ 0）
    seq: int
    # 連番の小さい順のコメント
    items: list[ReviewComment]


@dataclass(frozen=True, slots=True, kw_only=True)
class Draft:
    """`drafts.yaml` の 1 件。"""

    # 入力欄が向ける項目の ID
    target: str | None
    # 入力欄に添えた箇所
    loc: Location | None
    body: str
    # 書いた日時
    updated: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewCommentView:
    """『レビュー中のコメントの読み取り』の `items[]` の 1 行。"""

    id: str
    target: str | None
    # 向けた項目のタイトル（項目に紐づかないか、消えていれば None）
    target_title: str | None
    loc: dict[str, Any] | None
    body: str
    created: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SentComment:
    """『コメントをまとめて送る』の `items[]` の 1 行。"""

    comment: str
    submission: str


def load_comments(root: Path) -> CommentFile:
    """`comments.yaml` を読み、スキーマと突き合わせて `CommentFile` にする。"""
    value = _read_validated(records_root(root) / COMMENTS_FILE, COMMENTS_SCHEMA)
    # ファイルが無い
    if value is None:
        return CommentFile(seq=0, items=[])
    items = [
        ReviewComment(
            id=item["id"],
            target=item.get("target"),
            loc=parse_location(item["loc"]) if "loc" in item else None,
            body=item["body"],
            created=item["created"],
        )
        for item in value["items"]
    ]
    return CommentFile(seq=value["seq"], items=sorted(items, key=_number_of))


def load_drafts(root: Path) -> list[Draft]:
    """`drafts.yaml` を読み、スキーマと突き合わせて書きかけの並びにする。"""
    value = _read_validated(records_root(root) / DRAFTS_FILE, DRAFTS_SCHEMA)
    # ファイルが無い
    if value is None:
        return []
    return [
        Draft(
            target=item.get("target"),
            loc=parse_location(item["loc"]) if "loc" in item else None,
            body=item["body"],
            updated=item["updated"],
        )
        for item in value["items"]
    ]


def list_review(workspace: Workspace) -> dict[str, Any]:
    """レビュー中のコメントに向けた項目のタイトルを付け、書きかけと合わせて読み取りの形にする。"""
    views = [
        ReviewCommentView(
            id=comment.id,
            target=comment.target,
            target_title=_title_of(workspace, comment.target),
            loc=None if comment.loc is None else location_to_dict(comment.loc),
            body=comment.body,
            created=comment.created,
        )
        for comment in load_comments(workspace.root).items
    ]
    drafts = [
        {
            "target": draft.target,
            "loc": None if draft.loc is None else location_to_dict(draft.loc),
            "body": draft.body,
        }
        for draft in load_drafts(workspace.root)
    ]
    return {"items": [asdict(view) for view in views], "drafts": drafts}


def add_comment(
    root: Path, data: dict[str, Any], now: NowFn = now_utc
) -> tuple[ReviewComment, int]:
    """向けた先と本文を確かめ、レビュー中のコメントを 1 件足す。`id` を渡されたら消したコメントを同じ ID で戻す。"""
    target, loc, body, comment_id, created = _parse_comment_input(data)
    workspace = load_workspace(root)
    # 向けた項目が無ければ ItemNotFoundError が上がる
    item = None if target is None else find_item(workspace, target).item
    if loc is not None and item is not None:
        reason = check_location(workspace, item, loc)
        # 箇所が今の項目に合わない
        if reason is not None:
            raise CommentConflictError(reason)

    current = load_comments(root)
    if comment_id is not None:
        # 戻す ID が今のレビュー中にあるか、これまでに振った連番を超える
        if (
            any(comment.id == comment_id for comment in current.items)
            or _number_of_id(comment_id) > current.seq
        ):
            raise CommentConflictError(f"元に戻せないコメントです: {comment_id}")
        comment = ReviewComment(
            id=comment_id, target=target, loc=loc, body=body, created=created or ""
        )
        seq = current.seq
    else:
        # 連番は `seq` + 1 で振る
        seq = current.seq + 1
        comment = ReviewComment(
            id=f"{COMMENT_ID_PREFIX}-{seq}", target=target, loc=loc, body=body, created=now()
        )
    items = sorted([*current.items, comment], key=_number_of)
    _write_comments(root, seq, items)
    # 新しく溜めたときは、同じ向けた先の書きかけを消す
    if comment_id is None:
        _remove_draft(root, target, loc)
    return comment, len(items)


def update_comment(root: Path, comment_id: str, data: dict[str, Any]) -> ReviewComment:
    """レビュー中のコメント 1 件の本文を書き換えるか、箇所を外す。"""
    has_body, has_loc = "body" in data, "loc" in data
    # 書き換えるものが無い
    if not has_body and not has_loc:
        raise CommentInvalidError("body: body か loc を渡してください")
    body = None
    if has_body:
        body = _validate_body(data["body"])
    # 箇所は外すこと（null）だけを受ける
    if has_loc and data["loc"] is not None:
        raise CommentInvalidError("loc: null だけを受けます")

    current = load_comments(root)
    found = next((comment for comment in current.items if comment.id == comment_id), None)
    # その ID のコメントが無い
    if found is None:
        raise CommentNotFoundError(f"コメントがありません: {comment_id}")
    updated = ReviewComment(
        id=found.id,
        target=found.target,
        loc=None if has_loc else found.loc,
        body=found.body if body is None else body,
        created=found.created,
    )
    items = [updated if comment.id == comment_id else comment for comment in current.items]
    _write_comments(root, current.seq, items)
    return updated


def delete_comment(root: Path, comment_id: str) -> tuple[ReviewComment, int]:
    """レビュー中のコメント 1 件を消し、消した中身と消した後の件数を返す。"""
    current = load_comments(root)
    found = next((comment for comment in current.items if comment.id == comment_id), None)
    # その ID のコメントが無い（既に消した・送ったものを含む）
    if found is None:
        raise CommentNotFoundError(f"コメントがありません: {comment_id}")
    items = [comment for comment in current.items if comment.id != comment_id]
    _write_comments(root, current.seq, items)
    return found, len(items)


def save_draft(root: Path, data: dict[str, Any], now: NowFn = now_utc) -> None:
    """向けた先（`target` と `loc` の組）の書きかけを上書きする。空の本文なら消す。"""
    body = data.get("body")
    # 本文が無いか、文字列でないか、上限を超える
    if not isinstance(body, str) or len(body) > MAX_BODY_CHARS:
        raise CommentInvalidError(f"body: {MAX_BODY_CHARS} 文字以下の文字列で渡してください")
    target = data.get("target")
    # 向ける項目が文字列でない
    if target is not None and not isinstance(target, str):
        raise CommentInvalidError("target: 文字列で渡してください")
    loc = None
    if data.get("loc") is not None:
        # 箇所だけで項目が無い
        if target is None:
            raise CommentInvalidError("target: loc を渡すときは target も渡してください")
        loc = parse_location(data["loc"])
    # 空でない本文は、向けた項目があるかを確かめる（無ければ ItemNotFoundError）
    if body != "" and target is not None:
        find_item(load_workspace(root), target)

    kept = [draft for draft in load_drafts(root) if (draft.target, draft.loc) != (target, loc)]
    if body != "":
        kept.append(Draft(target=target, loc=loc, body=body, updated=now()))
    _write_drafts(root, kept)


def send_comments(
    root: Path, data: dict[str, Any], now: NowFn = now_utc
) -> tuple[str, list[SentComment]]:
    """渡した ID のコメントを全て確かめてから送信へ足し、レビュー中から外す。1 件でも合わなければ何も書き換えない。"""
    ids = data.get("ids")
    # ids が 1 件以上の文字列の配列でない、または重なりがある
    if not isinstance(ids, list) or not ids or not all(isinstance(entry, str) for entry in ids):
        raise CommentInvalidError("ids: 1 件以上の文字列の配列で渡してください")
    if len(set(ids)) != len(ids):
        raise CommentInvalidError("ids: 重ならないように渡してください")

    current = load_comments(root)
    known = {comment.id for comment in current.items}
    missing = [comment_id for comment_id in ids if comment_id not in known]
    # レビュー中に無い ID がある
    if missing:
        raise CommentNotFoundError(f"コメントがありません: {'、'.join(missing)}")
    chosen = [comment for comment in current.items if comment.id in set(ids)]

    workspace = load_workspace(root)
    stale = [
        (comment.id, reason)
        for comment in chosen
        if (reason := _stale_reason(workspace, comment)) is not None
    ]
    # 向けた項目が消えたか、箇所が合わないコメントがある
    if stale:
        raise CommentConflictError(f"箇所が合わないコメントが {len(stale)} 件あります", stale=stale)

    submissions_path = records_root(root) / SUBMISSIONS_FILE
    previous = submissions_path.read_bytes() if submissions_path.exists() else None
    sent = now()
    submissions = append_submissions(root, chosen, now=lambda: sent)
    try:
        _write_comments(
            root, current.seq, [comment for comment in current.items if comment.id not in set(ids)]
        )
    except WriteFailedError:
        # レビュー中を書けなかった: 足した送信を書き戻し、どちらも前のままにする
        _restore_file(submissions_path, previous)
        raise
    sent_comments = [
        SentComment(comment=comment.id, submission=submission.id)
        for comment, submission in zip(chosen, submissions, strict=True)
    ]
    logger.info(
        "コメントを送った: %d 件 %s",
        len(sent_comments),
        [entry.submission for entry in sent_comments],
    )
    return sent, sent_comments


def _parse_comment_input(
    data: dict[str, Any],
) -> tuple[str | None, Location | None, str, str | None, str | None]:
    """溜める要求の `target`・`loc`・`body`・`id`・`created` の形を確かめる。"""
    body = _validate_body(data.get("body"))
    target = data.get("target")
    # 向ける項目が文字列でない
    if target is not None and not isinstance(target, str):
        raise CommentInvalidError("target: 文字列で渡してください")
    loc = None
    if data.get("loc") is not None:
        # 箇所だけで項目が無い
        if target is None:
            raise CommentInvalidError("target: loc を渡すときは target も渡してください")
        loc = parse_location(data["loc"])
    comment_id, created = data.get("id"), data.get("created")
    if comment_id is not None:
        # `C-{数字}` の形でない
        if not isinstance(comment_id, str) or COMMENT_ID_PATTERN.match(comment_id) is None:
            raise CommentInvalidError(f"id: {COMMENT_ID_PREFIX}-{{連番}} の形で渡してください")
        # 元に戻す日時が無い
        if not isinstance(created, str):
            raise CommentInvalidError("created: id を渡すときは created も渡してください")
    elif created is not None:
        raise CommentInvalidError("id: created を渡すときは id も渡してください")
    return target, loc, body, comment_id, created


def _validate_body(value: Any) -> str:
    """本文が文字列で、前後の空白を除いて 1〜`MAX_BODY_CHARS` 文字かを確かめ、空白を除いた本文を返す。"""
    # 文字列でない
    if not isinstance(value, str):
        raise CommentInvalidError("body: 文字列で渡してください")
    body = value.strip()
    # 空白だけか、上限を超える
    if not body or len(body) > MAX_BODY_CHARS:
        raise CommentInvalidError(f"body: 1〜{MAX_BODY_CHARS} 文字で渡してください")
    return body


def _stale_reason(workspace: Workspace, comment: ReviewComment) -> str | None:
    """向けた項目が消えたか、箇所が今の項目に合わないときの理由を返す（合えば None）。"""
    # 項目に紐づかないコメントは確かめるものが無い
    if comment.target is None:
        return None
    try:
        item = find_item(workspace, comment.target).item
    except ItemNotFoundError:
        return f"{comment.target} がありません"
    if comment.loc is None:
        return None
    return check_location(workspace, item, comment.loc)


def _title_of(workspace: Workspace, item_id: str | None) -> str | None:
    """項目のタイトルを返す（項目に紐づかないか、消えていれば None）。"""
    if item_id is None:
        return None
    try:
        return find_item(workspace, item_id).item["title"]
    except ItemNotFoundError:
        return None


def _number_of(comment: ReviewComment) -> int:
    """コメントの ID の連番を返す。"""
    return _number_of_id(comment.id)


def _number_of_id(comment_id: str) -> int:
    """コメントの ID の連番を返す。"""
    return int(comment_id.removeprefix(f"{COMMENT_ID_PREFIX}-"))


def _read_validated(path: Path, schema_name: str) -> Any | None:
    """YAML を読んでスキーマと突き合わせる（ファイルが無ければ None）。"""
    # ファイルが無い: 0 件として扱う
    if not path.is_file():
        return None
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        # YAML として読めない: 全体の問題として送る
        reason = " ".join(str(error).split())
        raise SchemaMismatchError(
            [f"{path.name}: {WHOLE_PATH}: YAML として読めません: {reason}"]
        ) from error
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    # スキーマに合わない: 合わない箇所ごとの行を持って送る
    if errors:
        raise SchemaMismatchError(
            [
                f"{path.name}: {format_path(error.absolute_path)}: {error.message}"
                for error in errors
            ]
        )
    return value


def _comment_dict(comment: ReviewComment) -> dict[str, Any]:
    """コメントを YAML に書く辞書にする（持たない `target`・`loc` は書かない）。"""
    result: dict[str, Any] = {"id": comment.id}
    if comment.target is not None:
        result["target"] = comment.target
    if comment.loc is not None:
        result["loc"] = location_to_dict(comment.loc)
    result["body"] = comment.body
    result["created"] = comment.created
    return result


def _draft_dict(draft: Draft) -> dict[str, Any]:
    """書きかけを YAML に書く辞書にする（持たない `target`・`loc` は書かない）。"""
    result: dict[str, Any] = {}
    if draft.target is not None:
        result["target"] = draft.target
    if draft.loc is not None:
        result["loc"] = location_to_dict(draft.loc)
    result["body"] = draft.body
    result["updated"] = draft.updated
    return result


def _write_comments(root: Path, seq: int, items: list[ReviewComment]) -> None:
    """`seq` とコメントの並びを `comments.yaml` に書く。"""
    _write_yaml(
        records_root(root) / COMMENTS_FILE,
        {"seq": seq, "items": [_comment_dict(comment) for comment in items]},
    )


def _write_drafts(root: Path, drafts: list[Draft]) -> None:
    """書きかけの並びを `drafts.yaml` に書く。"""
    _write_yaml(
        records_root(root) / DRAFTS_FILE, {"items": [_draft_dict(draft) for draft in drafts]}
    )


def _remove_draft(root: Path, target: str | None, loc: Location | None) -> None:
    """同じ向けた先の書きかけがあれば消す。消せなくても溜めたコメントは残す。"""
    try:
        drafts = load_drafts(root)
        kept = [draft for draft in drafts if (draft.target, draft.loc) != (target, loc)]
        # 消す書きかけが無い
        if len(kept) == len(drafts):
            return
        _write_drafts(root, kept)
    except (WriteFailedError, SchemaMismatchError) as error:
        logger.warning("書きかけを消せなかった: %s", error)


def _restore_file(path: Path, previous: bytes | None) -> None:
    """ファイルを前の中身に戻す（前が無かったときは消す）。"""
    # 前は無かった: 足したファイルを消す
    if previous is None:
        path.unlink(missing_ok=True)
        return
    _write_yaml(path, previous.decode("utf-8"))


def _write_yaml(path: Path, data: dict[str, Any] | str) -> None:
    """ワークスペースの 1 ファイルを一時ファイルから置き換える（文字列はそのまま書く）。"""
    text = data if isinstance(data, str) else dump_yaml(data)
    try:
        temp = write_temp(path, text)
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えに失敗: 一時ファイルを消し、前の中身を残す
        remove_files([temp])
        raise write_failed(path, error) from error
