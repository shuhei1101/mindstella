"""直下の README.md の結合テストが使う、期待する中身の組み立てと、見出しごとの切り出し（インターフェース定義『README の書き出し』の制約「README の中身」）。"""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path

from workspace_fixtures import REPO_ROOT

# README の 1 行目の、自動で書いた印
README_MARK = "<!-- mindstella:readme -->"

# 配信していないときにプレビューの節へ書く行
PREVIEW_HINT = "`/mindstella:session` でプレビューを頼むと URL が表示されます。"

# サーバーのプラグインのフォルダ（テストが動かす server.py の 3 つ上）
PLUGIN_DIR = REPO_ROOT / "plugins" / "mindstella"

# セッションの名前の頭と、絶対パスの SHA-256 から取る桁数
SESSION_PREFIX = "mindstella-"
HASH_DIGITS = 6


def session_name_of(root: Path) -> str:
    """起動スクリプトが立てる tmux のセッションの名前（`mindstella-{フォルダ名}-{ハッシュ}`）を作る。"""
    resolved = root.resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:HASH_DIGITS]
    name = resolved.name.replace(".", "-").replace(":", "-")
    return f"{SESSION_PREFIX}{name}-{digest}"


def expected_readme(root: Path, *, preview_url: str | None = None) -> str:
    """制約「README の中身」の形に、プラグインのフォルダ・絶対パス・セッションの名前を埋めた README を作る。"""
    resolved = root.resolve()
    folder = shlex.quote(str(resolved))
    launch = shlex.quote(str(PLUGIN_DIR / "bin" / "mindstella"))
    session = shlex.quote(session_name_of(root))
    return f"""{README_MARK}
# {resolved.name}

mindstella の話し合いのワークスペースです。記録は `.mindstella/` にあり、プレビューで読みます。
このファイルは `/mindstella:session` を始めるたびに書き直されます。

## プレビュー

{preview_url or PREVIEW_HINT}

URL は起動のたびに変わります。

## コマンド

**起動:**

このフォルダで Claude Code を立ち上げます。

```bash
{launch} {folder}
```

**接続:**

立ち上げ済みのセッションにつなぎ直します。

```bash
tmux attach-session -t ={session}
```

**セッション:**

立ち上げた Claude Code で、話し合いを進めます。

```bash
/mindstella:session {folder}
```

**セットアップ:**

立ち上げた Claude Code で、状況を確かめて話し合いを始めます。

```bash
/mindstella:setup {folder}
```

**アップグレード:**

プラグインを上げた後、記録を今の版へ移し替えます。

```bash
/mindstella:upgrade {folder}
```

## ドキュメント

- [プレビューを見る](https://shuhei1101.github.io/mindstella/使い方/プレビューを見る.html)
- [起動スクリプトで立ち上げる](https://shuhei1101.github.io/mindstella/使い方/セットアップ手順/起動スクリプトで立ち上げる.html)
"""


def section_of(text: str, heading: str) -> str:
    """`## ` の見出しから、次の `## ` の見出しの手前までを返す。"""
    return text.split(f"{heading}\n", 1)[1].split("\n## ", 1)[0]
