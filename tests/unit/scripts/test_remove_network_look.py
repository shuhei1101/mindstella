"""migrations/v0.14.0/scripts/remove_network_look.py（ネットワークの見た目の既定を消す変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.14.0" / "scripts" / "remove_network_look.py"

# ワークスペースの直下からの設定のファイル
CONFIG_PATH = Path(".mindstella") / "config.yaml"


@pytest.fixture
def remove_network_look(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_14_0_remove_network_look", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_config(root: Path, text: str | None) -> Path:
    """ワークスペースの設定のファイルに中身を書いて、そのパスを返す。text が None なら書かない。"""
    path = root / CONFIG_PATH
    # 設定を持たないワークスペースは、記録のフォルダだけを作る
    path.parent.mkdir(parents=True, exist_ok=True)
    if text is not None:
        path.write_text(text, encoding="utf-8")
    return path


def _read_config(path: Path) -> str | None:
    """設定のファイルの中身を返す。ファイルが無ければ None を返す。"""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param(
            {"summary": "題名", "history_limit": 3, "display": {"network_look": "glow"}},
            {"summary": "題名", "history_limit": 3},
            id="display_emptied",
        ),
        pytest.param(
            {
                "summary": "題名",
                "display": {"network_look": "dust", "visible_kinds": ["decisions"]},
                "history_limit": 3,
            },
            {"summary": "題名", "display": {"visible_kinds": ["decisions"]}, "history_limit": 3},
            id="kinds_kept",
        ),
    ],
)
def test_migrate(
    remove_network_look: ModuleType,
    tmp_path: Path,
    config: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """`network_look` を消し、空になった `display` も消す（正常系）。"""
    # 準備
    path = _write_config(tmp_path, yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    # 実行
    changed = remove_network_look.migrate(tmp_path)
    # 検証（ほかのキーと並びは変えない）
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert changed == [".mindstella/config.yaml"]
    assert saved == expected
    assert list(saved) == list(expected)


@pytest.mark.parametrize(
    "config_text",
    [
        pytest.param(
            "summary: 題名\ndisplay:\n  visible_kinds:\n  - decisions\n", id="already_migrated"
        ),
        pytest.param("summary: 題名\nhistory_limit: 3\n", id="without_display"),
        pytest.param(None, id="without_config"),
    ],
)
def test_migrate_when_already_current(
    remove_network_look: ModuleType, tmp_path: Path, config_text: str | None
) -> None:
    """もう一度当てても変わらない（正常系）。"""
    # 準備
    path = _write_config(tmp_path, config_text)
    # 実行
    changed = remove_network_look.migrate(tmp_path)
    # 検証（無いファイルを作らない）
    assert changed == []
    assert _read_config(path) == config_text


def test_migrate_when_unreadable(remove_network_look: ModuleType, tmp_path: Path) -> None:
    """読めない設定は書き換えずに失敗する（異常系）。"""
    # 準備
    broken = "summary: [題名\n"
    path = _write_config(tmp_path, broken)
    # 実行・検証
    with pytest.raises(RuntimeError, match="config.yaml"):
        remove_network_look.migrate(tmp_path)
    assert path.read_text(encoding="utf-8") == broken
