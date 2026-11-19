"""mindstella のホームの設定 `${XDG_CONFIG_HOME:-~/.config}/mindstella/settings.yaml` を読み、既定値を埋めた値を返す。"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# claude_balancer.url が無いときに利用枠の見回りがつなぐ claude-balancer の常駐の待ち受け先
DEFAULT_BALANCER_URL = "http://127.0.0.1:8770"

# 設定のファイルのフォルダとファイル名
SETTINGS_DIR = "mindstella"
SETTINGS_FILE = "settings.yaml"

# 知っているキー（最上位のキーごとに、その下に持つキー）
KNOWN_KEYS: dict[str, tuple[str, ...]] = {
    "claude_balancer": ("url",),
    "account": ("release_on_limit",),
}

# claude_balancer.url に受けるスキーム
URL_SCHEMES = ("http://", "https://")


class InvalidSettingsError(ValueError):
    """ホームの設定が読めないか値が誤っている。"""


@dataclass(frozen=True)
class HomeSettings:
    """読んだホームの設定。"""

    # claude_balancer.url。キーが無ければ None（ペインに CLAUDE_BALANCER_URL を渡さない）
    balancer_url: str | None = None
    # account.release_on_limit。指定したアカウントを利用上限・しきい値で解除するか
    release_on_limit: bool = True

    def query_url(self) -> str:
        """利用枠を問い合わせる claude-balancer の常駐の待ち受け先を返す。"""
        return self.balancer_url or DEFAULT_BALANCER_URL


def home_settings_path(environ: Mapping[str, str]) -> Path:
    """ホームの設定のファイルの絶対パスを返す。"""
    base = environ.get("XDG_CONFIG_HOME")
    # XDG_CONFIG_HOME があればその下、無ければホームの .config の下
    folder = Path(base) if base else Path(environ.get("HOME") or Path.home()) / ".config"
    return folder / SETTINGS_DIR / SETTINGS_FILE


def load_home_settings(path: Path) -> HomeSettings:
    """ホームの設定を読む。ファイルが無ければ既定値を返し、知らないキーは記録して読み飛ばす。"""
    # ファイルが無い: 全てのキーを既定値で扱う
    if not path.exists():
        return HomeSettings()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise InvalidSettingsError(f"{path}: YAML として読めません: {error}") from error
    # 空のファイル: 既定値で扱う
    if data is None:
        return HomeSettings()
    if not isinstance(data, dict):
        raise InvalidSettingsError(f"{path}: 最上位はキーと値のマッピングにしてください")
    _report_unknown(path, data)
    balancer = _section(path, data, "claude_balancer")
    account = _section(path, data, "account")
    return HomeSettings(
        balancer_url=_balancer_url(path, balancer.get("url")),
        release_on_limit=_release_on_limit(path, account.get("release_on_limit", True)),
    )


def _section(path: Path, data: dict[str, Any], key: str) -> dict[str, Any]:
    """最上位のキーの下のマッピングを返す。無ければ空のマッピング。"""
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise InvalidSettingsError(f"{path}: {key} はキーと値のマッピングにしてください")
    return value


def _balancer_url(path: Path, value: object) -> str | None:
    """claude_balancer.url を検証して返却する。"""
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith(URL_SCHEMES):
        raise InvalidSettingsError(
            f"{path}: claude_balancer.url は http:// か https:// で始まる URL にしてください"
        )
    return value


def _release_on_limit(path: Path, value: object) -> bool:
    """account.release_on_limit を検証して返却する。"""
    if not isinstance(value, bool):
        raise InvalidSettingsError(
            f"{path}: account.release_on_limit は true か false にしてください"
        )
    return value


def _report_unknown(path: Path, data: dict[str, Any]) -> None:
    """知らないキーを標準エラーへ 1 行ずつ記録する。"""
    for key, value in data.items():
        # 最上位の知らないキー（ドットを含む 1 つのキーを含む）
        if key not in KNOWN_KEYS:
            print(f"[mindstella] {path}: 知らないキーを読み飛ばします: {key}", file=sys.stderr)
            continue
        # 知っている最上位のキーの下の知らないキー
        if isinstance(value, dict):
            for child in value:
                if child not in KNOWN_KEYS[key]:
                    print(
                        f"[mindstella] {path}: 知らないキーを読み飛ばします: {key}.{child}",
                        file=sys.stderr,
                    )
