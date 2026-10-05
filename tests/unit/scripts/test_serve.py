"""serve.py（プレビューの配信の台帳・待ち受け・応答・書き換えの知らせ・コメントの受け付け）の単体テスト。"""

from __future__ import annotations

import http.client
import json
import threading
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import yaml

import builder
import errors
import serve
from errors import (
    CommentConflictError,
    CommentInvalidError,
    CommentNotFoundError,
    ItemNotFoundError,
    MindmapError,
    SchemaMismatchError,
    ServeFailedError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from export_helpers import write_preview_dir
from fixture_types import MakeComment, MakeItem, MakeWorkspace, WriteComments
from workspace_fixtures import write_yaml

# index_response の雛形（差し込み口と、記録の入る空の要素）
SMALL_TEMPLATE = f"{builder.STYLE_SLOT}{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT}"

# 配信のテストで使う待ち受けのポート（check_host・check_origin の比較用。実際には待ち受けない）
PORT = 5000

# 接続や応答を待つ上限秒数
HTTP_TIMEOUT_SEC = 10

# 前回開いた日時として、1 回目・2 回目の呼び出しで返す日時
FIRST_OPENED = "2026-10-04T13:05:00+00:00"
SECOND_OPENED = "2026-10-04T14:45:00+00:00"


@pytest.fixture
def registry() -> Iterator[serve.PreviewRegistry]:
    """配信の台帳を作り、使い終わったら立てた配信を全て止める。"""
    created = serve.PreviewRegistry(threading.Lock())
    yield created
    created.stop_all()


def _port_of(url: str) -> int:
    """配信の URL から待ち受けのポートを取り出す。"""
    port = urlparse(url).port
    assert port is not None
    return port


def _get_status(url: str) -> int:
    """URL に GET して、ステータスコードを返す。"""
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SEC) as response:
        return response.status


def _context(root: Path, settings: dict[str, Any] | None = None) -> serve.ServeContext:
    """ワークスペースを配る文脈（待ち受けず、ポートだけ持つ）を作る。最後に検査に通った設定は settings（無ければ空）。"""
    return serve.ServeContext(
        root=root,
        port=PORT,
        write_lock=threading.Lock(),
        settings=serve.SettingsHolder({} if settings is None else settings),
    )


def _first_opened_now() -> str:
    """今の日時の代わりに、1 回目に開いた日時を返す。"""
    return FIRST_OPENED


def _second_opened_now() -> str:
    """今の日時の代わりに、2 回目に開いた日時を返す。"""
    return SECOND_OPENED


def _failing_touch_opened(*args: Any, **kwargs: Any) -> Any:
    """書き込めないことにして WriteFailedError を送る、前回開いた日時を書き換える代わりの関数。"""
    raise WriteFailedError("書き込めませんでした: .mindstella-opened（権限がありません）")


def test_start(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """同じワークスペースは同じ URL、別なら別の URL（正常系）。"""
    # 準備
    first = make_workspace(make_item("D-1"), name="first")
    second = make_workspace(make_item("D-1"), name="second")
    # 実行
    url1, started1 = registry.start(first)
    again_url1, started_again = registry.start(first)
    url2, started2 = registry.start(second)
    # 検証
    assert (started1, started_again, started2) == (True, False, True)
    assert again_url1 == url1
    assert _port_of(url1) != _port_of(url2)
    assert url1.startswith("http://127.0.0.1:")
    assert url2.startswith("http://127.0.0.1:")
    assert url1.endswith("/mindstella.html")
    assert url2.endswith("/mindstella.html")


def _start_expecting_mismatch(registry: serve.PreviewRegistry, root: Path) -> list[str]:
    """start が SchemaMismatchError を送ることを確かめ、その lines を返す。"""
    with pytest.raises(SchemaMismatchError) as raised:
        registry.start(root)
    return raised.value.lines


def test_start_when_settings_invalid(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, valid_settings: dict[str, Any]
) -> None:
    """config.yaml が合わなければ配信を立てず、直せば立てる（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"network_look": "rainbow"}})
    # 実行（合わない間は 2 回とも立てず、直した後の 1 回で立てる）
    first_lines = _start_expecting_mismatch(registry, root)
    second_lines = _start_expecting_mismatch(registry, root)
    write_yaml(root / "config.yaml", {**valid_settings, "display": {"network_look": "deep"}})
    url, started = registry.start(root)
    # 検証
    assert first_lines[0].startswith("config.yaml: display.network_look: ")
    assert second_lines[0].startswith("config.yaml: display.network_look: ")
    assert started is True
    assert url.endswith("/mindstella.html")


def test_stop_all(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """止めた配信にはつながらない（正常系）。"""
    # 準備
    url, _started = registry.start(make_workspace(make_item("D-1")))
    # 実行
    registry.stop_all()
    # 検証
    connection = http.client.HTTPConnection("127.0.0.1", _port_of(url), timeout=HTTP_TIMEOUT_SEC)
    with pytest.raises(ConnectionRefusedError):
        connection.request("GET", "/")


def test_start_preview_server(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """127.0.0.1 だけで待ち受ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    preview = serve.start_preview_server(root, write_lock=threading.Lock(), settings={})
    try:
        # 検証
        host, port = preview.httpd.server_address[:2]
        assert host == "127.0.0.1"
        assert port != 0
        assert preview.url.endswith("/mindstella.html")
        assert _get_status(preview.url) == 200
        # `/` は送り直しを辿らずに、画面のパスへ送り直す 302
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=HTTP_TIMEOUT_SEC)
        connection.request("GET", "/")
        redirect = connection.getresponse()
        assert redirect.status == 302
        assert redirect.getheader("Location") == "/mindstella.html"
        connection.close()
    finally:
        preview.stop()


def test_start_preview_server_when_bind_fails(
    monkeypatch: pytest.MonkeyPatch, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """待ち受けを立てられなければ ServeFailedError（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))

    def _fail(*args: Any, **kwargs: Any) -> None:
        """待ち受けのソケットを開けないことにする。"""
        raise OSError("ポートが取れません")

    monkeypatch.setattr(serve, "ThreadingHTTPServer", _fail)
    # 実行・検証
    with pytest.raises(ServeFailedError):
        serve.start_preview_server(root, write_lock=threading.Lock(), settings={})


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        pytest.param("127.0.0.1:5000", True, id="loopback"),
        pytest.param("LOCALHOST:5000", True, id="localhost_uppercase"),
        pytest.param("127.0.0.1:5001", False, id="other_port"),
        pytest.param("attacker.example:5000", False, id="other_name"),
        pytest.param(None, False, id="missing"),
    ],
)
def test_check_host(host: str | None, expected: bool) -> None:
    """端末の中の名前と同じポートだけ通す（正常系）。"""
    # 実行
    result = serve.check_host(host, PORT)
    # 検証
    assert result is expected


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        pytest.param(None, True, id="missing"),
        pytest.param("http://127.0.0.1:5000", True, id="loopback"),
        pytest.param("http://localhost:5000", True, id="localhost"),
        pytest.param("https://attacker.example", False, id="other_site"),
        pytest.param("http://127.0.0.1:5001", False, id="other_port"),
    ],
)
def test_check_origin(origin: str | None, expected: bool) -> None:
    """無いか配信と同じ送り元だけ通す（正常系）。"""
    # 実行
    result = serve.check_origin(origin, PORT)
    # 検証
    assert result is expected


def test_problem_response() -> None:
    """問題の JSON を作る（正常系）。"""
    # 実行
    response = serve.problem_response(404, "項目がありません: D-99")
    # 検証
    assert response.content_type == "application/problem+json; charset=utf-8"
    assert json.loads(response.body) == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "項目がありません: D-99",
    }


def test_index_response(tmp_path: Path) -> None:
    """差し込んだ雛形を返し、記録は空のまま（正常系）。"""
    # 準備
    preview_dir = tmp_path / "preview"
    write_preview_dir(preview_dir, SMALL_TEMPLATE)
    # 実行
    response = serve.index_response(preview_dir)
    # 検証
    body = response.body.decode("utf-8")
    assert response.status == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert builder.DATA_ELEMENT in body
    assert all(f"/* {name} */" in body for name in builder.STYLE_FILES)


def test_index_response_when_template_invalid(tmp_path: Path) -> None:
    """雛形の誤りは 500（正常系）。"""
    # 準備
    preview_dir = tmp_path / "preview"
    write_preview_dir(preview_dir, SMALL_TEMPLATE)
    (preview_dir / builder.SCRIPT_FILES[-1]).write_text("</script>", encoding="utf-8")
    # 実行
    response = serve.index_response(preview_dir)
    # 検証
    assert response.status == 500
    assert response.content_type == "application/problem+json; charset=utf-8"


def test_records_response(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """記録を JSON で返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    response = serve.records_response(_context(root))
    # 検証
    assert response.status == 200
    assert response.content_type == "application/json; charset=utf-8"
    assert json.loads(response.body)["decisions"][0]["id"] == "D-1"


def test_records_response_when_schema_mismatch(tmp_path: Path) -> None:
    """スキーマに合わなければ 422（正常系）。"""

    def _read(root: Path, **kwargs: Any) -> dict[str, Any]:
        """スキーマに合わないエラーを送る。"""
        raise SchemaMismatchError(lines=["decisions.yaml: items[0].status: 理由"])

    # 実行
    response = serve.records_response(_context(tmp_path), read=_read)
    # 検証
    assert response.status == 422
    assert json.loads(response.body)["detail"] == "decisions.yaml: items[0].status: 理由"


def test_records_response_when_workspace_removed(tmp_path: Path) -> None:
    """config.yaml が無くなったら 422（正常系）。"""

    def _read(root: Path, **kwargs: Any) -> dict[str, Any]:
        """ワークスペースが無いエラーを送る。"""
        raise WorkspaceNotFoundError("ワークスペースがありません")

    # 実行
    response = serve.records_response(_context(tmp_path), read=_read)
    # 検証
    assert response.status == 422


def test_records_response_when_settings_changed(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any]
) -> None:
    """通った設定は控え、崩れた設定では控えた設定で返す（正常系）。"""
    # 準備
    root = make_workspace()
    context = _context(root, {**valid_settings, "display": {"network_look": "starlight"}})
    # 実行（通る設定と崩れた設定を、この順に読む）
    write_yaml(root / "config.yaml", {**valid_settings, "display": {"network_look": "dust"}})
    first = serve.records_response(context)
    held_after_first = context.settings.current()["display"]["network_look"]
    write_yaml(root / "config.yaml", {**valid_settings, "display": {"network_look": "rainbow"}})
    second = serve.records_response(context)
    # 検証
    first_payload = json.loads(first.body)
    second_payload = json.loads(second.body)
    assert first.status == 200
    assert first_payload["settings"]["display"]["network_look"] == "dust"
    assert first_payload["settings_problem"] is None
    assert held_after_first == "dust"
    assert second.status == 200
    assert second_payload["settings"]["display"]["network_look"] == "dust"
    assert second_payload["settings_problem"][0].startswith("config.yaml: display.network_look: ")


@pytest.mark.parametrize(
    ("file_name", "text", "changes"),
    [
        pytest.param("decisions.yaml", "items: []\n", True, id="rewrite_yaml"),
        pytest.param("docs/D-1.md", "本文\n", True, id="add_body"),
        pytest.param("submissions.yaml", "items: []\n", True, id="add_submissions"),
        pytest.param("comments.yaml", "seq: 0\nitems: []\n", False, id="add_comments"),
        pytest.param("drafts.yaml", "items: []\n", False, id="add_drafts"),
        pytest.param(".mindstella.lock", "", False, id="add_lock_file"),
    ],
)
def test_workspace_signature(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    file_name: str,
    text: str,
    changes: bool,
) -> None:
    """書き換え・足す・消すで印が変わり、ロックのファイルでは変わらない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = serve.workspace_signature(root)
    # 実行
    (root / file_name).write_text(text, encoding="utf-8")
    after = serve.workspace_signature(root)
    # 検証
    assert (after != before) is changes


@pytest.mark.parametrize(
    ("file_name", "text", "changes"),
    [
        pytest.param(
            "changes.yaml",
            "last_seq: 0\nsets: []\npending:\n  added: []\n  changed: []\n",
            True,
            id="add_changes",
        ),
        pytest.param(".mindstella-opened", FIRST_OPENED, False, id="add_opened"),
    ],
)
def test_workspace_signature_with_changes(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    file_name: str,
    text: str,
    changes: bool,
) -> None:
    """まとまりは見て、前回開いた日時は見ない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = serve.workspace_signature(root)
    # 実行
    (root / file_name).write_text(text, encoding="utf-8")
    after = serve.workspace_signature(root)
    # 検証
    assert (after != before) is changes


class _ScriptedSignature:
    """決めた印を順に返す、書き換えの印を作る代わりの関数。"""

    def __init__(self, *values: str) -> None:
        """返す印を順に並べる。"""
        self._values = iter(values)

    def __call__(self, root: Path) -> str:
        """次の印を返す。"""
        return next(self._values)


class _SteppingClock:
    """呼ばれるたびに決めた秒数ずつ進む、単調な時計の代わりの関数。"""

    def __init__(self, step: float) -> None:
        """進める秒数を決める。"""
        self._step = step
        self._now = 0.0

    def __call__(self) -> float:
        """時計を進めて、今の時刻を返す。"""
        self._now += self._step
        return self._now


def _recording_write(
    written: list[bytes], *, fail_on_call: int, error: type[Exception]
) -> Callable[[bytes], None]:
    """書いたものを控え、fail_on_call 回目の呼び出しで error を送る関数を作る。"""

    def _write(chunk: bytes) -> None:
        """fail_on_call 回目なら失敗し、それまでは書いたものを控える。"""
        # 失敗させる呼び出しの番
        if len(written) + 1 == fail_on_call:
            raise error
        written.append(chunk)

    return _write


def test_stream_events(tmp_path: Path) -> None:
    """印が変わったときだけ changed を書く（正常系）。"""
    # 準備
    written: list[bytes] = []
    write = _recording_write(written, fail_on_call=2, error=BrokenPipeError)
    # 実行
    serve.stream_events(
        tmp_path,
        write,
        sleep=lambda seconds: None,
        clock=_SteppingClock(0.25),
        signature=_ScriptedSignature("a", "a", "b", "b", "c"),
    )
    # 検証
    assert written == [b"event: changed\ndata: b\n\n"]


def test_stream_events_when_idle(tmp_path: Path) -> None:
    """変わらないまま 15 秒経つと保つための行を書く（正常系）。"""
    # 準備
    written: list[bytes] = []
    write = _recording_write(written, fail_on_call=2, error=ConnectionResetError)
    # 実行
    serve.stream_events(
        tmp_path,
        write,
        sleep=lambda seconds: None,
        clock=_SteppingClock(5),
        signature=lambda root: "a",
    )
    # 検証
    assert written == [b": keepalive\n\n"]


def _post_body(**fields: Any) -> bytes:
    """送信の要求の本文（JSON）を作る。"""
    return json.dumps(fields, ensure_ascii=False).encode("utf-8")


# レビュー中のコメントと書きかけの YAML（comments_response の入力）
COMMENTS_TEXT = (
    "seq: 1\nitems:\n  - id: C-1\n    target: D-1\n    body: 案 A にする\n"
    "    created: '2026-10-01T00:00:00+00:00'\n"
)
DRAFTS_TEXT = (
    "items:\n  - target: D-1\n    body: 案 B も見たい\n    updated: '2026-10-01T00:00:00+00:00'\n"
)


@pytest.mark.parametrize(
    ("raw_files", "expected_titles", "expected_draft_count"),
    [
        pytest.param(
            {"comments.yaml": COMMENTS_TEXT, "drafts.yaml": DRAFTS_TEXT},
            ["問い"],
            1,
            id="comments_and_drafts",
        ),
        pytest.param({}, [], 0, id="no_files"),
    ],
)
def test_comments_response(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    raw_files: dict[str, str],
    expected_titles: list[str],
    expected_draft_count: int,
) -> None:
    """レビュー中と書きかけを返す。無ければ空（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="問い"), raw_files=raw_files)
    # 実行
    response = serve.comments_response(root)
    # 検証
    assert response.status == 200
    assert response.content_type == "application/json; charset=utf-8"
    payload = json.loads(response.body)
    assert [item["target_title"] for item in payload["items"]] == expected_titles
    assert len(payload["drafts"]) == expected_draft_count


def test_comments_response_when_invalid(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """崩れたファイルは 422（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"comments.yaml": "items: [\n"})
    # 実行
    response = serve.comments_response(root)
    # 検証
    assert response.status == 422


@pytest.mark.parametrize(
    ("status", "handled", "expected_body"),
    [
        pytest.param(201, {"ok": True}, b'{"ok": true}', id="created"),
        pytest.param(204, None, b"", id="no_content"),
    ],
)
def test_write_response(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    status: int,
    handled: dict[str, Any] | None,
    expected_body: bytes,
) -> None:
    """処理の結果を指定のステータスで返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    calls: list[tuple[Path, dict[str, Any]]] = []

    def _handle(root: Path, data: dict[str, Any]) -> dict[str, Any] | None:
        """呼ばれた引数を控えて、決めた結果を返す。"""
        calls.append((root, data))
        return handled

    # 実行
    response = serve.write_response(
        _context(root),
        content_type="application/json",
        origin=None,
        body=_post_body(a=1),
        handle=_handle,
        status=status,
    )
    # 検証
    assert response.status == status
    assert response.body == expected_body
    assert calls == [(root, {"a": 1})]


@pytest.mark.parametrize(
    ("content_type", "origin", "body", "expected_status"),
    [
        pytest.param("text/plain", None, _post_body(a=1), 415, id="content_type"),
        pytest.param(
            "application/json", "https://attacker.example", _post_body(a=1), 403, id="origin"
        ),
        pytest.param("application/json", None, b"[1]", 400, id="not_object"),
        pytest.param("application/json", None, b"{", 400, id="not_json"),
    ],
)
def test_write_response_when_rejected(
    tmp_path: Path, content_type: str, origin: str | None, body: bytes, expected_status: int
) -> None:
    """形・送り元の誤りは処理を呼ばずに問題の応答（正常系）。"""
    # 準備
    calls: list[tuple[Path, dict[str, Any]]] = []

    def _handle(root: Path, data: dict[str, Any]) -> dict[str, Any] | None:
        """呼ばれたら控える（呼ばれないはず）。"""
        calls.append((root, data))
        return None

    # 実行
    response = serve.write_response(
        _context(tmp_path),
        content_type=content_type,
        origin=origin,
        body=body,
        handle=_handle,
        status=201,
    )
    # 検証
    assert response.status == expected_status
    assert response.content_type == "application/problem+json; charset=utf-8"
    assert calls == []


def test_opened_response(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """2 回目は 1 回目の日時を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    first = serve.opened_response(_context(root), now=_first_opened_now)
    second = serve.opened_response(_context(root), now=_second_opened_now)
    # 検証
    assert (first.status, second.status) == (200, 200)
    assert second.content_type == "application/json; charset=utf-8"
    assert json.loads(first.body) == {"previous": None, "opened": FIRST_OPENED}
    assert json.loads(second.body) == {"previous": FIRST_OPENED, "opened": SECOND_OPENED}


def test_opened_response_when_write_fails(
    make_workspace: MakeWorkspace, make_item: MakeItem, monkeypatch: pytest.MonkeyPatch
) -> None:
    """書けなければ 500（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # serve モジュールの参照を、書き込めないエラーを送る関数に差し替える
    monkeypatch.setattr(serve, "touch_opened", _failing_touch_opened)
    # 実行
    response = serve.opened_response(_context(root))
    # 検証
    assert response.status == 500
    assert response.content_type == "application/problem+json; charset=utf-8"


@pytest.mark.parametrize(
    ("origin", "comment_id", "expected_status", "expected_remaining", "expected_deleted"),
    [
        pytest.param(None, "C-2", 200, ["C-1"], ("C-2", 1), id="deleted"),
        pytest.param(
            "https://attacker.example", "C-2", 403, ["C-1", "C-2"], (None, None), id="origin"
        ),
        pytest.param(None, "C-9", 404, ["C-1", "C-2"], (None, None), id="not_found"),
    ],
)
def test_delete_response(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    origin: str | None,
    comment_id: str,
    expected_status: int,
    expected_remaining: list[str],
    expected_deleted: tuple[str | None, int | None],
) -> None:
    """消して中身を返し、送り元が違えば消さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"), make_comment("C-2"))
    # 実行
    response = serve.delete_response(_context(root), origin=origin, comment_id=comment_id)
    # 検証
    assert response.status == expected_status
    payload = json.loads(response.body)
    assert (payload.get("id"), payload.get("count")) == expected_deleted
    saved = yaml.safe_load((root / "comments.yaml").read_text(encoding="utf-8"))["items"]
    assert [item["id"] for item in saved] == expected_remaining


@pytest.mark.parametrize(
    ("build_error", "expected_status", "expected_stale"),
    [
        pytest.param(lambda: CommentInvalidError("body: 空です"), 400, None, id="invalid"),
        pytest.param(
            lambda: errors.SettingsInvalidError("network_look: 選べません"),
            400,
            None,
            id="settings_invalid",
        ),
        pytest.param(
            lambda: ItemNotFoundError("項目がありません: D-99"), 404, None, id="item_not_found"
        ),
        pytest.param(
            lambda: CommentNotFoundError("コメントがありません: C-9"),
            404,
            None,
            id="comment_not_found",
        ),
        pytest.param(
            lambda: CommentConflictError(
                "箇所が合わないコメントがあります", stale=[("C-2", "理由")]
            ),
            409,
            [{"id": "C-2", "reason": "理由"}],
            id="conflict",
        ),
        pytest.param(
            lambda: SchemaMismatchError(["comments.yaml: items[0]: body がありません"]),
            422,
            None,
            id="schema_mismatch",
        ),
        pytest.param(
            lambda: WriteFailedError("書き込めませんでした: comments.yaml"), 500, None, id="write"
        ),
    ],
)
def test_error_response(
    build_error: Callable[[], MindmapError],
    expected_status: int,
    expected_stale: list[dict[str, str]] | None,
) -> None:
    """種類ごとのステータスコード（正常系）。"""
    # 準備
    error = build_error()
    # 実行
    response = serve.error_response(error)
    # 検証
    payload = json.loads(response.body)
    assert response.status == expected_status
    assert error.args[0] in payload["detail"]
    assert payload.get("stale") == expected_stale


def test_settings_holder() -> None:
    """accept は回数を変えず、reload だけが進める（正常系）。"""
    # 準備
    holder = serve.SettingsHolder({"summary": "a"})
    # 実行
    first = (holder.current(), holder.revision())
    holder.accept({"summary": "b"})
    second = (holder.current(), holder.revision())
    holder.reload({"summary": "c"})
    third = (holder.current(), holder.revision())
    # 検証
    assert first == ({"summary": "a"}, 0)
    assert second == ({"summary": "b"}, 0)
    assert third == ({"summary": "c"}, 1)


@pytest.mark.parametrize(
    (
        "network_look",
        "origin",
        "expected_status",
        "expected_look",
        "expected_held",
        "expected_revision",
        "expected_detail",
    ),
    [
        pytest.param("dust", None, 200, "dust", "dust", 1, "", id="passes"),
        pytest.param(
            "rainbow",
            None,
            422,
            None,
            "starlight",
            0,
            "config.yaml: display.network_look: ",
            id="schema_mismatch",
        ),
        pytest.param(
            "dust", "https://attacker.example", 403, None, "starlight", 0, "", id="other_origin"
        ),
    ],
)
def test_reload_response(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    network_look: str,
    origin: str | None,
    expected_status: int,
    expected_look: str | None,
    expected_held: str,
    expected_revision: int,
    expected_detail: str,
) -> None:
    """通れば差し替え、通らなければ前の設定のまま違う箇所を返す（正常系）。"""
    # 準備
    root = make_workspace()
    context = _context(root, {**valid_settings, "display": {"network_look": "starlight"}})
    # 手で直した config.yaml
    write_yaml(root / "config.yaml", {**valid_settings, "display": {"network_look": network_look}})
    before = (root / "config.yaml").read_bytes()
    # 実行
    response = serve.reload_response(context, origin=origin)
    # 検証
    payload = json.loads(response.body)
    assert response.status == expected_status
    assert payload.get("settings", {}).get("display", {}).get("network_look") == expected_look
    assert expected_detail in payload.get("detail", "")
    assert context.settings.current()["display"]["network_look"] == expected_held
    assert context.settings.revision() == expected_revision
    assert (root / "config.yaml").read_bytes() == before
