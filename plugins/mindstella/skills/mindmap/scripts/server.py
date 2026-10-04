"""mindstella の MCP サーバー。ワークスペースを読み書きするツールを登録し、stdio で動かす。

起動スクリプトが書いた MCP の設定で、Claude Code が `{仮想環境の Python} server.py` として立てる。
標準出力は MCP の JSON-RPC が使うので、記録は `logging` で標準エラーへ書く。
"""

import json
import logging
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent
from pydantic import Field

import commands
from errors import MindmapError, SchemaMismatchError
from kinds import Kind
from query import SearchFilter, parse_attr
from serve import PreviewRegistry
from store import LEGACY_HINT, workspace_lock

# MCP サーバーの名前。Claude Code の中のツールの名前は `mcp__mindstella__{ツール}` になる
SERVER_NAME = "mindstella"

# 登録するツールの名前の並び
TOOL_NAMES = (
    "init",
    "add",
    "update",
    "adopt",
    "status",
    "next",
    "impact",
    "find",
    "show",
    "attrs",
    "check",
    "goal",
    "migrate",
    "clear_release",
    "export",
    "preview_url",
    "submissions",
    "take_submission",
)

# `MindmapError` でない例外をツールのエラーにするときの文言
UNEXPECTED_ERROR = "予期しないエラー（{type}）: {message}"

# ツールの引数の型（入力のスキーマに説明が載る）
type WorkspaceArg = Annotated[str, Field(description="ワークスペースのフォルダのパス")]
type ItemIdArg = Annotated[str, Field(description="項目の ID（例 D-1）")]

logger = logging.getLogger(__name__)


def main(build: Callable[..., MCPServer] | None = None) -> int:
    """MCP サーバーを組み立てて stdio で動かし、標準入力が閉じたら配信を止めて終える。"""
    # 標準出力は MCP が使うので、記録は標準エラーへ書く
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    write_lock = threading.Lock()
    previews = PreviewRegistry(write_lock)
    server = (build or build_server)(previews=previews, write_lock=write_lock, cwd=Path.cwd())
    try:
        server.run("stdio")
    finally:
        # run が例外で戻ったときも、立てた配信を止める
        previews.stop_all()
    return 0


def build_server(*, previews: PreviewRegistry, write_lock: threading.Lock, cwd: Path) -> MCPServer:
    """`TOOL_NAMES` のツールを登録した MCP サーバーを作る。"""
    server = MCPServer(SERVER_NAME)

    def read(workspace: str, run: Callable[[Path], dict[str, Any]]) -> CallToolResult:
        """ワークスペースを読むだけのツールの処理を、鍵を取らずに呼ぶ。"""
        root = resolve_workspace(workspace, cwd)
        return call_tool(lambda: run(root), write_lock=write_lock)

    def write(workspace: str, run: Callable[[Path], dict[str, Any]]) -> CallToolResult:
        """ワークスペースを書き換えるツールの処理を、書き換えの鍵を取って呼ぶ。"""
        root = resolve_workspace(workspace, cwd)
        return call_tool(lambda: run(root), write_lock=write_lock, lock_root=root)

    @server.tool(name="init", description="設定を受け取って空のワークスペースを作る")
    def init(
        workspace: WorkspaceArg,
        settings: Annotated[dict[str, Any], Field(description="mindmap.yaml の中身")],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_init(root, settings))

    @server.tool(name="add", description="項目を 1 つ足す（ID・日時・本文を付ける）")
    def add(
        workspace: WorkspaceArg,
        kind: Annotated[Kind, Field(description="足す項目の種類")],
        item: Annotated[dict[str, Any], Field(description="項目の中身。本文は body_markdown")],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_add(root, kind, item))

    @server.tool(name="update", description="項目 1 つのキーを置き換える")
    def update(
        workspace: WorkspaceArg,
        id: ItemIdArg,  # noqa: A002
        item: Annotated[dict[str, Any], Field(description="置き換えるキーと値。null で消す")],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_update(root, id, item))

    @server.tool(name="adopt", description="検討事項の採用する案を 1 つに切り替える")
    def adopt(
        workspace: WorkspaceArg,
        id: ItemIdArg,  # noqa: A002
        key: Annotated[str, Field(description="採用する案の記号")],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_adopt(root, id, key))

    @server.tool(name="status", description="再開時の状況（要見直し・進行中・再開可能など）を返す")
    def status(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_status)

    @server.tool(name="next", description="前提が揃った未決定を決める順に返す")
    def next_candidates(
        workspace: WorkspaceArg,
        limit: Annotated[int | None, Field(description="返す件数の上限（1 以上）")] = None,
    ) -> CallToolResult:
        return read(workspace, lambda root: commands.run_next(root, limit))

    @server.tool(name="impact", description="参照を逆向きにたどって影響を受ける項目を返す")
    def impact(workspace: WorkspaceArg, id: ItemIdArg) -> CallToolResult:  # noqa: A002
        return read(workspace, lambda root: commands.run_impact(root, id))

    @server.tool(name="find", description="条件に合う項目を返す")
    def find(
        workspace: WorkspaceArg,
        text: str | None = None,
        kind: Kind | None = None,
        status: str | None = None,
        tag: str | None = None,
        target: str | None = None,
        category: str | None = None,
        phase: str | None = None,
        attr: Annotated[
            list[str] | None, Field(description="`名前=値`（`名前` だけならその属性を持つ項目）")
        ] = None,
    ) -> CallToolResult:
        search_filter = SearchFilter(
            text=text,
            kind=kind,
            status=status,
            tag=tag,
            target=target,
            category=category,
            phase=phase,
            attrs=[parse_attr(entry) for entry in attr or []],
        )
        return read(workspace, lambda root: commands.run_find(root, search_filter))

    @server.tool(name="show", description="項目 1 つの中身・本文・参照元を返す")
    def show(workspace: WorkspaceArg, id: ItemIdArg) -> CallToolResult:  # noqa: A002
        return read(workspace, lambda root: commands.run_show(root, id))

    @server.tool(name="attrs", description="使っている属性名と件数を返す")
    def attrs(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_attrs)

    @server.tool(name="check", description="スキーマ違反・参照切れ・本文のずれを洗い出す")
    def check(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_check)

    @server.tool(name="goal", description="ゴールに届いたかと、残りの項目を返す")
    def goal(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_goal)

    @server.tool(
        name="migrate",
        description="ワークスペースの版とプラグインの版を比べ、版ごとの手順を並べる・当てる・版を書く",
    )
    def migrate(
        workspace: WorkspaceArg,
        plan: Annotated[bool, Field(description="当てずに、版を比べた結果を返す")] = False,
        from_version: Annotated[str | None, Field(description="この版より後の手順を当てる")] = None,
        to_version: Annotated[str | None, Field(description="この版以下の手順を当てる")] = None,
        values: Annotated[
            list[dict[str, Any]] | None,
            Field(description="値が要るキーに入れる値。要素は file・key・value"),
        ] = None,
        record: Annotated[bool, Field(description="点検して、版のファイルを書き換える")] = False,
    ) -> CallToolResult:
        def run(root: Path) -> dict[str, Any]:
            return commands.run_migrate(
                root,
                plan=plan,
                record=record,
                values=values,
                from_version=from_version,
                to_version=to_version,
            )

        # 並べるだけの `plan` は何も書かないので、鍵を取らない
        return read(workspace, run) if plan else write(workspace, run)

    @server.tool(name="clear_release", description="release/ の中身を消す")
    def clear_release(workspace: WorkspaceArg) -> CallToolResult:
        return write(workspace, commands.run_clear_release)

    @server.tool(name="export", description="見るだけの 1 枚の HTML（配る書き出し）を書き出す")
    def export(
        workspace: WorkspaceArg,
        out: Annotated[str, Field(description="書き出す HTML のパス（.html で終わる）")],
    ) -> CallToolResult:
        out_path = resolve_workspace(out, cwd)
        return read(workspace, lambda root: commands.run_export(root, out_path))

    @server.tool(name="preview_url", description="プレビューを配る URL を返す（無ければ配信を立てる）")
    def preview_url(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, lambda root: commands.run_preview_url(root, previews=previews))

    @server.tool(name="submissions", description="取り込んでいない送信を送った順に返す")
    def submissions(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_submissions)

    @server.tool(name="take_submission", description="送信 1 件を取り込み済みにする")
    def take_submission(
        workspace: WorkspaceArg,
        id: Annotated[str, Field(description="送信の ID（例 S-1）")],  # noqa: A002
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_take_submission(root, id))

    return server


def call_tool(
    handler: Callable[[], dict[str, Any]],
    *,
    write_lock: threading.Lock,
    lock_root: Path | None = None,
) -> CallToolResult:
    """ツールの処理を呼び、結果を構造化の結果に、エラーをツールのエラーにする。"""
    try:
        if lock_root is not None:
            # 書き換えるツール: 読む前から書き終えるまで鍵を持つ
            with workspace_lock(lock_root, write_lock):
                payload = handler()
        else:
            payload = handler()
    except MindmapError as error:
        return error_result(error)
    except Exception as error:  # noqa: BLE001
        # 想定していない例外: トレースバックは記録に残し、利用者には文言だけ返す
        logger.exception("ツールの予期しないエラー")
        message = UNEXPECTED_ERROR.format(type=type(error).__name__, message=error)
        return error_result(MindmapError(message))
    return ok_result(payload)


def ok_result(payload: dict[str, Any]) -> CallToolResult:
    """辞書を、構造化の結果と同じ JSON の本文を持つ結果にする。"""
    text = json.dumps(payload, ensure_ascii=False)
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=payload)


def error_result(error: MindmapError) -> CallToolResult:
    """`MindmapError` を、`エラー: {内容}` で始まる本文のツールのエラーにする。"""
    lines = [f"エラー: {error}", *error.lines]
    # 前の版の形式のスキーマ違反: 移し替えのスキルを案内する
    if isinstance(error, SchemaMismatchError) and error.legacy:
        lines.append(LEGACY_HINT)
    return CallToolResult(
        content=[TextContent(type="text", text="\n".join(lines))], is_error=True
    )


def resolve_workspace(path: str, cwd: Path) -> Path:
    """ツールに渡されたパスを、作業フォルダを基準にした絶対パスにする。"""
    expanded = Path(path).expanduser()
    return expanded if expanded.is_absolute() else cwd / expanded


if __name__ == "__main__":
    sys.exit(main())
