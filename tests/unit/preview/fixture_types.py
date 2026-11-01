"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from workspace_fixtures import MakeEdit, MakeItem

__all__ = [
    "LoadLibrary",
    "LoadMdmark",
    "LoadPreviewScripts",
    "LoadPreviewStyles",
    "MakeData",
    "MakeEdit",
    "MakeItem",
    "MdmarkDist",
    "PutEmbeddedMdmark",
    "PutMdmarkCss",
    "PutMdmarkImportMap",
    "ServeMdmark",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class MdmarkDist:
    """外部ライブラリの設計書が固定した mdmark の JavaScript の URL・integrity・中身。"""

    # 配信元の URL（import map の `integrity` のキー）
    url: str
    # 設計書の `integrity`（`sha384-{Base64}`）
    integrity: str
    # 配布物の中身
    body: str


type LoadPreviewScripts = Callable[..., None]
type LoadPreviewStyles = Callable[[], None]
type LoadLibrary = Callable[[str], None]
type LoadMdmark = Callable[[], None]
type ServeMdmark = Callable[..., None]
type PutMdmarkImportMap = Callable[..., None]
type PutEmbeddedMdmark = Callable[[], None]
type PutMdmarkCss = Callable[..., None]
type MakeData = Callable[..., dict[str, Any]]
