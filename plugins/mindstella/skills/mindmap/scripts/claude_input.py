"""ツールの呼び出しが運んだセッションの値をワークスペースごとの宛先として持ち、まとめて送った後にそのペインへ 1 行の文字列を貼る。

貼る前に宛先の Claude Code が生きているかを確かめ、貼った後に Claude Code の会話の記録に入ったかを確かめる。
tmux と ps を子プロセスで呼び、会話の記録（jsonl）を読む。
"""

from __future__ import annotations

import json
import logging
import math
import re
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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

# Claude Code のプロセスからペインのプロセスまで `ps -o ppid=` でたどる段の上限
PARENT_DEPTH_MAX = 32

# これ以下の PID に着いたら、親をたどるのをやめる（init）
INIT_PID = 1

# `session.claude_config_dir` が無いか空のときの Claude Code の設定のフォルダ
DEFAULT_CONFIG_DIR = Path.home() / ".claude"

# Claude Code が会話の記録のフォルダ名をそのまま使う上限の文字数（超えると先頭この文字数に `-{パスのハッシュ}` を足す）
TRANSCRIPT_NAME_MAX = 200

# UTF-16 で 1 単位に収まる最大のコードポイント（これを超える文字は 2 単位になる）
UTF16_SINGLE_UNIT_MAX = 0xFFFF


@dataclass(frozen=True, slots=True, kw_only=True)
class Session:
    """ツールの引数 `session` を読んだ、ツールを呼んだセッションの値。"""

    # セッションの作業フォルダ（絶対パス）
    cwd: Path
    # セッションの `CLAUDE_CONFIG_DIR`
    claude_config_dir: Path
    # セッションの `TMUX`（tmux の外なら None）
    tmux: str | None = None
    # セッションの `TMUX_PANE`（tmux の外なら None）
    tmux_pane: str | None = None
    # Claude Code のプロセスの PID
    claude_pid: int | None = None
    # そのプロセスの起動時刻（空白を 1 つにつめた `ps -o lstart=` の文字列）
    claude_started_at: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class InputTarget:
    """ペインへ入力するのに要る値がそろったセッションの宛先と会話の記録の場所。"""

    # tmux のサーバーのソケット（`session.tmux` の最初の `,` より前）
    socket: str
    # Claude Code が動くペイン
    pane: str
    # 会話の記録を引く設定のフォルダ
    config_dir: Path
    # セッションの作業フォルダ（会話の記録のフォルダ名と、行の `cwd` に使う）
    cwd: Path
    # Claude Code のプロセスの PID（終わったか・使い回されたかの確かめに使う）
    claude_pid: int
    # そのプロセスの起動時刻
    claude_started_at: str


class InputTargets:
    """ワークスペースの絶対パスごとに、最後にツールを呼んだセッションの宛先を 1 つ持つ台帳。"""

    def __init__(self) -> None:
        """空の台帳と、台帳の鍵・入力の鍵を作る。"""
        # ワークスペース → 宛先（最後のセッションが tmux の外なら None）
        self._targets: dict[Path, InputTarget | None] = {}
        self._guard = threading.Lock()
        # プロセスの中の 1 本の入力の鍵（同時に送られた 2 回の入力と確かめを重ねない）
        self._input_lock = threading.Lock()

    def remember(self, root: Path, session: Session) -> None:
        """そのワークスペースの宛先を、渡したセッションの宛先にする（tmux の外なら宛先を外す）。"""
        target = input_target(session)
        with self._guard:
            self._targets[root.resolve()] = target

    def target_of(self, root: Path) -> InputTarget | None:
        """そのワークスペースの宛先を返す。"""
        with self._guard:
            return self._targets.get(root.resolve())

    def enter(self, root: Path, count: int) -> bool:
        """そのワークスペースの宛先へ、届いた件数の 1 行を入力し、会話の記録に入ったかを返す。"""
        return enter_to_claude(self.target_of(root), count, lock=self._input_lock)


def parse_session(raw: Mapping[str, Any] | None) -> Session | None:
    """ツールの引数 `session` を `Session` にする。作業フォルダが読めなければ None。"""
    if raw is None:
        return None
    cwd = raw.get("cwd")
    # 作業フォルダが空でない絶対パスの文字列でない: 相対パスを解けない
    if not isinstance(cwd, str) or not cwd or not Path(cwd).is_absolute():
        return None
    config_dir = _text_or_none(raw.get("claude_config_dir"))
    started_at = _text_or_none(raw.get("claude_started_at"))
    pid = raw.get("claude_pid")
    return Session(
        cwd=Path(cwd),
        claude_config_dir=Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR,
        tmux=_text_or_none(raw.get("tmux")),
        tmux_pane=_text_or_none(raw.get("tmux_pane")),
        # bool は int の仲間なので除く
        claude_pid=pid if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0 else None,
        claude_started_at=" ".join(started_at.split()) if started_at else None,
    )


def _text_or_none(value: Any) -> str | None:
    """空でない文字列ならそのまま、それ以外は None を返す。"""
    return value if isinstance(value, str) and value else None


def input_target(session: Session) -> InputTarget | None:
    """セッションから送り先を作る。ペインへ入力するのに要る値が欠けていれば None。"""
    if (
        session.tmux is None
        or session.tmux_pane is None
        or session.claude_pid is None
        or session.claude_started_at is None
    ):
        return None
    return InputTarget(
        socket=session.tmux.split(",", 1)[0],
        pane=session.tmux_pane,
        config_dir=session.claude_config_dir,
        cwd=session.cwd,
        claude_pid=session.claude_pid,
        claude_started_at=session.claude_started_at,
    )


def is_session_alive(
    target: InputTarget,
    *,
    deadline: float,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    clock: Callable[[], float] = time.monotonic,
) -> str | None:
    """宛先の Claude Code が起動時刻ごと残り、宛先のペインのプロセスかその子孫かを確かめ、違えば理由を返す。"""

    def call(command: list[str]) -> subprocess.CompletedProcess[str] | str:
        """残り時間を上限にコマンドを呼ぶ。時間切れか起動できなければ理由を返す。"""
        remaining = deadline - clock()
        if remaining <= 0:
            return "時間切れ"
        try:
            return run(command, capture_output=True, text=True, timeout=remaining, check=False)
        except subprocess.TimeoutExpired:
            return "時間切れ"
        except OSError as error:
            return f"{' '.join(command[:2])}: {error}"

    pid = target.claude_pid
    started = call(["ps", "-o", "lstart=", "-p", str(pid)])
    if isinstance(started, str):
        return started
    # プロセスが無い: Claude Code が終わった
    if started.returncode != 0:
        return f"Claude Code のプロセス {pid} が無い"
    # 起動時刻が違う: 同じ PID を別のプロセスが使っている
    if " ".join(started.stdout.split()) != target.claude_started_at:
        return f"PID {pid} が別のプロセスに使い回された"

    pane = target.pane
    shown = call(["tmux", "-S", target.socket, "display-message", "-p", "-t", pane, "#{pane_pid}"])
    if isinstance(shown, str):
        return shown
    pane_pid = shown.stdout.strip()
    if shown.returncode != 0 or not pane_pid.isdigit():
        return f"ペイン {pane} が無い"

    # Claude Code のプロセスから親へたどり、ペインのプロセスに着けばペインの中で動いている
    current = pid
    for _ in range(PARENT_DEPTH_MAX):
        if current == int(pane_pid):
            return None
        parent = call(["ps", "-o", "ppid=", "-p", str(current)])
        if isinstance(parent, str):
            return parent
        text = parent.stdout.strip()
        # 親を引けないか init に着いた: ペインの外で動いている
        if parent.returncode != 0 or not text.isdigit() or int(text) <= INIT_PID:
            break
        current = int(text)
    return f"Claude Code がペイン {pane} の中に無い"


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
    # どのコマンドもソケットを `-S` で指し、環境変数 `TMUX` に頼らない
    tmux = ["tmux", "-S", target.socket]
    pane = target.pane
    commands: list[tuple[list[str], bytes | None]] = [
        ([*tmux, "load-buffer", "-b", PASTE_BUFFER, "-"], text.encode("utf-8")),
        ([*tmux, "paste-buffer", "-p", "-d", "-b", PASTE_BUFFER, "-t", pane], None),
        ([*tmux, "send-keys", "-t", pane, "Enter"], None),
    ]
    for command, stdin in commands:
        name = f"tmux {command[3]}"
        remaining = deadline - clock()
        # 打ち切りの時刻を過ぎた: 残りを呼ばない
        if remaining <= 0:
            return "時間切れ"
        try:
            completed = run(
                command, input=stdin, timeout=remaining, check=False, capture_output=True
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
    target: InputTarget | None,
    count: int,
    *,
    lock: threading.Lock,
    run: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """宛先が生きていれば届いた件数の 1 行をペインへ貼り、上限までに会話の記録に入ったかを返す。入力できなかった理由は記録する。"""
    # 宛先が無い（セッションを受けていないか tmux の外）: ps・tmux を呼ばない
    if target is None:
        logger.info("宛先のセッションが無いか tmux の外のため、Claude Code へ入力しません")
        return False
    # 同時に送られた入力と確かめを重ねない
    with lock:
        text = input_text(count)
        sizes = snapshot_sizes(transcript_dirs(target))
        deadline = clock() + INPUT_DEADLINE_SEC
        ended = is_session_alive(target, deadline=deadline, run=run, clock=clock)
        # 宛先のセッションが終わった: 別のプロセスへ貼らない
        if ended is not None:
            logger.warning("宛先のセッションが終わったため、Claude Code へ入力しません（%s）", ended)
            return False
        reason = paste_to_pane(target, text, deadline=deadline, run=run, clock=clock)
        # 貼れなかった: 会話の記録は読み直さない
        if reason is not None:
            logger.warning("Claude Code へ入力できません（%s）", reason)
            return False
        # 上限まで、書き足された行を読み直す（新しい会話のフォルダが貼った後に作られても拾うため、毎回引き直す）
        # 待った秒の合計も上限を越えないよう、待った秒を誤差なく足し合わせて残りを出す
        waited: list[float] = []
        while True:
            if find_delivery(transcript_dirs(target), sizes, cwd=target.cwd, text=text):
                return True
            remaining = min(deadline - clock(), INPUT_DEADLINE_SEC - math.fsum(waited))
            if remaining <= 0:
                break
            wait = min(DELIVERY_POLL_SEC, remaining)
            sleep(wait)
            waited.append(wait)
        logger.warning("Claude Code の会話の記録に入力が入りません（%s 秒）", INPUT_DEADLINE_SEC)
        return False
