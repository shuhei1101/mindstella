"""launch.py（起動の手助け：プラグインのフォルダ・セッションの名前・MCP の設定）の単体テスト。"""

from __future__ import annotations

import hashlib
import io
import json
from functools import partial
from pathlib import Path
from typing import Any

import pytest

import launch

# claude plugin list --json の、mindstella 以外のプラグインの要素
OTHER_PLUGIN: dict[str, Any] = {"id": "other@market", "installPath": "/o/1.0.0"}

# claude plugin list --json の、mindstella の要素
MINDSTELLA_PLUGIN: dict[str, Any] = {"id": "mindstella@mindstella", "installPath": "/p/0.0.2"}

# セッションの名前に付けるハッシュの桁数
HASH_DIGITS = 6


def _path_hash(path: Path) -> str:
    """絶対パスの SHA-256 の 16 進の先頭 6 桁を返す。"""
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:HASH_DIGITS]


def _use_temp_root(monkeypatch: pytest.MonkeyPatch, temp_root: Path) -> None:
    """MCP の設定を書く一時フォルダの場所を temp_root にした write_mcp_config に差し替える。"""
    monkeypatch.setattr(
        launch, "write_mcp_config", partial(launch.write_mcp_config, temp_root=temp_root)
    )


def test_find_plugin_dir() -> None:
    """mindstella の installPath を返す（正常系）。"""
    # 実行
    result = launch.find_plugin_dir([OTHER_PLUGIN, MINDSTELLA_PLUGIN])
    # 検証
    assert result == Path("/p/0.0.2")


def test_find_plugin_dir_when_missing() -> None:
    """mindstella が無ければ PluginNotInstalledError（異常系）。"""
    # 実行・検証
    with pytest.raises(launch.PluginNotInstalledError):
        launch.find_plugin_dir([])


def test_session_name(tmp_path: Path) -> None:
    """フォルダ名とパスのハッシュをつなぐ（正常系）。"""
    # 準備
    folder = tmp_path / "家計簿.v2:アプリ"
    # 実行
    name = launch.session_name(folder)
    # 検証
    assert name == f"mindstella-家計簿-v2-アプリ-{_path_hash(folder)}"


def test_session_name_when_same_name_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同じ名前でも場所が違えば別の名前（正常系）。"""
    # 準備
    work = tmp_path / "仕事" / "家計簿アプリ"
    private = tmp_path / "個人" / "家計簿アプリ"
    (tmp_path / "仕事").mkdir()
    monkeypatch.chdir(tmp_path / "仕事")
    # 実行
    work_name = launch.session_name(work)
    private_name = launch.session_name(private)
    relative_name = launch.session_name(Path("家計簿アプリ"))
    # 検証
    assert work_name != private_name
    assert relative_name == work_name


def test_write_mcp_config(tmp_path: Path) -> None:
    """今の版のサーバーを指す設定を書く（正常系）。"""
    # 実行
    config = launch.write_mcp_config(Path("/v/bin/python"), Path("/p/0.0.2"), temp_root=tmp_path)
    # 検証
    assert config.name == "mcp.json"
    assert config.parent.parent == tmp_path
    assert config.parent.name.startswith("mindstella-")
    assert json.loads(config.read_text(encoding="utf-8")) == {
        "mcpServers": {
            "mindstella": {
                "command": "/v/bin/python",
                "args": ["/p/0.0.2/skills/mindmap/scripts/server.py"],
            }
        }
    }


@pytest.mark.parametrize(
    ("env", "expected_env"),
    [
        pytest.param(
            {"MINDSTELLA_ALLOWED_HOSTS": "preview.example.test"},
            {"MINDSTELLA_ALLOWED_HOSTS": "preview.example.test"},
            id="env_set",
        ),
        pytest.param({}, None, id="env_empty"),
    ],
)
def test_write_mcp_config_when_env_set(
    tmp_path: Path, env: dict[str, str], expected_env: dict[str, str] | None
) -> None:
    """渡す環境変数があれば env に書き、無ければ env を持たない（正常系）。"""
    # 実行
    config = launch.write_mcp_config(
        Path("/v/bin/python"), Path("/p/0.0.2"), temp_root=tmp_path, env=env
    )
    # 検証
    server_config = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]["mindstella"]
    assert server_config.get("env") == expected_env
    assert ("env" in server_config) is (expected_env is not None)


def test_external_env() -> None:
    """設定されているキーだけを返す（正常系）。"""
    # 準備
    environ = {
        "MINDSTELLA_ALLOWED_HOSTS": "preview.example.test",
        "MINDSTELLA_PREVIEW_START_HOOK": "",
        "PATH": "/bin",
    }
    # 実行
    result = launch.external_env(environ)
    # 検証
    assert result == {"MINDSTELLA_ALLOWED_HOSTS": "preview.example.test"}


def test_run_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """3 つの値を 1 行ずつ出す（正常系）。"""
    # 準備
    folder = tmp_path / "家計簿アプリ"
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    _use_temp_root(monkeypatch, temp_root)
    stdin = io.StringIO(json.dumps([OTHER_PLUGIN, MINDSTELLA_PLUGIN]))
    # 実行
    exit_code = launch.run_launch(
        ["--python", "/v/bin/python", "--folder", str(folder)], stdin=stdin
    )
    # 検証
    assert exit_code == 0
    lines = capsys.readouterr().out.splitlines()
    configs = list(temp_root.glob("mindstella-*/mcp.json"))
    assert len(configs) == 1
    assert lines == [
        "/p/0.0.2",
        f"mindstella-家計簿アプリ-{_path_hash(folder)}",
        str(configs[0]),
    ]


def test_run_launch_when_plugin_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """プラグインが無ければ案内して 1（正常系）。"""
    # 準備
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    _use_temp_root(monkeypatch, temp_root)
    # 実行
    exit_code = launch.run_launch(
        ["--python", "/v/bin/python", "--folder", str(tmp_path / "家計簿アプリ")],
        stdin=io.StringIO("[]"),
    )
    # 検証
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mindstella@mindstella" in captured.err
    assert captured.out == ""
    assert list(temp_root.iterdir()) == []


@pytest.mark.parametrize(
    "text", [pytest.param("{", id="not_json"), pytest.param("{}", id="not_array")]
)
def test_run_launch_when_listing_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    """一覧を読めなければ 1（正常系）。"""
    # 実行
    exit_code = launch.run_launch(
        ["--python", "/v/bin/python", "--folder", str(tmp_path / "家計簿アプリ")],
        stdin=io.StringIO(text),
    )
    # 検証
    assert exit_code == 1
    assert capsys.readouterr().err.startswith("[mindstella] エラー: ")
