"""常駐サーバーの起動の確認（SessionStart のフックと起動スクリプトが呼ぶ ensure_server.py）の結合テスト。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from launch_fixtures import PLUGIN_DIR, ServeFakeStatus
from workspace_fixtures import PORT_ENV, is_listening, plugin_version, read_server_status

from .fixture_types import MakeVenv

# 常駐サーバーの起動の確認のスクリプト
ENSURE_SCRIPT = PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "ensure_server.py"

# 起動の確認 1 回を待つ上限秒数（常駐サーバーが待ち受けるまでの上限 10 秒を含む）
COMMAND_TIMEOUT_SEC = 60

# 古いバージョンの常駐サーバーの代わりが返す状態
OUTDATED_STATUS = {"name": "mindstella", "version": "0.0.1"}

# 起動の確認が呼び出しの間に、mindstella の常駐サーバーかを確かめる状態の名前
SERVER_NAME = "mindstella"


@pytest.fixture
def run_ensure(tmp_path: Path, resident_port: int) -> object:
    """システムの python3 で起動の確認を呼ぶ関数を返す。ホームはテストの一時フォルダにする。"""
    system_python = shutil.which("python3", path="/usr/bin:/bin")
    assert system_python is not None
    home = tmp_path / "home"
    home.mkdir()

    def _run(
        venv: Path, *, hook: bool = True, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        """フックの入力（hook のときだけ）を標準入力に渡して起動の確認を呼び、終わるまで待つ。"""
        env = {
            **os.environ,
            "HOME": str(home),
            "PYTHONUTF8": "1",
            PORT_ENV: str(resident_port),
            "MINDSTELLA_VENV": str(venv),
        }
        return subprocess.run(
            [system_python, str(ENSURE_SCRIPT), *(["--hook"] if hook else [])],
            input=stdin,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=COMMAND_TIMEOUT_SEC,
            check=False,
        )

    return _run


def _hook_input(cwd: Path) -> str:
    """SessionStart のフックの入力の JSON を返す。"""
    return json.dumps({"hook_event_name": "SessionStart", "cwd": str(cwd), "source": "startup"})


def _server_pids(port: int) -> list[int]:
    """そのポートで待ち受けている mindstella の常駐サーバーの PID を返す（無ければ空）。"""
    status = read_server_status(port)
    return [] if status is None else [int(status["pid"])]


def test_normal(
    tmp_path: Path, ready_venv: Path, resident_port: int, run_ensure: object
) -> None:
    """常駐サーバーが落ちていれば起動し、待ち受けを確かめて、つなぎ直す案内を出す（正常系）。"""
    # 実行
    completed = run_ensure(ready_venv, stdin=_hook_input(tmp_path))
    # 検証
    assert completed.returncode == 0, completed.stdout + completed.stderr
    status = read_server_status(resident_port)
    assert status is not None
    assert status["name"] == SERVER_NAME
    assert f"[mindstella] 常駐サーバーを起動しました（ポート {resident_port}）" in completed.stdout
    assert "/mcp で mindstella につなぎ直してください" in completed.stdout
    assert os.path.exists(f"/proc/{status['pid']}")


def test_normal_when_running(
    tmp_path: Path, ready_venv: Path, resident_port: int, run_ensure: object
) -> None:
    """同じバージョンの常駐サーバーが待ち受けていれば、起動せずに何も出さない（正常系）。"""
    # 準備
    first = run_ensure(ready_venv, stdin=_hook_input(tmp_path))
    assert first.returncode == 0, first.stdout + first.stderr
    before = _server_pids(resident_port)
    # 実行
    completed = run_ensure(ready_venv, stdin=_hook_input(tmp_path))
    # 検証
    assert (completed.returncode, completed.stdout) == (0, "")
    assert _server_pids(resident_port) == before


def test_normal_when_outdated(
    tmp_path: Path,
    ready_venv: Path,
    resident_port: int,
    run_ensure: object,
    serve_fake_status: ServeFakeStatus,
) -> None:
    """待ち受けている常駐サーバーのバージョンがプラグインと違えば、起動し直さずに差と手順を示す（正常系）。"""
    # 準備
    serve_fake_status(resident_port, 200, OUTDATED_STATUS)
    # 実行
    completed = run_ensure(ready_venv, stdin=_hook_input(tmp_path))
    # 検証
    assert completed.returncode == 0
    assert (
        f"常駐サーバーのバージョン 0.0.1 と、インストールしたプラグインのバージョン {plugin_version()} が違います"
        in completed.stdout
    )
    assert "server_stop で常駐サーバーを止めてから、Claude Code を立ち上げ直してください" in completed.stdout
    assert read_server_status(resident_port) == OUTDATED_STATUS


def test_normal_when_called_by_launcher(
    ready_venv: Path, resident_port: int, run_ensure: object
) -> None:
    """`--hook` を付けずに呼ぶと、標準入力を読まず、起動したことを標準エラーに出す（正常系）。"""
    # 実行
    completed = run_ensure(ready_venv, hook=False)
    # 検証
    assert (completed.returncode, completed.stdout) == (0, ""), completed.stderr
    assert f"[mindstella] 常駐サーバーを起動しました（ポート {resident_port}）" in completed.stderr


def test_error_when_port_in_use(
    tmp_path: Path,
    ready_venv: Path,
    resident_port: int,
    run_ensure: object,
    serve_fake_status: ServeFakeStatus,
) -> None:
    """ポートを mindstella でないプロセスが使っていて常駐サーバーが待ち受けられないと、使われているポートを示し、会話の始まりは止めない（異常系）。"""
    # 準備
    serve_fake_status(resident_port, 404, None)
    guide = f"[mindstella] エラー: ポート {resident_port} は別のプロセスが使っています"
    # 実行
    hooked = run_ensure(ready_venv, stdin=_hook_input(tmp_path))
    launched = run_ensure(ready_venv, hook=False)
    # 検証
    assert hooked.returncode == 0
    assert guide in hooked.stdout
    assert "環境変数 MINDSTELLA_PORT で別のポートを渡してください" in hooked.stdout
    assert is_listening(resident_port) is True
    assert launched.returncode == 1
    assert guide in launched.stderr
    assert "環境変数 MINDSTELLA_PORT で別のポートを渡してください" in launched.stderr


def test_error_when_dependency_missing(
    tmp_path: Path, make_venv: MakeVenv, resident_port: int, run_ensure: object
) -> None:
    """仮想環境に依存がそろっていなければ、起動せずにそろえるコマンドを示す（異常系）。"""
    # 準備
    bare_venv = make_venv("bare-venv", with_libraries=False)
    # 実行
    completed = run_ensure(bare_venv, stdin=_hook_input(tmp_path))
    # 検証
    assert completed.returncode == 0
    assert [package in completed.stdout for package in ("PyYAML", "jsonschema", "mcp")] == [
        True,
        True,
        True,
    ]
    assert "-m pip install" in completed.stdout
    assert is_listening(resident_port) is False
