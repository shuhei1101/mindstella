"""ワークスペースの直下の `README.md`（起動・接続のコマンド、スキルの呼び方、プレビューの URL）の組み立てと書き込み。"""

from __future__ import annotations

import os
import shlex
import uuid
from pathlib import Path

from errors import WriteFailedError
from launch import session_name

# ワークスペースの直下に書くファイルの名前
README_FILE = "README.md"

# サーバーが書いた README の 1 行目。この行で始まる README だけを書き直す
README_MARK = "<!-- mindstella:readme -->"

# `readme.py` から見たプラグインのフォルダまでの階層（scripts → mindmap → skills → プラグイン）
PLUGIN_DIR_DEPTH = 3

# 動いているサーバーのプラグインのフォルダ（起動のコマンドに使う）
PLUGIN_DIR = Path(__file__).resolve().parents[PLUGIN_DIR_DEPTH]

# プラグインのフォルダからの起動スクリプトのパス
LAUNCH_SCRIPT = "bin/mindstella"

# プレビューの節に、URL の代わりに書く行
PREVIEW_HINT = "`/mindstella:session` でプレビューを頼むと URL が表示されます。"

# ドキュメントの節に並べる題名と URL
DOC_LINKS = (
    ("プレビューを見る", "https://shuhei1101.github.io/mindstella/使い方/プレビューを見る.html"),
    (
        "起動スクリプトで立ち上げる",
        "https://shuhei1101.github.io/mindstella/使い方/セットアップ手順/起動スクリプトで立ち上げる.html",
    ),
)

# 書き込む前に置く一時ファイルの拡張子（README と同じフォルダに作る）
TEMP_SUFFIX = ".tmp"


def render_readme(root: Path, *, plugin_dir: Path, preview_url: str | None) -> str:
    """1 行目が `README_MARK` で、プレビュー・コマンド・ドキュメントの節を持つ README の Markdown を作る。"""
    resolved = root.resolve()
    # コマンドに埋めるパスは、空白などを含んでもそのまま叩けるよう引用する
    folder = shlex.quote(str(resolved))
    launch_script = shlex.quote(str(plugin_dir / LAUNCH_SCRIPT))
    session = shlex.quote(session_name(resolved))
    # 見出し・短い説明・コマンドの 3 つ組を、起動・接続・セッション・セットアップ・アップグレードの順に並べる
    commands = (
        ("起動", "このフォルダで Claude Code を立ち上げます。", f"{launch_script} {folder}"),
        (
            "接続",
            "立ち上げ済みのセッションにつなぎ直します。",
            f"tmux attach-session -t ={session}",
        ),
        (
            "セッション",
            "立ち上げた Claude Code で、話し合いを進めます。",
            f"/mindstella:session {folder}",
        ),
        (
            "セットアップ",
            "立ち上げた Claude Code で、状況を確かめて話し合いを始めます。",
            f"/mindstella:setup {folder}",
        ),
        (
            "アップグレード",
            "プラグインを上げた後、記録を今の版へ移し替えます。",
            f"/mindstella:upgrade {folder}",
        ),
    )
    lines = [
        README_MARK,
        f"# {resolved.name}",
        "",
        "mindstella の話し合いのワークスペースです。記録は `.mindstella/` にあり、プレビューで読みます。",
        "このファイルは `/mindstella:session` を始めるたびに書き直されます。",
        "",
        "## プレビュー",
        "",
        # 配っていれば URL、配っていなければ頼み方の案内
        preview_url or PREVIEW_HINT,
        "",
        "URL は起動のたびに変わります。",
        "",
        "## コマンド",
        "",
    ]
    for label, description, command in commands:
        lines += [f"**{label}:**", "", description, "", "```bash", command, "```", ""]
    lines += ["## ドキュメント", ""]
    lines += [f"- [{title}]({url})" for title, url in DOC_LINKS]
    return "\n".join(lines) + "\n"


def write_readme(
    root: Path, *, preview_url: str | None = None, plugin_dir: Path = PLUGIN_DIR
) -> bool:
    """直下に `README.md` が無いか、自動で書いた印で始まるときだけ、今の値で書いて真を返す。"""
    path = root / README_FILE
    # 印の無い README は利用者のもの: 書かない（UTF-8 で読めないファイルも、権限が無く読めないファイルも利用者のものとして扱う）
    if path.is_file() and not _is_generated(path):
        return False
    text = render_readme(root, plugin_dir=plugin_dir, preview_url=preview_url)
    # 同じフォルダの一時ファイルに書いてから置き換える（同時に書かれても壊れたファイルにならない）
    temp = root / f"{README_FILE}.{uuid.uuid4().hex}{TEMP_SUFFIX}"
    try:
        temp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temp, path)
    except OSError as error:
        # 書けなかった一時ファイルは残さない
        temp.unlink(missing_ok=True)
        raise WriteFailedError(
            f"書き込めませんでした: {path}（{error.strerror or error}）"
        ) from error
    return True


def _is_generated(path: Path) -> bool:
    """README の 1 行目が `README_MARK` か（読めない文字コード・読み取りの権限が無い・空のファイルは偽）。"""
    try:
        first_line = path.read_text(encoding="utf-8").partition("\n")[0]
    except (UnicodeDecodeError, OSError):
        return False
    return first_line == README_MARK
