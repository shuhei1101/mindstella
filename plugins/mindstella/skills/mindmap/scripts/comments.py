"""レビュー中のコメント（`comments.yaml`）と下書き（`drafts.yaml`）を読み書きし、チェックしたコメントをスレッドへ移す。鍵は呼ぶ側が取る。"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from change_detection import accept_written
from errors import (
    CommentConflictError,
    CommentInvalidError,
    CommentNotFoundError,
    ItemNotFoundError,
    SchemaMismatchError,
    ThreadNotFoundError,
    WriteFailedError,
)
from history import (
    EXTERNAL_SUMMARY,
    commit_pending,
    load_changes,
    load_item_history,
)
from kinds import HISTORY_FILE as HISTORY_FILE_NAME, KINDS, records_root
from locations import Location, check_location, location_to_dict, parse_location
from read_point import save_turn_point
from store import (
    CHANGES_FILE as CHANGES_FILE_NAME,
    SCHEMA_DIR,
    WHOLE_PATH,
    NowFn,
    Workspace,
    dump_yaml,
    find_item,
    format_path,
    load_workspace,
    load_yaml_text,
    now_utc,
    remove_files,
    save_batch,
    BatchChange,
    write_failed,
    write_temp,
)
from threads import (
    MAX_BODY_CHARS,
    THREADS_FILE,
    SentPost,
    Thread,
    UserPostInput,
    append_user_posts,
    load_threads,
)

logger = logging.getLogger(__name__)

# ワークスペースのレビュー中のコメントのファイル名（無ければ 0 件）
COMMENTS_FILE = "comments.yaml"

# ワークスペースの下書きのファイル名（無ければ 0 件）
DRAFTS_FILE = "drafts.yaml"

# `SCHEMA_DIR` の下のレビュー中のコメントと下書きのスキーマのファイル名
COMMENTS_SCHEMA = "comments.schema.json"
DRAFTS_SCHEMA = "drafts.schema.json"

# コメントの ID の頭の文字（項目の種類とスレッドの頭の文字と重ならない）
COMMENT_ID_PREFIX = "C"

# コメントの ID の形（`C-{連番}`）
COMMENT_ID_PATTERN = re.compile(rf"^{COMMENT_ID_PREFIX}-(\d+)$")

# まとめて送信した案の選択を 1 つにしたまとまりの説明
CHOICE_SUMMARY = "画面からの案の選択"

# 案の選択を溜められる・送信できる検討事項の状態
CHOOSABLE_STATUSES = frozenset({"未決定", "要見直し"})

# 案の選択を記載する検討事項の種類と、利用者の選択のキー
DECISION_KIND = "decision"
USER_CHOICE_KEY = "user_choice"

# まだまとめていない変更を先にまとまりにするときの説明（保存待ちの編集の保存と同じ）
AI_PENDING_SUMMARY = "まとめる前の AI の書き換え"

# 利用者の選択を書いた項目と変更履歴の編集した人
USER_EDITOR = "user"


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewComment:
    """`comments.yaml` の 1 件。"""

    id: str
    # 向けた項目の ID（項目に紐づかないコメントは None）
    target: str | None
    # 選んだ箇所
    loc: Location | None
    # 前後の空白を除いた本文（一言を添えない案の選択は None で、キーを書かない）
    body: str | None
    # 溜めた日時
    created: str
    # 返信先のスレッドの ID（新規スレッドの最初の書き込みは None で、キーを書かない。持つときは target・loc を持たない）
    thread: str | None = None
    # 案の選択の選んだ案の記号（案の選択でないコメントは None で、キーを書かない。持つときは target が検討事項で、loc・thread を持たない）
    choice: str | None = None


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
    # 返信の入力欄が向けるスレッドの ID（キーを書かないときは None。持つときは target・loc を持たない）
    thread: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewCommentView:
    """『レビュー中のコメントの読み取り』の `items[]` の 1 行。"""

    id: str
    target: str | None
    # 向けた項目のタイトル（項目に紐づかないか、消えていれば None）
    target_title: str | None
    loc: dict[str, Any] | None
    # 本文（一言を添えない案の選択は None）
    body: str | None
    created: str
    # 返信先のスレッドの ID（新規スレッドの最初の書き込みは None）
    thread: str | None
    # 案の選択（`{key}`。案の選択でないコメントは None）
    choice: dict[str, str] | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CommentInput:
    """`_parse_comment_input` が確かめた溜める要求。"""

    target: str | None
    loc: Location | None
    thread: str | None
    # 前後の空白を除いた本文（案の選択で一言を渡さなければ None）
    body: str | None
    # 元に戻すときのコメントの ID と溜めた日時
    id: str | None
    created: str | None
    # 案の選択の選んだ案の記号
    choice: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SentItem:
    """『コメントをまとめて送信する』の `items[]` の 1 行。"""

    # 送信したレビュー中のコメントの ID
    comment: str
    # 書き込みを追加したスレッドと書き込みの ID（案の選択は None）
    thread: str | None
    post: str | None
    # 案の選択のとき、`user_choice` を記載した検討事項の ID（それ以外は None）
    decision: str | None


def load_comments(root: Path) -> CommentFile:
    """`comments.yaml` を読み、スキーマと突き合わせて `CommentFile` にする。"""
    value = read_validated(records_root(root) / COMMENTS_FILE, COMMENTS_SCHEMA)
    # ファイルが無い
    if value is None:
        return CommentFile(seq=0, items=[])
    items = [
        ReviewComment(
            id=item["id"],
            target=item.get("target"),
            loc=parse_location(item["loc"]) if "loc" in item else None,
            body=item.get("body"),
            created=item["created"],
            thread=item.get("thread"),
            choice=item["choice"]["key"] if "choice" in item else None,
        )
        for item in value["items"]
    ]
    return CommentFile(seq=value["seq"], items=sorted(items, key=_number_of))


def load_drafts(root: Path) -> list[Draft]:
    """`drafts.yaml` を読み、スキーマと突き合わせて下書きの並びにする。"""
    value = read_validated(records_root(root) / DRAFTS_FILE, DRAFTS_SCHEMA)
    # ファイルが無い
    if value is None:
        return []
    return [
        Draft(
            target=item.get("target"),
            loc=parse_location(item["loc"]) if "loc" in item else None,
            body=item["body"],
            updated=item["updated"],
            thread=item.get("thread"),
        )
        for item in value["items"]
    ]


def list_review(workspace: Workspace) -> dict[str, Any]:
    """レビュー中のコメントに向けた項目のタイトルを付け、下書きと合わせて読み取りの形にする。"""
    views = [
        ReviewCommentView(
            id=comment.id,
            target=comment.target,
            target_title=_title_of(workspace, comment.target),
            loc=None if comment.loc is None else location_to_dict(comment.loc),
            body=comment.body,
            created=comment.created,
            thread=comment.thread,
            choice=None if comment.choice is None else {"key": comment.choice},
        )
        for comment in load_comments(workspace.root).items
    ]
    drafts = [
        {
            "target": draft.target,
            "loc": None if draft.loc is None else location_to_dict(draft.loc),
            "thread": draft.thread,
            "body": draft.body,
        }
        for draft in load_drafts(workspace.root)
    ]
    return {"items": [asdict(view) for view in views], "drafts": drafts}


def add_comment(
    root: Path, data: dict[str, Any], now: NowFn = now_utc
) -> tuple[ReviewComment, int]:
    """向けた先（項目と箇所か、返信先のスレッド）と本文・案の選択を確かめ、レビュー中のコメントを 1 件足す。`id` を渡されたら消したコメントを同じ ID で戻す。"""
    parsed = _parse_comment_input(data)
    target, loc, thread, body = parsed.target, parsed.loc, parsed.thread, parsed.body
    comment_id, created, choice = parsed.id, parsed.created, parsed.choice
    workspace = load_workspace(root)
    # 向けた項目が無ければ ItemNotFoundError が上がる
    item = None if target is None else find_item(workspace, target).item
    if loc is not None and item is not None:
        reason = check_location(workspace, item, loc)
        # 箇所が今の項目に合わない
        if reason is not None:
            raise CommentConflictError(reason)
    # 案の選択: 選べる検討事項の案か
    if choice is not None and target is not None:
        reason = _check_choice(workspace, target, choice)
        if reason is not None:
            raise CommentConflictError(reason)
    # 返信先のスレッドが無い・クローズ: 溜めない（元に戻すときも同じ）
    if thread is not None:
        found_thread = _find_thread(load_threads(root), thread)
        # 返信先のスレッドが無い
        if found_thread is None:
            raise ThreadNotFoundError(f"スレッドがありません: {thread}")
        reason = _closed_reason(found_thread)
        # 返信先のスレッドがクローズ
        if reason is not None:
            raise CommentConflictError(reason)

    current = load_comments(root)
    if choice is not None:
        existing = next(
            (
                comment
                for comment in current.items
                if comment.target == target and comment.choice is not None
            ),
            None,
        )
        # 同じ検討事項への案の選択は 1 件だけ
        if existing is not None:
            raise CommentConflictError(f"{target} への案の選択は {existing.id} にあります")
    if comment_id is not None:
        # 戻す ID が今のレビュー中にあるか、これまでに振った連番を超える
        if (
            any(comment.id == comment_id for comment in current.items)
            or _number_of_id(comment_id) > current.seq
        ):
            raise CommentConflictError(f"元に戻せないコメントです: {comment_id}")
        comment = ReviewComment(
            id=comment_id,
            target=target,
            loc=loc,
            body=body,
            created=created or "",
            thread=thread,
            choice=choice,
        )
        seq = current.seq
    else:
        # 連番は `seq` + 1 で振る
        seq = current.seq + 1
        comment = ReviewComment(
            id=f"{COMMENT_ID_PREFIX}-{seq}",
            target=target,
            loc=loc,
            body=body,
            created=now(),
            thread=thread,
            choice=choice,
        )
    items = sorted([*current.items, comment], key=_number_of)
    _write_comments(root, seq, items)
    # 新しく溜めたときは、同じ向けた先の下書きを消す（案の選択は下書きを消さない）
    if comment_id is None and choice is None:
        _remove_draft(root, target, loc, thread)
    return comment, len(items)


def update_comment(root: Path, comment_id: str, data: dict[str, Any]) -> ReviewComment:
    """レビュー中のコメント 1 件の本文か案の選択の記号を書き換えるか、箇所を解除する。"""
    has_body, has_loc, has_choice = "body" in data, "loc" in data, "choice" in data
    # 書き換えるものが無い
    if not has_body and not has_loc and not has_choice:
        raise CommentInvalidError("body: body か loc か choice を渡してください")
    body = None
    if has_body and data["body"] is not None:
        body = _validate_body(data["body"])
    # 箇所は外すこと（null）だけを受ける
    if has_loc and data["loc"] is not None:
        raise CommentInvalidError("loc: null だけを受けます")
    choice = _parse_choice(data["choice"]) if has_choice else None

    current = load_comments(root)
    found = next((comment for comment in current.items if comment.id == comment_id), None)
    # その ID のコメントが無い
    if found is None:
        raise CommentNotFoundError(f"コメントがありません: {comment_id}")
    # 案の選択でないコメントは、選んだ案も本文を消すことも受けない
    if found.choice is None and has_choice:
        raise CommentInvalidError("choice: 案の選択のコメントだけが受けます")
    if found.choice is None and has_body and data["body"] is None:
        raise CommentInvalidError("body: 案の選択のコメントだけが null を受けます")
    if choice is not None and found.target is not None:
        reason = _check_choice(load_workspace(root), found.target, choice)
        if reason is not None:
            raise CommentConflictError(reason)
    updated = ReviewComment(
        id=found.id,
        target=found.target,
        loc=None if has_loc else found.loc,
        body=(body if has_body else found.body),
        created=found.created,
        thread=found.thread,
        choice=found.choice if choice is None else choice,
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
    """向けた先（`target` と `loc` の組か、`thread`）の下書きを上書きする。空の本文なら消す。"""
    body = data.get("body")
    # 本文が無いか、文字列でないか、上限を超える
    if not isinstance(body, str) or len(body) > MAX_BODY_CHARS:
        raise CommentInvalidError(f"body: {MAX_BODY_CHARS} 文字以下の文字列で渡してください")
    target, loc, thread = _parse_destination(data)
    # 空でない本文は、向けた項目・スレッドがあるかを確かめる（無ければ ItemNotFoundError・ThreadNotFoundError）
    if body != "":
        if target is not None:
            find_item(load_workspace(root), target)
        # 返信先のスレッドはクローズでも保つ
        if thread is not None and _find_thread(load_threads(root), thread) is None:
            raise ThreadNotFoundError(f"スレッドがありません: {thread}")

    kept = [
        draft
        for draft in load_drafts(root)
        if (draft.target, draft.loc, draft.thread) != (target, loc, thread)
    ]
    if body != "":
        kept.append(Draft(target=target, loc=loc, thread=thread, body=body, updated=now()))
    _write_drafts(root, kept)


def send_comments(
    root: Path, data: dict[str, Any], now: NowFn = now_utc
) -> tuple[str, list[SentItem]]:
    """渡した ID のコメントを全て確かめてから、案の選択は検討事項の `user_choice` へ、ほかはスレッドへ足し、レビュー中から外す。1 件でも合わなければ何も書き換えない。"""
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
    threads = load_threads(root)
    # 同じコメントの書き込みが既にあるものは確かめない（足さずに外すだけ）
    sent_already = {post.comment for thread in threads for post in thread.posts}
    stale = [
        (comment.id, reason)
        for comment in chosen
        if comment.id not in sent_already
        and (reason := _stale_reason(workspace, threads, comment)) is not None
    ]
    # 向けた項目が消えた・箇所が合わない・返信先が無いかクローズのコメントがある
    if stale:
        raise CommentConflictError(f"送信できない書き込みが {len(stale)} 件あります", stale=stale)

    choices = [comment for comment in chosen if comment.choice is not None]
    posts_to_send = [comment for comment in chosen if comment.choice is None]
    records = records_root(root)
    choice_paths = [
        records / name for name in (KINDS[DECISION_KIND].file, HISTORY_FILE_NAME, CHANGES_FILE_NAME)
    ]
    choice_previous = {
        path: (path.read_bytes() if path.exists() else None) for path in choice_paths
    }
    at = now()
    wrote_choices = bool(choices) and _write_user_choices(workspace, choices, at=at)
    # 利用者の選択を書かなかった: まだまとめていない変更だけを今回の差分の始まりの前に 1 つのまとまりにする
    if not wrote_choices:
        wrote_choices = _commit_pending_set(workspace, at=at)

    threads_path = records / THREADS_FILE
    previous = threads_path.read_bytes() if threads_path.exists() else None
    sent_posts: list[SentPost] = []
    sent = at
    if posts_to_send:
        posts = [
            UserPostInput(
                comment=comment.id,
                thread=comment.thread,
                target=comment.target,
                loc=None if comment.loc is None else location_to_dict(comment.loc),
                body=str(comment.body),
            )
            for comment in posts_to_send
        ]
        try:
            sent, sent_posts = append_user_posts(root, posts, now=lambda: at)
        except WriteFailedError:
            # スレッドを書けなかった: 書いた利用者の選択を書き戻す
            _restore_choice_files(root, choice_previous, wrote_choices)
            raise
    try:
        _write_comments(
            root, current.seq, [comment for comment in current.items if comment.id not in set(ids)]
        )
    except WriteFailedError:
        # レビュー中を書けなかった: 足したスレッドと利用者の選択を書き戻し、どれも前のままにする
        if posts_to_send:
            _restore_file(threads_path, previous)
        _restore_choice_files(root, choice_previous, wrote_choices)
        raise
    # 送った返信のスレッドの下書きは消す
    for comment in posts_to_send:
        if comment.thread is not None:
            _remove_draft(root, None, None, comment.thread)
    # 送信を受け付けた時点を、今回の差分の始まりとして記録する（失敗しても送信は取り消さない）
    _record_turn_point(root, at)
    by_comment = {entry.comment: entry for entry in sent_posts}
    items = [
        SentItem(comment=comment.id, thread=None, post=None, decision=comment.target)
        if comment.choice is not None
        else SentItem(
            comment=comment.id,
            thread=by_comment[comment.id].thread,
            post=by_comment[comment.id].post,
            decision=None,
        )
        for comment in chosen
    ]
    logger.info(
        "コメントを送った: %d 件 %s 案の選択 %d 件",
        len(sent_posts),
        sorted({entry.thread for entry in sent_posts}),
        len(choices),
    )
    return sent, items


def send_now(root: Path, data: dict[str, Any], now: NowFn = now_utc) -> tuple[str, SentPost]:
    """書き込み 1 件の向けた先と本文を確かめ、レビュー中に溜めずにスレッドへ足す（鍵は呼ぶ側が取る）。"""
    # 本文と向けた先の形（溜めるときと同じ確かめ）
    body = _validate_body(data.get("body"))
    target, loc, thread = _parse_destination(data)
    # 今送れる向けた先か（まとめて送るときと同じ理由）
    workspace = load_workspace(root)
    threads = load_threads(root)
    reason = _destination_reason(workspace, threads, target, loc, thread)
    if reason is not None:
        raise CommentConflictError(reason)
    # まだまとめていない変更を、スレッドより先に 1 つのまとまりにする（書き戻せるよう前の中身を控える）
    at = now()
    changes_path = records_root(root) / CHANGES_FILE_NAME
    changes_previous = changes_path.read_bytes() if changes_path.exists() else None
    committed = _commit_pending_set(workspace, at=at)
    try:
        sent, posts = append_user_posts(
            root,
            [
                UserPostInput(
                    comment=None,
                    thread=thread,
                    target=target,
                    loc=None if loc is None else location_to_dict(loc),
                    body=body,
                )
            ],
            now=lambda: at,
        )
    except WriteFailedError:
        # スレッドを書けなかった: まとめた changes.yaml を前の中身に戻す
        _restore_choice_files(root, {changes_path: changes_previous}, committed)
        raise
    # 送信を受け付けた時点を、今回の差分の始まりとして記録する（失敗しても送信は取り消さない）
    _record_turn_point(root, sent)
    logger.info("書き込みをすぐ送った: %s", posts[0].thread)
    return sent, posts[0]


def _parse_comment_input(data: dict[str, Any]) -> CommentInput:
    """溜める要求の `target`・`loc`・`thread`・`body`・`id`・`created`・`choice` の形を確かめる。"""
    has_choice = data.get("choice") is not None
    # 案の選択は一言（本文）を渡さなくてよい
    body = None if has_choice and data.get("body") is None else _validate_body(data.get("body"))
    target, loc, thread = _parse_destination(data)
    choice = None
    if has_choice:
        choice = _parse_choice(data["choice"])
        # 案の選択は検討事項に向け、箇所・返信先を持たない
        if target is None:
            raise CommentInvalidError("choice: choice を渡すときは target も渡してください")
        if loc is not None or thread is not None:
            raise CommentInvalidError("choice: loc・thread と一緒には渡せません")
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
    return CommentInput(
        target=target,
        loc=loc,
        thread=thread,
        body=body,
        id=comment_id,
        created=created,
        choice=choice,
    )


def _parse_choice(value: Any) -> str:
    """案の選択が `key` に文字列を持つオブジェクトかを確かめ、選んだ案の記号を返す。"""
    key = value.get("key") if isinstance(value, dict) else None
    # 形が崩れている
    if not isinstance(key, str) or not key:
        raise CommentInvalidError("choice: {key} のオブジェクトで渡してください")
    return key


def _parse_destination(data: dict[str, Any]) -> tuple[str | None, Location | None, str | None]:
    """要求の向けた先（`target` と `loc` の組か、`thread`）の形を確かめる。"""
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
    thread = data.get("thread")
    if thread is not None:
        # 返信先が文字列でない
        if not isinstance(thread, str):
            raise CommentInvalidError("thread: 文字列で渡してください")
        # 返信先を項目・箇所と一緒に渡した
        if target is not None or loc is not None:
            raise CommentInvalidError("thread: target・loc と一緒には渡せません")
    return target, loc, thread


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


def _stale_reason(workspace: Workspace, threads: list[Thread], comment: ReviewComment) -> str | None:
    """向けた項目が消えた・箇所が今の項目に合わない・返信先が無いかクローズ・案を選べないときの理由を返す（送れれば None）。"""
    if comment.choice is not None and comment.target is not None:
        return _check_choice(workspace, comment.target, comment.choice)
    return _destination_reason(workspace, threads, comment.target, comment.loc, comment.thread)


def _check_choice(workspace: Workspace, target: str, key: str) -> str | None:
    """案の選択が向けた検討事項に当てはまるかを確かめ、合わない理由を返す（当てはまれば None）。"""
    try:
        ref = find_item(workspace, target)
    except ItemNotFoundError:
        return f"{target} がありません"
    # 検討事項でない
    if ref.kind != DECISION_KIND:
        return f"{target} は検討事項ではありません"
    status = ref.item.get("status")
    # 案を選べる状態でない
    if status not in CHOOSABLE_STATUSES:
        return f"{target} は {status} のため案を選べません"
    keys = {
        str(option.get("key"))
        for option in ref.item.get("options") or []
        if isinstance(option, dict)
    }
    # 選んだ記号の案が無い
    if key not in keys:
        return f"{target} に案 {key} がありません"
    return None


def _write_user_choices(workspace: Workspace, choices: list[ReviewComment], *, at: str) -> bool:
    """送信する案の選択を検討事項の `user_choice` に当て、変更履歴とまとまりを積んで 1 回で書く。書いたかを返す。"""
    # ツールの処理が点検を読み、点検がこのモジュールを読むため、関数の中で読む
    from commands import Staged, stage_update

    updates: list[tuple[str, dict[str, Any]]] = []
    for comment in choices:
        target = str(comment.target)
        current = find_item(workspace, target).item.get(USER_CHOICE_KEY) or {}
        # 同じ記号と一言の利用者の選択を持つ: 書き換えない
        if current.get("key") == comment.choice and current.get("note") == comment.body:
            continue
        chosen: dict[str, Any] = {"key": comment.choice}
        if comment.body is not None:
            chosen["note"] = comment.body
        chosen["at"] = at
        updates.append((target, chosen))
    # 書き換える検討事項が無い
    if not updates:
        return False
    loaded = load_changes(workspace.root)
    pending_by = loaded["pending"].get("by", "ai")
    record, _ = commit_pending(
        loaded,
        EXTERNAL_SUMMARY if pending_by == "external" else AI_PENDING_SUMMARY,
        at,
        by=pending_by,
    )
    staged = Staged(
        workspace=workspace,
        items=workspace.items,
        touched=frozenset(),
        bodies={},
        history=load_item_history(workspace.root),
        changes=record,
    )
    for target, chosen in updates:
        staged, _ = stage_update(
            staged, target, {USER_CHOICE_KEY: chosen}, lambda: at, editor=USER_EDITOR
        )
    record, _ = commit_pending(staged.changes, CHOICE_SUMMARY, at, by=USER_EDITOR)
    written = save_batch(
        workspace,
        BatchChange(
            items={kind: staged.items[kind] for kind in KINDS if kind in staged.touched},
            bodies=[],
            history=dict(staged.history),
            changes=dict(record),
        ),
    )
    accept_written(workspace.root, written)
    return True


def _commit_pending_set(workspace: Workspace, *, at: str) -> bool:
    """`changes.yaml` のまだまとめていない変更を 1 つのまとまりにして書く。まとめる変更が無ければ書かない。書いたかを返す。"""
    loaded = load_changes(workspace.root)
    pending = loaded["pending"]
    # まとめる変更が無い
    if not pending["added"] and not pending["changed"] and not pending.get("removed"):
        return False
    pending_by = pending.get("by", "ai")
    record, _ = commit_pending(
        loaded,
        EXTERNAL_SUMMARY if pending_by == "external" else AI_PENDING_SUMMARY,
        at,
        by=pending_by,
    )
    written = save_batch(workspace, BatchChange(items={}, changes=dict(record)))
    accept_written(workspace.root, written)
    return True


def _record_turn_point(root: Path, at: str) -> None:
    """今の `last_seq` と受け付けた日時を今回の差分の始まりとして書く。書けなくても送信を取り消さない。"""
    try:
        save_turn_point(root, load_changes(root)["last_seq"], at)
    except (WriteFailedError, OSError) as error:
        # 巻き戻しの範囲に含めない: 理由を記録するだけにする
        print(f"[mindstella] 今回の差分の始まりを記録できません: {error}", file=sys.stderr)


def _restore_choice_files(root: Path, previous: dict[Path, bytes | None], wrote: bool) -> None:
    """利用者の選択を書いた `decisions.yaml`・`history.yaml`・`changes.yaml` を前の中身に戻し、変更の検知にも戻した中身を伝える。"""
    # 利用者の選択を書いていない: 戻すものが無い
    if not wrote:
        return
    for path, content in previous.items():
        _restore_file(path, content)
    accept_written(
        root,
        {
            path.name: (None if content is None else content.decode("utf-8"))
            for path, content in previous.items()
        },
    )


def _destination_reason(
    workspace: Workspace,
    threads: list[Thread],
    target: str | None,
    loc: Location | None,
    thread: str | None,
) -> str | None:
    """向けた先（項目と箇所か、返信先のスレッド）へ今送れないときの理由を返す（送れれば None）。"""
    # 返信: 返信先のスレッドが無いかクローズ
    if thread is not None:
        found = _find_thread(threads, thread)
        if found is None:
            return f"スレッド {thread} がありません"
        return _closed_reason(found)
    # 項目に紐づかないコメントは確かめるものが無い
    if target is None:
        return None
    try:
        item = find_item(workspace, target).item
    except ItemNotFoundError:
        return f"{target} がありません"
    if loc is None:
        return None
    return check_location(workspace, item, loc)


def _find_thread(threads: list[Thread], thread_id: str) -> Thread | None:
    """ID のスレッドを返す（無ければ None）。"""
    return next((thread for thread in threads if thread.id == thread_id), None)


def _closed_reason(thread: Thread) -> str | None:
    """スレッドがクローズのときの理由を返す（オープンなら None）。"""
    if thread.status == "closed":
        return f"スレッド {thread.id} はクローズです"
    return None


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


def read_validated(path: Path, schema_name: str) -> Any | None:
    """YAML を読んでスキーマと突き合わせる（ファイルが無ければ None）。"""
    # ファイルが無い: 0 件として扱う
    if not path.is_file():
        return None
    try:
        value = load_yaml_text(path.read_text(encoding="utf-8"))
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
    """コメントを YAML に書く辞書にする（持たない `target`・`loc`・`thread`・`body`・`choice` は書かない）。"""
    result: dict[str, Any] = {"id": comment.id}
    if comment.target is not None:
        result["target"] = comment.target
    if comment.loc is not None:
        result["loc"] = location_to_dict(comment.loc)
    if comment.body is not None:
        result["body"] = comment.body
    result["created"] = comment.created
    if comment.thread is not None:
        result["thread"] = comment.thread
    if comment.choice is not None:
        result["choice"] = {"key": comment.choice}
    return result


def _draft_dict(draft: Draft) -> dict[str, Any]:
    """下書きを YAML に書く辞書にする（持たない `target`・`loc`・`thread` は書かない）。"""
    result: dict[str, Any] = {}
    if draft.target is not None:
        result["target"] = draft.target
    if draft.loc is not None:
        result["loc"] = location_to_dict(draft.loc)
    result["body"] = draft.body
    result["updated"] = draft.updated
    if draft.thread is not None:
        result["thread"] = draft.thread
    return result


def _write_comments(root: Path, seq: int, items: list[ReviewComment]) -> None:
    """`seq` とコメントの並びを `comments.yaml` に書く。"""
    _write_yaml(
        records_root(root) / COMMENTS_FILE,
        {"seq": seq, "items": [_comment_dict(comment) for comment in items]},
    )


def _write_drafts(root: Path, drafts: list[Draft]) -> None:
    """下書きの並びを `drafts.yaml` に書く。"""
    _write_yaml(
        records_root(root) / DRAFTS_FILE, {"items": [_draft_dict(draft) for draft in drafts]}
    )


def _remove_draft(
    root: Path, target: str | None, loc: Location | None, thread: str | None
) -> None:
    """同じ向けた先の下書きがあれば消す。消せなくても溜めたコメントは残す。"""
    try:
        drafts = load_drafts(root)
        kept = [
            draft for draft in drafts if (draft.target, draft.loc, draft.thread) != (target, loc, thread)
        ]
        # 消す下書きが無い
        if len(kept) == len(drafts):
            return
        _write_drafts(root, kept)
    except (WriteFailedError, SchemaMismatchError) as error:
        logger.warning("下書きを消せなかった: %s", error)


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
