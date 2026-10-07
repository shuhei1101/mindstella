"""直下の README.md を確かめる E2E テストの共有の補助（書き方はインターフェース定義『README の書き出し』の制約「README の中身」）。"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from launch_fixtures import PLUGIN_DIR, session_name

__all__ = [
    "PREVIEW_HINT",
    "README_MARK",
    "assert_readme_commands",
    "preview_section",
]

# README の 1 行目の、自動で書いた印
README_MARK = "<!-- mindstella:readme -->"

# 配っていないときにプレビューの節へ書く行
PREVIEW_HINT = "`/mindstella:session` でプレビューを頼むと URL が表示されます。"

# コマンドの節の、太字の見出し・短い説明・`bash` のコードブロックの 3 つ組
COMMAND_PATTERN = re.compile(r"\*\*(.+?):\*\*\n\n(.+?)\n\n```bash\n(.+?)\n```")

# コマンドの見出しの並び
COMMAND_LABELS = ["起動", "接続", "セッション", "セットアップ", "アップグレード"]


def preview_section(text: str) -> str:
    """README の `## プレビュー` の節（次の `## ` の見出しの手前まで）を返す。"""
    return text.split("## プレビュー\n", 1)[1].split("\n## ", 1)[0]


def assert_readme_commands(root: Path, text: str) -> None:
    """README が、このフォルダの起動・接続のコマンドとスキルの呼び方の一覧であることを確かめる。"""
    resolved = root.resolve()
    assert text.splitlines()[0] == README_MARK
    commands = COMMAND_PATTERN.findall(
        text.split("## コマンド\n", 1)[1].split("\n## ", 1)[0]
    )
    assert [label for label, _description, _command in commands] == COMMAND_LABELS
    assert [shlex.split(command) for _label, _description, command in commands] == [
        [str(PLUGIN_DIR / "bin" / "mindstella"), str(resolved)],
        ["tmux", "attach-session", "-t", f"={session_name(resolved)}"],
        ["/mindstella:session", str(resolved)],
        ["/mindstella:setup", str(resolved)],
        ["/mindstella:upgrade", str(resolved)],
    ]
