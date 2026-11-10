"""文字起こしのサービスの代わりの偽のサーバーと、常駐サーバーの上限を差し替える sitecustomize（結合テストの共通の関数）。"""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass, field
from email.parser import BytesParser
from email.policy import HTTP
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

# 偽のサーバーの待ち受けのホスト
FAKE_HOST = "127.0.0.1"

# 用語集のプリセットの一覧の応答
PRESETS_BODY = {"presets": ["一般", "開発"], "active": "一般"}

# 偽のサーバーが払い出すジョブの ID
JOB_ID = "job-1"

# done で返す起こした文字
TRANSCRIBED_TEXT = "案 A にする"

# failed で返す失敗の理由
FAILED_REASON = "文字起こしワーカー無応答"

# 偽のサーバーの振る舞い
# done: 1 回目は running、2 回目に done / failed: 1 回目は running、2 回目に failed
# running: いつまでも同じ progress の running / unsupported: /web/ の下の全てに 404
type FakeMode = Literal["done", "failed", "running", "unsupported"]

# 常駐サーバーのモジュールを読み込んだ後に、定数を差し替える sitecustomize の雛形（{overrides} に JSON を入れる）
OVERRIDE_TEMPLATE = """\
import importlib.abc
import importlib.machinery
import json
import sys

_OVERRIDES = json.loads({overrides!r})


class _OverrideFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name not in _OVERRIDES:
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or spec.loader is None:
            return spec
        execute = spec.loader.exec_module

        def _exec_module(module):
            execute(module)
            for key, value in _OVERRIDES[name].items():
                setattr(module, key, value)

        spec.loader.exec_module = _exec_module
        return spec


sys.meta_path.insert(0, _OverrideFinder())
"""


def override_sitecustomize(overrides: dict[str, dict[str, object]]) -> str:
    """モジュール名 → 定数名 → 値を、読み込んだ後に差し替える sitecustomize の中身を返す。"""
    return OVERRIDE_TEMPLATE.format(overrides=json.dumps(overrides, ensure_ascii=False))


@dataclass
class ReceivedJob:
    """偽のサーバーが受けた文字起こしの依頼。"""

    # 依頼の audio の中身
    audio: bytes
    # 依頼の audio の Content-Type
    audio_type: str
    # 依頼の glossary_preset（無ければ None）
    preset: str | None


@dataclass
class FakeTranscriber:
    """文字起こしのサービスの 3 つのエンドポイントを、振る舞いの種類どおりに返す偽のサーバー。"""

    mode: FakeMode
    # 受けた依頼（受けた順）
    jobs: list[ReceivedJob] = field(default_factory=list)
    # ジョブの状態を返した回数
    polls: int = 0
    _server: ThreadingHTTPServer | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def url(self) -> str:
        """待ち受けの URL。"""
        assert self._server is not None
        return f"http://{FAKE_HOST}:{self._server.server_address[1]}"

    def start(self) -> None:
        """空きポートで待ち受け、別のスレッドで応答し続ける。"""
        fake = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                fake._handle_get(self)

            def do_POST(self) -> None:
                fake._handle_post(self)

            def log_message(self, format: str, *args: object) -> None:
                """アクセスのログを出さない。"""

        self._server = ThreadingHTTPServer((FAKE_HOST, 0), _Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        """待ち受けを止める。"""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

    def _handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        """プリセットの一覧とジョブの状態を返す。"""
        # 音声を受け付けるエンドポイントが無い: /web/ の下の全てに 404
        if self.mode == "unsupported":
            _reply(handler, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})
            return
        if handler.path == "/web/glossary-presets":
            _reply(handler, HTTPStatus.OK, PRESETS_BODY)
            return
        if handler.path == f"/web/transcriptions/{JOB_ID}":
            with self._lock:
                self.polls += 1
                polls = self.polls
            _reply(handler, HTTPStatus.OK, self._job_state(polls))
            return
        _reply(handler, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

    def _job_state(self, polls: int) -> dict[str, object]:
        """何回目に取りに来たかで、ジョブの状態を返す。"""
        # 終わらない: いつまでも同じ progress
        if self.mode == "running" or polls == 1:
            return {"job_id": JOB_ID, "state": "running", "progress": 0.5}
        if self.mode == "failed":
            return {"job_id": JOB_ID, "state": "failed", "error": FAILED_REASON}
        return {"job_id": JOB_ID, "state": "done", "text": TRANSCRIBED_TEXT}

    def _handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        """文字起こしの依頼を受けて記録し、202 とジョブの ID を返す。"""
        length = int(handler.headers.get("Content-Length", "0"))
        body = handler.rfile.read(length)
        if self.mode == "unsupported" or handler.path != "/web/transcriptions":
            _reply(handler, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})
            return
        with self._lock:
            self.jobs.append(_parse_job(handler.headers.get("Content-Type", ""), body))
        _reply(handler, HTTPStatus.ACCEPTED, {"job_id": JOB_ID})


def _parse_job(content_type: str, body: bytes) -> ReceivedJob:
    """multipart/form-data の本文から audio と glossary_preset を取り出す。"""
    message = BytesParser(policy=HTTP).parsebytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + body
    )
    audio = b""
    audio_type = ""
    preset: str | None = None
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True)
        if name == "audio":
            audio = payload
            audio_type = part.get_content_type()
        elif name == "glossary_preset":
            preset = payload.decode("utf-8")
    return ReceivedJob(audio=audio, audio_type=audio_type, preset=preset)


def _reply(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, object]) -> None:
    """JSON の本文で応答する。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def bind_closed_port() -> socket.socket:
    """127.0.0.1 の空きポートを待ち受けずに押さえたソケットを返す（つなぐと断られ、ほかのサーバーにも使われない）。"""
    held = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    held.bind((FAKE_HOST, 0))
    return held
