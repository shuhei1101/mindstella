"""結合テストと E2E テストの共通 fixture。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

# 偽の Claude Code を動かす tmux のペインを立てる fixture
from claude_pane_fixtures import start_claude_pane  # noqa: F401

# 起動スクリプトを隔離して動かす fixture
from launch_fixtures import ready_venv, sandbox  # noqa: F401

# 単体・結合・E2E が共有する fixture（pytest は conftest の名前空間にある fixture を登録する）
from workspace_fixtures import (  # noqa: F401
    call_tool,
    make_comment,
    make_draft,
    make_edit,
    make_item,
    make_legacy_item,
    make_legacy_workspace,
    make_post,
    make_submission,
    make_thread,
    make_venv,
    make_workspace,
    mcp_server,
    snapshot_tree,
    start_server,
    valid_settings,
    write_comments,
    write_drafts,
    write_edits,
    write_submissions,
    write_threads,
)

type RunClaude = Callable[..., subprocess.CompletedProcess[str]]

# claude の 1 コマンドを待つ上限秒数（マーケットプレイスの取り込みを含む）
CLAUDE_COMMAND_TIMEOUT_SEC = 180

# このファイルから見たリポジトリの直下（tests/conftest.py の 1 つ上）
REPO_ROOT_PARENT_DEPTH = 1

# 手元のシェルの値をテストへ持ち込まないよう消す、配信のフックと許可するホスト名の環境変数
ISOLATED_ENV_NAMES = (
    "MINDSTELLA_PREVIEW_START_HOOK",
    "MINDSTELLA_PREVIEW_STOP_HOOK",
    "MINDSTELLA_ALLOWED_HOSTS",
)


@pytest.fixture(scope="session", autouse=True)
def isolate_preview_env() -> Iterator[None]:
    """テスト全体の始まる前に手元のフックと許可するホスト名の環境変数を消し、終わったら戻す。"""
    with pytest.MonkeyPatch.context() as patch:
        for name in ISOLATED_ENV_NAMES:
            patch.delenv(name, raising=False)
        yield


@pytest.fixture
def repo_root() -> Path:
    """マーケットプレイスとして登録するリポジトリの作業ツリーの直下を返す。"""
    return Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]


@pytest.fixture
def run_claude(tmp_path: Path) -> RunClaude:
    """テストごとの空の一時フォルダを設定のフォルダにして claude を実行する関数を返す。"""
    # 利用者の環境を汚さないよう、設定のフォルダをテストごとの空のフォルダに差し替える
    config_dir = tmp_path / "claude-config"
    config_dir.mkdir()
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config_dir)}

    def _run(*args: str) -> subprocess.CompletedProcess[str]:
        """claude にサブコマンドを渡して実行し、終了コードが 0 以外なら例外にする。"""
        return subprocess.run(
            ["claude", *args],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=CLAUDE_COMMAND_TIMEOUT_SEC,
            check=True,
        )

    return _run
