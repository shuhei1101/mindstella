"""文字起こしのインターフェースの voice-paste の実装。

プリセットの一覧を読み、音声を multipart/form-data で依頼し、ジョブの状態を取りに行って終わるまで待つ。
HTTP は標準ライブラリの urllib.request で送り、文字起こし（抽象）だけに依存する。
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from http.client import HTTPResponse
from typing import Any, Literal

from transcriber import (
    TranscriberStoppedError,
    TranscriberUnsupportedError,
    TranscriptionFailedError,
    TranscriptionTimeoutError,
)

logger = logging.getLogger(__name__)

# プリセットの一覧のパス
PRESETS_PATH = "/web/glossary-presets"

# 文字起こしのジョブのパス（`/{job_id}` を足すと状態の読み取り）
JOBS_PATH = "/web/transcriptions"

# 1 回の要求を打ち切る秒数（非機能要件「文字起こしのサービスの応答の上限」）
REQUEST_TIMEOUT_SEC = 66.0

# state・progress が変わらないまま待てる秒数（非機能要件「文字起こしの待ちの上限」）
WAIT_LIMIT_SEC = 120.0

# 状態を取りに行く間隔（非機能要件「文字起こしの状態を取りに行く間隔」）
POLL_INTERVAL_SEC = 1.0

# Content-Type の `;` より前（小文字）→ audio のファイル名の拡張子
AUDIO_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
}

# 一覧に無い Content-Type の拡張子
UNKNOWN_EXTENSION = "bin"

# 待つ間に読み直す state（これ以外は終わり）
PENDING_STATES = ("queued", "running")

type Opener = Callable[..., HTTPResponse]


def _default_opener() -> Opener:
    """環境変数のプロキシを通さずに送る opener の open を返す。"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open


@dataclass(frozen=True, slots=True, kw_only=True)
class VoicePasteTranscriber:
    """文字起こしのインターフェースを、voice-paste の 3 つのエンドポイントで満たす。"""

    # 待ち受けの URL（末尾の `/` を除いたもの）
    base_url: str
    # 要求を送る関数。`opener(要求, timeout=秒数)` で呼ぶ（2 番目の位置引数は data のため、待ちの上限はキーワードで渡す）
    opener: Opener = field(default_factory=_default_opener)
    # 状態を取りに行く前に待つ関数
    sleep: Callable[[float], None] = time.sleep
    # 待ちの上限を数える時計
    clock: Callable[[], float] = time.monotonic

    def presets(self) -> list[str]:
        """GET /web/glossary-presets を読み、presets を返す。"""
        try:
            status, payload = self._request("GET", PRESETS_PATH)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            raise TranscriberStoppedError(f"{PRESETS_PATH} に届かない: {error}") from error
        # Linux で動いている: /web/ の下が無い
        if status == HTTPStatus.NOT_FOUND:
            raise TranscriberUnsupportedError(f"{PRESETS_PATH} が 404 です")
        if status != HTTPStatus.OK:
            logger.warning("文字起こしのサービスがプリセットの一覧に %s を返した", status)
            raise TranscriberStoppedError(f"{PRESETS_PATH} が {status} を返した")
        presets = payload.get("presets") if isinstance(payload, dict) else None
        # 形が違う: 使えないとして扱う
        if not isinstance(presets, list) or not all(isinstance(name, str) for name in presets):
            logger.warning("文字起こしのサービスのプリセットの一覧の形が違う")
            raise TranscriberStoppedError(f"{PRESETS_PATH} の presets が文字列の配列でない")
        return presets

    def transcribe(self, audio: bytes, content_type: str, *, preset: str | None) -> str:
        """音声を 1 回依頼し、ジョブの状態を取りに行って終わるまで待つ。"""
        job_id = self._submit(audio, content_type, preset)
        return self._wait(job_id)

    def _submit(self, audio: bytes, content_type: str, preset: str | None) -> str:
        """POST /web/transcriptions で依頼し、job_id を返す（再試行しない）。"""
        body, multipart_type = self._multipart(audio, content_type, preset=preset)
        try:
            status, payload = self._request("POST", JOBS_PATH, body=body, content_type=multipart_type)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            logger.warning("文字起こしに失敗した: 依頼が届かない（%s）", error)
            raise TranscriberStoppedError(f"{JOBS_PATH} に届かない: {error}") from error
        # 音声を受け付けるエンドポイントが無い
        if status == HTTPStatus.NOT_FOUND:
            logger.warning("文字起こしに失敗した: %s が 404", JOBS_PATH)
            raise TranscriberUnsupportedError(f"{JOBS_PATH} が 404 です")
        # 依頼を受け付けなかった（上限・音声として読めない・ジョブの待ちが一杯など）
        if status != HTTPStatus.ACCEPTED:
            detail = payload.get("detail") if isinstance(payload, dict) else None
            logger.warning("文字起こしに失敗した: 依頼が %s（%s）", status, detail)
            raise TranscriptionFailedError(f"依頼が {status} でした: {detail}")
        job_id = payload.get("job_id") if isinstance(payload, dict) else None
        if not isinstance(job_id, str):
            logger.warning("文字起こしに失敗した: job_id が無い")
            raise TranscriptionFailedError("依頼の応答に job_id がありません")
        return job_id

    def _wait(self, job_id: str) -> str:
        """ジョブが done か failed になるまで取りに行き、進まないまま上限を超えたら打ち切る。"""
        path = f"{JOBS_PATH}/{job_id}"
        last_seen: tuple[Any, Any] | None = None
        last_progress_at = self.clock()
        while True:
            self.sleep(POLL_INTERVAL_SEC)
            try:
                status, payload = self._request("GET", path)
            except TimeoutError:
                # 1 回の要求が打ち切られた: 待ちを続ける（進まない時間に数える）
                status, payload = None, None
            except (urllib.error.URLError, ConnectionError) as error:
                # 1 回の要求が打ち切られたときは URLError が TimeoutError を包む
                if isinstance(getattr(error, "reason", None), TimeoutError):
                    status, payload = None, None
                else:
                    logger.warning("文字起こしに失敗した: 待つ間に接続を断られた（%s）", error)
                    raise TranscriberStoppedError(f"{path} に届かない: {error}") from error
            # ジョブが無い（再起動した・終わったジョブを持つ件数を超えた）
            if status == HTTPStatus.NOT_FOUND:
                logger.warning("文字起こしに失敗した: ジョブ %s が無い", job_id)
                raise TranscriptionFailedError(f"ジョブ {job_id} がありません")
            if status is not None and status != HTTPStatus.OK:
                logger.warning("文字起こしのサービスがジョブの状態に %s を返した", status)
            if status == HTTPStatus.OK and isinstance(payload, dict):
                state = payload.get("state")
                if state == "done":
                    text = payload.get("text")
                    return text if isinstance(text, str) else ""
                if state == "failed":
                    logger.warning("文字起こしに失敗した: %s", payload.get("error"))
                    raise TranscriptionFailedError(f"文字起こしに失敗しました: {payload.get('error')}")
                seen = (state, payload.get("progress"))
                # 進んだ: 控えと最後に進んだ時刻を書き換える
                if seen != last_seen:
                    last_seen = seen
                    last_progress_at = self.clock()
                    continue
            if self.clock() - last_progress_at > WAIT_LIMIT_SEC:
                logger.warning("文字起こしに失敗した: ジョブ %s が %s 秒進まない", job_id, WAIT_LIMIT_SEC)
                raise TranscriptionTimeoutError(f"ジョブ {job_id} が進みません")

    def _request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> tuple[int, Any]:
        """1 回の要求を REQUEST_TIMEOUT_SEC で送り、ステータスと本文の JSON（読めなければ None）を返す。"""
        headers = {} if content_type is None else {"Content-Type": content_type}
        # Origin を付けない（voice-paste は Origin の無い要求だけを受ける）
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, method=method, headers=headers)
        try:
            with self.opener(request, timeout=REQUEST_TIMEOUT_SEC) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            # 4xx・5xx も、ステータスと本文で返す
            status = error.code
            raw = error.read()
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, ValueError):
            payload = None
        return status, payload

    def _multipart(self, audio: bytes, content_type: str, *, preset: str | None) -> tuple[bytes, str]:
        """audio と任意の glossary_preset を持つ multipart/form-data の本文と Content-Type を作る。"""
        boundary = uuid.uuid4().hex
        media = content_type.split(";")[0].strip().lower()
        extension = AUDIO_EXTENSIONS.get(media, UNKNOWN_EXTENSION)
        parts = [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="audio"; filename="audio.{extension}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            audio,
            b"\r\n",
        ]
        # プリセットがあるときだけ付ける（無ければサービスの既定）
        if preset is not None:
            parts.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    b'Content-Disposition: form-data; name="glossary_preset"\r\n\r\n',
                    preset.encode("utf-8"),
                    b"\r\n",
                ]
            )
        parts.append(f"--{boundary}--\r\n".encode())
        return b"".join(parts), f"multipart/form-data; boundary={boundary}"
