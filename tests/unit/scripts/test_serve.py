"""serve.py（プレビューの配信の台帳・待ち受け・応答・書き換えの知らせ・コメントの受け付け）の単体テスト。"""

from __future__ import annotations

import http.client
import json
import socket
import sys
import threading
import time
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
from workspace_fixtures import RECORD_DIR, write_yaml

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


@pytest.fixture
def make_registry() -> Iterator[Callable[[serve.ExternalAccess], serve.PreviewRegistry]]:
    """外から見る設定つきの配信の台帳を作る関数を返し、使い終わったら作った台帳の配信を全て止める。"""
    created: list[serve.PreviewRegistry] = []

    def _make(external: serve.ExternalAccess) -> serve.PreviewRegistry:
        """external を渡した台帳を作って控える。"""
        registry = serve.PreviewRegistry(threading.Lock(), external=external)
        created.append(registry)
        return registry

    yield _make
    for registry in created:
        registry.stop_all()


def _free_port() -> int:
    """127.0.0.1 の空きポートを 1 つ取って閉じ、その番号を返す。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _record_hook_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[str, ...], int, str]]:
    """serve.run_hook を、呼ばれた引数を控えて真を返す関数に差し替え、控える入れ物を返す。"""
    calls: list[tuple[tuple[str, ...], int, str]] = []

    def _run_hook(command: tuple[str, ...], port: int, name: str) -> bool:
        """フックを立てずに、渡された引数だけを控える。"""
        calls.append((command, port, name))
        return True

    monkeypatch.setattr(serve, "run_hook", _run_hook)
    return calls


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


def test_url_of(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """立てたワークスペースだけ URL を返す（正常系）。"""
    # 準備
    first = make_workspace(make_item("D-1"), name="first")
    second = make_workspace(make_item("D-1"), name="second")
    url, _started = registry.start(first)
    # 実行
    first_url = registry.url_of(first)
    second_url = registry.url_of(second)
    # 検証
    assert first_url == url
    assert second_url is None
    # url_of は配信を立てないので、台帳の配信は 1 つのまま
    assert len(registry._servers) == 1


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
    write_yaml(
        root / RECORD_DIR / "config.yaml", {**valid_settings, "display": {"network_look": "deep"}}
    )
    url, started = registry.start(root)
    # 検証
    assert first_lines[0].startswith("config.yaml: display.network_look: ")
    assert second_lines[0].startswith("config.yaml: display.network_look: ")
    assert started is True
    assert url.endswith("/mindstella.html")


def test_start_when_port_fixed(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, valid_settings: dict[str, Any]
) -> None:
    """preview.port のポートで立てる（正常系）。"""
    # 準備
    port = _free_port()
    root = make_workspace(settings={**valid_settings, "preview": {"port": port}})
    # 実行
    url, started = registry.start(root)
    # 検証
    assert started is True
    assert url == f"http://127.0.0.1:{port}/mindstella.html"


def test_start_when_start_hook_set(
    make_registry: Callable[[serve.ExternalAccess], serve.PreviewRegistry],
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """立てたときだけ起動時のフックを呼ぶ（正常系）。"""
    # 準備
    calls = _record_hook_calls(monkeypatch)
    registry = make_registry(serve.ExternalAccess(start_hook=("hook",)))
    root = make_workspace(make_item("D-1"), name="家計簿")
    # 実行（2 回目は立て済みなので呼ばれない）
    url, _started = registry.start(root)
    registry.start(root)
    # 検証
    assert calls == [(("hook",), _port_of(url), "家計簿")]


def test_start_when_port_in_use(
    make_registry: Callable[[serve.ExternalAccess], serve.PreviewRegistry],
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preview.port が使われていれば ServeFailedError でフックを呼ばない（異常系）。"""
    # 準備
    calls = _record_hook_calls(monkeypatch)
    registry = make_registry(serve.ExternalAccess(start_hook=("hook",)))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupier:
        occupier.bind(("127.0.0.1", 0))
        occupier.listen()
        port = int(occupier.getsockname()[1])
        root = make_workspace(settings={**valid_settings, "preview": {"port": port}})
        # 実行・検証
        with pytest.raises(ServeFailedError):
            registry.start(root)
    assert registry._servers == {}
    assert calls == []


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


def test_stop_all_when_stop_hook_set(
    make_registry: Callable[[serve.ExternalAccess], serve.PreviewRegistry],
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """配信ごとに 1 回だけ終了時のフックを呼ぶ（正常系）。"""
    # 準備
    calls = _record_hook_calls(monkeypatch)
    registry = make_registry(serve.ExternalAccess(stop_hook=("hook",)))
    url1, _started1 = registry.start(make_workspace(make_item("D-1"), name="first"))
    url2, _started2 = registry.start(make_workspace(make_item("D-1"), name="second"))
    # 実行（2 回目は台帳が空なので何もしない）
    registry.stop_all()
    registry.stop_all()
    # 検証
    assert sorted(calls, key=lambda call: call[2]) == [
        (("hook",), _port_of(url1), "first"),
        (("hook",), _port_of(url2), "second"),
    ]


def test_stop_all_when_reentered(
    make_workspace: MakeWorkspace, make_item: MakeItem, monkeypatch: pytest.MonkeyPatch
) -> None:
    """止めている途中に同じスレッドから呼ばれても止まらず、フックを重ねて呼ばない（正常系）。"""
    # 準備（鍵が戻らない実装でも後片付けで止まらないよう、後片付けの fixture を使わずテスト自身で止める）
    registry = serve.PreviewRegistry(
        threading.Lock(), external=serve.ExternalAccess(stop_hook=("hook",))
    )
    url, _started = registry.start(make_workspace(make_item("D-1")))
    calls: list[tuple[tuple[str, ...], int, str]] = []

    def _run_hook(command: tuple[str, ...], port: int, name: str) -> bool:
        """引数を控え、フックの中から同じ台帳の stop_all を呼び直す。"""
        calls.append((command, port, name))
        registry.stop_all()
        return True

    monkeypatch.setattr(serve, "run_hook", _run_hook)
    # 実行（鍵を持ったまま呼び直すと戻らないので、戻らないことを失敗にできるよう別スレッドで呼ぶ）
    runner = threading.Thread(target=registry.stop_all, daemon=True)
    runner.start()
    runner.join(timeout=HTTP_TIMEOUT_SEC)
    # 検証
    assert not runner.is_alive()
    assert len(calls) == 1
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
    result = serve.check_host(host, PORT, allowed_hosts=frozenset())
    # 検証
    assert result is expected


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        pytest.param("preview.example.test", True, id="allowed"),
        pytest.param("PREVIEW.example.test:8443", True, id="allowed_uppercase_with_port"),
        pytest.param("other.example.test", False, id="other_name"),
        pytest.param("preview.example.test.attacker.example", False, id="longer_name"),
    ],
)
def test_check_host_when_allowed(host: str, expected: bool) -> None:
    """許可したホスト名はポートを問わず通す（正常系）。"""
    # 実行
    result = serve.check_host(host, PORT, allowed_hosts=frozenset({"preview.example.test"}))
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
    result = serve.check_origin(origin, PORT, allowed_hosts=frozenset())
    # 検証
    assert result is expected


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        pytest.param("https://preview.example.test", True, id="https"),
        pytest.param("http://preview.example.test:8443", True, id="http_with_port"),
        pytest.param("ftp://preview.example.test", False, id="other_scheme"),
        pytest.param("https://other.example.test", False, id="other_name"),
    ],
)
def test_check_origin_when_allowed(origin: str, expected: bool) -> None:
    """許可したホスト名の https / http の送り元を通す（正常系）。"""
    # 実行
    result = serve.check_origin(origin, PORT, allowed_hosts=frozenset({"preview.example.test"}))
    # 検証
    assert result is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("Preview.Example.test:8443", "preview.example.test", id="port_removed"),
        pytest.param("preview.example.test", "preview.example.test", id="no_port"),
        pytest.param("preview.example.test:", "preview.example.test:", id="empty_port_kept"),
    ],
)
def test_host_part(value: str, expected: str) -> None:
    """末尾のポートだけを外して小文字にする（正常系）。"""
    # 実行
    result = serve.host_part(value)
    # 検証
    assert result == expected


def test_load_external_access() -> None:
    """3 つの環境変数を読み分ける（正常系）。"""
    # 準備
    environ = {
        "MINDSTELLA_ALLOWED_HOSTS": " Preview.example.test , ,https://x.example,a.example:443 ",
        "MINDSTELLA_PREVIEW_START_HOOK": "pub add",
        "MINDSTELLA_PREVIEW_STOP_HOOK": "pub rm",
    }
    # 実行
    result = serve.load_external_access(environ)
    # 検証（空の要素と、`:`・`/` を含む要素は捨てる）
    assert result.allowed_hosts == frozenset({"preview.example.test"})
    assert result.start_hook == ("pub", "add")
    assert result.stop_hook == ("pub", "rm")


def test_load_external_access_when_empty() -> None:
    """どれも無ければ空の既定値（正常系）。"""
    # 実行
    result = serve.load_external_access({})
    # 検証
    assert result == serve.ExternalAccess()


def test_load_external_access_when_hook_unparsable() -> None:
    """分けられないフックは空にする（異常系）。"""
    # 実行（閉じない引用符は例外を送らず、空にする）
    result = serve.load_external_access({"MINDSTELLA_PREVIEW_START_HOOK": 'pub "add'})
    # 検証
    assert result.start_hook == ()


def _read_when_written(path: Path) -> str:
    """子プロセスが path に書き終えるのを上限秒数まで待ち、書かれた中身を返す。"""
    deadline = time.monotonic() + HTTP_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if path.exists() and path.read_text(encoding="utf-8"):
            return path.read_text(encoding="utf-8")
        time.sleep(0.05)
    raise AssertionError(f"子プロセスが {path} に書きませんでした")


def test_run_hook(tmp_path: Path) -> None:
    """末尾にポートと名前を足して立てる（正常系）。"""
    # 準備
    written = tmp_path / "written.txt"
    command = (
        sys.executable,
        "-c",
        "import sys,pathlib; "
        "pathlib.Path(sys.argv[1]).write_text(' '.join(sys.argv[2:]), encoding='utf-8')",
        str(written),
    )
    # 実行
    started = serve.run_hook(command, 47800, "家計簿")
    # 検証（終わりは待たないので、書かれるのを待つ）
    assert started is True
    assert _read_when_written(written) == "47800 家計簿"


def test_run_hook_when_command_missing() -> None:
    """コマンドが無ければ偽で例外を送らない（異常系）。"""
    # 実行
    started = serve.run_hook(("mindstella-no-such-command",), 47800, "家計簿")
    # 検証
    assert started is False


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
    write_yaml(
        root / RECORD_DIR / "config.yaml", {**valid_settings, "display": {"network_look": "dust"}}
    )
    first = serve.records_response(context)
    held_after_first = context.settings.current()["display"]["network_look"]
    write_yaml(
        root / RECORD_DIR / "config.yaml",
        {**valid_settings, "display": {"network_look": "rainbow"}},
    )
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
    (root / RECORD_DIR / file_name).write_text(text, encoding="utf-8")
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
    (root / RECORD_DIR / file_name).write_text(text, encoding="utf-8")
    after = serve.workspace_signature(root)
    # 検証
    assert (after != before) is changes


@pytest.mark.parametrize(
    "file_name",
    [
        pytest.param("A-1.html", id="rewrite_html_body"),
        pytest.param("A-2.html", id="add_html_body"),
    ],
)
def test_workspace_signature_with_html_body(
    make_workspace: MakeWorkspace, make_item: MakeItem, file_name: str
) -> None:
    """HTML の本文の書き換えでも印が変わる（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", body="A-1.html"), bodies={"A-1.html": "<p>前</p>\n"})
    before = serve.workspace_signature(root)
    target = root / RECORD_DIR / "docs" / file_name
    # 実行
    target.write_text("<p>書き換えた後の本文</p>\n", encoding="utf-8")
    after = serve.workspace_signature(root)
    # 検証
    assert after != before


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


def _handle_succeeding(root: Path, data: dict[str, Any]) -> dict[str, Any] | None:
    """処理が成功したとして、本文を返す。"""
    return {"ok": True}


def _handle_conflicting(root: Path, data: dict[str, Any]) -> dict[str, Any] | None:
    """箇所が合わないとして、CommentConflictError を送る。"""
    raise CommentConflictError("箇所が合いません")


@pytest.mark.parametrize(
    (
        "handle",
        "expected_status",
        "expected_entered",
        "expected_after_bodies",
        "expected_lock_free",
    ),
    [
        pytest.param(_handle_succeeding, 201, True, [{"ok": True}], [True], id="succeeded"),
        pytest.param(_handle_conflicting, 409, False, [], [], id="conflict"),
    ],
)
def test_write_response_when_after(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    handle: Callable[[Path, dict[str, Any]], dict[str, Any] | None],
    expected_status: int,
    expected_entered: bool,
    expected_after_bodies: list[dict[str, Any]],
    expected_lock_free: list[bool],
) -> None:
    """鍵を外した後に after を呼び、その結果を返す（正常系）。"""
    # 準備
    context = _context(make_workspace(make_item("D-1")))
    after_bodies: list[dict[str, Any]] = []
    lock_free: list[bool] = []

    def _after(body: dict[str, Any]) -> dict[str, Any]:
        """呼ばれたときに書き換えの鍵が取れるかと受けた本文を控え、entered を足した本文を返す。"""
        acquired = context.write_lock.acquire(blocking=False)
        lock_free.append(acquired)
        if acquired:
            context.write_lock.release()
        after_bodies.append(body)
        return {**body, "entered": True}

    # 実行
    response = serve.write_response(
        context,
        content_type="application/json",
        origin=None,
        body=_post_body(a=1),
        handle=handle,
        status=201,
        after=_after,
    )
    # 検証
    assert response.status == expected_status
    assert (b'"entered": true' in response.body) is expected_entered
    assert after_bodies == expected_after_bodies
    assert lock_free == expected_lock_free


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
    saved = yaml.safe_load((root / RECORD_DIR / "comments.yaml").read_text(encoding="utf-8"))[
        "items"
    ]
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
    write_yaml(
        root / RECORD_DIR / "config.yaml",
        {**valid_settings, "display": {"network_look": network_look}},
    )
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    response = serve.reload_response(context, origin=origin)
    # 検証
    payload = json.loads(response.body)
    assert response.status == expected_status
    assert payload.get("settings", {}).get("display", {}).get("network_look") == expected_look
    assert expected_detail in payload.get("detail", "")
    assert context.settings.current()["display"]["network_look"] == expected_held
    assert context.settings.revision() == expected_revision
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == before
