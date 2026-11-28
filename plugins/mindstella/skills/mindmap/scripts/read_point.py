"""AI が前回参照した時点・変更履歴の今回の差分の始まりと、まだ知らせていない移し替えの報告を、常駐サーバーの状態のフォルダに読み書きする。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import state
from errors import ArgumentError, SchemaMismatchError
from store import remove_files, write_failed, write_temp

# `workspaces/{ID}/` の下の前回参照した時点（`{"read_seq": 整数}`）
READ_POINT_FILE = "read_point.json"

# `workspaces/{ID}/` の下の今回の差分の始まり（`{"turn_seq": 整数, "at": UTC の日時}`）
TURN_POINT_FILE = "turn_point.json"

# `workspaces/{ID}/` の下の、まだ知らせていない移し替えの報告（`{not_carried, provisional}`）
MIGRATION_REPORT_FILE = "migration.json"


def load_read_seq(root: Path, *, state_root: Path | None = None) -> int | None:
    """ワークスペースの `read_point.json` の `read_seq` を返す。ファイルが無ければ `None`。"""
    path = _workspace_state_dir(root, state_root) / READ_POINT_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(text)
    except ValueError as error:
        raise SchemaMismatchError(
            [f"{READ_POINT_FILE}: read_seq: JSON として読めません"]
        ) from error
    read_seq = data.get("read_seq") if isinstance(data, dict) else None
    # 0 以上の整数でない（真偽値も整数として扱わない）
    if isinstance(read_seq, bool) or not isinstance(read_seq, int) or read_seq < 0:
        raise SchemaMismatchError([f"{READ_POINT_FILE}: read_seq: 0 以上の整数ではありません"])
    return read_seq


def save_read_seq(root: Path, read_seq: int, *, state_root: Path | None = None) -> None:
    """`read_point.json` を一時ファイルから置き換えて書く（フォルダが無ければ作る）。"""
    _replace_json(_workspace_state_dir(root, state_root) / READ_POINT_FILE, {"read_seq": read_seq})


def load_turn_point(root: Path, *, state_root: Path | None = None) -> tuple[int, str | None]:
    """ワークスペースの `turn_point.json` の `turn_seq` と `at` を返す。ファイルが無ければ `(0, None)`。"""
    path = _workspace_state_dir(root, state_root) / TURN_POINT_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # まだ利用者の書き込みを受け付けていない: 最初のまとまりから全て
        return 0, None
    try:
        data = json.loads(text)
    except ValueError as error:
        raise SchemaMismatchError(
            [f"{TURN_POINT_FILE}: turn_seq: JSON として読めません"]
        ) from error
    turn_seq = data.get("turn_seq") if isinstance(data, dict) else None
    at = data.get("at") if isinstance(data, dict) else None
    # 0 以上の整数でない（真偽値も整数として扱わない）
    if isinstance(turn_seq, bool) or not isinstance(turn_seq, int) or turn_seq < 0:
        raise SchemaMismatchError([f"{TURN_POINT_FILE}: turn_seq: 0 以上の整数ではありません"])
    # 日時が文字列でない
    if not isinstance(at, str):
        raise SchemaMismatchError([f"{TURN_POINT_FILE}: at: 文字列ではありません"])
    return turn_seq, at


def save_turn_point(
    root: Path, turn_seq: int, at: str, *, state_root: Path | None = None
) -> None:
    """`turn_point.json` を一時ファイルから置き換えて書く（フォルダが無ければ作る）。"""
    if turn_seq < 0:
        raise ArgumentError("turn_seq", "0 以上の整数で渡してください")
    _replace_json(
        _workspace_state_dir(root, state_root) / TURN_POINT_FILE, {"turn_seq": turn_seq, "at": at}
    )


def advance_read_seq(root: Path, until_seq: int, *, state_root: Path | None = None) -> int:
    """今の時点より大きいときだけ `until_seq` を書き、移し替えの報告を消して、書き換えた後の時点を返す。"""
    # 履歴が前回参照した時点を読むため、関数の中で読む
    from history import load_changes

    last_seq = load_changes(root)["last_seq"]
    # 通し番号の外
    if until_seq < 0 or until_seq > last_seq:
        raise ArgumentError("until_seq", f"0〜{last_seq} の整数で渡してください")
    current = load_read_seq(root, state_root=state_root)
    # 無いか、今の時点より進む: 書く
    if current is None or current < until_seq:
        save_read_seq(root, until_seq, state_root=state_root)
        current = until_seq
    clear_migration_report(root, state_root=state_root)
    return current


def load_migration_report(root: Path, *, state_root: Path | None = None) -> dict[str, Any] | None:
    """`migration.json` を返す。無ければ `None`。"""
    path = _workspace_state_dir(root, state_root) / MIGRATION_REPORT_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def save_migration_report(
    root: Path, report: dict[str, Any], *, state_root: Path | None = None
) -> None:
    """移し替えの報告を `migration.json` に書く。既にあれば `not_carried`・`provisional` を末尾に足す。"""
    current = load_migration_report(root, state_root=state_root) or {
        "not_carried": [],
        "provisional": [],
    }
    merged = {
        key: [*current.get(key, []), *report.get(key, [])] for key in ("not_carried", "provisional")
    }
    _replace_json(_workspace_state_dir(root, state_root) / MIGRATION_REPORT_FILE, merged)


def clear_migration_report(root: Path, *, state_root: Path | None = None) -> None:
    """`migration.json` を消す（無ければ何もしない）。"""
    (_workspace_state_dir(root, state_root) / MIGRATION_REPORT_FILE).unlink(missing_ok=True)


def _workspace_state_dir(root: Path, state_root: Path | None) -> Path:
    """ワークスペースの状態を置くフォルダ（`workspaces/{ID}/`）を返す。"""
    # ワークスペースの管理がこのモジュールを読むため、関数の中で読む
    from workspaces import workspace_id_of

    base = state_root if state_root is not None else state.state_root(os.environ)
    return state.workspace_dir(base, workspace_id_of(root))


def _replace_json(path: Path, value: dict[str, Any]) -> None:
    """同じフォルダの一時ファイルに書いてから置き換える。書けなければ一時ファイルを消して送る。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = write_temp(path, json.dumps(value, ensure_ascii=False) + "\n")
    except OSError as error:
        raise write_failed(path, error) from error
    try:
        os.replace(temp, path)
    except OSError as error:
        remove_files([temp])
        raise write_failed(path, error) from error
