"""migrations/v0.14.0/scripts/remove_preview_port.py（プレビューの配信の設定を削除する変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.14.0" / "scripts" / "remove_preview_port.py"

# ワークスペースの直下からの設定のファイル
CONFIG_PATH = Path(".mindstella") / "config.yaml"


@pytest.fixture
def remove_preview_port(scripts_dir: Path) -> ModuleType:
    """バージョンのフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_14_0_remove_preview_port", path)
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


def test_migrate(remove_preview_port: ModuleType, tmp_path: Path) -> None:
    """`preview` を削除する（正常系）。"""
    # 準備
    config = {
        "summary": "題名",
        "preview": {"port": 47800},
        "display": {"visible_kinds": ["decisions"]},
    }
    path = _write_config(tmp_path, yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    # 実行
    changed = remove_preview_port.migrate(tmp_path)
    # 検証（ほかのキーと並びは変えない）
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {"summary": "題名", "display": {"visible_kinds": ["decisions"]}}
    assert changed == [".mindstella/config.yaml"]
    assert saved == expected
    assert list(saved) == list(expected)


@pytest.mark.parametrize(
    "config_text",
    [
        pytest.param(
            "summary: 題名\ndisplay:\n  visible_kinds:\n  - decisions\n", id="already_migrated"
        ),
        pytest.param(None, id="without_config"),
    ],
)
def test_migrate_when_already_current(
    remove_preview_port: ModuleType, tmp_path: Path, config_text: str | None
) -> None:
    """もう一度当てても変わらない（正常系）。"""
    # 準備
    path = _write_config(tmp_path, config_text)
    # 実行
    changed = remove_preview_port.migrate(tmp_path)
    # 検証（無いファイルを作らない）
    assert changed == []
    assert _read_config(path) == config_text


def test_migrate_when_unreadable(remove_preview_port: ModuleType, tmp_path: Path) -> None:
    """読めない設定は書き換えずに失敗する（異常系）。"""
    # 準備
    broken = "summary: [題名\n"
    path = _write_config(tmp_path, broken)
    # 実行・検証
    with pytest.raises(RuntimeError, match=r"config\.yaml"):
        remove_preview_port.migrate(tmp_path)
    assert path.read_text(encoding="utf-8") == broken
