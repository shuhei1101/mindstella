"""起動スクリプトの登録（セットアップのスキルで、起動スクリプトを呼ぶ alias と環境変数をシェルの設定に登録する）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねる登録のスクリプトの呼び出しを決めた引数で順に再生し、新しく開いた bash で alias と環境変数が効くことを確かめる。
隔離したホームと偽の `claude`・偽の起動スクリプトは `tests/e2e/launch_registration_helpers.py`。
"""

from __future__ import annotations

import platform
import shlex
import shutil
from typing import TYPE_CHECKING

import pytest
from launch_registration_helpers import (
    BASHRC_USER_LINE,
    CONFIG_UNSET,
    MARK_BEGIN,
    RegistrationSandbox,
    read_report,
)
from workspace_fixtures import SnapshotTree

if TYPE_CHECKING:
    from conftest import LockDirs

# macOS はログインシェルの設定ファイルが `~/.bashrc` でない
pytestmark = pytest.mark.skipif(
    platform.system() == "Darwin", reason="macOS のログインシェルの設定ファイルは ~/.bashrc でない"
)

# 登録する環境変数
ALLOWED_HOSTS = "MINDSTELLA_ALLOWED_HOSTS"
VENV = "MINDSTELLA_VENV"


@pytest.fixture
def stubbed(registration_sandbox: RegistrationSandbox) -> RegistrationSandbox:
    """既定のアカウントの偽の `claude` と偽の起動スクリプトを置いたホームのフォルダを返す。"""
    install = registration_sandbox.make_install("default")
    registration_sandbox.write_claude({"": str(install)})
    return registration_sandbox


@pytest.fixture
def registered(stubbed: RegistrationSandbox) -> RegistrationSandbox:
    """`MINDSTELLA_ALLOWED_HOSTS=preview.example.com` で登録を済ませたホームのフォルダを返す。"""
    result = stubbed.run("set", "--env", f"{ALLOWED_HOSTS}=preview.example.com")
    assert result.returncode == 0, result.stderr
    return stubbed


def test_normal(stubbed: RegistrationSandbox, snapshot_tree: SnapshotTree) -> None:
    """未登録のホームで、登録を読み、`mindstella` と環境変数を登録して、新しいシェルから起動スクリプトを叩ける（正常系）。"""
    # 準備
    workspace = stubbed.root / "家計簿アプリ"
    workspace.mkdir()
    workspace_before = snapshot_tree(workspace)
    # 実行
    # 手順が連ねるのは、登録を読む → 環境変数を渡して登録する
    shown = stubbed.run("show")
    result = stubbed.run("set", "--env", f"{ALLOWED_HOSTS}=preview.example.com")
    # 検証
    assert shown.returncode == 0, shown.stderr
    assert read_report(shown)["registered"] is False
    assert result.returncode == 0, result.stderr
    # 新しく開いた bash で、alias が定義され、環境変数が入る
    assert "mindstella is a function" in stubbed.bash("type mindstella").stdout
    assert "[preview.example.com]" in stubbed.bash(f'echo "[${ALLOWED_HOSTS}]"').stdout
    # 新しく開いた bash で alias にフォルダを渡すと、installPath の版の起動スクリプトがそのフォルダを受け取る
    stubbed.bash(f"mindstella {shlex.quote(str(workspace))}")
    assert stubbed.launch_record("default") == ([str(workspace)], CONFIG_UNSET)
    # 利用者が書いた行はそのままで、印の範囲は 1 つだけ
    rc_lines = stubbed.bashrc.read_text(encoding="utf-8").splitlines()
    assert rc_lines[0] == BASHRC_USER_LINE
    assert rc_lines.count(MARK_BEGIN) == 1
    # ワークスペースのフォルダに何も書かれていない
    assert snapshot_tree(workspace) == workspace_before == {}


def test_normal_when_registered(stubbed: RegistrationSandbox) -> None:
    """登録済みの値のうち、渡した環境変数だけを変え、登録の行は重ならない（正常系）。"""
    # 準備
    first = stubbed.run(
        "set", "--env", f"{ALLOWED_HOSTS}=a.example.com", "--env", f"{VENV}=~/venvs/mindstella"
    )
    assert first.returncode == 0, first.stderr
    # 実行
    # 手順が連ねるのは、登録を読む → 変える環境変数だけを渡して登録する
    shown = stubbed.run("show")
    result = stubbed.run("set", "--env", f"{ALLOWED_HOSTS}=b.example.com")
    # 検証
    assert shown.returncode == 0, shown.stderr
    assert read_report(shown)["env"] == {ALLOWED_HOSTS: "a.example.com", VENV: "~/venvs/mindstella"}
    assert result.returncode == 0, result.stderr
    # 新しく開いた bash で、変えた値だけが変わっている
    assert "[b.example.com]" in stubbed.bash(f'echo "[${ALLOWED_HOSTS}]"').stdout
    assert "[~/venvs/mindstella]" in stubbed.bash(f'echo "[${VENV}]"').stdout
    # 登録の行が 1 つずつしかない
    rc_lines = stubbed.bashrc.read_text(encoding="utf-8").splitlines()
    shell_lines = stubbed.shell_lines()
    assert rc_lines.count(MARK_BEGIN) == 1
    assert len([line for line in shell_lines if line.startswith(f"export {ALLOWED_HOSTS}=")]) == 1
    assert len([line for line in shell_lines if line.startswith(f"export {VENV}=")]) == 1
    assert len([line for line in shell_lines if line.startswith("mindstella()")]) == 1
    # 利用者が書いた行がそのまま残っている
    assert rc_lines[0] == BASHRC_USER_LINE


def test_normal_when_plugin_upgraded(registration_sandbox: RegistrationSandbox) -> None:
    """プラグインを上げた後も、登録し直さずに新しい版の起動スクリプトが立ち上がる（正常系）。"""
    # 準備
    old_install = registration_sandbox.make_install("old")
    registration_sandbox.write_claude({"": str(old_install)})
    registered = registration_sandbox.run("set", "--env", f"{ALLOWED_HOSTS}=preview.example.com")
    assert registered.returncode == 0, registered.stderr
    rc_before = registration_sandbox.bashrc.read_text(encoding="utf-8")
    shell_before = registration_sandbox.shell_lines()
    # プラグインを上げる: 新しい版のフォルダだけが残り、古い版のフォルダは消える
    shutil.rmtree(old_install)
    new_install = registration_sandbox.make_install("new")
    registration_sandbox.write_claude({"": str(new_install)})
    workspace = registration_sandbox.root / "家計簿アプリ"
    # 実行
    registration_sandbox.bash(f"mindstella {shlex.quote(str(workspace))}")
    # 検証
    # 新しい版のフォルダの起動スクリプトがフォルダを受け取って立ち上がる
    assert registration_sandbox.launch_record("new") == ([str(workspace)], CONFIG_UNSET)
    assert not registration_sandbox.launched("old")
    # シェルの設定の中身は、登録した直後と同じ
    assert registration_sandbox.bashrc.read_text(encoding="utf-8") == rc_before
    assert registration_sandbox.shell_lines() == shell_before


def test_normal_when_unregistered(registered: RegistrationSandbox) -> None:
    """登録を外すと、mindstella の登録だけが消える（正常系）。"""
    # 実行
    result = registered.run("remove")
    # 検証
    assert result.returncode == 0, result.stderr
    # 新しく開いた bash で、alias が定義されておらず、MINDSTELLA_ で始まる環境変数が無い
    # 見るのは登録が書く関数の定義（PATH にインストール済みのプラグインの bin/mindstella があっても左右されない）
    assert registered.bash("declare -F mindstella").returncode != 0
    environment = registered.bash("printenv").stdout.splitlines()
    assert [line for line in environment if line.startswith("MINDSTELLA_")] == []
    # 利用者が書いた行がそのまま残っている
    assert registered.bashrc.read_text(encoding="utf-8") == f"{BASHRC_USER_LINE}\n"


def test_error_when_not_writable(
    registration_sandbox: RegistrationSandbox,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """シェルの設定に書き込めないと、何も書かず、理由と手で書く行を返して止まる（異常系）。"""
    # 準備
    # 登録の書き先を作ってから、`~/.bashrc` と書き先を読み取りだけにする
    registration_sandbox.registration_dir.mkdir(parents=True)
    lock_dirs(registration_sandbox.bashrc, registration_sandbox.registration_dir)
    home_before = snapshot_tree(registration_sandbox.home)
    # 実行
    result = registration_sandbox.run("set", "--env", f"{ALLOWED_HOSTS}=preview.example.com")
    # 検証
    # 0 以外の終了コードで、書き込めない理由と、手で書けば同じ登録になる行を返す
    assert result.returncode != 0
    report = read_report(result)
    locked = (str(registration_sandbox.bashrc), str(registration_sandbox.registration_dir))
    assert any(path in report["error"] for path in locked)
    assert MARK_BEGIN in report["manual_lines"]
    assert any(line.startswith("mindstella()") for line in report["manual_lines"])
    # ホームのフォルダのどのファイルの中身も、呼ぶ前と同じ
    assert snapshot_tree(registration_sandbox.home) == home_before


def test_normal_when_account_added(registered: RegistrationSandbox) -> None:
    """アカウントを足すと、`mindstella-{名前}` がそのアカウントの設定のフォルダで起動スクリプトを立ち上げ、`mindstella` は既定のアカウントのままである（正常系）。"""
    # 準備
    sub1_dir = registered.home / ".claude-sub1"
    sub1_dir.mkdir()
    default_install = registered.root / "install-default"
    sub1_install = registered.make_install("sub1")
    registered.write_claude({"": str(default_install), str(sub1_dir): str(sub1_install)})
    workspace = registered.root / "家計簿アプリ"
    # 実行
    result = registered.run("add-account", "--name", "sub1", "--config-dir", "~/.claude-sub1")
    registered.bash(f"mindstella-sub1 {shlex.quote(str(workspace))}")
    registered.bash(f"mindstella {shlex.quote(str(workspace))}")
    # 検証
    assert result.returncode == 0, result.stderr
    # アカウントの alias は、そのアカウントで引いた installPath の起動スクリプトにフォルダと設定のフォルダを渡す
    assert registered.launch_record("sub1") == ([str(workspace)], str(sub1_dir))
    # 既定の alias は、既定のアカウントで引いた installPath の起動スクリプトを、設定のフォルダなしで立ち上げる
    assert registered.launch_record("default") == ([str(workspace)], CONFIG_UNSET)
    # 登録の行が 1 つずつしかない
    rc_lines = registered.bashrc.read_text(encoding="utf-8").splitlines()
    shell_lines = registered.shell_lines()
    assert rc_lines.count(MARK_BEGIN) == 1
    assert len([line for line in shell_lines if line.startswith("mindstella()")]) == 1
    assert len([line for line in shell_lines if line.startswith("mindstella-sub1()")]) == 1
    # 利用者が書いた行がそのまま残っている
    assert rc_lines[0] == BASHRC_USER_LINE
