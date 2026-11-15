"""常駐サーバーの起動の確認（SessionStart のフックと起動スクリプトが呼ぶ ensure_server.py）の結合テスト。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from launch_fixtures import PLUGIN_DIR, ServeFakeStatus, copy_plugin
from session_fixtures import FakeSystemctl
from workspace_fixtures import PORT_ENV, free_port, is_listening, plugin_version, read_server_status

from .fixture_types import MakeVenv

# 常駐サーバーの起動の確認のスクリプト
ENSURE_SCRIPT = PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "ensure_server.py"

# 起動の確認 1 回を待つ上限秒数（常駐サーバーが待ち受けるまでの上限 10 秒を含む）
COMMAND_TIMEOUT_SEC = 60

# 古いバージョンの常駐サーバーの代わりが返す状態
OUTDATED_STATUS = {"name": "mindstella", "version": "0.0.1"}

# 起動の確認が呼び出しの間に、mindstella の常駐サーバーかを確かめる状態の名前
SERVER_NAME = "mindstella"


# 呼び出し元の環境から外す、ユニットの置き場所・状態のフォルダ・mindstella の設定の環境変数
ISOLATED_PREFIXES = ("XDG_", "MINDSTELLA_", "PROJECT_INDEX_PORT")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """テストの一時フォルダのホーム（ユニットのファイルは `.config/systemd/user/` に書かれる）。"""
    folder = tmp_path / "home"
    folder.mkdir()
    return folder


@pytest.fixture
def run_ensure(home: Path, resident_port: int, fake_systemctl: FakeSystemctl) -> object:
    """システムの python3 で起動の確認を呼ぶ関数を返す。`PATH` は systemctl の Mock のフォルダだけにする。"""
    system_python = shutil.which("python3", path="/usr/bin:/bin")
    assert system_python is not None

    def _run(
        venv: Path,
        *,
        hook: bool = True,
        stdin: str | None = None,
        args: tuple[str, ...] = (),
        port: int | None = None,
        script: Path = ENSURE_SCRIPT,
        path: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """フックの入力（hook のときだけ）を標準入力に渡して起動の確認を呼び、終わるまで待つ。"""
        env = {
            key: value for key, value in os.environ.items() if not key.startswith(ISOLATED_PREFIXES)
        }
        env.update(
            {
                "HOME": str(home),
                "PATH": str(fake_systemctl.bin_dir) if path is None else path,
                "PYTHONUTF8": "1",
                PORT_ENV: str(resident_port if port is None else port),
                "MINDSTELLA_VENV": str(venv),
            }
        )
        return subprocess.run(
            [system_python, str(script), *(["--hook"] if hook else []), *args],
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


def _changes(fake_systemctl: FakeSystemctl) -> list[list[str]]:
    """systemctl の Mock が受けた引数のうち、状態を読むだけの is-active を除いたもの。"""
    return [call for call in fake_systemctl.calls() if call[:1] != ["is-active"]]


def _unit(home: Path) -> Path:
    """ユニットのファイルのパス。"""
    return home / ".config" / "systemd" / "user" / "mindstella.service"


def _exec_start(home: Path) -> str:
    """ユニットのファイルの ExecStart の値。"""
    for line in _unit(home).read_text(encoding="utf-8").splitlines():
        if line.startswith("ExecStart="):
            return line.removeprefix("ExecStart=")
    raise AssertionError("ExecStart が無い")


def test_normal(
    tmp_path: Path,
    home: Path,
    ready_venv: Path,
    resident_port: int,
    run_ensure: object,
    fake_systemctl: FakeSystemctl,
) -> None:
    """常駐サーバーが落ちていればユニットを書いて起動し、待ち受けを確かめて、つなぎ直す案内を出す（正常系）。"""
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
    assert (
        _exec_start(home)
        == f"{ready_venv}/bin/python {PLUGIN_DIR}/skills/mindmap/scripts/server.py"
    )
    assert _changes(fake_systemctl) == [
        ["show-environment"],
        ["daemon-reload"],
        ["start", "mindstella.service"],
    ]


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
    fake_systemctl: FakeSystemctl,
) -> None:
    """古いコードの常駐サーバーが待ち受けていれば、起動し直さずに違いと手順を示す（正常系）。"""
    # 準備
    serve_fake_status(resident_port, 200, OUTDATED_STATUS)
    other_port = free_port()
    other_root = f"/other/plugins/cache/mindstella/{PLUGIN_DIR.name}-old"
    serve_fake_status(
        other_port,
        200,
        {"name": SERVER_NAME, "version": plugin_version(), "plugin_root": other_root},
    )
    # 実行
    completed = run_ensure(ready_venv, stdin=_hook_input(tmp_path))
    other = run_ensure(ready_venv, stdin=_hook_input(tmp_path), port=other_port)
    # 検証
    assert completed.returncode == 0
    assert "0.0.1" in completed.stdout
    assert plugin_version() in completed.stdout
    assert "mindstella server restart" in completed.stdout
    assert read_server_status(resident_port) == OUTDATED_STATUS
    assert other.returncode == 0
    assert f"{PLUGIN_DIR.name}-old" in other.stdout
    assert PLUGIN_DIR.name in other.stdout
    assert "mindstella server restart" in other.stdout
    assert fake_systemctl.calls() == []


def test_normal_when_called_by_launcher(
    ready_venv: Path, resident_port: int, run_ensure: object
) -> None:
    """`--hook` を付けずに呼ぶと、標準入力を読まず、起動したことを標準エラーに出す（正常系）。"""
    # 実行
    completed = run_ensure(ready_venv, hook=False)
    # 検証
    assert (completed.returncode, completed.stdout) == (0, ""), completed.stderr
    assert f"[mindstella] 常駐サーバーを起動しました（ポート {resident_port}）" in completed.stderr


def test_normal_when_restarted(
    tmp_path: Path,
    home: Path,
    ready_venv: Path,
    resident_port: int,
    run_ensure: object,
    fake_systemctl: FakeSystemctl,
) -> None:
    """--restart では、このスクリプトのプラグインのフォルダでユニットを書き直して起動し直す（正常系）。"""
    # 準備
    old_plugin = copy_plugin(tmp_path / "old-plugin")
    old_script = old_plugin / "skills" / "mindmap" / "scripts" / "ensure_server.py"
    first = run_ensure(ready_venv, hook=False, script=old_script)
    assert first.returncode == 0, first.stderr
    assert str(old_plugin) in _exec_start(home)
    # 実行
    completed = run_ensure(ready_venv, hook=False, args=("--restart",))
    # 検証
    assert completed.returncode == 0, completed.stderr
    assert (
        _exec_start(home)
        == f"{ready_venv}/bin/python {PLUGIN_DIR}/skills/mindmap/scripts/server.py"
    )
    assert _changes(fake_systemctl)[-2:] == [["daemon-reload"], ["restart", "mindstella.service"]]
    status = read_server_status(resident_port)
    assert status is not None
    assert status["plugin_root"] == str(PLUGIN_DIR)


def test_error_when_port_in_use(
    tmp_path: Path,
    ready_venv: Path,
    resident_port: int,
    run_ensure: object,
    serve_fake_status: ServeFakeStatus,
    fake_systemctl: FakeSystemctl,
) -> None:
    """ポートを mindstella でないプロセスが使っていれば、起動せずに使われているポートを示す（異常系）。"""
    # 準備
    serve_fake_status(resident_port, 404, None)
    guide = (
        f"[mindstella] エラー: ポート {resident_port} は mindstella でないプロセスが使っています"
    )
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
    assert not any(call[:1] == ["start"] for call in fake_systemctl.calls())


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


def test_error_when_systemd_unavailable(
    tmp_path: Path, home: Path, ready_venv: Path, resident_port: int, run_ensure: object
) -> None:
    """systemd --user が使えなければ、ユニットを書かずに起動せず、要ることを示す（異常系）。"""
    # 準備
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    # 実行
    hooked = run_ensure(ready_venv, stdin=_hook_input(tmp_path), path=str(empty))
    launched = run_ensure(ready_venv, hook=False, path=str(empty))
    # 検証
    assert hooked.returncode == 0
    assert "systemd --user" in hooked.stdout
    assert launched.returncode == 1
    assert "systemd --user" in launched.stderr
    assert not _unit(home).exists()
    assert is_listening(resident_port) is False
