"""起動時に受け継いだ TMUX・TMUX_PANE をファイルへ書き、許可の確認を出すツールを 1 つ持つスタブの MCP サーバー。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

# 受け継いだ環境のうち書き出す変数
ENV_KEYS = ("TMUX", "TMUX_PANE", "MINDSTELLA_ALLOWED_HOSTS")

server = MCPServer("pocstub")


@server.tool()
def probe(note: str) -> str:
    """許可の確認を出させるためだけのツール。受け取った文字列をそのまま返す。"""
    return f"probe: {note}"


def main() -> None:
    """環境を書き出してから stdio で待ち受ける。"""
    out = Path(sys.argv[1])
    out.write_text(
        json.dumps({key: os.environ.get(key) for key in ENV_KEYS}, ensure_ascii=False),
        encoding="utf-8",
    )
    server.run("stdio")


if __name__ == "__main__":
    main()
