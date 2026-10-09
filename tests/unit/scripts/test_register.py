"""register.py（起動スクリプトの alias と環境変数の登録）の単体テスト。"""

from __future__ import annotations

import ast
import importlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from fixture_types import SnapshotTree

# 印の範囲の外にある、利用者が書いた行
USER_LINE = "export EDITOR=vim"

# 登録のスクリプトが読む Python の最も古い版（構文を確かめる版）
OLDEST_PYTHON = (3, 8)

# root は権限を外しても書けるため、書き込めない流れを飛ばす
RUNNING_AS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


@pytest.fixture
def register() -> ModuleType:
    """登録のスクリプトのモジュールを返す（まだ無い間も、他のテストの収集を止めないよう使うときに読む）。"""
    return importlib.import_module("register")


def _environ(home: Path, *, shell: str | None = "/bin/bash") -> dict[str, str]:
    """HOME と SHELL だけを持つ環境変数を返す（XDG_CONFIG_HOME は持たない）。"""
    environ = {"HOME": str(home)}
    # SHELL を持たない環境を作るときは足さない
    if shell is not None:
        environ["SHELL"] = shell
    return environ


def _run_main(
    register: ModuleType,
    argv: list[str],
    home: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    shell: str | None = "/bin/bash",
) -> tuple[int, dict[str, Any] | None]:
    """main を Linux として呼び、終了コードと、標準出力に出た JSON（無ければ None）を返す。"""
    code = register.main(argv, environ=_environ(home, shell=shell), system="Linux")
    out = capsys.readouterr().out
    return code, json.loads(out) if out else None


def _write_texts(directory: Path, files: dict[str, str]) -> None:
    """フォルダの直下に、ファイル名 → 中身のファイルを書く。"""
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")


def _registration_file(home: Path) -> Path:
    """登録の中身を書くファイルの場所を返す。"""
    return home / ".config" / "mindstella" / "registration.json"


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["set", "--env", "PATH=/tmp"], id="unknown_env_key"),
        pytest.param(["set", "--env", "MINDSTELLA_VENV"], id="env_without_value"),
        pytest.param(
            ["add-account", "--name", "Sub1", "--config-dir", "/c"], id="invalid_account_name"
        ),
        pytest.param(["add-account", "--name", "sub1"], id="add_account_without_config_dir"),
        pytest.param(["remove-account"], id="remove_account_without_name"),
    ],
)
def test_main_when_invalid_args(
    register: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    snapshot_tree: SnapshotTree,
    argv: list[str],
) -> None:
    """引数の誤りは何も書かず 2（異常系）。"""
    # 実行
    code, _ = _run_main(register, argv, tmp_path, capsys)
    # 検証
    assert code == 2
    assert snapshot_tree(tmp_path) == {}


def test_main_when_unknown_account(
    register: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    snapshot_tree: SnapshotTree,
) -> None:
    """登録に無いアカウントを外すと 1（異常系）。"""
    # 準備
    _run_main(register, ["set"], tmp_path, capsys)
    before = snapshot_tree(tmp_path)
    # 実行
    code, report = _run_main(register, ["remove-account", "--name", "sub9"], tmp_path, capsys)
    # 検証
    assert code == 1
    assert report is not None
    assert "sub9" in report["error"]
    assert snapshot_tree(tmp_path) == before


def test_main_when_unsupported_shell(
    register: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    snapshot_tree: SnapshotTree,
) -> None:
    """bash・zsh でなければ手で書く行を返して 1（異常系）。"""
    # 実行
    code, report = _run_main(register, ["set"], tmp_path, capsys, shell="/usr/bin/fish")
    # 検証
    assert code == 1
    assert report is not None
    assert "fish" in report["error"]
    assert register.MARK_BEGIN in report["manual_lines"]
    assert any(line.startswith("mindstella()") for line in report["manual_lines"])
    assert snapshot_tree(tmp_path) == {}


def test_main_when_old_syntax(setup_scripts_dir: Path) -> None:
    """登録のスクリプトが Python 3.8 の構文で読め、型注釈を実行時に評価しない（正常系）。"""
    # 準備
    source = (setup_scripts_dir / "register.py").read_text(encoding="utf-8")
    # 実行
    tree = ast.parse(source, feature_version=OLDEST_PYTHON)
    # 検証（docstring の次の文）
    statement = tree.body[1]
    assert isinstance(statement, ast.ImportFrom)
    assert statement.module == "__future__"
    assert [alias.name for alias in statement.names] == ["annotations"]


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["show"], id="show"),
        pytest.param(["set", "--env", "MINDSTELLA_ALLOWED_HOSTS=a"], id="set"),
    ],
)
def test_main_when_registration_broken(
    register: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    snapshot_tree: SnapshotTree,
    argv: list[str],
) -> None:
    """registration.json が壊れていれば何も書かず 1（異常系）。"""
    # 準備
    broken = _registration_file(tmp_path)
    broken.parent.mkdir(parents=True)
    broken.write_text("{", encoding="utf-8")
    before = snapshot_tree(tmp_path)
    # 実行
    code, report = _run_main(register, argv, tmp_path, capsys)
    # 検証
    assert code == 1
    assert report is not None
    assert str(broken) in report["error"]
    assert snapshot_tree(tmp_path) == before


def test_register_module_when_name_unique(register: ModuleType, scripts_dir: Path) -> None:
    """register.py と同じ名前のモジュールが mindmap のスクリプトに無く、セットアップ側のものを読む（正常系）。"""
    # 検証
    assert not (scripts_dir / "register.py").exists()
    assert Path(register.__file__).parent.name == "scripts"
    assert Path(register.__file__).parent.parent.name == "setup"


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        pytest.param({"HOME": "/h"}, Path("/h/.config/mindstella"), id="home_only"),
        pytest.param(
            {"HOME": "/h", "XDG_CONFIG_HOME": "/x"}, Path("/x/mindstella"), id="xdg_config_home"
        ),
        pytest.param(
            {"HOME": "/h", "XDG_CONFIG_HOME": ""}, Path("/h/.config/mindstella"), id="xdg_empty"
        ),
    ],
)
def test_registration_dir(register: ModuleType, environ: dict[str, str], expected: Path) -> None:
    """XDG_CONFIG_HOME を優先する（正常系）。"""
    # 実行
    result = register.registration_dir(environ)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("shell", "system", "expected"),
    [
        pytest.param("/bin/bash", "Linux", Path("/h/.bashrc"), id="bash_linux"),
        pytest.param("/bin/bash", "Darwin", Path("/h/.bash_profile"), id="bash_darwin"),
        pytest.param("/bin/zsh", "Darwin", Path("/h/.zshrc"), id="zsh_darwin"),
    ],
)
def test_rc_file_path(register: ModuleType, shell: str, system: str, expected: Path) -> None:
    """シェルと OS で分ける（正常系）。"""
    # 実行
    result = register.rc_file_path({"HOME": "/h", "SHELL": shell}, system=system)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    "environ",
    [
        pytest.param({"HOME": "/h", "SHELL": "/usr/bin/fish"}, id="fish"),
        pytest.param({"HOME": "/h"}, id="no_shell"),
    ],
)
def test_rc_file_path_when_unsupported(register: ModuleType, environ: dict[str, str]) -> None:
    """bash・zsh でなければ UnsupportedShellError（異常系）。"""
    # 実行・検証
    with pytest.raises(register.UnsupportedShellError, match="には登録できません"):
        register.rc_file_path(environ, system="Linux")


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        pytest.param(
            {
                "registration.json": json.dumps(
                    {
                        "env": {"MINDSTELLA_ALLOWED_HOSTS": "a.example"},
                        "accounts": [{"name": "sub1", "config_dir": "/c1"}],
                    }
                )
            },
            {
                "env": {"MINDSTELLA_ALLOWED_HOSTS": "a.example"},
                "accounts": [{"name": "sub1", "config_dir": "/c1"}],
            },
            id="written",
        ),
        pytest.param({}, None, id="missing"),
    ],
)
def test_read_registration(
    register: ModuleType,
    tmp_path: Path,
    files: dict[str, str],
    expected: dict[str, Any] | None,
) -> None:
    """書いた登録を読み、無ければ None（正常系）。"""
    # 準備
    _write_texts(tmp_path, files)
    # 実行
    result = register.read_registration(tmp_path)
    # 検証
    assert result == expected


def test_apply_set(register: ModuleType) -> None:
    """渡したキーだけを書き換える（正常系）。"""
    # 準備
    registration = {
        "env": {"MINDSTELLA_ALLOWED_HOSTS": "a", "MINDSTELLA_VENV": "/v"},
        "accounts": [],
    }
    # 実行
    result = register.apply_set(
        registration,
        updates={"MINDSTELLA_ALLOWED_HOSTS": "b"},
        removals=["MINDSTELLA_VENV"],
    )
    # 検証
    assert result["env"] == {"MINDSTELLA_ALLOWED_HOSTS": "b"}
    assert registration == {
        "env": {"MINDSTELLA_ALLOWED_HOSTS": "a", "MINDSTELLA_VENV": "/v"},
        "accounts": [],
    }


@pytest.mark.parametrize(
    ("accounts", "name", "config_dir", "expected"),
    [
        pytest.param(
            [{"name": "sub2", "config_dir": "/c2"}],
            "sub1",
            "/c1",
            [{"name": "sub1", "config_dir": "/c1"}, {"name": "sub2", "config_dir": "/c2"}],
            id="add",
        ),
        pytest.param(
            [{"name": "sub1", "config_dir": "/c1"}],
            "sub1",
            "/c9",
            [{"name": "sub1", "config_dir": "/c9"}],
            id="overwrite",
        ),
    ],
)
def test_apply_add_account(
    register: ModuleType,
    accounts: list[dict[str, str]],
    name: str,
    config_dir: str,
    expected: list[dict[str, str]],
) -> None:
    """足す・書き換える（正常系）。"""
    # 実行
    result = register.apply_add_account(
        {"env": {}, "accounts": accounts}, name=name, config_dir=Path(config_dir)
    )
    # 検証
    assert result["accounts"] == expected


def test_apply_remove_account(register: ModuleType) -> None:
    """そのアカウントだけを外す（正常系）。"""
    # 準備
    registration = {
        "env": {},
        "accounts": [
            {"name": "sub1", "config_dir": "/c1"},
            {"name": "sub2", "config_dir": "/c2"},
        ],
    }
    # 実行
    result = register.apply_remove_account(registration, name="sub1")
    # 検証
    assert result["accounts"] == [{"name": "sub2", "config_dir": "/c2"}]


@pytest.mark.parametrize(
    ("registration", "name", "expected_known"),
    [
        pytest.param(
            {"env": {}, "accounts": [{"name": "sub1", "config_dir": "/c1"}]},
            "sub9",
            ["sub1"],
            id="unknown_name",
        ),
        pytest.param(None, "sub1", [], id="no_registration"),
    ],
)
def test_apply_remove_account_when_unknown(
    register: ModuleType,
    registration: dict[str, Any] | None,
    name: str,
    expected_known: list[str],
) -> None:
    """無いアカウントは UnknownAccountError（異常系）。"""
    # 実行・検証
    with pytest.raises(register.UnknownAccountError) as excinfo:
        register.apply_remove_account(registration, name=name)
    assert excinfo.value.known == expected_known


@pytest.mark.parametrize(
    "shell",
    [
        pytest.param("bash", id="bash"),
        pytest.param(
            "zsh",
            marks=pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh が入っていません"),
            id="zsh",
        ),
    ],
)
def test_render_shell(register: ModuleType, tmp_path: Path, shell: str) -> None:
    """export と alias を書き、bash と zsh で読める（正常系）。"""
    # 準備
    registration = {
        "env": {"MINDSTELLA_ALLOWED_HOSTS": "it's.example"},
        "accounts": [{"name": "sub1", "config_dir": "/c1"}],
    }
    # 実行
    text = register.render_shell(registration)
    script = tmp_path / "shell.sh"
    script.write_text(text, encoding="utf-8")
    syntax = subprocess.run([shell, "-n", str(script)], capture_output=True, text=True, check=False)
    # 検証
    lines = text.splitlines()
    assert "export MINDSTELLA_ALLOWED_HOSTS='it'\\''s.example'" in lines
    assert any(line.startswith("mindstella()") for line in lines)
    assert any(line.startswith("mindstella-sub1()") and "'/c1'" in line for line in lines)
    assert syntax.returncode == 0, syntax.stderr


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(USER_LINE, id="no_trailing_newline"),
        pytest.param("", id="empty"),
    ],
)
def test_add_rc_block(register: ModuleType, text: str) -> None:
    """無ければ足す（正常系）。"""
    # 準備
    shell_file = Path("/h/.config/mindstella/shell.sh")
    # 実行
    result = register.add_rc_block(text, shell_file=shell_file)
    # 検証（利用者の行の後に、印と読み込む 1 行だけの 3 行を足す）
    block = [
        register.MARK_BEGIN,
        "[ -f '/h/.config/mindstella/shell.sh' ] && . '/h/.config/mindstella/shell.sh'",
        register.MARK_END,
    ]
    assert result.splitlines() == [*text.splitlines(), *block]


def test_add_rc_block_when_already_added(register: ModuleType) -> None:
    """既に印の範囲があれば重ねない（正常系）。"""
    # 準備
    shell_file = Path("/h/.config/mindstella/shell.sh")
    added = register.add_rc_block(f"{USER_LINE}\n", shell_file=shell_file)
    # 実行
    result = register.add_rc_block(added, shell_file=shell_file)
    # 検証
    assert result == added


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(f"{USER_LINE}\n", id="trailing_newline"),
        pytest.param(USER_LINE, id="no_trailing_newline"),
    ],
)
def test_remove_rc_block(register: ModuleType, text: str) -> None:
    """add_rc_block で足した範囲を消すと元に戻る（正常系）。"""
    # 準備
    added = register.add_rc_block(text, shell_file=Path("/h/.config/mindstella/shell.sh"))
    # 実行
    result = register.remove_rc_block(added)
    # 検証
    assert result == text


def test_remove_rc_block_when_no_block(register: ModuleType) -> None:
    """範囲を持たない中身はそのまま返す（正常系）。"""
    # 準備
    text = f"{USER_LINE}\nalias ll='ls -l'\n"
    # 実行
    result = register.remove_rc_block(text)
    # 検証
    assert result == text


def test_write_files(register: ModuleType, tmp_path: Path) -> None:
    """書く・消す・フォルダを作る（正常系）。"""
    # 準備
    (tmp_path / "a").write_text("old a", encoding="utf-8")
    (tmp_path / "c").write_text("old c", encoding="utf-8")
    (tmp_path / "dotfiles").mkdir()
    (tmp_path / "dotfiles" / "rc").write_text("old rc", encoding="utf-8")
    (tmp_path / "d").symlink_to(tmp_path / "dotfiles" / "rc")
    # 実行
    register.write_files(
        {
            tmp_path / "a": None,
            tmp_path / "sub" / "b": "x",
            tmp_path / "c": "y",
            tmp_path / "d": "z",
        }
    )
    # 検証
    assert not (tmp_path / "a").exists()
    assert (tmp_path / "sub" / "b").read_text(encoding="utf-8") == "x"
    assert (tmp_path / "c").read_text(encoding="utf-8") == "y"
    assert (tmp_path / "d").is_symlink()
    assert (tmp_path / "dotfiles" / "rc").read_text(encoding="utf-8") == "z"
    # 一時ファイルが残っていない
    remains = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert remains == ["c", "d", "dotfiles", "dotfiles/rc", "sub", "sub/b"]


@pytest.mark.skipif(RUNNING_AS_ROOT, reason="root は権限を外しても書けます")
def test_write_files_when_not_writable(register: ModuleType, tmp_path: Path) -> None:
    """1 つでも書けなければ何も書かない（異常系）。"""
    # 準備
    read_only = tmp_path / "ro"
    read_only.write_text("before", encoding="utf-8")
    read_only.chmod(0o444)
    # 実行・検証
    with pytest.raises(register.NotWritableError) as excinfo:
        register.write_files({read_only: "x", tmp_path / "new": "y"})
    assert excinfo.value.path == read_only
    assert not (tmp_path / "new").exists()
    assert read_only.read_text(encoding="utf-8") == "before"


@pytest.mark.parametrize(
    ("registration", "expected"),
    [
        pytest.param(
            {"env": {}, "accounts": [{"name": "sub1", "config_dir": "/c1"}]},
            {
                "registered": True,
                "env": {},
                "accounts": [{"name": "sub1", "config_dir": "/c1"}],
                "aliases": ["mindstella", "mindstella-sub1"],
            },
            id="registered",
        ),
        pytest.param(
            None,
            {"registered": False, "env": {}, "accounts": [], "aliases": []},
            id="not_registered",
        ),
    ],
)
def test_build_report(
    register: ModuleType, registration: dict[str, Any] | None, expected: dict[str, Any]
) -> None:
    """登録の有無で registered と aliases を分ける（正常系）。"""
    # 準備
    rc_file = Path("/h/.bashrc")
    shell_file = Path("/h/.config/mindstella/shell.sh")
    # 実行
    report = register.build_report(registration, rc_file=rc_file, shell_file=shell_file)
    # 検証
    assert report == {**expected, "rc_file": str(rc_file), "shell_file": str(shell_file)}
