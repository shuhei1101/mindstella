"""mindstella の MCP サーバー。ワークスペースを読み書きするツールを登録し、stdio で動かす。

起動スクリプトが書いた MCP の設定で、Claude Code が `{仮想環境の Python} server.py` として立てる。
標準出力は MCP の JSON-RPC が使うので、記録は `logging` で標準エラーへ書く。
"""

import json
import logging
import os
import signal
import sys
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent
from pydantic import Field

import commands
from claude_input import load_input_target
from errors import MindmapError, SchemaMismatchError
from kinds import Kind
from query import DEFAULT_LIMIT, MAX_LIMIT, SearchFilter, parse_attr
from serve import PreviewRegistry, load_external_access
from migrator import require_migratable
from store import LEGACY_HINT, require_workspace, workspace_lock

# MCP サーバーの名前。Claude Code の中のツールの名前は `mcp__mindstella__{ツール}` になる
SERVER_NAME = "mindstella"

# 登録するツールの名前の並び
TOOL_NAMES = (
    "init",
    "add",
    "update",
    "remove",
    "update_settings",
    "adopt",
    "edit_option",
    "batch",
    "changes_since_read",
    "commit",
    "pending",
    "status",
    "next",
    "impact",
    "find",
    "show",
    "attrs",
    "tags",
    "check",
    "goal",
    "migrate",
    "clear_release",
    "export",
    "preview_url",
    "readme",
    "threads",
    "thread",
    "new_thread",
    "reply",
    "set_thread_status",
    "update_thread",
)

# `MindmapError` でない例外をツールのエラーにするときの文言
UNEXPECTED_ERROR = "予期しないエラー（{type}）: {message}"

# ツールの引数の型（入力のスキーマに説明が載る）
type WorkspaceArg = Annotated[str, Field(description="ワークスペースのフォルダのパス")]
type ItemIdArg = Annotated[str, Field(description="項目の ID（例 D-1）")]

logger = logging.getLogger(__name__)


def main(
    build: Callable[..., MCPServer] | None = None, *, environ: Mapping[str, str] | None = None
) -> int:
    """MCP サーバーを組み立てて stdio で動かし、標準入力が閉じるか SIGTERM を受けたら、終了時のフックを呼んで配信を止めて終える。"""
    # 標準出力は MCP が使うので、記録は標準エラーへ書く
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    write_lock = threading.Lock()
    source = os.environ if environ is None else environ
    external = load_external_access(source)
    # Claude Code から受け継いだ tmux のペインと会話の記録の場所（tmux の外なら入力しない）
    input_target = load_input_target(source, Path.cwd())
    previews = PreviewRegistry(write_lock, external=external, input_target=input_target)
    install_sigterm_handler(previews)
    server = (build or build_server)(previews=previews, write_lock=write_lock, cwd=Path.cwd())
    try:
        server.run("stdio")
    finally:
        # run が例外で戻ったときも、立てた配信を止める（終了時のフックもここで呼ぶ）
        previews.stop_all()
    return 0


def install_sigterm_handler(previews: PreviewRegistry) -> None:
    """SIGTERM を受けたら配信の台帳を止めて終わる受け口を置く（Claude Code は標準入力を閉じずに SIGTERM を送る）。"""

    def _handle(signum: int, frame: object) -> None:
        """配信を止め、記録を書き出してから、終了コード 0 で終わる。"""
        previews.stop_all()
        logger.info("SIGTERM を受けて配信を止めた")
        logging.shutdown()
        # SystemExit では終えない。標準入力が開いたままだと、MCP の SDK が標準入力を読む作業スレッド（daemon でない）をインタープリタの終わりが待ち続け、プロセスが残る
        os._exit(0)

    signal.signal(signal.SIGTERM, _handle)


def build_server(*, previews: PreviewRegistry, write_lock: threading.Lock, cwd: Path) -> MCPServer:
    """`TOOL_NAMES` のツールを登録した MCP サーバーを作る。"""
    server = MCPServer(SERVER_NAME)

    def read(workspace: str, run: Callable[[Path], dict[str, Any]]) -> CallToolResult:
        """ワークスペースを読むだけのツールの処理を、鍵を取らずに呼ぶ。"""
        root = resolve_workspace(workspace, cwd)
        return call_tool(lambda: run(root), write_lock=write_lock)

    def write(
        workspace: str,
        run: Callable[[Path], dict[str, Any]],
        *,
        create: bool = False,
        require: Callable[[Path], None] = require_workspace,
    ) -> CallToolResult:
        """ワークスペースを書き換えるツールの処理を、書き換えの鍵を取って呼ぶ。"""
        root = resolve_workspace(workspace, cwd)
        return call_tool(
            lambda: run(root),
            write_lock=write_lock,
            lock_root=root,
            lock_create=create,
            lock_require=require,
        )

    @server.tool(name="init", description="設定を受け取って空のワークスペースを作る")
    def init(
        workspace: WorkspaceArg,
        settings: Annotated[dict[str, Any], Field(description=".mindstella/config.yaml の中身")],
    ) -> CallToolResult:
        # まだ無いフォルダへ書く `init` だけが、フォルダを作る鍵を取る
        return write(workspace, lambda root: commands.run_init(root, settings), create=True)

    @server.tool(name="add", description="項目を 1 つ足す（ID・日時・本文を付ける）")
    def add(
        workspace: WorkspaceArg,
        kind: Annotated[Kind, Field(description="足す項目の種類")],
        item: Annotated[
            dict[str, Any],
            Field(
                description="項目の中身。本文は body_markdown（資料だけ body_html で HTML の本文も書ける）"
            ),
        ],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_add(root, kind, item))

    @server.tool(name="update", description="項目 1 つのキーを置き換える")
    def update(
        workspace: WorkspaceArg,
        id: ItemIdArg,
        item: Annotated[dict[str, Any], Field(description="置き換えるキーと値。null で消す")],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_update(root, id, item))

    @server.tool(
        name="remove",
        description="項目 1 つを消す（本文も消し、消した項目をまだまとめていない変更に残す）。ほかの記録が指している項目は消さずにエラーにする。やめた項目を残すときは update で取り下げる",
    )
    def remove(
        workspace: WorkspaceArg,
        id: ItemIdArg,
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_remove(root, id))

    @server.tool(
        name="update_settings",
        description="設定（題名・話し合いの概要・プレイブック・フェーズ・最上位の軸の呼び名・ゴール・対象・カテゴリー・タグの語彙・関連する場所・保持する回数）を書き換える。フェーズ・対象・カテゴリー・タグの語彙を変えるときは項目とスレッドの付け替えもする",
    )
    def update_settings(
        workspace: WorkspaceArg,
        settings: Annotated[
            dict[str, Any],
            Field(
                description="置き換える設定のキーと値。description・goal・tags・links・history_limit は null で消す。tags は name と任意の summary を持つタグの配列で、語彙を丸ごと置き換える"
            ),
        ],
        phase_map: Annotated[
            dict[str, str] | None,
            Field(description="古いフェーズ → 新しいフェーズの対応。phases を変えるときだけ渡す"),
        ] = None,
        target_map: Annotated[
            dict[str, str] | None,
            Field(description="古い対象 → 新しい対象の対応。targets を変えるときだけ渡す"),
        ] = None,
        category_map: Annotated[
            dict[str, str] | None,
            Field(
                description="古いカテゴリー → 新しいカテゴリーの対応。categories を変えるときだけ渡す"
            ),
        ] = None,
        tag_map: Annotated[
            dict[str, str | None] | None,
            Field(
                description="古いタグ → 新しいタグの対応（null で外す）。tags を変えるときだけ渡す"
            ),
        ] = None,
    ) -> CallToolResult:
        return write(
            workspace,
            lambda root: commands.run_update_settings(
                root, settings, phase_map, target_map, category_map, tag_map
            ),
        )

    @server.tool(
        name="adopt", description="検討事項の採用する案を 1 つに切り替え、状態を決定済みにする"
    )
    def adopt(
        workspace: WorkspaceArg,
        id: ItemIdArg,
        key: Annotated[str, Field(description="採用する案の記号")],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_adopt(root, id, key))

    @server.tool(
        name="edit_option",
        description="検討事項の案を記号で指して、1 つ足す・中身と推奨の印を直す・消す。指さない案はそのまま残る",
    )
    def edit_option(
        workspace: WorkspaceArg,
        id: ItemIdArg,
        action: Annotated[
            Literal["add", "update", "remove"],
            Field(description="add は末尾に足す、update は指した案を直す、remove は指した案を消す"),
        ],
        key: Annotated[str, Field(description="案の記号。add では足す案、update・remove では指す案")],
        option: Annotated[
            dict[str, Any] | None,
            Field(
                description="add・update の案の中身（content・pros・cons・note・reason・recommended）。recommended は true で推奨の印を立て（ほかの案の印は外れる）、false か null で外す。update は null のキーを消す。remove では渡さない"
            ),
        ] = None,
    ) -> CallToolResult:
        return write(
            workspace, lambda root: commands.run_edit_option(root, id, action, key, option)
        )

    @server.tool(
        name="batch",
        description="項目の追加・更新・取得の操作を並べた順に 1 回で当てる。全てを当ててから 1 回だけ書き、1 つでも失敗したら何も書かない。先に足した項目は $番号（add の番号、1 始まり）で指せる",
    )
    def batch(
        workspace: WorkspaceArg,
        operations: Annotated[
            list[dict[str, Any]],
            Field(
                description="当てる操作の並び。要素は op（add・update・show）と、add は kind・item、update は id・item、show は id"
            ),
        ],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_batch(root, operations))

    @server.tool(
        name="changes_since_read",
        description="AI が最後に読んだ時点より後に足した・変えた項目を、変わったキーと読んだ時点の値つきで返し、読んだ時点を今に進める",
    )
    def changes_since_read(workspace: WorkspaceArg) -> CallToolResult:
        return write(workspace, commands.run_changes_since_read)

    @server.tool(
        name="commit",
        description="まだまとめていない書き換えを、日時と一言の説明を付けた 1 つのまとまりにする",
    )
    def commit(
        workspace: WorkspaceArg,
        summary: Annotated[
            str, Field(description="このまとまりで何をしたかの一言の説明（1〜200 文字）")
        ],
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_commit(root, summary))

    @server.tool(
        name="pending", description="まだまとめていない変更（足した項目・変えた項目とキー・消した項目）を返す"
    )
    def pending(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_pending)

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
    def impact(workspace: WorkspaceArg, id: ItemIdArg) -> CallToolResult:
        return read(workspace, lambda root: commands.run_impact(root, id))

    @server.tool(
        name="find",
        description="文字・種類・状態・タグ・対象・カテゴリー・フェーズ・属性の条件に合う項目を、ページに分けて返す。タグは語彙のタグだけを受け付ける。使える絞り込みは text・kind・status・tags・any_tags・target・category・phase・attr。タグで絞る前に tags で語彙を引く。全体の件数が 1 ページより多いときは next_cursor を同じ条件で cursor に渡して続きを読む",
    )
    def find(
        workspace: WorkspaceArg,
        text: str | None = None,
        kind: Kind | None = None,
        status: str | None = None,
        tags: Annotated[
            list[str] | None, Field(description="全てを持つ項目に絞るタグ（AND）。語彙のタグだけ")
        ] = None,
        any_tags: Annotated[
            list[str] | None, Field(description="いずれかを持つ項目に絞るタグ（OR）。語彙のタグだけ")
        ] = None,
        target: str | None = None,
        category: str | None = None,
        phase: str | None = None,
        attr: Annotated[
            list[str] | None, Field(description="`名前=値`（`名前` だけならその属性を持つ項目）")
        ] = None,
        limit: Annotated[
            int, Field(description=f"1 ページに返す件数（1〜{MAX_LIMIT}）")
        ] = DEFAULT_LIMIT,
        cursor: Annotated[
            str | None,
            Field(description="前のページの next_cursor。前のページと同じ条件で渡す"),
        ] = None,
        response_format: Annotated[
            Literal["concise", "detailed"],
            Field(
                description="返す量。concise は ID・種類・タイトル・状態・タグ、detailed はそれに対象・カテゴリー・フェーズ・属性・更新日時を足す"
            ),
        ] = "concise",
    ) -> CallToolResult:
        search_filter = SearchFilter(
            text=text,
            kind=kind,
            status=status,
            target=target,
            category=category,
            phase=phase,
            attrs=[parse_attr(entry) for entry in attr or []],
            tags=tuple(tags or []),
            any_tags=tuple(any_tags or []),
        )
        return read(
            workspace,
            lambda root: commands.run_find(
                root,
                search_filter,
                limit=limit,
                cursor=cursor,
                response_format=response_format,
            ),
        )

    @server.tool(name="show", description="項目 1 つの中身・本文・参照元を返す")
    def show(workspace: WorkspaceArg, id: ItemIdArg) -> CallToolResult:
        return read(workspace, lambda root: commands.run_show(root, id))

    @server.tool(name="attrs", description="使っている属性名と件数を返す")
    def attrs(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_attrs)

    @server.tool(
        name="tags",
        description="ワークスペースのタグの語彙を、タグごとの説明と、付いている項目の数・種類を添えて返す。取り込みで話題に合うタグを選ぶためと、find のタグの条件を決めるために、find でタグを渡す前やタグを付ける前に引く",
    )
    def tags(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, commands.run_tags)

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
        # 書き換える `migrate` は、前の版の設定ファイルだけのフォルダにも鍵を取る
        return read(workspace, run) if plan else write(workspace, run, require=require_migratable)

    @server.tool(name="clear_release", description=".mindstella/release/ の中身を消す")
    def clear_release(workspace: WorkspaceArg) -> CallToolResult:
        return write(workspace, commands.run_clear_release)

    @server.tool(name="export", description="見るだけの 1 枚の HTML（配る書き出し）を書き出す")
    def export(
        workspace: WorkspaceArg,
        out: Annotated[str, Field(description="書き出す HTML のパス（.html で終わる）")],
    ) -> CallToolResult:
        out_path = resolve_workspace(out, cwd)
        return read(workspace, lambda root: commands.run_export(root, out_path))

    @server.tool(
        name="preview_url", description="プレビューを配る URL を返す（無ければ配信を立てる）"
    )
    def preview_url(
        workspace: WorkspaceArg,
        diff: Annotated[
            str | None, Field(description="差分を開くまとまりの ID（`commit` の `id`。例 V-3）")
        ] = None,
    ) -> CallToolResult:
        return read(workspace, lambda root: commands.run_preview_url(root, previews=previews, diff=diff))

    @server.tool(
        name="readme",
        description="直下の README.md を、起動・接続のコマンドと配っているプレビューの URL で書き直す",
    )
    def readme(workspace: WorkspaceArg) -> CallToolResult:
        return read(workspace, lambda root: commands.run_readme(root, previews=previews))

    @server.tool(
        name="threads",
        description="スレッドを状態・タグ・未読・取り込み待ちで絞り、本文を含めないキーだけを返す（読むだけ）",
    )
    def threads(
        workspace: WorkspaceArg,
        status: Annotated[
            Literal["open", "closed", "all"] | None,
            Field(
                description="返す状態。省略は、awaiting が偽ならオープンだけ、真ならオープンとクローズの両方"
            ),
        ] = None,
        tag: Annotated[str | None, Field(description="このタグを持つスレッドだけ")] = None,
        unread: Annotated[bool, Field(description="真なら AI の未読の書き込みを持つスレッドだけ")] = False,
        awaiting: Annotated[
            bool, Field(description="真なら AI が取り込んでいない利用者の書き込みを持つスレッドだけ")
        ] = False,
    ) -> CallToolResult:
        return read(workspace, lambda root: commands.run_threads(root, status, tag, unread, awaiting))

    @server.tool(
        name="thread",
        description="スレッド 1 件の書き込みと状態の記録を返し、返した書き込みを AI の既読にする（取り込み済みにはしない）",
    )
    def thread(
        workspace: WorkspaceArg,
        id: Annotated[str, Field(description="スレッドの ID（例 TH-1）")],
        unread_only: Annotated[
            bool, Field(description="真なら AI の未読の書き込みだけ、偽なら全ての書き込み")
        ] = True,
    ) -> CallToolResult:
        root = resolve_workspace(workspace, cwd)
        return call_tool(
            lambda: commands.run_thread(
                root, id, unread_only, lock=lambda: workspace_lock(root, write_lock)
            ),
            write_lock=write_lock,
        )

    @server.tool(
        name="new_thread",
        description="AI から利用者へ返事を求めるスレッドを立てる（最初の書き込みは AI の本文）",
    )
    def new_thread(
        workspace: WorkspaceArg,
        body: Annotated[str, Field(description="最初の書き込みの本文（1〜10000 文字）")],
        summary: Annotated[str, Field(description="スレッドの要約（1〜400 文字）")],
        tags: Annotated[list[str] | None, Field(description="付けるタグ")] = None,
        target: Annotated[str | None, Field(description="向ける項目の ID")] = None,
    ) -> CallToolResult:
        return write(
            workspace, lambda root: commands.run_new_thread(root, body, summary, tags, target)
        )

    @server.tool(
        name="reply",
        description="オープンのスレッドに AI の返信を足し、要約を書き直し、既読にした利用者の書き込みを取り込み済みにする",
    )
    def reply(
        workspace: WorkspaceArg,
        id: Annotated[str, Field(description="スレッドの ID")],
        body: Annotated[str, Field(description="返信の本文（1〜10000 文字）")],
        summary: Annotated[str, Field(description="書き直した要約（1〜400 文字）")],
        take: Annotated[
            bool, Field(description="真なら既読にした取り込んでいない利用者の書き込みを取り込み済みにする")
        ] = True,
    ) -> CallToolResult:
        return write(workspace, lambda root: commands.run_reply(root, id, body, summary, take))

    @server.tool(
        name="set_thread_status",
        description="AI がスレッドをクローズにするかオープンに戻し、理由を残す",
    )
    def set_thread_status(
        workspace: WorkspaceArg,
        id: Annotated[str, Field(description="スレッドの ID")],
        status: Annotated[Literal["open", "closed"], Field(description="変えた後の状態")],
        reason: Annotated[str | None, Field(description="状態を変える理由（400 文字まで）")] = None,
    ) -> CallToolResult:
        return write(
            workspace, lambda root: commands.run_set_thread_status(root, id, status, reason)
        )

    @server.tool(
        name="update_thread",
        description="スレッドの要約とタグを書き換え、既読にした利用者の書き込みを取り込み済みにする（クローズのスレッドも書き換える）",
    )
    def update_thread(
        workspace: WorkspaceArg,
        id: Annotated[str, Field(description="スレッドの ID")],
        summary: Annotated[str | None, Field(description="書き直した要約（1〜400 文字）")] = None,
        tags: Annotated[
            list[str] | None, Field(description="置き換えるタグ。空の一覧でタグを外す")
        ] = None,
        take: Annotated[
            bool, Field(description="真なら既読にした取り込んでいない利用者の書き込みを取り込み済みにする")
        ] = False,
    ) -> CallToolResult:
        return write(
            workspace, lambda root: commands.run_update_thread(root, id, summary, tags, take)
        )

    return server


def call_tool(
    handler: Callable[[], dict[str, Any]],
    *,
    write_lock: threading.Lock,
    lock_root: Path | None = None,
    lock_create: bool = False,
    lock_require: Callable[[Path], None] = require_workspace,
) -> CallToolResult:
    """ツールの処理を呼び、結果を構造化の結果に、エラーをツールのエラーにする。"""
    try:
        if lock_root is not None:
            # 書き換えるツール: 読む前から書き終えるまで鍵を持つ
            with workspace_lock(
                lock_root, write_lock, create=lock_create, require=lock_require
            ):
                payload = handler()
        else:
            payload = handler()
    except MindmapError as error:
        return error_result(error)
    except Exception as error:
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
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))], is_error=True)


def resolve_workspace(path: str, cwd: Path) -> Path:
    """ツールに渡されたパスを、作業フォルダを基準にした絶対パスにする。"""
    expanded = Path(path).expanduser()
    return expanded if expanded.is_absolute() else cwd / expanded


if __name__ == "__main__":
    sys.exit(main())
