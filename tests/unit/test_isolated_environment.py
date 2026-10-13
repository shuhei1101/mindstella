"""tests/conftest.py が手元のフックと許可するホスト名の環境変数を消して走らせることの単体テスト。"""

from __future__ import annotations

import os

import pytest

# テストのプロセスから消えているはずの、配信のフックと許可するホスト名の環境変数
ISOLATED_ENV_NAMES = [
    "MINDSTELLA_PREVIEW_START_HOOK",
    "MINDSTELLA_PREVIEW_STOP_HOOK",
    "MINDSTELLA_ALLOWED_HOSTS",
]


@pytest.mark.parametrize("name", ISOLATED_ENV_NAMES)
def test_isolated_environment_when_set_in_shell(name: str) -> None:
    """手元のシェルに設定してあっても、テストのプロセスの環境変数に無い（正常系）。"""
    # 実行
    value = os.environ.get(name)

    # 検証
    assert value is None
