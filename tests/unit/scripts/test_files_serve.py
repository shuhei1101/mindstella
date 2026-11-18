"""files_serve.py（ファイルのフォルダのパスの解決・Range の解釈・返す範囲の決定・分けた書き出し）の単体テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import files_serve

# 応答の計画のテストで使うファイルの大きさ（バイト）
FILE_SIZE = 1000


@pytest.fixture
def files_dir(tmp_path: Path) -> Path:
    """ワークスペースのファイルのフォルダ（`clip.mp4`・`img/shot a.png` を配置し、フォルダの外部に `decisions.yaml`・`secret.txt` を配置する）を返却する。"""
    records = tmp_path / ".mindstella"
    folder = records / files_serve.FILES_DIR
    (folder / "img").mkdir(parents=True)
    (folder / "clip.mp4").write_bytes(b"\x00" * FILE_SIZE)
    (folder / "img" / "shot a.png").write_bytes(b"png")
    (records / "decisions.yaml").write_text("items: []\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    # フォルダの外部のファイルを指すシンボリックリンク
    (folder / "outside").symlink_to(tmp_path / "secret.txt")
    return folder


def _collect(chunks: list[bytes]) -> Callable[[bytes], object]:
    """受け取ったバイト列を chunks へ追加する書き込みの関数を返却する。"""

    def _write(data: bytes) -> None:
        """応答の本文へ記載する代わりに記録する。"""
        chunks.append(data)

    return _write


def test_resolve_file(files_dir: Path) -> None:
    """配下のファイルを解決する（正常系）。"""
    # 準備
    expected_clip = (files_dir / "clip.mp4").resolve()
    expected_shot = (files_dir / "img" / "shot a.png").resolve()
    # 実行
    clip = files_serve.resolve_file(files_dir, "clip.mp4")
    shot = files_serve.resolve_file(files_dir, "img/shot%20a.png")
    # 検証
    assert clip == expected_clip
    assert shot == expected_shot


@pytest.mark.parametrize(
    "sub_path",
    [
        pytest.param("../decisions.yaml", id="parent"),
        pytest.param("%2e%2e/decisions.yaml", id="encoded_parent"),
        pytest.param("outside", id="symlink"),
        pytest.param("/etc/passwd", id="absolute"),
    ],
)
def test_resolve_file_when_outside(files_dir: Path, sub_path: str) -> None:
    """フォルダの外部を指すパスは None（正常系）。"""
    # 準備
    # 実行
    resolved = files_serve.resolve_file(files_dir, sub_path)
    # 検証
    assert resolved is None


@pytest.mark.parametrize(
    ("folder", "sub_path"),
    [
        pytest.param(files_serve.FILES_DIR, "missing.mp4", id="missing"),
        pytest.param(files_serve.FILES_DIR, "img", id="folder"),
        pytest.param(files_serve.FILES_DIR, "", id="empty"),
        pytest.param(files_serve.FILES_DIR, "a%00b", id="nul"),
        pytest.param("absent", "clip.mp4", id="files_dir_missing"),
    ],
)
def test_resolve_file_when_not_file(files_dir: Path, folder: str, sub_path: str) -> None:
    """無い・フォルダ・空・NUL と、ファイルのフォルダが無いときは None（正常系）。"""
    # 準備
    target = files_dir.parent / folder
    # 実行
    resolved = files_serve.resolve_file(target, sub_path)
    # 検証
    assert resolved is None


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        pytest.param("bytes=100-199", (100, 199), id="closed"),
        pytest.param("bytes=900-", (900, 999), id="open_end"),
        pytest.param("bytes=-50", (950, 999), id="suffix"),
        pytest.param("bytes=990-2000", (990, 999), id="end_over"),
        pytest.param("bytes=-2000", (0, 999), id="suffix_over"),
    ],
)
def test_parse_range(header: str, expected: tuple[int, int]) -> None:
    """1 つの範囲を解釈する（正常系）。"""
    # 準備
    # 実行
    result = files_serve.parse_range(header, 1000)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    "header",
    [
        pytest.param(None, id="none"),
        pytest.param("items=0-1", id="unit"),
        pytest.param("bytes=0-1,5-6", id="multiple"),
        pytest.param("bytes=a-b", id="not_number"),
        pytest.param("bytes=5-2", id="reversed"),
        pytest.param("bytes=-", id="both_empty"),
    ],
)
def test_parse_range_when_whole(header: str | None) -> None:
    """受けない値は全体（正常系）。"""
    # 準備
    # 実行
    result = files_serve.parse_range(header, 1000)
    # 検証
    assert result == "whole"


@pytest.mark.parametrize(
    ("header", "size"),
    [
        pytest.param("bytes=1000-", 1000, id="start_at_size"),
        pytest.param("bytes=-0", 1000, id="suffix_zero"),
        pytest.param("bytes=0-", 0, id="empty_file"),
        pytest.param("bytes=-10", 0, id="empty_file_suffix"),
    ],
)
def test_parse_range_when_unsatisfiable(header: str, size: int) -> None:
    """ファイルの範囲外（正常系）。"""
    # 準備
    # 実行
    result = files_serve.parse_range(header, size)
    # 検証
    assert result == "unsatisfiable"


def test_plan_file(files_dir: Path) -> None:
    """全体を返却する計画（正常系）。"""
    # 準備
    path = (files_dir / "clip.mp4").resolve()
    # 実行
    plan = files_serve.plan_file(path, None)
    # 検証
    assert plan.status == 200
    assert plan.content_type == "video/mp4"
    assert plan.path == path
    assert plan.size == 1000
    assert plan.start == 0
    assert plan.length == 1000
    assert dict(plan.headers) == {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    }


def test_plan_file_when_range(files_dir: Path) -> None:
    """範囲を返却する計画（正常系）。"""
    # 準備
    path = (files_dir / "clip.mp4").resolve()
    # 実行
    plan = files_serve.plan_file(path, "bytes=100-199")
    # 検証
    assert plan.status == 206
    assert plan.start == 100
    assert plan.length == 100
    assert dict(plan.headers)["Content-Range"] == "bytes 100-199/1000"
    assert dict(plan.headers)["Accept-Ranges"] == "bytes"


def test_plan_file_when_unsatisfiable(files_dir: Path) -> None:
    """416 の計画（正常系）。"""
    # 準備
    path = (files_dir / "clip.mp4").resolve()
    # 実行
    plan = files_serve.plan_file(path, "bytes=1000-")
    # 検証
    assert plan.status == 416
    assert plan.length == 0
    assert dict(plan.headers)["Content-Range"] == "bytes */1000"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        pytest.param("a.bin", "application/octet-stream", id="unknown"),
        pytest.param("B.PNG", "image/png", id="upper"),
    ],
)
def test_plan_file_when_unknown_suffix(tmp_path: Path, name: str, expected: str) -> None:
    """表に無い拡張子と大文字の拡張子（正常系）。"""
    # 準備
    path = tmp_path / name
    path.write_bytes(b"data")
    # 実行
    plan = files_serve.plan_file(path, None)
    # 検証
    assert plan.content_type == expected


def test_write_file(tmp_path: Path) -> None:
    """範囲を分けて書き出す（正常系）。"""
    # 準備
    # FILE_WRITE_CHUNK（65536）の 2.5 倍の 163840 バイト
    data = bytes(range(256)) * 640
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)
    whole = files_serve.plan_file(path, None)
    part = files_serve.plan_file(path, "bytes=10-109")
    whole_chunks: list[bytes] = []
    part_chunks: list[bytes] = []
    # 実行
    files_serve.write_file(whole, _collect(whole_chunks))
    files_serve.write_file(part, _collect(part_chunks))
    # 検証
    assert len(whole_chunks) == 3
    assert b"".join(whole_chunks) == data
    assert b"".join(part_chunks) == data[10:110]


def test_write_file_when_empty(files_dir: Path) -> None:
    """長さ 0 は書き出さない（正常系）。"""
    # 準備
    plan = files_serve.plan_file((files_dir / "clip.mp4").resolve(), "bytes=1000-")
    chunks: list[bytes] = []
    # 実行
    files_serve.write_file(plan, _collect(chunks))
    # 検証
    assert chunks == []
