"""ワークスペースのファイルのフォルダのパスの解決・Range の解釈・返却する範囲の決定・分けた書き出し。"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Literal
from urllib.parse import unquote

# 記録のフォルダ `.mindstella/` の中のファイルのフォルダの名前
FILES_DIR = "files"

# 配信がファイルを返却するパスの頭
FILES_PATH = "/files/"

# 小文字の拡張子から検索する Content-Type（表に無い拡張子は FILE_DEFAULT_TYPE）
FILE_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
FILE_DEFAULT_TYPE = "application/octet-stream"

# ファイルから参照して応答へ書き出す 1 回のバイト数（配信が音声の本文を読む単位と同じ）
FILE_WRITE_CHUNK = 65536

# 200・206・416 に共通して付けるヘッダー
FILE_HEADERS: tuple[tuple[str, str], ...] = (
    ("Accept-Ranges", "bytes"),
    ("Cache-Control", "no-cache"),
    ("X-Content-Type-Options", "nosniff"),
    ("Content-Security-Policy", "sandbox"),
)

# `bytes=` より後ろの 1 つの範囲（始め・終わりのどちらかが空でもよい）
_RANGE_PATTERN = re.compile(r"(\d*)-(\d*)")


@dataclass(frozen=True, slots=True, kw_only=True)
class FilePlan:
    """書き出す前に決めた、ステータス・ヘッダー・書き出すファイルの範囲。"""

    # 200 / 206 / 416
    status: int
    content_type: str
    # 書き出すファイル（解決済みの絶対パス）
    path: Path
    size: int
    # 書き出す最初のバイトの位置と、書き出すバイト数（416 はどちらも 0）
    start: int
    length: int
    # Content-Type と Content-Length のほかに付けるヘッダー
    headers: tuple[tuple[str, str], ...]


def resolve_file(files_dir: Path, sub_path: str) -> Path | None:
    """`/files/` より後ろのパスを、ファイルのフォルダの配下の通常のファイルに解決する。外部を指す・無い・フォルダなら None。"""
    decoded = unquote(sub_path)
    # 空のパスと NUL を含むパスはファイルを指さない
    if not decoded or "\0" in decoded:
        return None
    base = files_dir.resolve()
    # シンボリックリンクをたどった先で、フォルダの配下かを確認する
    target = (files_dir / decoded).resolve()
    if not target.is_relative_to(base):
        return None
    # 無い・フォルダは返却しない
    if not target.is_file():
        return None
    return target


def parse_range(header: str | None, size: int) -> tuple[int, int] | Literal["whole", "unsatisfiable"]:
    """`Range` の値とファイルの大きさから、返却する範囲（始めと終わり。どちらも含む）を求める。"""
    # Range が無い・バイト以外の単位は全体を返却する
    if header is None or not header.startswith("bytes="):
        return "whole"
    spec = header.removeprefix("bytes=")
    # 複数の範囲は受けず、全体を返却する
    if "," in spec:
        return "whole"
    matched = _RANGE_PATTERN.fullmatch(spec.strip())
    # 構造の合わない値（数字以外・両方が空）は全体を返却する
    if matched is None or (not matched[1] and not matched[2]):
        return "whole"
    first, last = matched[1], matched[2]
    if not first:
        # 末尾からの長さ: 長さ 0 と空のファイルは返却できる範囲が無い
        suffix = int(last)
        if size == 0 or suffix == 0:
            return "unsatisfiable"
        return (max(size - suffix, 0), size - 1)
    start = int(first)
    # 始めが終わりより後ろの値は全体を返却する
    if last and start > int(last):
        return "whole"
    # 始めがファイルの外部
    if start >= size:
        return "unsatisfiable"
    end = size - 1 if not last else min(int(last), size - 1)
    return (start, end)


def plan_file(path: Path, range_header: str | None) -> FilePlan:
    """解決したファイルと `Range` から、200・206・416 のどれで何を書き出すかを決める。"""
    size = path.stat().st_size
    content_type = FILE_TYPES.get(path.suffix.lower(), FILE_DEFAULT_TYPE)
    resolved = parse_range(range_header, size)
    if resolved == "whole":
        # 全体
        return FilePlan(
            status=HTTPStatus.OK,
            content_type=content_type,
            path=path,
            size=size,
            start=0,
            length=size,
            headers=FILE_HEADERS,
        )
    if resolved == "unsatisfiable":
        # ファイルの範囲外: 本文を持たない 416
        return FilePlan(
            status=HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE,
            content_type=content_type,
            path=path,
            size=size,
            start=0,
            length=0,
            headers=(*FILE_HEADERS, ("Content-Range", f"bytes */{size}")),
        )
    # 1 つの範囲
    start, end = resolved
    return FilePlan(
        status=HTTPStatus.PARTIAL_CONTENT,
        content_type=content_type,
        path=path,
        size=size,
        start=start,
        length=end - start + 1,
        headers=(*FILE_HEADERS, ("Content-Range", f"bytes {start}-{end}/{size}")),
    )


def write_file(plan: FilePlan, write: Callable[[bytes], object]) -> None:
    """計画の範囲を FILE_WRITE_CHUNK ずつ参照して、指定した書き込みの関数へ指定する。"""
    if plan.length == 0:
        return
    remaining = plan.length
    with plan.path.open("rb") as stream:
        stream.seek(plan.start)
        while remaining > 0:
            chunk = stream.read(min(FILE_WRITE_CHUNK, remaining))
            # 書き出す途中でファイルが縮んだ
            if not chunk:
                return
            write(chunk)
            remaining -= len(chunk)
