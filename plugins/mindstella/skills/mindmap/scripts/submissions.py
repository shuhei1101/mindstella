"""プレビューから送られた回答・意見（`submissions.yaml`）を読み書きする。鍵は呼ぶ側が取る。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    SubmissionInvalidError,
    SubmissionNotFoundError,
)
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
    # 回答・意見を向けた項目の ID
    target: str
    # 前後の空白を除いた本文
    body: str
    # 送った日時
    sent: str
    # 取り込んだ日時（取り込んでいなければ None）
    taken: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingSubmission:
    """`submissions` の出力の `items[]` の 1 行（取り込んでいない送信）。"""

    id: str
    target: str
    # 向けた項目のタイトル（項目が消えていれば None）
    target_title: str | None
    body: str
    sent: str


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
    return [Submission(**item) for item in value["items"]]


def add_submission(root: Path, data: dict[str, Any], now: NowFn = now_utc) -> Submission:
    """本文と向けた項目を確かめ、取り込んでいない送信として 1 件足す。"""
    target, body = _validate_input(data)
    # 向けた項目がワークスペースにあるか（無ければ ItemNotFoundError が上がる）
    find_item(load_workspace(root), target)

    current = load_submissions(root)
    # 連番は最大 + 1 で振り、消した番号を使い回さない
    number = max((_number_of(submission) for submission in current), default=0) + 1
    submission = Submission(
        id=f"{ID_PREFIX}-{number}", target=target, body=body, sent=now(), taken=None
    )
    _write_submissions(root, [*current, submission])
    return submission


def list_pending_submissions(workspace: Workspace) -> list[PendingSubmission]:
    """`taken` が空の送信を連番の小さい順に、向けた項目のタイトルを付けて返す。"""
    pending = [
        submission
        for submission in load_submissions(workspace.root)
        if submission.taken is None
    ]
    return [
        PendingSubmission(
            id=submission.id,
            target=submission.target,
            target_title=_title_of(workspace, submission.target),
            body=submission.body,
            sent=submission.sent,
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


def _validate_input(data: dict[str, Any]) -> tuple[str, str]:
    """`target`・`body` が文字列で、`body` が空白だけでも上限超えでもないかを確かめる。"""
    for key in ("target", "body"):
        # 無いか文字列でない
        if not isinstance(data.get(key), str):
            raise SubmissionInvalidError(f"{key}: 文字列で渡してください")
    body = data["body"].strip()
    # 空白だけ
    if not body:
        raise SubmissionInvalidError("body: 回答・意見を入れてください")
    # 上限超え
    if len(body) > MAX_BODY_CHARS:
        raise SubmissionInvalidError(f"body: {MAX_BODY_CHARS} 文字以内にしてください")
    return data["target"], body


def _number_of(submission: Submission) -> int:
    """送信の ID の連番を返す。"""
    return int(submission.id.removeprefix(f"{ID_PREFIX}-"))


def _title_of(workspace: Workspace, item_id: str) -> str | None:
    """項目のタイトルを返す（項目が消えていれば None）。"""
    try:
        return find_item(workspace, item_id).item["title"]
    except ItemNotFoundError:
        # 向けた項目が消えている: タイトルは持たない
        return None


def _write_submissions(root: Path, submissions: list[Submission]) -> None:
    """送信の並びを一時ファイルに書いてから `submissions.yaml` を置き換える。"""
    path = root / SUBMISSIONS_FILE
    text = dump_yaml({"items": [asdict(submission) for submission in submissions]})
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
