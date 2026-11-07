"""bin/mindstella（起動スクリプト）の結合テスト。

隔離した環境（偽の `claude`・専用のソケットの `tmux`・空きポート）は `tests/launch_fixtures.py`。
起動スクリプトが起動した常駐サーバーへは、MCP のクライアントでつないで確かめる。
"""

from __future__ import annotations

from pathlib import Path

from launch_fixtures import (
    PLUGIN_DIR,
    LaunchSandbox,
    ServeFakeStatus,
    copy_plugin,
    read_tool_names,
    session_name,
)
from workspace_fixtures import (
    LISTEN_HOST,
    MCP_PATH,
    McpClient,
    is_listening,
    plugin_version,
    read_server_status,
)

from .fixture_types import MakeVenv

# 起動スクリプトが起動する常駐サーバーの入口
SERVER_SCRIPT = PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "server.py"

# 古いバージョンの常駐サーバーの代わりが返す状態
OUTDATED_STATUS = {"name": "mindstella", "version": "0.0.1"}

# 起動時の指示のファイル（`installPath` からの場所）と、Claude Code へ渡すオプション
STARTUP_PROMPT = Path("skills") / "mindmap" / "references" / "起動時の指示.md"
APPEND_PROMPT_OPTION = "--append-system-prompt"


def _expected_args(plugin_dir: Path) -> str:
    """偽の claude が 1 行 1 引数で書く、起動時の指示を渡したときの引数の中身を返す。"""
    # 起動スクリプトはコマンド置換で読むので、末尾の改行は落ちる
    prompt = (plugin_dir / STARTUP_PROMPT).read_text(encoding="utf-8").rstrip("\n")
    return f"{APPEND_PROMPT_OPTION}\n{prompt}\n"


# 外から見る設定の環境変数とその値
ALLOWED_HOSTS_ENV = "MINDSTELLA_ALLOWED_HOSTS"
ALLOWED_HOST = "preview.example.test"


def _process_env(pid: int) -> dict[str, str]:
    """プロセスの環境変数を読む（Linux の /proc）。"""
    raw = Path(f"/proc/{pid}/environ").read_bytes().decode("utf-8")
    return dict(entry.split("=", 1) for entry in raw.split("\0") if "=" in entry)


def test_normal(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """依存がそろっていれば、常駐サーバーが落ちていれば起動してから、Claude Code を tmux のセッションで立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert folder.is_dir()
    # セッションの名前のハッシュは、フォルダと渡した設定のフォルダ（アカウント）から作る
    name = session_name(folder, sandbox.config_dir)
    assert sandbox.sessions() == [name]
    assert sandbox.session_path(name) == folder.resolve()
    started = sandbox.wait_started()
    assert len(started) == 1
    assert "--mcp-config" not in started[0].read_text(encoding="utf-8").splitlines()
    assert started[0].read_text(encoding="utf-8") == _expected_args(PLUGIN_DIR)
    assert started[0].with_suffix(".config").read_text(encoding="utf-8") == str(sandbox.config_dir)
    status = read_server_status(sandbox.port)
    assert status is not None
    assert status["plugin_root"] == str(PLUGIN_DIR)
    client = McpClient(f"http://{LISTEN_HOST}:{sandbox.port}{MCP_PATH}")
    try:
        assert [tool["name"] for tool in client.list_tools()] == read_tool_names(SERVER_SCRIPT)
    finally:
        client.close()
    assert f"tmux attach-session -t ={name}" in result.stdout


def test_normal_when_external_settings(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """呼び出し元の外から見る環境変数を、起動する常駐サーバーへ渡す（正常系）。"""
    # 実行
    result = sandbox.launch(
        "家計簿アプリ", venv=ready_venv, extra_env={ALLOWED_HOSTS_ENV: ALLOWED_HOST}
    )
    # 検証
    assert result.returncode == 0, result.stderr
    status = read_server_status(sandbox.port)
    assert status is not None
    assert _process_env(int(status["pid"]))[ALLOWED_HOSTS_ENV] == ALLOWED_HOST
    started = sandbox.wait_started()
    assert len(started) == 1
    # Claude Code の環境は呼び出し元から受け継いだ分だけで、起動スクリプトは値を足さない
    assert started[0].with_suffix(".hosts").read_text(encoding="utf-8") in ("", ALLOWED_HOST)
    assert started[0].read_text(encoding="utf-8") == _expected_args(PLUGIN_DIR)


def test_normal_when_plugin_upgraded(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """古い版のフォルダのスクリプトを叩いても、新しい版の常駐サーバーを起動する（正常系）。"""
    # 準備
    old_dir = copy_plugin(tmp_path / "plugin-old")
    new_dir = copy_plugin(tmp_path / "plugin-new")
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(new_dir)}])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv, script=old_dir / "bin" / "mindstella")
    # 検証
    assert result.returncode == 0, result.stderr
    status = read_server_status(sandbox.port)
    assert status is not None
    assert status["plugin_root"] == str(new_dir)


def test_normal_when_session_exists(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """既にあるセッションには新しく立てず、つなぐコマンドを返す（正常系）。"""
    # 準備
    first = sandbox.launch("家計簿アプリ", venv=ready_venv)
    assert first.returncode == 0, first.stderr
    sandbox.wait_started()
    sessions_before = sandbox.sessions()
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert sandbox.sessions() == sessions_before
    assert len(sandbox.started()) == 1
    assert "既にある" in result.stderr
    assert f"tmux attach-session -t ={sessions_before[0]}" in result.stdout


def test_error_when_dependency_missing(sandbox: LaunchSandbox, make_venv: MakeVenv) -> None:
    """ライブラリを入れていない仮想環境では、そろえるコマンドを示して何も立てない（異常系）。"""
    # 準備
    bare_venv = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=bare_venv)
    # 検証
    assert result.returncode == 1
    for package in ("PyYAML", "jsonschema", "mcp"):
        assert package in result.stderr
    assert "-m pip install" in result.stderr
    assert sandbox.sessions() == []
    assert sandbox.started() == []


def test_error_when_tmux_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """tmux が無ければ、入れるよう示して Claude Code を立てない（異常系）。"""
    # 準備
    sandbox.remove_tool("tmux")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "tmux" in result.stderr
    assert sandbox.started() == []


def test_error_when_claude_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """claude が無ければ、入れるよう示して止まる（異常系）。"""
    # 準備
    sandbox.remove_tool("claude")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "claude" in result.stderr
    assert sandbox.sessions() == []


def test_error_when_plugin_not_installed(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """プラグインの一覧に mindstella が無ければ、インストールを案内して止まる（異常系）。"""
    # 準備
    sandbox.write_claude([])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "mindstella@mindstella" in result.stderr
    assert "インストール" in result.stderr
    assert sandbox.sessions() == []


def test_error_when_startup_prompt_missing(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """インストールした版のフォルダに起動時の指示が無ければ、入れ直すよう示して何も立てない（異常系）。"""
    # 準備
    plugin_dir = copy_plugin(tmp_path / "plugin-without-prompt")
    (plugin_dir / STARTUP_PROMPT).unlink()
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(plugin_dir)}])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv, script=plugin_dir / "bin" / "mindstella")
    # 検証
    assert result.returncode == 1
    assert str(plugin_dir / STARTUP_PROMPT) in result.stderr
    assert "入れ直" in result.stderr
    assert sandbox.sessions() == []
    assert sandbox.started() == []
    assert read_server_status(sandbox.port) is None


def test_error_when_folder_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """引数が無ければ、使い方を出して止まる（異常系）。"""
    # 実行
    result = sandbox.launch(venv=ready_venv)
    # 検証
    assert result.returncode == 2
    assert "使い方" in result.stderr
    assert sandbox.started() == []


def test_normal_when_same_folder_name_elsewhere(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """名前が同じでも場所が違うフォルダは、別のセッションを立てる（正常系）。"""
    # 準備
    first = sandbox.launch("仕事/家計簿アプリ", venv=ready_venv)
    assert first.returncode == 0, first.stderr
    sandbox.wait_started()
    work_folder = sandbox.root / "仕事" / "家計簿アプリ"
    personal_folder = sandbox.root / "個人" / "家計簿アプリ"
    # 実行
    result = sandbox.launch("個人/家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    work_name = session_name(work_folder, sandbox.config_dir)
    personal_name = session_name(personal_folder, sandbox.config_dir)
    assert sorted(sandbox.sessions()) == sorted([work_name, personal_name])
    assert sandbox.session_path(work_name) == work_folder.resolve()
    assert sandbox.session_path(personal_name) == personal_folder.resolve()
    assert f"tmux attach-session -t ={personal_name}" in result.stdout
    assert "既にある" not in result.stderr


def test_normal_when_another_account(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """同じフォルダでも別のアカウント（`CLAUDE_CONFIG_DIR`）で開けば、別のセッションを立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    sub1 = tmp_path / "claude-sub1"
    sub1.mkdir()
    first = sandbox.launch("家計簿アプリ", venv=ready_venv, with_config=False)
    assert first.returncode == 0, first.stderr
    before = sandbox.wait_started()
    assert len(before) == 1
    # 実行
    result = sandbox.launch(
        "家計簿アプリ", venv=ready_venv, extra_env={"CLAUDE_CONFIG_DIR": str(sub1)}
    )
    # 検証
    assert result.returncode == 0, result.stderr
    first_name = session_name(folder)
    sub1_name = session_name(folder, sub1)
    assert first_name != sub1_name
    assert sorted(sandbox.sessions()) == sorted([first_name, sub1_name])
    started = sandbox.wait_started(2)
    assert len(started) == 2
    added = [path for path in started if path not in before]
    assert len(added) == 1
    assert added[0].with_suffix(".config").read_text(encoding="utf-8") == str(sub1)
    assert before[0].with_suffix(".config").read_text(encoding="utf-8") == ""
    assert f"tmux attach-session -t ={sub1_name}" in result.stdout
    assert "既にある" not in result.stderr


def test_normal_when_server_outdated(
    sandbox: LaunchSandbox, ready_venv: Path, serve_fake_status: ServeFakeStatus
) -> None:
    """待ち受けている常駐サーバーのバージョンが違えば、起動し直さずに差と手順を示し、Claude Code は立ち上げる（正常系）。"""
    # 準備
    serve_fake_status(sandbox.port, 200, OUTDATED_STATUS)
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert (
        f"常駐サーバーのバージョン 0.0.1 と、インストールしたプラグインのバージョン {plugin_version()} が違います"
        in result.stderr
    )
    assert "server_stop で常駐サーバーを止めてから、Claude Code を立ち上げ直してください" in result.stderr
    assert sandbox.sessions() == [session_name(folder, sandbox.config_dir)]
    assert read_server_status(sandbox.port) == OUTDATED_STATUS


def test_error_when_server_start_fails(
    sandbox: LaunchSandbox, ready_venv: Path, serve_fake_status: ServeFakeStatus
) -> None:
    """常駐サーバーを起動できなければ、理由を示して Claude Code を立てない（異常系）。"""
    # 準備
    serve_fake_status(sandbox.port, 404, None)
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert f"ポート {sandbox.port} は別のプロセスが使っています" in result.stderr
    assert "MINDSTELLA_PORT" in result.stderr
    assert (sandbox.sessions(), sandbox.started()) == ([], [])
    assert is_listening(sandbox.port) is True
