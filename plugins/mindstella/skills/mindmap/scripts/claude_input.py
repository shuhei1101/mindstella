"""まとめて送った後に、受け継いだ `TMUX_PANE` のペインへ 1 行の文字列を貼り、Claude Code の会話の記録に入ったかを確かめる。

tmux を子プロセスで呼び、会話の記録（jsonl）を読む。
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# `{count}` に件数を入れて貼る 1 行。`[mindstella]` は `session` が利用者の発言と見分ける印
INPUT_TEMPLATE = "[mindstella] ユーザーからのコメントが {count} 件届きました。読み直してください。"

# 貼り始めてから tmux の 3 つのコマンドと届いたかの確かめを打ち切るまでの秒数
INPUT_DEADLINE_SEC = 0.5

# `Enter` の後、書き足された行を読み直す間隔（秒）
DELIVERY_POLL_SEC = 0.05

# `load-buffer` と `paste-buffer` で使う名前の付いたバッファ（利用者のバッファを書き換えない）
PASTE_BUFFER = "mindstella-input"

# `CLAUDE_CONFIG_DIR` が空のときの Claude Code の設定のフォルダ
DEFAULT_CONFIG_DIR = Path.home() / ".claude"

# Claude Code が会話の記録のフォルダ名をそのまま使う上限の文字数（超えると先頭この文字数に `-{パスのハッシュ}` を足す）
TRANSCRIPT_NAME_MAX = 200

# UTF-16 で 1 単位に収まる最大のコードポイント（これを超える文字は 2 単位になる）
UTF16_SINGLE_UNIT_MAX = 0xFFFF


@dataclass(frozen=True, slots=True, kw_only=True)
class InputTarget:
    """起動時に Claude Code から受け継いだ送り先と会話の記録の場所と、同時の入力を重ねない 1 本の鍵。"""

    # `TMUX`（tmux のサーバーのソケット）。空なら None
    socket: str | None
    # `TMUX_PANE`（Claude Code が動くペイン）。空なら None
    pane: str | None
    # `CLAUDE_CONFIG_DIR`（空なら `~/.claude`）
    config_dir: Path
    # サーバーの起動時の作業フォルダ（絶対パス）
    cwd: Path
    # 入力の鍵（同時に送られた 2 回の入力と確かめを重ねない）
    lock: threading.Lock = field(default_factory=threading.Lock)


def load_input_target(environ: Mapping[str, str], cwd: Path) -> InputTarget:
    """環境変数と起動時の作業フォルダから `InputTarget` を作る。"""
    config_dir = environ.get("CLAUDE_CONFIG_DIR", "")
    return InputTarget(
        # 空文字列か無ければ tmux の外として None にする
        socket=environ.get("TMUX") or None,
        pane=environ.get("TMUX_PANE") or None,
        config_dir=Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR,
        cwd=cwd.resolve(),
    )


def transcript_dirs(target: InputTarget) -> list[Path]:
    """作業フォルダに当たる会話の記録のフォルダを、Claude Code と同じ名前の作り方で引く。"""
    # Claude Code は UTF-16 の単位ごとに英数字以外を `-` にする。2 単位になる文字は `--` にそろえてから置き換える
    two_units = "".join(
        "--" if ord(char) > UTF16_SINGLE_UNIT_MAX else char for char in str(target.cwd)
    )
    name = re.sub(r"[^A-Za-z0-9]", "-", two_units)
    projects = target.config_dir / "projects"
    # 名前が上限以内: その名前のフォルダだけ（無くてもよい）
    if len(name) <= TRANSCRIPT_NAME_MAX:
        return [projects / name]
    # 上限を超える: Claude Code が末尾に足すパスのハッシュは作らず、先頭が同じフォルダを全て引く
    if not projects.is_dir():
        return []
    prefix = f"{name[:TRANSCRIPT_NAME_MAX]}-"
    return [path for path in projects.iterdir() if path.name.startswith(prefix)]


def input_text(count: int) -> str:
    """件数を入れた `INPUT_TEMPLATE`（改行を含まない 1 行）を返す。"""
    return INPUT_TEMPLATE.format(count=count)


def snapshot_sizes(folders: list[Path]) -> dict[Path, int]:
    """フォルダごとに直下の各 jsonl の大きさを控える（無いフォルダは飛ばす）。"""
    sizes: dict[Path, int] = {}
    for folder in folders:
        # フォルダが無い: 新しい会話が最初の行を書くまで jsonl を作らない
        if not folder.is_dir():
            continue
        for path in folder.glob("*.jsonl"):
            sizes[path] = path.stat().st_size
    return sizes


def find_delivery(folders: list[Path], sizes: dict[Path, int], *, cwd: Path, text: str) -> bool:
    """控えより後ろへ書き足された行に、入力が会話か待ち行列に入った印があるかを返す。"""
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in folder.glob("*.jsonl"):
            # 控えの後ろから読む（控えに無いファイルは大きさ 0 から）。書きかけの行（最後の改行より後ろ）は読まない
            with path.open("rb") as stream:
                stream.seek(sizes.get(path, 0))
                appended = stream.read()
            complete = appended[: appended.rfind(b"\n") + 1]
            for line in complete.splitlines():
                try:
                    record = json.loads(line)
                except ValueError:
                    # 読めない行は飛ばす
                    continue
                if _is_delivery(record, cwd=cwd, text=text):
                    return True
    return False


def _is_delivery(record: Any, *, cwd: Path, text: str) -> bool:
    """会話の記録の 1 行が、入力が入った user の行か、待ち行列へ入った行かを返す。"""
    if not isinstance(record, dict):
        return False
    # 処理中で入力が待ち行列に入った（この行は本文も `cwd` も持たない）
    if record.get("type") == "queue-operation":
        return record.get("operation") == "enqueue"
    # 入力を待っていた Claude Code の会話に、入力した文字列が入った
    return (
        record.get("type") == "user"
        and record.get("cwd") == str(cwd)
        and text in _message_text(record)
    )


def _message_text(record: dict[str, Any]) -> str:
    """user の行の本文（`message.content` の文字列か、`text` の要素の文字列）を 1 つの文字列にして返す。"""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    # 本文が文字列
    if isinstance(content, str):
        return content
    # 本文が要素の並び: `text` の要素の文字列をつなぐ
    if isinstance(content, list):
        return "".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
    return ""


def paste_to_pane(
    target: InputTarget,
    text: str,
    *,
    deadline: float,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    clock: Callable[[], float] = time.monotonic,
) -> str | None:
    """文字列をブラケットペーストでペインへ貼り、`Enter` で確定する。失敗の理由を返す（成功なら None）。"""
    # tmux のサーバーのソケットは環境変数 `TMUX` で渡す
    env = {**os.environ, "TMUX": str(target.socket)}
    pane = str(target.pane)
    commands: list[tuple[list[str], bytes | None]] = [
        (["tmux", "load-buffer", "-b", PASTE_BUFFER, "-"], text.encode("utf-8")),
        (["tmux", "paste-buffer", "-p", "-d", "-b", PASTE_BUFFER, "-t", pane], None),
        (["tmux", "send-keys", "-t", pane, "Enter"], None),
    ]
    for command, stdin in commands:
        name = " ".join(command[:2])
        remaining = deadline - clock()
        # 打ち切りの時刻を過ぎた: 残りを呼ばない
        if remaining <= 0:
            return "時間切れ"
        try:
            completed = run(
                command, input=stdin, env=env, timeout=remaining, check=False, capture_output=True
            )
        except subprocess.TimeoutExpired:
            return f"{name}: 時間内に終わらない"
        except OSError as error:
            return f"{name}: {error}"
        # 終了コードが 0 以外: 残りを呼ばない
        if completed.returncode != 0:
            return f"{name}: 終了コード {completed.returncode}"
    return None


def enter_to_claude(
    target: InputTarget,
    count: int,
    *,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """届いた件数の 1 行をペインへ貼り、上限までに会話の記録に入ったかを返す。入力できなかった理由は記録する。"""
    # tmux の外で立てた: tmux を呼ばない
    if target.socket is None or target.pane is None:
        logger.info("tmux の外で立てたため、Claude Code へ入力しません")
        return False
    # 同時に送られた入力と確かめを重ねない
    with target.lock:
        text = input_text(count)
        sizes = snapshot_sizes(transcript_dirs(target))
        deadline = clock() + INPUT_DEADLINE_SEC
        reason = paste_to_pane(target, text, deadline=deadline, run=run, clock=clock)
        # 貼れなかった: 会話の記録は読み直さない
        if reason is not None:
            logger.warning("Claude Code へ入力できません（%s）", reason)
            return False
        # 上限まで、書き足された行を読み直す（新しい会話のフォルダが貼った後に作られても拾うため、毎回引き直す）
        while True:
            if find_delivery(transcript_dirs(target), sizes, cwd=target.cwd, text=text):
                return True
            remaining = deadline - clock()
            if remaining <= 0:
                break
            sleep(min(DELIVERY_POLL_SEC, remaining))
        logger.warning("Claude Code の会話の記録に入力が入りません（%s 秒）", INPUT_DEADLINE_SEC)
        return False
