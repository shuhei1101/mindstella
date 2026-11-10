"""配信が依存する文字起こしのインターフェースと、失敗の種類・使えるかの確かめ。

サービスごとの呼び方は実装のモジュールが持ち、環境変数で実装を選ぶ処理は transcriber_registry が持つ。
このモジュールはほかのモジュールを import しない。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

logger = logging.getLogger(__name__)

# 使えない理由（サービスに届かない / 届くが音声を受け付けるエンドポイントが無い）
type UnavailableReason = Literal["stopped", "unsupported"]

# 使えない理由 → 画面に出す文（サービスの名前を含めない）
UNAVAILABLE_DETAILS: dict[UnavailableReason, str] = {
    "stopped": "文字起こしのサービスが起動していないため、音声で入力できません。",
    "unsupported": "文字起こしのサービスが音声の受け付けに対応していないため、音声で入力できません。",
}

# 文字起こしに失敗した・終わらないときに画面に出す文
FAILED_DETAIL = "文字起こしできませんでした。もう一度お試しください。"


class TranscriberError(Exception):
    """文字起こしのインターフェースが送る例外の基底。メッセージはサービスの理由（応答には出さない）。"""


class TranscriberStoppedError(TranscriberError):
    """接続を断られたか、サービスの応答の上限を超えた。"""


class TranscriberUnsupportedError(TranscriberError):
    """サービスには届くが、音声を受け付けるエンドポイントが無い。"""


class TranscriptionFailedError(TranscriberError):
    """サービスが文字起こしの失敗を返したか、依頼を受け付けなかった。"""


class TranscriptionTimeoutError(TranscriberError):
    """文字起こしの待ちの上限までに終わらない。"""


class Transcriber(Protocol):
    """配信が依存する文字起こしの契約。サービスの名前・エンドポイント・待ち方を持たない。"""

    def presets(self) -> list[str]:
        """用語集のプリセットの名前の一覧を返す。使えるかの確かめも兼ねる。"""
        ...

    def transcribe(self, audio: bytes, content_type: str, *, preset: str | None) -> str:
        """音声とプリセットを 1 回だけ渡し、終わるまで待って起こした文字を返す。"""
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class Availability:
    """文字起こしを使えるか・使えない理由・画面に出す文・用語集のプリセットの候補。"""

    available: bool
    # 使えない理由。使えるときは None
    reason: UnavailableReason | None
    # 使えない理由を画面に出す文。使えるときは None
    detail: str | None
    # サービスが返した並びのままのプリセットの候補。使えないときは空
    presets: list[str]


def _unavailable(reason: UnavailableReason) -> Availability:
    """理由の文を添えた、使えない Availability を作る。"""
    return Availability(available=False, reason=reason, detail=UNAVAILABLE_DETAILS[reason], presets=[])


def check_availability(transcriber: Transcriber | None) -> Availability:
    """文字起こしのインターフェースへプリセットの一覧を 1 回尋ね、使えるかと候補を返す（結果を持ち越さない）。"""
    # 配信が文字起こしを持たない: 届かないと同じに扱う
    if transcriber is None:
        return _unavailable("stopped")
    try:
        presets = transcriber.presets()
    except TranscriberStoppedError as error:
        logger.warning("文字起こしのサービスに届かない: %s", error)
        return _unavailable("stopped")
    except TranscriberUnsupportedError as error:
        logger.warning("文字起こしのサービスが音声を受け付けない: %s", error)
        return _unavailable("unsupported")
    return Availability(available=True, reason=None, detail=None, presets=presets)
