"""ワークスペースのファイルの配信（GET /files/{path}）の結合テスト。"""

from __future__ import annotations

import http.client
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


from .fixture_types import MakeItem, MakeWorkspace
from .http_helpers import HTTP_TIMEOUT_SEC, workspace_path

# ファイルのフォルダ（ワークスペースの直下からの相対パス）
FILES_DIR = "files"

# 範囲の要求で使用する 1000 バイトのファイルの中身（バイトの位置が値から分かる並び）
CLIP_BYTES = bytes(range(250)) * 4

# 画像のファイルの中身（png の頭のバイトを持つ）
SHOT_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24

# ワークスペースの外部に配置するファイルの中身の目印
OUTSIDE_MARK = b"outside-secret"


@dataclass(frozen=True)
class RawResult:
    """本文をバイト列のまま持つ HTTP の応答。ヘッダー名は小文字で引く。"""

    status: int
    headers: dict[str, str]
    body: bytes


def _get(base_url: str, path: str, headers: dict[str, str] | None = None) -> RawResult:
    """配信の URL のワークスペースの経路の下のパスを、正規化せずに 1 回 GET し、本文をバイト列で返却する。"""
    parts = urlsplit(base_url)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=HTTP_TIMEOUT_SEC)
    try:
        connection.request("GET", workspace_path(base_url, path), headers=headers or {})
        response = connection.getresponse()
        return RawResult(
            status=response.status,
            headers={name.lower(): value for name, value in response.getheaders()},
            body=response.read(),
        )
    finally:
        connection.close()


def _port(url: str) -> int:
    """配信の URL のポートを返却する。"""
    port = urlsplit(url).port
    assert port is not None
    return port


def _put_file(root: Path, name: str, data: bytes) -> None:
    """ワークスペースのファイルのフォルダに、name のファイルを配置する。"""
    path = root / FILES_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """ファイルのフォルダのファイルを、拡張子に合う Content-Type で返却する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _put_file(root, "clip.mp4", CLIP_BYTES)
    _put_file(root, "img/shot.png", SHOT_BYTES)
    url = serve_preview(root)
    # 実行
    clip = _get(url, "/files/clip.mp4")
    shot = _get(url, "/files/img/shot.png")
    # 検証
    assert clip.status == 200
    assert clip.headers["content-type"] == "video/mp4"
    assert clip.headers["accept-ranges"] == "bytes"
    assert clip.headers["content-length"] == "1000"
    assert clip.headers["content-security-policy"] == "sandbox"
    assert clip.body == CLIP_BYTES
    assert shot.status == 200
    assert shot.headers["content-type"] == "image/png"
    assert shot.body == SHOT_BYTES


def test_normal_when_range(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """`Range` の要求に、要求した範囲だけを部分の応答で返却する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _put_file(root, "clip.mp4", CLIP_BYTES)
    url = serve_preview(root)
    # 実行
    closed = _get(url, "/files/clip.mp4", {"Range": "bytes=100-199"})
    open_end = _get(url, "/files/clip.mp4", {"Range": "bytes=900-"})
    suffix = _get(url, "/files/clip.mp4", {"Range": "bytes=-50"})
    # 検証
    assert closed.status == 206
    assert closed.headers["content-range"] == "bytes 100-199/1000"
    assert closed.headers["content-length"] == "100"
    assert closed.body == CLIP_BYTES[100:200]
    assert open_end.status == 206
    assert open_end.headers["content-range"] == "bytes 900-999/1000"
    assert open_end.body == CLIP_BYTES[900:]
    assert suffix.status == 206
    assert suffix.headers["content-range"] == "bytes 950-999/1000"
    assert suffix.body == CLIP_BYTES[950:]


def test_error_when_range_not_satisfiable(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """ファイルの大きさを超えた範囲は 416 を返却する（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _put_file(root, "clip.mp4", CLIP_BYTES)
    url = serve_preview(root)
    # 実行
    result = _get(url, "/files/clip.mp4", {"Range": "bytes=1000-"})
    # 検証
    assert result.status == 416
    assert result.headers["content-range"] == "bytes */1000"
    assert result.body == b""


def test_error_when_not_found_or_outside(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """無いファイルと、ファイルのフォルダの外部を指すパスは 404 を返却する（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _put_file(root, "clip.mp4", CLIP_BYTES)
    outside = root.parent / "outside-secret.txt"
    outside.write_bytes(OUTSIDE_MARK)
    (root / FILES_DIR / "outside").symlink_to(outside)
    url = serve_preview(root)
    # 実行（`..` は正規化せずにそのまま送信する）
    missing = _get(url, "/files/missing.mp4")
    parent = _get(url, "/files/../.mindstella/decisions.yaml")
    encoded = _get(url, "/files/%2e%2e/.mindstella/decisions.yaml")
    symlink = _get(url, "/files/outside")
    folder = _get(url, "/files/")
    # 検証
    assert missing.status == 404
    assert missing.headers["content-type"].startswith("application/problem+json")
    assert parent.status == 404
    assert parent.headers["content-type"].startswith("application/problem+json")
    assert b"items:" not in parent.body
    assert encoded.status == 404
    assert encoded.headers["content-type"].startswith("application/problem+json")
    assert b"items:" not in encoded.body
    assert symlink.status == 404
    assert symlink.headers["content-type"].startswith("application/problem+json")
    assert OUTSIDE_MARK not in symlink.body
    assert folder.status == 404
    assert folder.headers["content-type"].startswith("application/problem+json")
    assert b"clip.mp4" not in folder.body


def test_error_when_host_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """Host が端末の中の名前でなければファイルを返却しない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _put_file(root, "clip.mp4", CLIP_BYTES)
    url = serve_preview(root)
    # 実行
    result = _get(url, "/files/clip.mp4", {"Host": f"attacker.example:{_port(url)}"})
    # 検証
    assert result.status == 403
    assert CLIP_BYTES not in result.body
