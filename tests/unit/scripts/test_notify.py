"""notify.py（書き込みのマーカーと作業の完了の通知）の単体テスト。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import notify

# テストの Webhook の URL（送信しないドメイン）
WEBHOOK_URL = "https://example.invalid/api/webhooks/1/secret-token"

# テストのワークスペースの ID
WORKSPACE_ID = "ws"

# テストの画面の URL
PAGE_URL = "http://127.0.0.1:47800/mindstella.html"


@pytest.fixture(autouse=True)
def markers(monkeypatch: pytest.MonkeyPatch) -> notify.WriteMarkers:
    """テストごとに空のマーカーへ差し替える。"""
    fresh = notify.WriteMarkers()
    monkeypatch.setattr(notify, "MARKERS", fresh)
    return fresh


@pytest.fixture
def webhook_file(tmp_path: Path) -> Path:
    """1 行目に Webhook の URL を記載した設定のファイル。"""
    path = tmp_path / "webhook.ini"
    path.write_text(f"{WEBHOOK_URL}\n", encoding="utf-8")
    return path


class FakeResponse:
    """urlopen が返却する応答の代わり。"""

    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _opener_returning(
    status: int, calls: list[tuple[urllib.request.Request, float]]
) -> Callable[..., FakeResponse]:
    """呼び出しを記録し、決めたステータスの応答を返却する opener を作る。"""

    def opener(request: urllib.request.Request, *, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse(status)

    return opener


def _opener_raising(error: BaseException, calls: list[Any]) -> Callable[..., FakeResponse]:
    """呼び出しを記録し、決めた例外を送出する opener を作る。"""

    def opener(request: urllib.request.Request, *, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        raise error

    return opener


def _recording_send(sent: list[tuple[str, str]]) -> Callable[[str, str], bool]:
    """送信の代わりに URL と本文を記録し、成功を返却する関数を作る。"""

    def send(url: str, content: str) -> bool:
        sent.append((url, content))
        return True

    return send


def _recording_describe(
    described: list[bool], result: tuple[str, str | None]
) -> Callable[[], tuple[str, str | None]]:
    """呼ばれたことを記録し、決めた名前と URL を返却する関数を作る。"""

    def describe() -> tuple[str, str | None]:
        described.append(True)
        return result

    return describe


def test_take(markers: notify.WriteMarkers) -> None:
    """付けたマーカーを 1 回だけ取り出す（正常系）。"""
    # 準備
    markers.mark("ws")
    # 実行
    first = markers.take("ws")
    second = markers.take("ws")
    # 検証
    assert first is True
    assert second is False


def test_take_when_cleared(markers: notify.WriteMarkers) -> None:
    """解除したマーカーは取り出さない（正常系）。"""
    # 準備
    markers.mark("ws")
    markers.clear("ws")
    # 実行
    result = markers.take("ws")
    # 検証
    assert result is False


def test_take_when_other_workspace(markers: notify.WriteMarkers) -> None:
    """ワークスペースごとに分ける（正常系）。"""
    # 準備
    markers.mark("a")
    # 実行
    other = markers.take("b")
    own = markers.take("a")
    # 検証
    assert other is False
    assert own is True


def test_read_webhook_url(tmp_path: Path) -> None:
    """1 行目の URL を返却する（正常系）。"""
    # 準備
    path = tmp_path / "webhook.ini"
    path.write_text("  https://example.invalid/hook  \n2 行目\n", encoding="utf-8")
    # 実行
    result = notify.read_webhook_url({"MINDSTELLA_DISCORD_WEBHOOK_FILE": str(path)})
    # 検証
    assert result == "https://example.invalid/hook"


@pytest.mark.parametrize(
    "environ",
    [
        pytest.param({}, id="missing"),
        pytest.param({"MINDSTELLA_DISCORD_WEBHOOK_FILE": ""}, id="empty"),
    ],
)
def test_read_webhook_url_when_unset(environ: dict[str, str]) -> None:
    """環境変数が無い・空なら None（正常系）。"""
    # 実行
    result = notify.read_webhook_url(environ)
    # 検証
    assert result is None


@pytest.mark.parametrize(
    ("read_name", "content"),
    [
        pytest.param("missing.ini", "https://example.invalid/hook\n", id="missing-file"),
        pytest.param("webhook.ini", "discord\n", id="not-url"),
    ],
)
def test_read_webhook_url_when_unreadable(
    read_name: str, content: str, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ファイルが無い・URL でないなら None（正常系）。"""
    # 準備
    (tmp_path / "webhook.ini").write_text(content, encoding="utf-8")
    path = tmp_path / read_name
    caplog.set_level(logging.DEBUG)
    # 実行
    result = notify.read_webhook_url({"MINDSTELLA_DISCORD_WEBHOOK_FILE": str(path)})
    # 検証
    assert result is None
    assert str(tmp_path) not in caplog.text
    assert "discord" not in caplog.text
    assert "example.invalid" not in caplog.text


def test_build_content() -> None:
    """名前と完了と URL の 2 行（正常系）。"""
    # 実行
    result = notify.build_content("家計簿", PAGE_URL)
    # 検証
    assert result == "家計簿: 作業が完了しました\nhttp://127.0.0.1:47800/mindstella.html"


def test_build_content_when_no_url() -> None:
    """URL が無いときは 1 行（正常系）。"""
    # 実行
    result = notify.build_content("家計簿", None)
    # 検証
    assert result == "家計簿: 作業が完了しました"


def test_build_content_when_too_long() -> None:
    """上限を超える名前を切り詰める（正常系）。"""
    # 準備
    name = "あ" * 3000
    # 実行
    result = notify.build_content(name, PAGE_URL)
    # 検証
    assert len(result) <= 2000
    assert result.endswith("…: 作業が完了しました\nhttp://127.0.0.1:47800/mindstella.html")
    assert result.startswith("あ")


def test_send_webhook() -> None:
    """wait=true で JSON を送信し、200 で真（正常系）。"""
    # 準備
    calls: list[tuple[urllib.request.Request, float]] = []
    # 実行
    result = notify.send_webhook(WEBHOOK_URL, "本文", opener=_opener_returning(200, calls))
    # 検証
    assert result is True
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == f"{WEBHOOK_URL}?wait=true"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {"content": "本文"}  # type: ignore[arg-type]
    assert timeout == notify.SEND_TIMEOUT_SEC
    assert (
        request.get_header("User-agent")
        == "DiscordBot (https://github.com/shuhei1101/mindstella, 1.0)"
    )


def test_send_webhook_when_http_error(caplog: pytest.LogCaptureFixture) -> None:
    """500 は偽で、記録に URL を含めない（正常系）。"""
    # 準備
    calls: list[Any] = []
    error = urllib.error.HTTPError(WEBHOOK_URL, 500, "Internal Server Error", None, None)  # type: ignore[arg-type]
    caplog.set_level(logging.DEBUG)
    # 実行
    result = notify.send_webhook(WEBHOOK_URL, "本文", opener=_opener_raising(error, calls))
    # 検証
    assert result is False
    assert len(calls) == 1
    assert "500" in caplog.text
    assert "example.invalid" not in caplog.text
    assert "secret-token" not in caplog.text


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(urllib.error.URLError(f"unreachable {WEBHOOK_URL}"), id="unreachable"),
        pytest.param(TimeoutError(f"timed out {WEBHOOK_URL}"), id="timeout"),
    ],
)
def test_send_webhook_when_unreachable(
    error: BaseException, caplog: pytest.LogCaptureFixture
) -> None:
    """接続できない・上限を過ぎたときは偽で、例外を送出しない（正常系）。"""
    # 準備
    calls: list[Any] = []
    caplog.set_level(logging.DEBUG)
    # 実行
    result = notify.send_webhook(WEBHOOK_URL, "本文", opener=_opener_raising(error, calls))
    # 検証
    assert result is False
    assert "example.invalid" not in caplog.text
    assert "secret-token" not in caplog.text


@pytest.mark.parametrize(
    ("tool", "payload"),
    [
        pytest.param("commit", {"id": "V-3"}, id="commit"),
        pytest.param("new_thread", {"id": "TH-1", "post": "P-1", "created": True}, id="new-thread"),
        pytest.param("reply", {"post": "P-2"}, id="reply"),
    ],
)
def test_mark_written(tool: str, payload: dict[str, Any], markers: notify.WriteMarkers) -> None:
    """commit・new_thread・reply でマーカーを付ける（正常系）。"""
    # 実行
    notify.mark_written(tool, WORKSPACE_ID, payload)
    # 検証
    assert markers.take(WORKSPACE_ID) is True


@pytest.mark.parametrize(
    ("tool", "payload"),
    [
        pytest.param("set_thread_status", {"id": "TH-1"}, id="set-thread-status"),
        pytest.param("update_thread", {"id": "TH-1"}, id="update-thread"),
        pytest.param("commit", {"id": None}, id="commit-nothing"),
    ],
)
def test_mark_written_when_not_marking(
    tool: str, payload: dict[str, Any], markers: notify.WriteMarkers
) -> None:
    """対象外のツールと、まとめなかった commit は付けない（正常系）。"""
    # 実行
    notify.mark_written(tool, WORKSPACE_ID, payload)
    # 検証
    assert markers.take(WORKSPACE_ID) is False


def test_notify_if_written(webhook_file: Path, markers: notify.WriteMarkers) -> None:
    """マーカーがあれば 1 回送信して解除する（正常系）。"""
    # 準備
    notify.mark_written("reply", WORKSPACE_ID, {})
    sent: list[tuple[str, str]] = []
    described: list[bool] = []
    # 実行
    thread = notify.notify_if_written(
        WORKSPACE_ID,
        _recording_describe(described, ("家計簿", "http://127.0.0.1:1/mindstella.html")),
        environ={"MINDSTELLA_DISCORD_WEBHOOK_FILE": str(webhook_file)},
        send=_recording_send(sent),
    )
    assert thread is not None
    thread.join(timeout=5)
    # 検証
    assert thread.daemon is True
    assert sent == [(WEBHOOK_URL, "家計簿: 作業が完了しました\nhttp://127.0.0.1:1/mindstella.html")]
    assert markers.take(WORKSPACE_ID) is False


def test_notify_if_written_when_not_marked(webhook_file: Path) -> None:
    """マーカーが無ければ送信しない（正常系）。"""
    # 準備
    sent: list[tuple[str, str]] = []
    described: list[bool] = []
    # 実行
    thread = notify.notify_if_written(
        WORKSPACE_ID,
        _recording_describe(described, ("家計簿", None)),
        environ={"MINDSTELLA_DISCORD_WEBHOOK_FILE": str(webhook_file)},
        send=_recording_send(sent),
    )
    # 検証
    assert thread is None
    assert sent == []
    assert described == []


def test_notify_if_written_when_not_configured(markers: notify.WriteMarkers) -> None:
    """Webhook の設定が無ければ送信せずマーカーも解除する（正常系）。"""
    # 準備
    markers.mark(WORKSPACE_ID)
    sent: list[tuple[str, str]] = []
    described: list[bool] = []
    # 実行
    thread = notify.notify_if_written(
        WORKSPACE_ID,
        _recording_describe(described, ("家計簿", None)),
        environ={},
        send=_recording_send(sent),
    )
    # 検証
    assert thread is None
    assert sent == []
    assert markers.take(WORKSPACE_ID) is False
