"""テストが起動した常駐サーバーを、pytest のプロセスが無くなったら止める見張り。

`python server_watchdog.py {pytest の PID} {常駐サーバーの PID}` で、起動側から切り離して動かす。
pytest が後片付けの前に終わっても、常駐サーバー（自分のプロセスグループを持つなら、そのグループ）へ
SIGTERM を送信し、待っても終わらなければ SIGKILL を送信する。常駐サーバーが先に終われば、何もせずに終わる。
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# プロセスが残っているかを確認する間隔（秒）
POLL_SEC = 1.0

# SIGTERM の後、終わるのを待つ上限（秒）。常駐サーバーの後片付け（一時ファイルの削除）が済む長さ
TERM_WAIT_SEC = 10.0

# /proc/{PID}/stat の、コマンド名の閉じ括弧より後ろでの、起動の時刻（starttime）の位置
STARTTIME_INDEX = 19


def _start_time(pid: int) -> str | None:
    """プロセスの起動の時刻を返却する。プロセスが無いかゾンビなら None。"""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except (FileNotFoundError, ProcessLookupError):
        return None
    # コマンド名に空白・括弧が入りうるため、最後の閉じ括弧より後ろを区切る
    fields = stat.rsplit(")", 1)[1].split()
    # 状態が Z（ゾンビ）なら、終わったものとして扱う
    if fields[0] == "Z":
        return None
    return fields[STARTTIME_INDEX]


def _alive(pid: int, started: str) -> bool:
    """起動したときと同じプロセス（PID の再使用でない）が残っているか。"""
    return _start_time(pid) == started


def _send(pid: int, sig: signal.Signals) -> None:
    """常駐サーバーがプロセスグループの先頭ならグループへ、そうでなければそのプロセスだけへ送信する。"""
    try:
        # 切り離して起動した常駐サーバー: 子のプロセスごと止める
        if os.getpgid(pid) == pid:
            os.killpg(pid, sig)
        # pytest と同じグループにいる常駐サーバー: グループの他のプロセスを巻き込まない
        else:
            os.kill(pid, sig)
    except ProcessLookupError:
        return


def watch(parent: int, target: int) -> None:
    """pytest が無くなるまで待ち、常駐サーバーが残っていれば止める。"""
    parent_started = _start_time(parent)
    target_started = _start_time(target)
    # 常駐サーバーが既に終わっている: 見張るものが無い
    if target_started is None:
        return
    # pytest が残っている間は待つ（既に終わっていれば、待たずに止める）
    while parent_started is not None and _alive(parent, parent_started) and _alive(target, target_started):
        time.sleep(POLL_SEC)
    # 常駐サーバーが先に終わった（テストの後片付けで止めた）: 何もしない
    if not _alive(target, target_started):
        return
    _send(target, signal.SIGTERM)
    deadline = time.monotonic() + TERM_WAIT_SEC
    while _alive(target, target_started) and time.monotonic() < deadline:
        time.sleep(POLL_SEC)
    if _alive(target, target_started):
        _send(target, signal.SIGKILL)


def spawn(target: int, *, parent: int | None = None, python: str = sys.executable) -> subprocess.Popen[bytes]:
    """pytest の PID（省くと今のプロセス）と常駐サーバーの PID を指定して、見張りを切り離して起動する。"""
    return subprocess.Popen(
        [python, str(Path(__file__).resolve()), str(parent or os.getpid()), str(target)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    watch(int(sys.argv[1]), int(sys.argv[2]))
