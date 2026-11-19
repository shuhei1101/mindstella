"""home_settings.py（mindstella のホームの設定の読み込み）の単体テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

import home_settings
from home_settings import HomeSettings, InvalidSettingsError


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        pytest.param(
            {"XDG_CONFIG_HOME": "/x", "HOME": "/h"},
            Path("/x/mindstella/settings.yaml"),
            id="xdg",
        ),
        pytest.param({"HOME": "/h"}, Path("/h/.config/mindstella/settings.yaml"), id="home"),
    ],
)
def test_home_settings_path(environ: dict[str, str], expected: Path) -> None:
    """XDG_CONFIG_HOME の有無で場所が変わる（正常系）。"""
    # 実行
    result = home_settings.home_settings_path(environ)
    # 検証
    assert result == expected


def _settings_file(folder: Path, content: str | None) -> Path:
    """設定のファイルのパスを返す。content が None ならファイルを作らない。"""
    path = folder / "settings.yaml"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("content", "expected", "query_url"),
    [
        pytest.param(None, HomeSettings(None, True), "http://127.0.0.1:8770", id="missing"),
        pytest.param("", HomeSettings(None, True), "http://127.0.0.1:8770", id="empty"),
        pytest.param(
            "claude_balancer:\n  url: http://127.0.0.1:8780\naccount:\n  release_on_limit: false\n",
            HomeSettings("http://127.0.0.1:8780", False),
            "http://127.0.0.1:8780",
            id="nested",
        ),
    ],
)
def test_load_home_settings(
    content: str | None, expected: HomeSettings, query_url: str, tmp_path: Path
) -> None:
    """ファイルの有無とキーで値が決まる（正常系）。"""
    # 準備
    path = _settings_file(tmp_path, content)
    # 実行
    result = home_settings.load_home_settings(path)
    # 検証
    assert result == expected
    assert result.query_url() == query_url


def test_load_home_settings_when_unknown_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """知らないキーは記録して読み飛ばす（正常系）。"""
    # 準備
    path = tmp_path / "settings.yaml"
    path.write_text(
        'foo: 1\naccount:\n  bar: 2\n"claude_balancer.url": http://x\n', encoding="utf-8"
    )
    # 実行
    result = home_settings.load_home_settings(path)
    # 検証
    assert result == HomeSettings(None, True)
    err = capsys.readouterr().err
    assert len(err.splitlines()) == 3
    assert "foo" in err
    assert "account.bar" in err
    assert "claude_balancer.url" in err


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("claude_balancer: [\n", id="syntax"),
        pytest.param("- 1\n- 2\n", id="list"),
        pytest.param("claude_balancer: 1\n", id="balancer-not-mapping"),
        pytest.param("account:\n  - true\n", id="account-not-mapping"),
        pytest.param("claude_balancer:\n  url: ftp://x\n", id="url"),
        pytest.param('account:\n  release_on_limit: "no"\n', id="release"),
    ],
)
def test_load_home_settings_when_invalid(content: str, tmp_path: Path) -> None:
    """読めない・型が違うときは InvalidSettingsError（異常系）。"""
    # 準備
    path = tmp_path / "settings.yaml"
    path.write_text(content, encoding="utf-8")
    # 実行・検証
    with pytest.raises(InvalidSettingsError, match=r"settings\.yaml"):
        home_settings.load_home_settings(path)
