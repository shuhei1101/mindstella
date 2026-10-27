"""スレッド（`threads.yaml`）を読み書きする。鍵は呼ぶ側が取る。"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator

from errors import (
    ArgumentError,
    ItemNotFoundError,
    SchemaMismatchError,
    ThreadClosedError,
    ThreadNotFoundError,
)
from kinds import records_root
from store import (
    SCHEMA_DIR,
    THREADS_FILE,
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

logger = logging.getLogger(__name__)

# `SCHEMA_DIR` の下のスレッドのスキーマのファイル名
THREADS_SCHEMA = "threads.schema.json"

# 本文の上限（前後の空白を除いた文字数。非機能要件の「送信の本文の長さ」）
MAX_BODY_CHARS = 10000

# 要約と状態を変える理由の上限（前後の空白を除いた文字数。非機能要件の「スレッドの要約と理由の長さ」）
MAX_SUMMARY_CHARS = 400

# スレッドの ID の頭の文字（項目の種類とコメントの頭の文字と重ならない）
THREAD_ID_PREFIX = "TH"

# 一覧の `head`（最初の書き込みの先頭）の文字数
HEAD_CHARS = 80

# 状態の記録の種類（変えた後の状態ごと）
EVENT_KINDS: dict[str, Literal["closed", "reopened"]] = {"closed": "closed", "open": "reopened"}


@dataclass(frozen=True, slots=True, kw_only=True)
class Post:
    """スレッドの書き込み 1 件。"""

    # `{スレッドの ID}-{連番}`
    id: str
    author: Literal["user", "ai"]
    # 前後の空白を除いた本文
    body: str
    created: str
    # AI の既読
    read: bool
    # 利用者の既読（AI の書き込みは偽で足し、利用者の書き込みは真で足す。画面で開くと真になる）
    seen: bool
    # 利用者の書き込みを AI が取り込んだ日時（取り込んでいなければ None。AI の書き込みはキーを書かない）
    taken: str | None = None
    # 送ったレビュー中のコメントの ID（まとめて送る途中で落ちたとき二重に足さないために持つ。無ければキーを書かない）
    comment: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ThreadEvent:
    """クローズかオープンへの戻しの 1 件。"""

    kind: Literal["closed", "reopened"]
    author: Literal["user", "ai"]
    # 理由（持たなければ None で、`null` と書く）
    reason: str | None
    created: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Thread:
    """`threads.yaml` の 1 件。"""

    id: str
    status: Literal["open", "closed"]
    tags: list[str]
    # 要約（まだ書いていなければ None で、`null` と書く）
    summary: str | None
    posts: list[Post]
    events: list[ThreadEvent]
    # 向けた項目の ID（項目に紐づかないスレッドは None で、キーを書かない）
    target: str | None = None
    # 最初の書き込みに添えた箇所（持たなければ None で、キーを書かない）
    loc: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPostInput:
    """まとめて送るレビュー中のコメント 1 件を、スレッドへ足す形にしたもの。"""

    comment: str
    # 返信先のスレッドの ID（新しいスレッドの最初の書き込みは None）
    thread: str | None
    # 新しいスレッドの向けた項目の ID
    target: str | None
    # 新しいスレッドの最初の書き込みに添えた箇所
    loc: dict[str, Any] | None
    body: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SentPost:
    """まとめて送るの `items[]` の 1 行。"""

    comment: str
    thread: str
    post: str


def load_threads(root: Path) -> list[Thread]:
    """`threads.yaml` を読み、スキーマと突き合わせてスレッドの並びにする。"""
    path = records_root(root) / THREADS_FILE
    # ファイルが無い: スレッド 0 件として扱う
    if not path.is_file():
        return []
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        # YAML として読めない: 全体の問題として送る
        reason = " ".join(str(error).split())
        raise SchemaMismatchError(
            [f"{THREADS_FILE}: {WHOLE_PATH}: YAML として読めません: {reason}"]
        ) from error

    schema = json.loads((SCHEMA_DIR / THREADS_SCHEMA).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    # スキーマに合わない: 合わない箇所ごとの行を持って送る
    if errors:
        raise SchemaMismatchError(
            [
                f"{THREADS_FILE}: {format_path(error.absolute_path)}: {error.message}"
                for error in errors
            ]
        )
    return [_thread_of(item) for item in value["items"]]


def raw_thread_targets(root: Path) -> list[tuple[str, str, bool]]:
    """スキーマに合わない `threads.yaml` から、項目を指すスレッドの（ID・向けた項目・取り込み待ちか）を読める範囲で拾う。"""
    path = records_root(root) / THREADS_FILE
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        # 読めない: 拾えるものが無い
        return []
    items = value.get("items") if isinstance(value, dict) else None
    # スレッドの並びでない: 拾えるものが無い
    if not isinstance(items, list):
        return []
    targets: list[tuple[str, str, bool]] = []
    for item in items:
        # ID と向けた項目が文字列のスレッドだけを拾う
        if not (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("target"), str)
        ):
            continue
        posts = item.get("posts")
        # 取り込んでいない利用者の書き込みを 1 件でも持つ
        waiting = isinstance(posts, list) and any(
            isinstance(post, dict) and post.get("author") == "user" and post.get("taken") is None
            for post in posts
        )
        targets.append((item["id"], item["target"], waiting))
    return targets


def awaiting_posts(thread: Thread) -> list[Post]:
    """AI が取り込んでいない利用者の書き込みを書いた順に返す。"""
    return [post for post in thread.posts if post.author == "user" and post.taken is None]


def list_threads(
    workspace: Workspace,
    *,
    status: Literal["open", "closed", "all"] | None = None,
    tag: str | None = None,
    unread: bool = False,
    awaiting: bool = False,
) -> list[dict[str, Any]]:
    """スレッドを状態・タグ・未読・取り込み待ちで絞り、本文を含めないキーだけの行にする。"""
    # 状態を渡さない: 取り込み待ちを探すときはクローズも含め、そうでなければオープンだけ
    if status is None:
        status = "all" if awaiting else "open"
    rows: list[tuple[Thread, list[Post], int]] = []
    for thread in load_threads(workspace.root):
        waiting = awaiting_posts(thread)
        unread_count = sum(1 for post in thread.posts if not post.read)
        if status != "all" and thread.status != status:
            continue
        if tag is not None and tag not in thread.tags:
            continue
        if unread and unread_count == 0:
            continue
        if awaiting and not waiting:
            continue
        rows.append((thread, waiting, unread_count))
    rows.sort(key=lambda row: _recency_key(row[0]), reverse=True)
    return [
        {
            "id": thread.id,
            "status": thread.status,
            "tags": thread.tags,
            "summary": thread.summary,
            "head": " ".join(thread.posts[0].body.splitlines())[:HEAD_CHARS],
            "target": thread.target,
            "target_title": _title_of(workspace, thread.target),
            "last_author": thread.posts[-1].author,
            "last_at": thread.posts[-1].created,
            "posts": len(thread.posts),
            "unread": unread_count,
            "awaiting": len(waiting),
        }
        for thread, waiting, unread_count in rows
    ]


def view_thread(
    workspace: Workspace, thread_id: str, *, unread_only: bool = True
) -> tuple[dict[str, Any], list[str]]:
    """スレッド 1 件を読む形にし、返した書き込みのうち未読の ID を添える。"""
    thread = _find_thread(load_threads(workspace.root), thread_id)
    shown = [post for post in thread.posts if not (unread_only and post.read)]
    view = {
        "id": thread.id,
        "status": thread.status,
        "tags": thread.tags,
        "summary": thread.summary,
        "target": thread.target,
        "target_title": _title_of(workspace, thread.target),
        "loc": thread.loc,
        "posts": [
            {
                "id": post.id,
                "author": post.author,
                "body": post.body,
                "created": post.created,
                "read": post.read,
                "taken": post.taken,
            }
            for post in shown
        ],
        "events": [_event_dict(event) for event in thread.events],
    }
    return view, [post.id for post in shown if not post.read]


def mark_read(root: Path, thread_id: str, post_ids: list[str]) -> None:
    """スレッドの渡した書き込みの `read` を真にする。変わるものが無ければ書かない。"""
    current = load_threads(root)
    thread = _find_thread(current, thread_id)
    ids = set(post_ids)
    # 渡した書き込みのうち、まだ未読のもの（鍵を取るまでに足された書き込みは変えない）
    unread = [post for post in thread.posts if post.id in ids and not post.read]
    # 変わるものが無い: 書かない
    if not unread:
        return
    posts = [replace(post, read=True) if post.id in ids else post for post in thread.posts]
    _replace_thread(root, current, replace(thread, posts=posts))


def mark_seen(root: Path, thread_id: str) -> list[str]:
    """スレッドの `seen` が偽の書き込みを全て真にし、真にした書き込みの ID を返す。未読が無ければ書かない。"""
    current = load_threads(root)
    thread = _find_thread(current, thread_id)
    unseen = [post.id for post in thread.posts if not post.seen]
    # 未読が無い: 書かずに空を返す
    if not unseen:
        return []
    posts = [post if post.seen else replace(post, seen=True) for post in thread.posts]
    _replace_thread(root, current, replace(thread, posts=posts))
    logger.info("利用者の既読にした: %s %d", thread_id, len(unseen))
    return unseen


def create_thread(
    workspace: Workspace,
    *,
    body: str,
    summary: str,
    tags: list[str] | None = None,
    target: str | None = None,
    now: NowFn = now_utc,
) -> tuple[str, str, str]:
    """AI の書き込みを最初の 1 件にしたオープンのスレッドを足す。"""
    text = _check_text("body", body, MAX_BODY_CHARS)
    summary_text = _check_text("summary", summary, MAX_SUMMARY_CHARS)
    checked_tags = _check_tags([] if tags is None else tags)
    # 向ける項目がある: 無ければ ItemNotFoundError にする
    if target is not None:
        find_item(workspace, target)

    root = workspace.root
    current = load_threads(root)
    created = now()
    thread_id = f"{THREAD_ID_PREFIX}-{_next_number(current)}"
    post_id = f"{thread_id}-1"
    thread = Thread(
        id=thread_id,
        status="open",
        tags=checked_tags,
        summary=summary_text,
        target=target,
        posts=[Post(id=post_id, author="ai", body=text, created=created, read=True, seen=False)],
        events=[],
    )
    _write_threads(root, [*current, thread])
    logger.info("スレッドを立てた: %s %s", thread_id, target)
    return thread_id, post_id, created


def reply_thread(
    root: Path,
    thread_id: str,
    *,
    body: str,
    summary: str,
    take: bool = True,
    now: NowFn = now_utc,
) -> tuple[str, str, list[str]]:
    """オープンのスレッドの末尾に AI の書き込みを足し、要約を書き直し、既読の利用者の書き込みを取り込み済みにする。"""
    text = _check_text("body", body, MAX_BODY_CHARS)
    summary_text = _check_text("summary", summary, MAX_SUMMARY_CHARS)
    current = load_threads(root)
    thread = _find_thread(current, thread_id)
    # クローズのスレッド: 返信せず、オープンに戻す手段を案内する
    if thread.status == "closed":
        raise ThreadClosedError(
            f"スレッド {thread_id} はクローズです。set_thread_status でオープンに戻してから返信してください"
        )

    created = now()
    taken: list[str] = []
    # 既読にした利用者の書き込みを取り込み済みにする（足す書き込みと同じ日時）
    if take:
        thread, taken = _take_read(thread, created)
    post_id = f"{thread_id}-{len(thread.posts) + 1}"
    post = Post(id=post_id, author="ai", body=text, created=created, read=True, seen=False)
    updated = replace(thread, summary=summary_text, posts=[*thread.posts, post])
    _replace_thread(root, current, updated)
    logger.info("返信した: %s %s %d", thread_id, post_id, len(taken))
    return post_id, created, taken


def set_thread_status(
    root: Path,
    thread_id: str,
    *,
    status: str,
    reason: str | None = None,
    author: Literal["user", "ai"],
    now: NowFn = now_utc,
) -> bool:
    """スレッドをクローズにするかオープンに戻し、書き手・理由・日時を状態の記録に足す。既にその状態なら書かない。"""
    # 状態は open・closed のどちらか
    if status not in EVENT_KINDS:
        raise ArgumentError("status", "open か closed を渡してください")
    note = _check_reason(reason)
    current = load_threads(root)
    thread = _find_thread(current, thread_id)
    # 既にその状態: 書かずに偽を返す
    if thread.status == status:
        return False

    event = ThreadEvent(kind=EVENT_KINDS[status], author=author, reason=note, created=now())
    updated = replace(
        thread,
        status="closed" if status == "closed" else "open",
        events=[*thread.events, event],
    )
    _replace_thread(root, current, updated)
    logger.info("スレッドの状態を変えた: %s %s %s", thread_id, status, author)
    return True


def update_thread(
    root: Path,
    thread_id: str,
    *,
    summary: str | None = None,
    tags: list[str] | None = None,
    take: bool = False,
    now: NowFn = now_utc,
) -> list[str]:
    """スレッドの要約とタグを置き換え、既読の利用者の書き込みを取り込み済みにする。クローズのスレッドも書き換える。"""
    # 変えるものを何も渡していない
    if summary is None and tags is None and not take:
        raise ArgumentError("summary", "summary・tags・take のどれかを渡してください")
    summary_text = None if summary is None else _check_text("summary", summary, MAX_SUMMARY_CHARS)
    checked_tags = None if tags is None else _check_tags(tags)
    current = load_threads(root)
    thread = _find_thread(current, thread_id)

    taken: list[str] = []
    if take:
        thread, taken = _take_read(thread, now())
    updated = replace(
        thread,
        summary=thread.summary if summary_text is None else summary_text,
        tags=thread.tags if checked_tags is None else checked_tags,
    )
    _replace_thread(root, current, updated)
    return taken


def append_user_posts(
    root: Path, posts: list[UserPostInput], now: NowFn = now_utc
) -> tuple[str, list[SentPost]]:
    """まとめて送る書き込みを並びの順に足す。同じコメントの書き込みが既にあれば足さずにそれを返す。"""
    current = load_threads(root)
    sent_already = {
        post.comment: (thread.id, post.id)
        for thread in current
        for post in thread.posts
        if post.comment is not None
    }
    by_id = {thread.id: thread for thread in current}
    order = [thread.id for thread in current]
    # 連番は最大 + 1 から振り、消した番号を使い回さない
    number = _next_number(current) - 1
    sent = ""
    added = False
    result: list[SentPost] = []
    for item in posts:
        existing = sent_already.get(item.comment)
        # 既に送っている: 足さずにその書き込みを返す
        if existing is not None:
            logger.warning("既に送っていたコメント: %s %s", item.comment, existing[1])
            result.append(SentPost(comment=item.comment, thread=existing[0], post=existing[1]))
            continue
        # この呼び出しの書き込みは 1 つの日時にそろえる
        if not sent:
            sent = now()
        added = True
        if item.thread is None:
            # 返信先を持たない: オープンのスレッドを立てて、その最初の書き込みにする
            number += 1
            thread_id = f"{THREAD_ID_PREFIX}-{number}"
            post = _user_post(f"{thread_id}-1", item, sent)
            by_id[thread_id] = Thread(
                id=thread_id,
                status="open",
                tags=[],
                summary=None,
                target=item.target,
                loc=item.loc,
                posts=[post],
                events=[],
            )
            order.append(thread_id)
        else:
            # 返信先を持つ: そのスレッドの末尾に足す
            thread = by_id.get(item.thread)
            if thread is None:
                raise ThreadNotFoundError(f"スレッドがありません: {item.thread}")
            thread_id = thread.id
            post = _user_post(f"{thread_id}-{len(thread.posts) + 1}", item, sent)
            by_id[thread_id] = replace(thread, posts=[*thread.posts, post])
        sent_already[item.comment] = (thread_id, post.id)
        result.append(SentPost(comment=item.comment, thread=thread_id, post=post.id))
    # 足したものがある: 1 回で置き換える
    if added:
        _write_threads(root, [by_id[thread_id] for thread_id in order])
    return sent, result


def threads_for_preview(workspace: Workspace) -> dict[str, Any]:
    """全てのスレッドを画面へ返す形にする。AI の既読と取り込み済みは含めず、利用者の既読は含める。"""
    threads = sorted(load_threads(workspace.root), key=_recency_key, reverse=True)
    return {
        "threads": [
            {
                "id": thread.id,
                "status": thread.status,
                "tags": thread.tags,
                "summary": thread.summary,
                "target": thread.target,
                "target_title": _title_of(workspace, thread.target),
                "loc": thread.loc,
                "posts": [
                    {
                        "id": post.id,
                        "author": post.author,
                        "body": post.body,
                        "created": post.created,
                        "seen": post.seen,
                    }
                    for post in thread.posts
                ],
                "events": [_event_dict(event) for event in thread.events],
            }
            for thread in threads
        ]
    }


def reset_unread(root: Path) -> int:
    """全てのスレッドの書き込みの `read` を偽にし、未読に戻した件数を返す。"""
    current = load_threads(root)
    count = sum(1 for thread in current for post in thread.posts if post.read)
    # 既読が無い: 書かずに 0 を返す
    if count == 0:
        return 0
    _write_threads(
        root,
        [
            replace(thread, posts=[replace(post, read=False) for post in thread.posts])
            for thread in current
        ],
    )
    return count


def _take_read(thread: Thread, at: str) -> tuple[Thread, list[str]]:
    """既読にした取り込んでいない利用者の書き込みの `taken` に日時を入れ、その ID を返す。未読の書き込みは取り込み待ちに残す。"""
    posts: list[Post] = []
    taken: list[str] = []
    for post in thread.posts:
        if post.author == "user" and post.read and post.taken is None:
            posts.append(replace(post, taken=at))
            taken.append(post.id)
        else:
            posts.append(post)
    return replace(thread, posts=posts), taken


def _check_text(argument: str, value: Any, max_chars: int) -> str:
    """本文・要約が文字列で、前後の空白を除いて 1 文字以上・上限以下かを確かめ、空白を除いた文を返す。"""
    if not isinstance(value, str):
        raise ArgumentError(argument, "文字列を渡してください")
    text = value.strip()
    # 空白だけ
    if not text:
        raise ArgumentError(argument, "空白だけです")
    # 上限を超える
    if len(text) > max_chars:
        raise ArgumentError(argument, f"{max_chars} 文字までです")
    return text


def _check_tags(tags: Any) -> list[str]:
    """タグが文字列の並びで、重なりと空の文字列を持たないかを確かめる。"""
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ArgumentError("tags", "文字列の並びを渡してください")
    # 空の文字列
    if any(not tag.strip() for tag in tags):
        raise ArgumentError("tags", "空のタグがあります")
    # 重なり
    if len(set(tags)) != len(tags):
        raise ArgumentError("tags", "同じタグが重なっています")
    return list(tags)


def _check_reason(reason: Any) -> str | None:
    """状態を変える理由が `None` か上限以下の文字列かを確かめ、空白だけは `None` にする。"""
    if reason is None:
        return None
    if not isinstance(reason, str):
        raise ArgumentError("reason", "文字列を渡してください")
    text = reason.strip()
    # 上限を超える
    if len(text) > MAX_SUMMARY_CHARS:
        raise ArgumentError("reason", f"{MAX_SUMMARY_CHARS} 文字までです")
    return text or None


def _find_thread(threads: list[Thread], thread_id: str) -> Thread:
    """ID のスレッドを返す。無ければ `ThreadNotFoundError`。"""
    found = next((thread for thread in threads if thread.id == thread_id), None)
    if found is None:
        raise ThreadNotFoundError(f"スレッドがありません: {thread_id}")
    return found


def _next_number(threads: Iterable[Thread]) -> int:
    """次に振るスレッドの連番（最大 + 1。消した番号を使い回さない）を返す。"""
    return max((_number_of(thread) for thread in threads), default=0) + 1


def _number_of(thread: Thread) -> int:
    """スレッドの ID の連番を返す。"""
    return int(thread.id.removeprefix(f"{THREAD_ID_PREFIX}-"))


def _recency_key(thread: Thread) -> tuple[str, int]:
    """最後の書き込みの日時、同じ日時は連番で並べるためのキーを返す。"""
    return thread.posts[-1].created, _number_of(thread)


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


def _user_post(post_id: str, item: UserPostInput, created: str) -> Post:
    """まとめて送るコメントから、AI が読んでいない、取り込んでいない利用者の既読の書き込みを作る。"""
    return Post(
        id=post_id,
        author="user",
        body=item.body,
        created=created,
        read=False,
        seen=True,
        taken=None,
        comment=item.comment,
    )


def _replace_thread(root: Path, current: list[Thread], updated: Thread) -> None:
    """並びの中の同じ ID のスレッドを置き換えて書く。"""
    _write_threads(root, [updated if thread.id == updated.id else thread for thread in current])


def _write_threads(root: Path, threads: list[Thread]) -> None:
    """スレッドの並びを一時ファイルに書いてから `threads.yaml` を置き換える。"""
    path = records_root(root) / THREADS_FILE
    text = dump_yaml({"items": [_thread_dict(thread) for thread in threads]})
    try:
        temp = write_temp(path, text)
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えに失敗: 一時ファイルを消し、前のスレッドを残す
        remove_files([temp])
        raise write_failed(path, error) from error


def _thread_of(item: dict[str, Any]) -> Thread:
    """`threads.yaml` の 1 要素をスレッドにする。"""
    return Thread(
        id=item["id"],
        status=item["status"],
        tags=list(item["tags"]),
        summary=item["summary"],
        target=item.get("target"),
        loc=item.get("loc"),
        posts=[
            Post(
                id=post["id"],
                author=post["author"],
                body=post["body"],
                created=post["created"],
                read=post["read"],
                seen=post["seen"],
                taken=post.get("taken"),
                comment=post.get("comment"),
            )
            for post in item["posts"]
        ],
        events=[ThreadEvent(**event) for event in item["events"]],
    )


def _thread_dict(thread: Thread) -> dict[str, Any]:
    """スレッドを YAML に書く辞書にする（`target`・`loc` は無ければ書かず、`summary` は `null` のまま書く）。"""
    result: dict[str, Any] = {"id": thread.id, "status": thread.status, "tags": thread.tags}
    result["summary"] = thread.summary
    if thread.target is not None:
        result["target"] = thread.target
    if thread.loc is not None:
        result["loc"] = thread.loc
    result["posts"] = [_post_dict(post) for post in thread.posts]
    result["events"] = [_event_dict(event) for event in thread.events]
    return result


def _post_dict(post: Post) -> dict[str, Any]:
    """書き込みを YAML に書く辞書にする（利用者の書き込みの `taken` は `null` のまま書き、AI の書き込みと `comment` が無いものは書かない）。"""
    return {
        name: value
        for name, value in asdict(post).items()
        if (name == "taken" and post.author == "user") or (name != "taken" and value is not None)
    }


def _event_dict(event: ThreadEvent) -> dict[str, Any]:
    """状態の記録を辞書にする。"""
    return asdict(event)
