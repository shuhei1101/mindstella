"""配信しているワークスペースの記録のファイルの書き換えを前回の中身と比べて履歴に記録し、外部の変更をまとめ、重なった ID を知らせる。

記録のファイル（種類ごとの YAML と本文）は書かず、`history.yaml` と `changes.yaml` だけを書く。
"""

from __future__ import annotations

import contextlib
import dataclasses
import logging
import os
import subprocess
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from claude_input import PASTE_DEADLINE_SEC, InputTarget, InputTargets, paste_to_pane
from errors import WriteFailedError
from history import (
    EXTERNAL_SUMMARY,
    HISTORY_FILE,
    Changes,
    ItemHistory,
    RemovedItem,
    advance_seq,
    commit_pending,
    flush_pending,
    history_limit,
    load_changes,
    load_item_history,
    make_entry,
    note_pending,
    note_removed,
    stack_history,
)
from inject_session import process_started_at
from kinds import BODY_DIR, KINDS, SETTINGS_FILE, Kind, kind_of_id, records_root
from state import read_session, workspace_dir
from store import (
    CHANGES_FILE,
    dump_yaml,
    load_yaml_text,
    now_utc,
    remove_files,
    workspace_lock,
    write_failed,
    write_temp,
)

logger = logging.getLogger(__name__)

# 書き換えの印を作り直す間隔（秒。書き換えの知らせと同じ）
POLL_INTERVAL_SEC = 0.25

# 外部の変更を最後に記録してから、まとめるまで待つ秒数
EXTERNAL_COMMIT_DELAY_SEC = 60

# 外部の変更をまとめるまでの秒数を置き換える環境変数（結合テストで縮める）
EXTERNAL_COMMIT_DELAY_ENV = "MINDSTELLA_EXTERNAL_COMMIT_DELAY_SEC"

# 状態のフォルダの `workspaces/{ID}/` の下の、前回の中身のフォルダ名
SNAPSHOT_DIR = "snapshot"

# ペインへ貼り付ける、重なった ID の文の形（`{entries}` に `{ID}（{ファイル名}）` を `、` でつないで入れる）
DUPLICATE_MESSAGE = (
    "[mindstella] 同じ ID の項目が 2 件あります: {entries}。片方の ID を next_id で振り直してください"
)

# 重なった ID の文で、ID を並べる区切り
DUPLICATE_SEPARATOR = "、"

# ログの行の頭
LOG_PREFIX = "[change-detection]"

# 見る本文の拡張子
BODY_PATTERNS = ("*.md", "*.html")

# 見る種類の YAML（記録のフォルダからのパス）
WATCHED_FILES = tuple(spec.file for spec in KINDS.values())


class Writer(StrEnum):
    """見つけた書き換えの書いた元。"""

    # Git の操作: 前回の中身を置き換えるだけで記録しない
    GIT = "git"
    # MindStella のセッションの応答の途中の変更として記録する
    AI = "ai"
    # 外部の変更として記録し、自動でまとめる
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True, kw_only=True)
class Snapshot:
    """見るファイルの前回の中身と、そのときの Git の位置。"""

    # 記録のフォルダからのパス（`decisions.yaml`・`docs/D-1.md` など）→ 中身
    files: dict[str, str]
    # `git rev-parse HEAD`（Git の作業ツリーでなければ None）
    git_head: str | None
    # `git symbolic-ref -q HEAD`（無ければ None）
    git_ref: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemDiff:
    """前回と今の中身を比べた、項目ごとの追加・変更・削除。"""

    # 足した項目（種類の順・項目の並びの順）
    added: list[tuple[Kind, dict[str, Any]]]
    # 変えた項目（種類・前の項目・今の項目・前の本文・今の本文）
    changed: list[tuple[Kind, dict[str, Any], dict[str, Any], str | None, str | None]]
    # 消した項目（種類・前の項目）
    removed: list[tuple[Kind, dict[str, Any]]]

    def is_empty(self) -> bool:
        """追加・変更・削除がどれも無いか。"""
        return not self.added and not self.changed and not self.removed


# ワークスペースの絶対パス → 動いている変更の検知
_DETECTORS: dict[Path, ChangeDetector] = {}
_DETECTORS_GUARD = threading.Lock()


class ChangeDetector:
    """1 つのワークスペースの変更の検知。配信を立てるときに作って始め、止めるときに止める。"""

    def __init__(
        self,
        root: Path,
        state_dir: Path,
        write_lock: threading.Lock,
        targets: InputTargets,
    ) -> None:
        """ワークスペース・状態のフォルダ・ツールと共有する書き換えの鍵・入力の宛先を受け取る。"""
        self._root = root.resolve()
        self._state_dir = state_dir
        self._write_lock = write_lock
        self._targets = targets
        self._snapshot = Snapshot(files={}, git_head=None, git_ref=None)
        self._signature = ""
        self._duplicates: tuple[str, ...] = ()
        self._external_since: float | None = None
        self._unreadable: set[str] = set()
        self._stop = threading.Event()
        self._thread: Any = None
        self._delay = float(os.environ.get(EXTERNAL_COMMIT_DELAY_ENV, EXTERNAL_COMMIT_DELAY_SEC))

    def start(self) -> None:
        """前回の中身と今の中身を比べて止まっていた間の変更を記録し、一定の間隔で見るスレッドを始める。"""
        previous = load_snapshot(self._snapshot_dir())
        with workspace_lock(self._root, self._write_lock):
            # 前回の中身が無い: 今の中身で作り、比べない
            if previous is None:
                self._snapshot, _ = take_snapshot(self._root)
                self._signature = signature_of(self._root)
                save_snapshot(self._snapshot_dir(), self._snapshot)
                self._notice_duplicates(self._snapshot)
            else:
                # 止まっていた間の変更は、どのセッションの応答の途中か分からないため外部の変更にする
                self._snapshot = previous
                self._check(writer=Writer.EXTERNAL)
        with _DETECTORS_GUARD:
            _DETECTORS[self._root] = self
        self._thread = threading.Thread(target=self._run, name="change-detection", daemon=True)
        self._thread.start()

    def poll(self) -> None:
        """書き換えの印が変わったときだけ中身を読んで違いを記録し、外部の変更をまとめる時刻も見る。"""
        if signature_of(self._root) != self._signature:
            with workspace_lock(self._root, self._write_lock):
                self._check(writer=None)
        # 外部の変更を最後に記録してから時間が過ぎた: まとめる
        if self._external_since is not None and time.monotonic() - self._external_since >= self._delay:
            with workspace_lock(self._root, self._write_lock):
                self._commit_external()
            self._external_since = None

    def accept_own_write(self, written: dict[str, str | None]) -> None:
        """常駐サーバーが書いたファイルの分だけ、前回の中身を書いた中身で置き換える（None は消したファイル）。"""
        files = dict(self._snapshot.files)
        for name, text in written.items():
            if text is None:
                files.pop(name, None)
            else:
                files[name] = text
        self._snapshot = dataclasses.replace(self._snapshot, files=files)
        save_snapshot(self._snapshot_dir(), self._snapshot)

    def duplicate_ids(self) -> tuple[str, ...]:
        """最後に求めた重なった ID を返す。"""
        return self._duplicates

    def stop(self) -> None:
        """見るスレッドを止め、終わりを待つ。"""
        self._stop.set()
        with _DETECTORS_GUARD:
            if _DETECTORS.get(self._root) is self:
                del _DETECTORS[self._root]
        if self._thread is not None:
            self._thread.join(POLL_INTERVAL_SEC * 2)

    def _run(self) -> None:
        """止める合図が立つまで、一定の間隔で見る。"""
        while not self._stop.wait(POLL_INTERVAL_SEC):
            try:
                self.poll()
            except Exception:
                # 1 回の失敗で見るのをやめない（次の回で読み直す）
                logger.exception("%s %s poll_failed", LOG_PREFIX, self._workspace_id())

    def _check(self, *, writer: Writer | None) -> None:
        """今の中身を読み、書いた元を見分けて違いを記録する（鍵は呼ぶ側が取る）。writer を渡すと見分けない。"""
        self._signature = signature_of(self._root)
        current, unreadable = take_snapshot(self._root, previous=self._snapshot)
        self._log_unreadable(unreadable)
        diff = diff_snapshots(self._snapshot, current)
        found = writer or classify_writer(self._snapshot, current, self._root, self._state_dir)
        # 違いが無いか Git の操作: 前回の中身を置き換えるだけ
        if diff.is_empty() or found == Writer.GIT:
            self._replace_snapshot(current)
        else:
            try:
                record_diff(self._root, diff, "ai" if found == Writer.AI else "external")
            except WriteFailedError as error:
                # 次の回で記録し直すため、前回の中身も書き換えの印も置き換えない
                self._signature = ""
                logger.exception("%s %s write_failed: %s", LOG_PREFIX, self._workspace_id(), error)
                return
            self._replace_snapshot(current)
            if found == Writer.EXTERNAL:
                self._external_since = time.monotonic()
        self._notice_duplicates(current)

    def _commit_external(self) -> None:
        """まだまとめていない外部の変更を、外部の変更のまとまりにして書く（鍵は呼ぶ側が取る）。"""
        changes = load_changes(self._root)
        # 外部の変更が入っていない（commit や AI の変更で先にまとまった）
        if changes["pending"].get("by") != "external":
            return
        committed, _ = commit_pending(changes, EXTERNAL_SUMMARY, now_utc(), by="external")
        try:
            _replace_texts({records_root(self._root) / CHANGES_FILE: dump_yaml(committed)})
        except WriteFailedError as error:
            logger.exception("%s %s write_failed: %s", LOG_PREFIX, self._workspace_id(), error)

    def _replace_snapshot(self, snapshot: Snapshot) -> None:
        """前回の中身を置き換え、状態のフォルダにも書く。"""
        self._snapshot = snapshot
        save_snapshot(self._snapshot_dir(), snapshot)

    def _notice_duplicates(self, snapshot: Snapshot) -> None:
        """重なった ID の集まりが前に知らせたものと違えば置き換え、ペインへ貼り付ける。"""
        duplicates = find_duplicate_ids(snapshot)
        if duplicates == self._duplicates:
            return
        self._duplicates = duplicates
        paste_duplicates(self._root, duplicates, self._targets)

    def _log_unreadable(self, unreadable: list[str]) -> None:
        """読めないファイルを、読めるようになるまで 1 回だけログに残す。"""
        for name in unreadable:
            if name not in self._unreadable:
                logger.warning("%s %s unreadable: %s", LOG_PREFIX, self._workspace_id(), name)
        self._unreadable = set(unreadable)

    def _snapshot_dir(self) -> Path:
        """状態のフォルダの前回の中身のフォルダを返す。"""
        return workspace_dir(self._state_dir, self._workspace_id()) / SNAPSHOT_DIR

    def _workspace_id(self) -> str:
        """ワークスペースの ID を返す。"""
        return workspace_id_of(self._root)


def workspace_id_of(root: Path) -> str:
    """ワークスペースの ID を返す。"""
    # ワークスペースの管理がツールの処理を読み、ツールの処理がこのモジュールを読むため、関数の中で読む
    from workspaces import workspace_id_of as read_id

    return read_id(root)


def accept_written(root: Path, written: dict[str, str | None]) -> None:
    """そのワークスペースの変更の検知が動いていれば、常駐サーバーが書いたファイルを前回の中身に入れる。"""
    with _DETECTORS_GUARD:
        detector = _DETECTORS.get(root.resolve())
    if detector is not None:
        detector.accept_own_write(written)


def detector_of(root: Path) -> ChangeDetector | None:
    """そのワークスペースで動いている変更の検知を返す（無ければ None）。"""
    with _DETECTORS_GUARD:
        return _DETECTORS.get(root.resolve())


def signature_of(root: Path) -> str:
    """見るファイルの名前・更新日時（ナノ秒）・大きさをつないだ、書き換えの印を返す。"""
    records = records_root(root)
    parts: list[str] = []
    for name in _watched_names(records):
        try:
            stat = (records / name).stat()
        except OSError:
            # 無いファイルは名前だけを入れる
            parts.append(f"{name}:-")
            continue
        parts.append(f"{name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def take_snapshot(
    root: Path,
    *,
    previous: Snapshot | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[Snapshot, list[str]]:
    """見るファイルの今の中身と Git の位置を読み、読めなかったファイルは前回の中身で埋める。"""
    records = records_root(root)
    files: dict[str, str] = {}
    unreadable: list[str] = []
    for name in WATCHED_FILES:
        path = records / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        # YAML として読めて items が配列のときだけ今の中身にする
        if _items_of(text) is None:
            unreadable.append(name)
            if previous is not None and name in previous.files:
                files[name] = previous.files[name]
            continue
        files[name] = text
    body_dir = records / BODY_DIR
    if body_dir.is_dir():
        for pattern in BODY_PATTERNS:
            for path in sorted(body_dir.glob(pattern)):
                files[f"{BODY_DIR}/{path.name}"] = path.read_text(encoding="utf-8")
    return (
        Snapshot(
            files=files,
            git_head=_git_output(root, ["rev-parse", "HEAD"], run),
            git_ref=_git_output(root, ["symbolic-ref", "-q", "HEAD"], run),
        ),
        unreadable,
    )


def diff_snapshots(before: Snapshot, after: Snapshot) -> ItemDiff:
    """前回と今の中身の種類ごとの items を id で突き合わせ、追加・変更・削除を返す。"""
    added: list[tuple[Kind, dict[str, Any]]] = []
    changed: list[tuple[Kind, dict[str, Any], dict[str, Any], str | None, str | None]] = []
    removed: list[tuple[Kind, dict[str, Any]]] = []
    for kind, spec in KINDS.items():
        before_items = _first_by_id(before.files.get(spec.file))
        after_items = _first_by_id(after.files.get(spec.file))
        for item_id, item in after_items.items():
            previous = before_items.get(item_id)
            # 今にだけある ID
            if previous is None:
                added.append((kind, item))
                continue
            before_body = _body_text(before, previous)
            after_body = _body_text(after, item)
            # キーか本文の中身が違う
            if previous != item or before_body != after_body:
                changed.append((kind, previous, item, before_body, after_body))
        removed.extend(
            (kind, item) for item_id, item in before_items.items() if item_id not in after_items
        )
    return ItemDiff(added=added, changed=changed, removed=removed)


def classify_writer(
    before: Snapshot,
    after: Snapshot,
    root: Path,
    state_dir: Path,
    alive: Callable[[dict[str, Any]], bool] | None = None,
) -> Writer:
    """Git の位置の変化と MindStella のセッションの状態から、書き換えの書いた元を決める。"""
    git_dir = root / ".git"
    # HEAD かシンボリック参照が動いた、またはマージ・インデックスの書き換えの途中
    if (
        before.git_head != after.git_head
        or before.git_ref != after.git_ref
        or (git_dir / "MERGE_HEAD").exists()
        or (git_dir / "index.lock").exists()
    ):
        return Writer.GIT
    session = read_session(state_dir, workspace_id_of(root))
    check = alive or session_alive
    # MindStella のセッションが応答の途中で、ペインとプロセスがある
    if session is not None and session.responding and check(dataclasses.asdict(session)):
        return Writer.AI
    return Writer.EXTERNAL


def session_alive(
    session: dict[str, Any],
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> bool:
    """`session.json` のペインが tmux で引け、プロセスの起動時刻が記録と同じかを返す。"""
    pane = session.get("pane")
    socket = session.get("socket")
    pid = session.get("pid")
    # ペイン・ソケット・PID を持たない
    if not pane or not socket or not isinstance(pid, int):
        return False
    try:
        found = run(
            ["tmux", "-S", socket, "display-message", "-p", "-t", pane, "#{pane_id}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=PASTE_DEADLINE_SEC,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    # ペインが無い
    if found.returncode != 0:
        return False
    return process_started_at(pid) == session.get("pid_started_at")


def record_diff(
    root: Path,
    diff: ItemDiff,
    writer: Literal["ai", "external"],
    now: Callable[[], str] = now_utc,
) -> None:
    """項目の違いを、書いた元つきで `history.yaml` と `changes.yaml` に記録する（鍵は呼ぶ側が取る）。"""
    rows: dict[str, ItemHistory] = dict(load_item_history(root))
    at = now()
    # 書いた元が違う変更が入っていれば、先にまとめる
    changes = flush_pending(load_changes(root), writer, at)
    limit = history_limit(_read_settings(root))
    read_seq = changes.get("read_seq")
    for _kind, item in diff.added:
        changes, seq = advance_seq(changes)
        rows[item["id"]] = {
            "created": at,
            "updated": at,
            "updated_by": writer,
            "seq": seq,
            "added_seq": seq,
        }
        changes = note_pending(changes, item["id"], "added", by=writer)
    for _kind, before_item, after_item, before_body, after_body in diff.changed:
        entry = make_entry(
            before_item,
            after_item,
            before_body=before_body,
            after_body=after_body,
            seq=changes["last_seq"] + 1,
            at=at,
            by=writer,
        )
        # 変わったものが無い（積まない・pending にも足さない）
        if entry is None:
            continue
        changes, seq = advance_seq(changes)
        row: dict[str, Any] = {
            **rows.get(after_item["id"], {}),
            "updated": at,
            "updated_by": writer,
            "seq": seq,
        }
        rows[after_item["id"]] = stack_history(row, entry, limit, read_seq=read_seq)  # type: ignore[assignment]
        if limit > 0:
            changes = note_pending(changes, after_item["id"], "changed", by=writer)
    for kind, item in diff.removed:
        changes, seq = advance_seq(changes)
        removed: RemovedItem = {
            "id": item["id"],
            "kind": kind,
            "title": str(item.get("title", "")),
            "seq": seq,
            "added_seq": rows.get(item["id"], {}).get("added_seq", 0),
        }
        changes = _with_writer(note_removed(changes, removed), writer)
        rows.pop(item["id"], None)
    records = records_root(root)
    _replace_texts(
        {
            records / HISTORY_FILE: dump_yaml({"items": rows}),
            records / CHANGES_FILE: dump_yaml(changes),
        }
    )


def find_duplicate_ids(snapshot: Snapshot) -> tuple[str, ...]:
    """全ての種類の YAML で同じ id を持つ項目が 2 件以上ある ID を、ID の順に返す。"""
    counts: Counter[str] = Counter()
    for name in WATCHED_FILES:
        items = _items_of(snapshot.files.get(name))
        for item in items or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                counts[item["id"]] += 1
    return tuple(sorted((item_id for item_id, count in counts.items() if count > 1), key=_id_order))


def paste_duplicates(root: Path, duplicates: tuple[str, ...], targets: InputTargets) -> None:
    """そのワークスペースの MindStella のセッションのペインへ、重なった ID の文を貼り付ける。"""
    # 重なった ID が無い
    if not duplicates:
        return
    target = targets.target_of(root)
    # 宛先が無いか、貼れない状態のセッション
    if not isinstance(target, InputTarget):
        return
    entries = DUPLICATE_SEPARATOR.join(f"{item_id}（{_file_of(item_id)}）" for item_id in duplicates)
    reason = paste_to_pane(
        target,
        DUPLICATE_MESSAGE.format(entries=entries),
        deadline=time.monotonic() + PASTE_DEADLINE_SEC,
    )
    if reason is not None:
        logger.warning(
            "%s %s paste_failed: %s（%s）", LOG_PREFIX, workspace_id_of(root), target.pane, reason
        )


def load_snapshot(folder: Path) -> Snapshot | None:
    """状態のフォルダの前回の中身を読む（無ければ None。Git の位置は持たない）。"""
    if not folder.is_dir():
        return None
    files = {
        path.relative_to(folder).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }
    return Snapshot(files=files, git_head=None, git_ref=None)


def save_snapshot(folder: Path, snapshot: Snapshot) -> None:
    """前回の中身を、見るファイルと同じ名前で状態のフォルダに書き、無くなったファイルを消す。"""
    (folder / BODY_DIR).mkdir(parents=True, exist_ok=True)
    for path in folder.rglob("*"):
        if path.is_file() and path.relative_to(folder).as_posix() not in snapshot.files:
            path.unlink()
    for name, text in snapshot.files.items():
        target = folder / name
        # 同じ中身なら書かない
        if target.is_file() and target.read_text(encoding="utf-8") == text:
            continue
        target.write_text(text, encoding="utf-8")


def _watched_names(records: Path) -> list[str]:
    """見るファイルの名前（種類の YAML と、`docs/` の直下の本文）を返す。"""
    names = list(WATCHED_FILES)
    body_dir = records / BODY_DIR
    if body_dir.is_dir():
        names.extend(
            f"{BODY_DIR}/{path.name}"
            for pattern in BODY_PATTERNS
            for path in sorted(body_dir.glob(pattern))
        )
    return names


def _items_of(text: str | None) -> list[Any] | None:
    """種類の YAML の中身の items を返す。YAML として読めないか items が配列でなければ None。"""
    if text is None:
        return []
    try:
        value = load_yaml_text(text)
    except yaml.YAMLError:
        return None
    items = value.get("items") if isinstance(value, dict) else None
    return items if isinstance(items, list) else None


def _first_by_id(text: str | None) -> dict[str, dict[str, Any]]:
    """種類の YAML の項目を、同じ ID は最初の 1 件だけで ID → 項目にする。"""
    found: dict[str, dict[str, Any]] = {}
    for item in _items_of(text) or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            found.setdefault(item["id"], item)
    return found


def _body_text(snapshot: Snapshot, item: dict[str, Any]) -> str | None:
    """項目の body が指す本文の中身を返す（body を持たないか本文が無ければ None）。"""
    name = item.get("body")
    return snapshot.files.get(name) if isinstance(name, str) else None


def _git_output(
    root: Path, args: list[str], run: Callable[..., subprocess.CompletedProcess[str]]
) -> str | None:
    """ワークスペースで git を呼び、成功すれば標準出力の 1 行を返す（失敗・Git の作業ツリーでなければ None）。"""
    try:
        result = run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=PASTE_DEADLINE_SEC * 10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _read_settings(root: Path) -> dict[str, Any]:
    """`config.yaml` を読む（読めなければ空）。"""
    path = records_root(root) / SETTINGS_FILE
    try:
        value = load_yaml_text(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return value if isinstance(value, dict) else {}


def _with_writer(changes: Changes, writer: Literal["ai", "external"]) -> Changes:
    """まだまとめていない変更の書いた元を writer にした新しい記録を返す。"""
    pending = {**changes["pending"], "by": writer}
    return {**changes, "pending": pending}  # type: ignore[typeddict-item]


def _replace_texts(texts: dict[Path, str]) -> None:
    """ファイルごとに一時ファイルへ書いてから置き換える。書けなければ一時ファイルを消して WriteFailedError。"""
    temps: dict[Path, Path] = {}
    for path, text in texts.items():
        try:
            temps[path] = write_temp(path, text)
        except OSError as error:
            remove_files(list(temps.values()))
            raise write_failed(path, error) from error
    for path, temp in temps.items():
        try:
            os.replace(temp, path)
        except OSError as error:
            remove_files(list(temps.values()))
            raise write_failed(path, error) from error


def _file_of(item_id: str) -> str:
    """ID の種類の YAML のファイル名を返す。"""
    kind = kind_of_id(item_id)
    return KINDS[kind].file if kind is not None else ""


def _id_order(item_id: str) -> tuple[str, int]:
    """ID を頭の文字と連番の順に並べる鍵を返す。"""
    prefix, _, number = item_id.partition("-")
    with contextlib.suppress(ValueError):
        return prefix, int(number)
    return prefix, 0
