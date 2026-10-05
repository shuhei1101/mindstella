"""プレビューのコメントの一覧からまとめて送られたコメント（`submissions.yaml`）を読み書きする。鍵は呼ぶ側が取る。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from jsonschema import Draft202012Validator

from errors import ItemNotFoundError, SchemaMismatchError, SubmissionNotFoundError
from store import (
    SCHEMA_DIR,
    WHOLE_PATH,
    NowFn,
    Workspace,
    dump_yaml,
    find_item,
    format_path,
    now_utc,
    remove_files,
    write_failed,
    write_temp,
)

if TYPE_CHECKING:
    from comments import ReviewComment

logger = logging.getLogger(__name__)

# ワークスペースの送信のファイル名（無ければ送信 0 件）
SUBMISSIONS_FILE = "submissions.yaml"

# `SCHEMA_DIR` の下の送信のスキーマのファイル名
SUBMISSIONS_SCHEMA = "submissions.schema.json"

# 本文の上限（前後の空白を除いた文字数。非機能要件の「送信の本文の長さ」）
MAX_BODY_CHARS = 10000

# 送信の ID の頭の文字（項目の種類の頭の文字と重ならない）
ID_PREFIX = "S"


@dataclass(frozen=True, slots=True, kw_only=True)
class Submission:
    """`submissions.yaml` の 1 件。"""

    id: str
    # コメントを向けた項目の ID（項目に紐づかない送信は None で、キーを書かない）
    target: str | None
    # 前後の空白を除いた本文
    body: str
    # 送った日時
    sent: str
    # 取り込んだ日時（取り込んでいなければ None）
    taken: str | None
    # 選んだ箇所（持たない送信は None で、キーを書かない）
    loc: dict[str, Any] | None = None
    # 送ったレビュー中のコメントの ID。まとめて送る途中で止まったときに二重に送らないために持つ（前の版の送信は None で、キーを書かない）
    comment: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingSubmission:
    """`submissions` の出力の `items[]` の 1 行（取り込んでいない送信）。"""

    id: str
    target: str | None
    # 向けた項目のタイトル（項目に紐づかないか、項目が消えていれば None）
    target_title: str | None
    body: str
    sent: str
    # 選んだ箇所（持たなければ None）
    loc: dict[str, Any] | None


def load_submissions(root: Path) -> list[Submission]:
    """`submissions.yaml` を読み、スキーマと突き合わせて送信の並びにする。"""
    path = root / SUBMISSIONS_FILE
    # ファイルが無い: 送信 0 件として扱う
    if not path.is_file():
        return []
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        # YAML として読めない: 全体の問題として送る
        reason = " ".join(str(error).split())
        raise SchemaMismatchError(
            [f"{SUBMISSIONS_FILE}: {WHOLE_PATH}: YAML として読めません: {reason}"]
        ) from error

    schema = json.loads((SCHEMA_DIR / SUBMISSIONS_SCHEMA).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    # スキーマに合わない: 合わない箇所ごとの行を持って送る
    if errors:
        raise SchemaMismatchError(
            [
                f"{SUBMISSIONS_FILE}: {format_path(error.absolute_path)}: {error.message}"
                for error in errors
            ]
        )
    return [
        Submission(
            id=item["id"],
            target=item.get("target"),
            body=item["body"],
            sent=item["sent"],
            taken=item["taken"],
            loc=item.get("loc"),
            comment=item.get("comment"),
        )
        for item in value["items"]
    ]


def list_pending_submissions(workspace: Workspace) -> list[PendingSubmission]:
    """`taken` が空の送信を連番の小さい順に、向けた項目のタイトルを付けて返す。"""
    pending = [
        submission for submission in load_submissions(workspace.root) if submission.taken is None
    ]
    return [
        PendingSubmission(
            id=submission.id,
            target=submission.target,
            target_title=_title_of(workspace, submission.target),
            body=submission.body,
            sent=submission.sent,
            loc=submission.loc,
        )
        for submission in sorted(pending, key=_number_of)
    ]


def take_submission(root: Path, submission_id: str, now: NowFn = now_utc) -> tuple[str, bool]:
    """送信 1 件の `taken` に日時を書く。既に取り込み済みなら書き換えずに前の日時を返す。"""
    current = load_submissions(root)
    found = next((submission for submission in current if submission.id == submission_id), None)
    # その ID の送信が無い
    if found is None:
        raise SubmissionNotFoundError(f"送信がありません: {submission_id}")
    # 既に取り込み済み: 書かずに前の日時を返す
    if found.taken is not None:
        return found.taken, True

    taken = now()
    _write_submissions(
        root,
        [replace(item, taken=taken) if item.id == submission_id else item for item in current],
    )
    return taken, False


def append_submissions(
    root: Path, comments: list[ReviewComment], now: NowFn = now_utc
) -> list[Submission]:
    """レビュー中のコメントを並びの順に、取り込んでいない送信として足す。同じコメントの送信が既にあれば足さずにそれを返す。"""
    current = load_submissions(root)
    sent_already = {submission.comment: submission for submission in current if submission.comment}
    # 連番は最大 + 1 から振り、消した番号を使い回さない
    number = max((_number_of(submission) for submission in current), default=0)
    sent = ""
    added: list[Submission] = []
    result: list[Submission] = []
    for comment in comments:
        existing = sent_already.get(comment.id)
        # 既に送っている: 足さずにその送信を返す
        if existing is not None:
            logger.warning("既に送っていたコメント: %s %s", comment.id, existing.id)
            result.append(existing)
            continue
        # この呼び出しの送信は 1 つの日時にそろえる
        if not sent:
            sent = now()
        number += 1
        submission = Submission(
            id=f"{ID_PREFIX}-{number}",
            target=comment.target,
            body=comment.body,
            sent=sent,
            taken=None,
            loc=None if comment.loc is None else _location_dict(comment.loc),
            comment=comment.id,
        )
        added.append(submission)
        result.append(submission)
    # 足すものがある: 1 回で置き換える
    if added:
        _write_submissions(root, [*current, *added])
    return result


def _number_of(submission: Submission) -> int:
    """送信の ID の連番を返す。"""
    return int(submission.id.removeprefix(f"{ID_PREFIX}-"))


def _title_of(workspace: Workspace, item_id: str | None) -> str | None:
    """項目のタイトルを返す（項目に紐づかないか、項目が消えていれば None）。"""
    # 項目に紐づかない
    if item_id is None:
        return None
    try:
        return find_item(workspace, item_id).item["title"]
    except ItemNotFoundError:
        # 向けた項目が消えている: タイトルは持たない
        return None


def _write_submissions(root: Path, submissions: list[Submission]) -> None:
    """送信の並びを一時ファイルに書いてから `submissions.yaml` を置き換える。"""
    path = root / SUBMISSIONS_FILE
    text = dump_yaml({"items": [_submission_dict(submission) for submission in submissions]})
    try:
        temp = write_temp(path, text)
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えに失敗: 一時ファイルを消し、前の送信を残す
        remove_files([temp])
        raise write_failed(path, error) from error


def _submission_dict(submission: Submission) -> dict[str, Any]:
    """送信を YAML に書く辞書にする（`taken` は `null` のまま書き、`target`・`loc`・`comment` は無ければ書かない）。"""
    return {
        name: value
        for name, value in asdict(submission).items()
        if name == "taken" or value is not None
    }


def _location_dict(location: Any) -> dict[str, Any]:
    """箇所を YAML に書く辞書にする（値を持たないキーは書かない）。"""
    return {name: value for name, value in asdict(location).items() if value is not None}
