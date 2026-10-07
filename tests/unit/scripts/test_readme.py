"""readme.py（直下の README.md の組み立て・書くかの判定・書き込み）の単体テスト。"""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

import pytest

import launch
import readme
from errors import WriteFailedError

# 自動で書いた印の README を書き直すときの、古い中身の行
OLD_BODY = "古い中身"

# プレビューを配っているときの URL
SERVING_URL = "http://127.0.0.1:43817/mindstella.html"

# コマンドの節の見出し・短い説明・bash のコードブロックの 3 つ組
COMMAND_PATTERN = re.compile(r"\*\*(.+?):\*\*\n\n(.+?)\n\n```bash\n(.+?)\n```")

# 読める README.md の権限
READABLE_MODE = 0o644

# 利用者が書いた README.md の中身と権限（自動で書いた印が無い 4 通り）
USER_READMES = [
    pytest.param("# 家計簿アプリの話し合い\n".encode(), READABLE_MODE, id="user_text"),
    pytest.param(b"", READABLE_MODE, id="empty"),
    pytest.param(b"\xff\xfe\xfa", READABLE_MODE, id="not_utf8"),
    pytest.param(
        "# 読めない README\n".encode(),
        0o000,
        id="unreadable",
        marks=pytest.mark.skipif(
            sys.platform == "win32" or os.geteuid() == 0,
            reason="権限のビットは Windows と root では読み取りを止めない",
        ),
    ),
]


def _headings(text: str) -> list[str]:
    """README の `## ` の見出しを、現れる順に返す。"""
    return [line for line in text.splitlines() if line.startswith("## ")]


def _section(text: str, heading: str) -> str:
    """`## ` の見出しから次の `## ` の見出しの手前までを返す。"""
    return text.split(f"{heading}\n", 1)[1].split("\n## ", 1)[0]


def test_render_readme(tmp_path: Path) -> None:
    """配っていないときの一覧を作る（正常系）。"""
    # 準備
    root = tmp_path / "家計簿アプリ"
    plugin_dir = Path("/p/mindstella/0.7.0")
    # 実行
    text = readme.render_readme(root, plugin_dir=plugin_dir, preview_url=None)
    # 検証
    lines = text.splitlines()
    assert lines[0] == "<!-- mindstella:readme -->"
    assert "# 家計簿アプリ" in lines
    assert _headings(text) == ["## プレビュー", "## コマンド", "## ドキュメント"]
    assert "`/mindstella:session` でプレビューを頼むと URL が表示されます。" in _section(
        text, "## プレビュー"
    )
    assert "http://127.0.0.1" not in text
    commands = COMMAND_PATTERN.findall(_section(text, "## コマンド"))
    assert [label for label, _description, _command in commands] == [
        "起動",
        "接続",
        "セッション",
        "セットアップ",
        "アップグレード",
    ]
    absolute = str(root.resolve())
    assert [shlex.split(command) for _label, _description, command in commands] == [
        ["/p/mindstella/0.7.0/bin/mindstella", absolute],
        ["tmux", "attach-session", "-t", f"={launch.session_name(root)}"],
        ["/mindstella:session", absolute],
        ["/mindstella:setup", absolute],
        ["/mindstella:upgrade", absolute],
    ]
    assert "(https://shuhei1101.github.io/mindstella/使い方/プレビューを見る.html)" in text
    assert (
        "(https://shuhei1101.github.io/mindstella/使い方/セットアップ手順/起動スクリプトで立ち上げる.html)"
        in text
    )


def test_render_readme_when_serving(tmp_path: Path) -> None:
    """配っているときは URL を書く（正常系）。"""
    # 準備
    root = tmp_path / "家計簿アプリ"
    # 実行
    text = readme.render_readme(root, plugin_dir=Path("/p"), preview_url=SERVING_URL)
    # 検証
    assert SERVING_URL in _section(text, "## プレビュー")
    assert "でプレビューを頼むと URL が表示されます" not in text


def test_render_readme_when_path_has_space(tmp_path: Path) -> None:
    """空白を含むパスを引用する（正常系）。"""
    # 準備
    root = tmp_path / "my notes"
    plugin_dir = Path("/p/my plugins/mindstella")
    # 実行
    text = readme.render_readme(root, plugin_dir=plugin_dir, preview_url=None)
    # 検証
    launch_command = COMMAND_PATTERN.findall(_section(text, "## コマンド"))[0][2]
    assert shlex.split(launch_command) == [
        "/p/my plugins/mindstella/bin/mindstella",
        str(root.resolve()),
    ]


def test_write_readme(tmp_path: Path) -> None:
    """README が無ければ書く（正常系）。"""
    # 準備
    plugin_dir = Path("/p")
    # 実行
    written = readme.write_readme(tmp_path, plugin_dir=plugin_dir)
    # 検証
    assert written is True
    expected = readme.render_readme(tmp_path, plugin_dir=plugin_dir, preview_url=None)
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == expected
    assert [path.name for path in tmp_path.iterdir()] == ["README.md"]


def test_write_readme_when_generated(tmp_path: Path) -> None:
    """印で始まる README は書き直す（正常系）。"""
    # 準備
    (tmp_path / "README.md").write_text(
        f"<!-- mindstella:readme -->\n{OLD_BODY}\n", encoding="utf-8"
    )
    url = "http://127.0.0.1:1/mindstella.html"
    # 実行
    written = readme.write_readme(tmp_path, preview_url=url, plugin_dir=Path("/p"))
    # 検証
    assert written is True
    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert OLD_BODY not in text
    assert url in text


@pytest.mark.parametrize(("content", "mode"), USER_READMES)
def test_write_readme_when_user_file(tmp_path: Path, content: bytes, mode: int) -> None:
    """印の無い README は書かない（正常系）。"""
    # 準備
    path = tmp_path / "README.md"
    path.write_bytes(content)
    path.chmod(mode)
    # 実行
    written = readme.write_readme(tmp_path, plugin_dir=Path("/p"))
    # 検証（中身を比べるため、読める権限に戻してから読む）
    path.chmod(READABLE_MODE)
    assert written is False
    assert path.read_bytes() == content


def test_write_readme_when_write_fails(tmp_path: Path) -> None:
    """README.md を書けなければ WriteFailedError を送る（異常系）。"""
    # 準備
    (tmp_path / "README.md").mkdir()
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"README\.md"):
        readme.write_readme(tmp_path, plugin_dir=Path("/p"))
    assert [path.name for path in tmp_path.iterdir()] == ["README.md"]
