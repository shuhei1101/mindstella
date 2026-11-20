"""PoC: 書き出し用のビルドの 1 枚の HTML に、記録と描画のライブラリの中身を差し込む。"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from builder import escape_for_script  # noqa: E402

VENDOR = Path(__file__).resolve().parent / "vendor"
MDMARK_BASE = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@{ref}/dist/{name}"
LIBRARIES = {
    "marked": "https://cdn.jsdelivr.net/npm/marked@18.0.14/lib/marked.umd.js",
    "mermaid": "https://cdn.jsdelivr.net/npm/mermaid@12.1.0/dist/mermaid.min.js",
    "jsdiff": "https://cdn.jsdelivr.net/npm/diff@9.0.0/dist/diff.min.js",
}
MDMARK_FILES = ("index.css", "index.js", "map.js", "view.js", "comments.js")
FONT_LINK = re.compile(r"<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*")


def fetch(url: str, dest: Path) -> str:
    """URL を取り、手元に残す（2 回目からは手元を読む）。"""
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
            dest.write_bytes(response.read())
    return dest.read_text(encoding="utf-8")


def inject(*, built: Path, data: dict[str, Any], out: Path, mdmark_ref: str) -> None:
    """built に記録・mdmark・描画のライブラリを差し込み out へ書く。"""
    html = FONT_LINK.sub("", built.read_text(encoding="utf-8"))
    mdmark = {name: fetch(MDMARK_BASE.format(ref=mdmark_ref, name=name), VENDOR / "mdmark" / name) for name in MDMARK_FILES}
    libs = [fetch(url, VENDOR / f"{name}.js") for name, url in LIBRARIES.items()]
    for text in (*mdmark.values(), *libs):
        if "</script" in text.lower():
            raise ValueError("配布ファイルが </script を含む")
    elements = (
        f'<style id="mindmap-mdmark-css">{mdmark["index.css"]}</style>'
        f'<script type="text/plain" id="mindmap-mdmark">{mdmark["index.js"]}</script>'
        + "".join(f'<script type="text/plain" id="mindmap-mdmark-{n}">{mdmark[f"{n}.js"]}</script>' for n in ("map", "view", "comments"))
        + "".join(f"<script>{text}</script>" for text in libs)
        + f'<script type="application/json" id="mindmap-data">{escape_for_script(json.dumps(data, ensure_ascii=False))}</script>'
    )
    # ビルドの JavaScript が文字列として </body> を持つため、最後の </body> の前に入れる
    end = html.rindex("</body>")
    out.write_text(html[:end] + elements + html[end:], encoding="utf-8")


if __name__ == "__main__":
    inject(built=Path(sys.argv[1]), data=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")), out=Path(sys.argv[3]), mdmark_ref=sys.argv[4])
