"""環境変数で文字起こしの実装を選び、URL を確かめて作る。

常駐サーバーの起動の入口だけが import する。import は一方向（入口 → 引き当て → 実装 → 抽象）。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from transcriber import Transcriber
from voice_paste import VoicePasteTranscriber

# 実装を選ぶ環境変数の名前
TRANSCRIBER_ENV = "MINDSTELLA_TRANSCRIBER"

# サービスの待ち受けの URL を読む環境変数の名前
TRANSCRIBER_URL_ENV = "MINDSTELLA_TRANSCRIBER_URL"

# MINDSTELLA_TRANSCRIBER が無いか空のときの実装の名前
DEFAULT_TRANSCRIBER = "voice-paste"

# MINDSTELLA_TRANSCRIBER_URL が無いか空のときの URL
DEFAULT_TRANSCRIBER_URL = "http://127.0.0.1:47823"

# MINDSTELLA_TRANSCRIBER の値 → URL を受けて実装を作る関数。別のサービスを足すときは、実装のモジュールとこの行を足す
TRANSCRIBER_FACTORIES: dict[str, Callable[[str], Transcriber]] = {
    "voice-paste": lambda base_url: VoicePasteTranscriber(base_url=base_url),
}

# MINDSTELLA_TRANSCRIBER_URL に許す形（127.0.0.1 か localhost の http。末尾の / は許す）
URL_PATTERN = re.compile(r"\Ahttp://(?:127\.0\.0\.1|localhost):(\d{1,5})/?\Z")

# ポートの範囲
MIN_PORT = 1
MAX_PORT = 65535


class InvalidTranscriberError(ValueError):
    """MINDSTELLA_TRANSCRIBER が実装の一覧に無いか、MINDSTELLA_TRANSCRIBER_URL が許す形でない。"""

    def __init__(self, key: str, value: str) -> None:
        super().__init__(f"{key} の値が誤りです: {value}")
        # 誤っていた環境変数の名前
        self.key = key
        # 誤っていた値
        self.value = value


def load_transcriber(environ: Mapping[str, str]) -> Transcriber:
    """環境変数で選んだ実装を、環境変数の URL で作って返す。"""
    # 実装の名前（無いか空なら既定）
    name = environ.get(TRANSCRIBER_ENV, "").strip() or DEFAULT_TRANSCRIBER
    factory = TRANSCRIBER_FACTORIES.get(name)
    if factory is None:
        raise InvalidTranscriberError(TRANSCRIBER_ENV, name)
    # 待ち受けの URL（無いか空なら既定）
    url = environ.get(TRANSCRIBER_URL_ENV, "").strip() or DEFAULT_TRANSCRIBER_URL
    matched = URL_PATTERN.match(url)
    if matched is None or not MIN_PORT <= int(matched.group(1)) <= MAX_PORT:
        raise InvalidTranscriberError(TRANSCRIBER_URL_ENV, url)
    return factory(url.rstrip("/"))
