"""常駐する mindstella の MCP サーバー。ワークスペースを読み書きするツールを登録し、`127.0.0.1` の HTTP で待ち受ける。

常駐サーバーの起動の確認（`ensure_server.py`）が `{仮想環境の Python} server.py` を新しいセッションで起動する。
プレビューの配信と、常駐サーバーの状態と停止も同じプロセスに持つ。記録は `logging` で標準エラーへ書く。
"""

import json
import logging
import os
import signal
import socket
import sys
import threading
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

import commands
from claude_input import Session, parse_session
from errors import ArgumentError, MindmapError, SchemaMismatchError
from kinds import Kind
from query import DEFAULT_LIMIT, MAX_LIMIT, SearchFilter, parse_attr, render_find_markdown
from serve import LISTEN_HOST, PreviewRegistry, load_external_access
from migrator import require_migratable
from store import LEGACY_HINT, require_workspace, workspace_lock
from versions import PLUGIN_VERSION_FILE, read_plugin_version

# `find` の `include`・`exclude` に渡せる名前
FieldName = Literal[
    "title",
    "status",
    "tags",
    "chars",
    "target",
    "category",
    "phase",
    "attrs",
    "updated",
    "extra",
    "body",
]

# MCP サーバーの名前（`server_status` の `name`）。Claude Code の中のツールの名前は `mcp__plugin_mindstella_mindstella__{ツール}` になる
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
    "server_status",
    "server_stop",
)

# `MINDSTELLA_PORT` が無いか空のときに待ち受けるポート（`ensure_server.py` の同じ名前の定数と合わせる）
DEFAULT_PORT = 8784

# 待ち受けのポートを読む環境変数の名前
PORT_ENV = "MINDSTELLA_PORT"

# ポートの値の範囲
PORT_MIN = 1
PORT_MAX = 65535

# Streamable HTTP で待ち受けるパス（プラグインの `.mcp.json` の URL のパス）
MCP_PATH = "/mcp"

# `server_status` と同じ JSON を返す GET のパス（`ensure_server.py` の同じ名前の定数と合わせる）
STATUS_PATH = "/_admin/status"

# 終わり始めてから、返している途中のレスポンスとつながったままの MCP の通り道を待つ秒数
SHUTDOWN_GRACE_SEC = 2

# `MindmapError` でない例外をツールのエラーにするときの文言
UNEXPECTED_ERROR = "予期しないエラー（{type}）: {message}"

# ツールの引数の型（入力のスキーマに説明が載る）
type WorkspaceArg = Annotated[str, Field(description="ワークスペースのフォルダのパス")]
type ItemIdArg = Annotated[str, Field(description="項目の ID（例 D-1）")]
type SessionArg = Annotated[
    dict[str, Any] | None,
    Field(description="ツールを呼んだセッションの値（PreToolUse のフックが入れる）"),
]

logger = logging.getLogger(__name__)


class InvalidPortError(Exception):
    """`MINDSTELLA_PORT` が 1〜65535 の整数でない。"""

    def __init__(self, value: str) -> None:
        """環境変数の値を持つ。"""
        super().__init__(f"{PORT_ENV} の値 {value} は誤りです。1〜65535 の整数を渡してください")
        self.value = value


class PortInUseError(Exception):
    """`MINDSTELLA_PORT` のポートで待ち受けられない。"""

    def __init__(self, port: int) -> None:
        """待ち受けようとしたポートを持つ。"""
        super().__init__(
            f"ポート {port} は別のプロセスが使っています。{PORT_ENV} で別のポートを渡してください"
        )
        self.port = port


def main(
    build: Callable[..., MCPServer] | None = None,
    *,
    make_server: Callable[[Starlette], uvicorn.Server] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """待ち受けのポートを取り、MCP サーバーを HTTP で動かし、終わり方を受けたら終了時のフックを呼んで配信を止めて終える。"""
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    source = os.environ if environ is None else environ
    # 待ち受けを始める前にポートを取り、使われていれば止まる
    try:
        port = read_port(source)
        listening = bind_socket(port)
    except (InvalidPortError, PortInUseError) as error:
        # 想定した止まり方なので、トレースバックは残さない
        logger.error("常駐サーバーを待ち受けられません: %s", error)  # noqa: TRY400
        return 1

    write_lock = threading.Lock()
    previews = PreviewRegistry(write_lock, external=load_external_access(source))
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    plugin_root = PLUGIN_VERSION_FILE.parent
    version = str(read_plugin_version())

    def status() -> dict[str, Any]:
        """今の常駐サーバーの状態を作る。"""
        return build_status(
            previews, port=port, started_at=started_at, plugin_root=plugin_root, version=version
        )

    def request_stop() -> None:
        """HTTP のサーバーに終わり始めるよう頼む。"""
        http_server.should_exit = True

    mcp_server = (build or build_server)(
        previews=previews, write_lock=write_lock, status=status, request_stop=request_stop
    )
    app = mcp_server.streamable_http_app(streamable_http_path=MCP_PATH, host=LISTEN_HOST)
    http_server = (make_server or _make_http_server)(app)
    logger.info("常駐サーバーが待ち受けを始めた（ポート %s、バージョン %s、PID %s）", port, version, os.getpid())
    # uvicorn は終わり終えてから受けたシグナルを元の受け口へ送り直すので、SIGTERM を SystemExit にして finally まで進める
    previous_sigterm = signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        # 走っている間の SIGTERM・SIGINT の受け口は uvicorn が置き、受けると should_exit を真にする
        http_server.run(sockets=[listening])
    finally:
        # シグナルで終えたときと run が例外で戻ったときも、立てた配信を止める（終了時のフックもここで呼ぶ）
        signal.signal(signal.SIGTERM, previous_sigterm)
        previews.stop_all()
        listening.close()
        logger.info("常駐サーバーを終えた")
    return 0


def _exit_on_sigterm(signum: int, frame: object) -> None:
    """uvicorn が送り直した SIGTERM を、終了コード 0 の SystemExit にする。"""
    raise SystemExit(0)


def _make_http_server(app: Starlette) -> uvicorn.Server:
    """アプリを動かす uvicorn の HTTP のサーバーを作る（記録の設定は `logging` のものを使う）。"""
    return uvicorn.Server(
        uvicorn.Config(app, log_config=None, timeout_graceful_shutdown=SHUTDOWN_GRACE_SEC)
    )


def read_port(environ: Mapping[str, str]) -> int:
    """`MINDSTELLA_PORT` を読み、待ち受けのポートにする（無いか空なら既定のポート）。"""
    value = environ.get(PORT_ENV) or ""
    if not value:
        return DEFAULT_PORT
    try:
        port = int(value)
    except ValueError:
        raise InvalidPortError(value) from None
    if not PORT_MIN <= port <= PORT_MAX:
        raise InvalidPortError(value)
    return port


def bind_socket(port: int) -> socket.socket:
    """`LISTEN_HOST` のポートに bind したソケットを返す（使われていれば PortInUseError）。"""
    listening = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listening.bind((LISTEN_HOST, port))
    except OSError as error:
        listening.close()
        raise PortInUseError(port) from error
    return listening


def build_status(
    previews: PreviewRegistry, *, port: int, started_at: str, plugin_root: Path, version: str
) -> dict[str, Any]:
    """`server_status` と `GET /_admin/status` が返す常駐サーバーの状態を作る。"""
    return {
        "name": SERVER_NAME,
        "version": version,
        "port": port,
        "pid": os.getpid(),
        "started_at": started_at,
        "plugin_root": str(plugin_root),
        "previews": previews.listing(),
    }


def run_server_stop(
    previews: PreviewRegistry, *, request_stop: Callable[[], None]
) -> dict[str, Any]:
    """止める配信を結果にし、HTTP のサーバーに終わり始めるよう頼む（このレスポンスは返し終えてから閉じる）。"""
    stopping = previews.listing()
    request_stop()
    logger.info("server_stop で終わり始めた")
    return {"stopping": True, "previews": stopping}


def build_server(
    *,
    previews: PreviewRegistry,
    write_lock: threading.Lock,
    status: Callable[[], dict[str, Any]],
    request_stop: Callable[[], None],
) -> MCPServer:
    """`TOOL_NAMES` のツールを登録した MCP サーバーを作る。"""
    server = MCPServer(SERVER_NAME)
    # ツールの `status` が同じ名前を覆うので、常駐サーバーの状態を作る関数は別の名前で持つ
    server_state = status

    def locate(workspace: str, session: dict[str, Any] | None) -> Path:
        """workspace をセッションの作業フォルダから絶対パスにし、セッションがあればその宛先を書き換える。"""
        parsed = parse_session(session)
        root = resolve_workspace(workspace, parsed)
        if parsed is not None:
            previews.remember_session(root, parsed)
        return root

    def read(
        workspace: str,
        session: dict[str, Any] | None,
        run: Callable[[Path], dict[str, Any]],
        *,
        render: Callable[[dict[str, Any]], str] | None = None,
    ) -> CallToolResult:
        """ワークスペースを読むだけのツールの処理を、鍵を取らずに呼ぶ。render は結果を本文の文字にする関数。"""
        try:
            root = locate(workspace, session)
        except ArgumentError as error:
            return error_result(error)
        return call_tool(lambda: run(root), write_lock=write_lock, render=render)

    def write(
        workspace: str,
        session: dict[str, Any] | None,
        run: Callable[[Path], dict[str, Any]],
        *,
        create: bool = False,
        require: Callable[[Path], None] = require_workspace,
    ) -> CallToolResult:
        """ワークスペースを書き換えるツールの処理を、書き換えの鍵を取って呼ぶ。"""
        try:
            root = locate(workspace, session)
        except ArgumentError as error:
            return error_result(error)
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
        session: SessionArg = None,
    ) -> CallToolResult:
        # まだ無いフォルダへ書く `init` だけが、フォルダを作る鍵を取る
        return write(workspace, session, lambda root: commands.run_init(root, settings), create=True)

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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_add(root, kind, item))

    @server.tool(name="update", description="項目 1 つのキーを置き換える")
    def update(
        workspace: WorkspaceArg,
        id: ItemIdArg,
        item: Annotated[dict[str, Any], Field(description="置き換えるキーと値。null で消す")],
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_update(root, id, item))

    @server.tool(
        name="remove",
        description="項目 1 つを消す（本文も消し、消した項目をまだまとめていない変更に残す）。ほかの記録が指している項目は消さずにエラーにする。やめた項目を残すときは update で取り下げる",
    )
    def remove(
        workspace: WorkspaceArg,
        id: ItemIdArg,
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_remove(root, id))

    @server.tool(
        name="update_settings",
        description="設定（題名・話し合いの概要・プレイブック・フェーズ・最上位の軸の呼び名・ゴール・対象・カテゴリー・関連する場所・保持する回数）を書き換える。フェーズ・対象・カテゴリーを変えるときは項目の付け替えもする",
    )
    def update_settings(
        workspace: WorkspaceArg,
        settings: Annotated[
            dict[str, Any],
            Field(
                description="置き換える設定のキーと値。description・goal・links・history_limit は null で消す"
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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(
            workspace,
            session,
            lambda root: commands.run_update_settings(
                root, settings, phase_map, target_map, category_map
            ),
        )

    @server.tool(
        name="adopt", description="検討事項の採用する案を 1 つに切り替え、状態を決定済みにする"
    )
    def adopt(
        workspace: WorkspaceArg,
        id: ItemIdArg,
        key: Annotated[str, Field(description="採用する案の記号")],
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_adopt(root, id, key))

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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(
            workspace, session, lambda root: commands.run_edit_option(root, id, action, key, option)
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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_batch(root, operations))

    @server.tool(
        name="changes_since_read",
        description="AI が最後に読んだ時点より後に足した・変えた項目を、変わったキーと読んだ時点の値つきで返し、読んだ時点を今に進める",
    )
    def changes_since_read(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return write(workspace, session, commands.run_changes_since_read)

    @server.tool(
        name="commit",
        description="まだまとめていない書き換えを、日時と一言の説明を付けた 1 つのまとまりにする",
    )
    def commit(
        workspace: WorkspaceArg,
        summary: Annotated[
            str, Field(description="このまとまりで何をしたかの一言の説明（1〜200 文字）")
        ],
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_commit(root, summary))

    @server.tool(
        name="pending", description="まだまとめていない変更（足した項目・変えた項目とキー・消した項目）を返す"
    )
    def pending(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, commands.run_pending)

    @server.tool(name="status", description="再開時の状況（要見直し・進行中・再開可能など）を返す")
    def status(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, commands.run_status)

    @server.tool(name="next", description="前提が揃った未決定を決める順に返す")
    def next_candidates(
        workspace: WorkspaceArg,
        limit: Annotated[int | None, Field(description="返す件数の上限（1 以上）")] = None,
        session: SessionArg = None,
    ) -> CallToolResult:
        return read(workspace, session, lambda root: commands.run_next(root, limit))

    @server.tool(name="impact", description="参照を逆向きにたどって影響を受ける項目を返す")
    def impact(
        workspace: WorkspaceArg, id: ItemIdArg, session: SessionArg = None
    ) -> CallToolResult:
        return read(workspace, session, lambda root: commands.run_impact(root, id))

    @server.tool(
        name="find",
        description="文字・種類・状態・タグ・対象・カテゴリー・フェーズ・属性の条件に合う項目を、ページに分けて返す。タグは NFKC と小文字にそろえて比べる。使える絞り込みは text・kind・status・tags・any_tags・target・category・phase・attr。タグで絞る前に tags で使われているタグを引く。全体の件数が 1 ページより多いときは next_cursor を同じ条件で cursor に渡して続きを読む。量の見積もりは count_only と各項目の chars・total_chars で行い、返す量は view・include・exclude で選ぶ",
    )
    def find(
        workspace: WorkspaceArg,
        text: str | None = None,
        kind: Kind | None = None,
        status: str | None = None,
        tags: Annotated[
            list[str] | None, Field(description="全てを持つ項目に絞るタグ（AND）")
        ] = None,
        any_tags: Annotated[
            list[str] | None, Field(description="いずれかを持つ項目に絞るタグ（OR）")
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
        view: Annotated[
            Literal["brief", "standard", "full"],
            Field(
                description="返す量。brief は title・status・tags・chars、standard はそれに target・category・phase・attrs・updated、full はさらに extra・body・body_format を加える。id・kind はどの量でも返す"
            ),
        ] = "brief",
        include: Annotated[
            list[FieldName] | None, Field(description="view に加えて返す項目の名前")
        ] = None,
        exclude: Annotated[
            list[FieldName] | None, Field(description="view から外す項目の名前")
        ] = None,
        count_only: Annotated[
            bool,
            Field(description="true のとき、一覧を返さず total・total_chars・tag_counts だけを返す"),
        ] = False,
        format: Annotated[
            Literal["markdown", "json"],
            Field(
                description="結果の書き方。markdown は本文に Markdown を入れ、json は構造化の結果と本文に同じ JSON を入れる"
            ),
        ] = "markdown",
        session: SessionArg = None,
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
            session,
            lambda root: commands.run_find(
                root,
                search_filter,
                limit=limit,
                cursor=cursor,
                view=view,
                include=list(include or []),
                exclude=list(exclude or []),
                count_only=count_only,
            ),
            render=render_find_markdown if format == "markdown" else None,
        )

    @server.tool(name="show", description="項目 1 つの中身・本文・参照元を返す")
    def show(
        workspace: WorkspaceArg, id: ItemIdArg, session: SessionArg = None
    ) -> CallToolResult:
        return read(workspace, session, lambda root: commands.run_show(root, id))

    @server.tool(name="attrs", description="使っている属性名と件数を返す")
    def attrs(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, commands.run_attrs)

    @server.tool(
        name="tags",
        description="項目とスレッドに付いているタグを、正規化した表記ごとに件数と種類を添えて返す。タグを付ける前や find でタグを渡す前に呼び、同じ概念の言い方・活用の違いのタグがあれば使い回す",
    )
    def tags(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, commands.run_tags)

    @server.tool(name="check", description="スキーマ違反・参照切れ・本文のずれを洗い出す")
    def check(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, commands.run_check)

    @server.tool(name="goal", description="ゴールに届いたかと、残りの項目を返す")
    def goal(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, commands.run_goal)

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
        session: SessionArg = None,
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
        return read(workspace, session, run) if plan else write(workspace, session, run, require=require_migratable)

    @server.tool(name="clear_release", description=".mindstella/release/ の中身を消す")
    def clear_release(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return write(workspace, session, commands.run_clear_release)

    @server.tool(name="export", description="見るだけの 1 枚の HTML（配る書き出し）を書き出す")
    def export(
        workspace: WorkspaceArg,
        out: Annotated[str, Field(description="書き出す HTML のパス（.html で終わる）")],
        session: SessionArg = None,
    ) -> CallToolResult:
        try:
            out_path = resolve_workspace(out, parse_session(session), argument="out")
        except ArgumentError as error:
            return error_result(error)
        return read(workspace, session, lambda root: commands.run_export(root, out_path))

    @server.tool(
        name="preview_url", description="プレビューを配る URL を返す（無ければ配信を立てる）"
    )
    def preview_url(
        workspace: WorkspaceArg,
        diff: Annotated[
            str | None, Field(description="差分を開くまとまりの ID（`commit` の `id`。例 V-3）")
        ] = None,
        session: SessionArg = None,
    ) -> CallToolResult:
        return read(workspace, session, lambda root: commands.run_preview_url(root, previews=previews, diff=diff))

    @server.tool(
        name="readme",
        description="直下の README.md を、起動・接続のコマンドと配っているプレビューの URL で書き直す",
    )
    def readme(workspace: WorkspaceArg, session: SessionArg = None) -> CallToolResult:
        return read(workspace, session, lambda root: commands.run_readme(root, previews=previews))

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
        session: SessionArg = None,
    ) -> CallToolResult:
        return read(workspace, session, lambda root: commands.run_threads(root, status, tag, unread, awaiting))

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
        session: SessionArg = None,
    ) -> CallToolResult:
        try:
            root = locate(workspace, session)
        except ArgumentError as error:
            return error_result(error)
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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(
            workspace, session, lambda root: commands.run_new_thread(root, body, summary, tags, target)
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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(workspace, session, lambda root: commands.run_reply(root, id, body, summary, take))

    @server.tool(
        name="set_thread_status",
        description="AI がスレッドをクローズにするかオープンに戻し、理由を残す",
    )
    def set_thread_status(
        workspace: WorkspaceArg,
        id: Annotated[str, Field(description="スレッドの ID")],
        status: Annotated[Literal["open", "closed"], Field(description="変えた後の状態")],
        reason: Annotated[str | None, Field(description="状態を変える理由（400 文字まで）")] = None,
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(
            workspace, session, lambda root: commands.run_set_thread_status(root, id, status, reason)
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
        session: SessionArg = None,
    ) -> CallToolResult:
        return write(
            workspace, session, lambda root: commands.run_update_thread(root, id, summary, tags, take)
        )

    @server.tool(
        name="server_status",
        description="常駐サーバーの待ち受けのポート・バージョン・プロセスと、配信しているワークスペースごとのポートを返す",
    )
    def server_status(session: SessionArg = None) -> CallToolResult:
        return call_tool(server_state, write_lock=write_lock)

    @server.tool(
        name="server_stop",
        description="常駐サーバーを止める。配信ごとに終了時のフックを呼び、全ての配信を止めて、プロセスを終える",
    )
    def server_stop(session: SessionArg = None) -> CallToolResult:
        return call_tool(
            lambda: run_server_stop(previews, request_stop=request_stop), write_lock=write_lock
        )

    @server.custom_route(STATUS_PATH, methods=["GET"])
    async def admin_status(request: Request) -> JSONResponse:
        """常駐サーバーの状態を JSON で返す（起動の確認が待ち受けているかを見分ける）。"""
        return JSONResponse(server_state())

    return server


def call_tool(
    handler: Callable[[], dict[str, Any]],
    *,
    write_lock: threading.Lock,
    lock_root: Path | None = None,
    lock_create: bool = False,
    lock_require: Callable[[Path], None] = require_workspace,
    render: Callable[[dict[str, Any]], str] | None = None,
) -> CallToolResult:
    """ツールの処理を呼び、結果を構造化の結果（render を渡したときは本文だけ）に、エラーをツールのエラーにする。"""
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
    if render is not None:
        return text_result(render(payload))
    return ok_result(payload)


def text_result(text: str) -> CallToolResult:
    """文字を、構造化の結果を持たない本文だけの結果にする。"""
    return CallToolResult(content=[TextContent(type="text", text=text)])


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


def resolve_workspace(path: str, session: Session | None, *, argument: str = "workspace") -> Path:
    """ツールに渡されたパスを、セッションの作業フォルダを基準にした絶対パスにする。"""
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded
    # 相対パスでセッションが無い: 常駐サーバーの作業フォルダは使わない
    if session is None:
        raise ArgumentError(
            argument, "相対パスはセッションの作業フォルダが無いと読めません。絶対パスで渡してください"
        )
    return session.cwd / expanded


if __name__ == "__main__":
    sys.exit(main())
