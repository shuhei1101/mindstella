"""register.py（起動スクリプトの alias と環境変数の登録）の結合テスト。

隔離したホームのフォルダ・偽の `claude`・偽の起動スクリプトは `register_helpers.py` と `conftest.py`。
登録のスクリプトは実物を子プロセスで動かし、alias は `bash -ic` で呼んで確かめる。
"""

from __future__ import annotations

import platform

import pytest
from workspace_fixtures import SnapshotTree

from .register_helpers import (
    BASHRC_USER_LINE,
    CONFIG_UNSET,
    MARK_BEGIN,
    LockFiles,
    RegisterSandbox,
    read_report,
)

# macOS はログインシェルの設定ファイルが `~/.bashrc` でない
pytestmark = pytest.mark.skipif(
    platform.system() == "Darwin", reason="macOS のログインシェルの設定ファイルは ~/.bashrc でない"
)

# 登録する環境変数
ALLOWED_HOSTS = "MINDSTELLA_ALLOWED_HOSTS"
VENV = "MINDSTELLA_VENV"


@pytest.fixture
def stubbed(register_sandbox: RegisterSandbox) -> RegisterSandbox:
    """既定のアカウントの偽の `claude` と偽の起動スクリプトを置いたホームのフォルダを返す。"""
    install = register_sandbox.make_install("default")
    register_sandbox.write_claude({"": str(install)})
    return register_sandbox


@pytest.fixture
def registered(stubbed: RegisterSandbox) -> RegisterSandbox:
    """`MINDSTELLA_ALLOWED_HOSTS=preview.example.com` で登録を済ませたホームのフォルダを返す。"""
    result = stubbed.run("set", "--env", f"{ALLOWED_HOSTS}=preview.example.com")
    assert result.returncode == 0, result.stderr
    return stubbed


def test_normal(stubbed: RegisterSandbox) -> None:
    """未登録のホームに、起動スクリプトを呼ぶ `mindstella` と環境変数を登録する（正常系）。"""
    # 実行
    result = stubbed.run("set", "--env", f"{ALLOWED_HOSTS}=preview.example.com")
    # 検証
    assert result.returncode == 0, result.stderr
    report = read_report(result)
    assert report["registered"] is True
    assert report["aliases"] == ["mindstella"]
    assert report["env"] == {ALLOWED_HOSTS: "preview.example.com"}
    assert report["rc_file"] == str(stubbed.bashrc)
    # 新しいシェルで alias が関数として使え、環境変数が入る
    defined = stubbed.bash("type mindstella")
    assert "mindstella is a function" in defined.stdout
    assert "[preview.example.com]" in stubbed.bash(f"echo [${ALLOWED_HOSTS}]").stdout
    # alias が installPath の起動スクリプトへ引数をそのまま渡す
    stubbed.bash("mindstella 家計簿アプリ")
    assert stubbed.launch_record("default") == (["家計簿アプリ"], CONFIG_UNSET)
    # 利用者の行はそのままで、印の範囲は 1 つだけ
    rc_text = stubbed.bashrc.read_text(encoding="utf-8")
    assert rc_text.splitlines()[0] == BASHRC_USER_LINE
    assert rc_text.splitlines().count(MARK_BEGIN) == 1


def test_normal_when_show(registered: RegisterSandbox, snapshot_tree: SnapshotTree) -> None:
    """登録済みの alias と環境変数を、何も書かずに返す（正常系）。"""
    # 準備
    before = snapshot_tree(registered.home)
    # 実行
    result = registered.run("show")
    # 検証
    assert result.returncode == 0, result.stderr
    report = read_report(result)
    assert report["registered"] is True
    assert report["env"] == {ALLOWED_HOSTS: "preview.example.com"}
    assert snapshot_tree(registered.home) == before


def test_normal_when_set_again(stubbed: RegisterSandbox) -> None:
    """登録し直すと、渡した環境変数だけを書き換え、印の範囲は重ねない（正常系）。"""
    # 準備
    first = stubbed.run(
        "set", "--env", f"{ALLOWED_HOSTS}=a.example.com", "--env", f"{VENV}=~/venvs/mindstella"
    )
    assert first.returncode == 0, first.stderr
    rc_before = stubbed.bashrc.read_text(encoding="utf-8")
    # 実行
    result = stubbed.run("set", "--env", f"{ALLOWED_HOSTS}=b.example.com")
    # 検証
    assert result.returncode == 0, result.stderr
    assert read_report(result)["env"] == {
        ALLOWED_HOSTS: "b.example.com",
        VENV: "~/venvs/mindstella",
    }
    rc_after = stubbed.bashrc.read_text(encoding="utf-8")
    assert rc_after.splitlines().count(MARK_BEGIN) == 1
    assert rc_after == rc_before


def test_normal_when_account_added(registered: RegisterSandbox) -> None:
    """アカウントを足すと、`mindstella-{名前}` がそのアカウントの `installPath` で起動スクリプトを叩く（正常系）。"""
    # 準備
    sub1_dir = registered.home / ".claude-sub1"
    sub1_dir.mkdir()
    sub1_install = registered.make_install("sub1")
    default_install = registered.root / "install-default"
    registered.write_claude({"": str(default_install), str(sub1_dir): str(sub1_install)})
    # 実行
    result = registered.run("add-account", "--name", "sub1", "--config-dir", "~/.claude-sub1")
    # 検証
    assert result.returncode == 0, result.stderr
    report = read_report(result)
    assert report["aliases"] == ["mindstella", "mindstella-sub1"]
    assert report["accounts"] == [{"name": "sub1", "config_dir": str(sub1_dir)}]
    # アカウントの alias は、そのアカウントで引いた installPath の起動スクリプトに設定のフォルダを渡す
    registered.bash("mindstella-sub1 家計簿アプリ")
    assert registered.launch_record("sub1") == (["家計簿アプリ"], str(sub1_dir))
    # 既定の alias は、既定のアカウントの起動スクリプトを設定のフォルダなしで動かす
    registered.bash("mindstella 家計簿アプリ")
    assert registered.launch_record("default") == (["家計簿アプリ"], CONFIG_UNSET)


def test_normal_when_removed(registered: RegisterSandbox) -> None:
    """外すと、登録のファイルと印の範囲だけを消す（正常系）。"""
    # 実行
    result = registered.run("remove")
    # 検証
    assert result.returncode == 0, result.stderr
    assert read_report(result)["registered"] is False
    assert not (registered.registration_dir / "registration.json").exists()
    assert not (registered.registration_dir / "shell.sh").exists()
    assert registered.bashrc.read_text(encoding="utf-8") == f"{BASHRC_USER_LINE}\n"


def test_error_when_unknown_env_key(
    register_sandbox: RegisterSandbox, snapshot_tree: SnapshotTree
) -> None:
    """許さない環境変数のキーを渡すと、何も書かず 2 で終わる（異常系）。"""
    # 準備
    before = snapshot_tree(register_sandbox.home)
    # 実行
    result = register_sandbox.run("set", "--env", "PATH=/tmp")
    # 検証
    assert result.returncode == 2
    assert snapshot_tree(register_sandbox.home) == before


def test_error_when_not_writable(
    register_sandbox: RegisterSandbox, snapshot_tree: SnapshotTree, lock_files: LockFiles
) -> None:
    """ログインシェルの設定ファイルに書き込めないと、何も書かず手で書く行を返す（異常系）。"""
    # 準備
    lock_files(register_sandbox.bashrc)
    before = snapshot_tree(register_sandbox.home)
    # 実行
    result = register_sandbox.run("set")
    # 検証
    assert result.returncode == 1
    report = read_report(result)
    assert str(register_sandbox.bashrc) in str(report["error"])
    manual_lines = report["manual_lines"]
    assert MARK_BEGIN in manual_lines
    assert any(line.startswith("mindstella()") for line in manual_lines)
    assert not (register_sandbox.registration_dir / "registration.json").exists()
    assert not (register_sandbox.registration_dir / "shell.sh").exists()
    assert snapshot_tree(register_sandbox.home) == before
