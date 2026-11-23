"""migrations/v0.14.0/scripts/remove_confirmed.py（確認済みを削除する変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.14.0" / "scripts" / "remove_confirmed.py"

# ワークスペースの直下からの項目の履歴と設定のファイル
HISTORY_PATH = Path(".mindstella") / "history.yaml"
CONFIG_PATH = Path(".mindstella") / "config.yaml"


@pytest.fixture
def remove_confirmed(scripts_dir: Path) -> ModuleType:
    """バージョンのフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_14_0_remove_confirmed", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: Path, text: str | None) -> Path:
    """ワークスペースのファイルに中身を書いて、そのパスを返す。text が None なら書かない。"""
    path = root / relative
    # ファイルを持たないワークスペースは、記録のフォルダだけを作る
    path.parent.mkdir(parents=True, exist_ok=True)
    if text is not None:
        path.write_text(text, encoding="utf-8")
    return path


def _read(path: Path) -> str | None:
    """ファイルの中身を返す。ファイルが無ければ None を返す。"""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _dump(data: object) -> str:
    """記録と同じ書き方の YAML にする。"""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def test_migrate(remove_confirmed: ModuleType, tmp_path: Path) -> None:
    """`confirmed` と `confirm_on_comment` を削除する（正常系）。"""
    # 準備
    d1_history = [{"seq": 2, "at": "2026-11-01T00:00:00+00:00", "by": "ai", "before": {"title": "前"}}]
    history = {
        "items": {
            "D-1": {
                "created": "2026-10-01T00:00:00+00:00",
                "updated": "2026-11-01T00:00:00+00:00",
                "history": d1_history,
                "confirmed": True,
            },
            "D-2": {"confirmed": True},
        }
    }
    config = {"summary": "題名", "confirm_on_comment": False, "display": {"visible_kinds": ["decisions"]}}
    history_path = _write(tmp_path, HISTORY_PATH, _dump(history))
    config_path = _write(tmp_path, CONFIG_PATH, _dump(config))
    # 実行
    changed = remove_confirmed.migrate(tmp_path)
    # 検証（ほかのキーと並びは変えない）
    saved_history = yaml.safe_load(history_path.read_text(encoding="utf-8"))
    saved_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    expected_config = {"summary": "題名", "display": {"visible_kinds": ["decisions"]}}
    assert changed == [".mindstella/history.yaml", ".mindstella/config.yaml"]
    assert saved_history == {
        "items": {
            "D-1": {
                "created": "2026-10-01T00:00:00+00:00",
                "updated": "2026-11-01T00:00:00+00:00",
                "history": d1_history,
            }
        }
    }
    assert saved_config == expected_config
    assert list(saved_config) == list(expected_config)


@pytest.mark.parametrize(
    ("history_text", "config_text"),
    [
        pytest.param(
            "items:\n  D-1:\n    created: '2026-10-01T00:00:00+00:00'\n",
            "summary: 題名\n",
            id="already_migrated",
        ),
        pytest.param(None, "summary: 題名\n", id="without_history"),
    ],
)
def test_migrate_when_already_current(
    remove_confirmed: ModuleType, tmp_path: Path, history_text: str | None, config_text: str
) -> None:
    """もう一度当てても変わらない（正常系）。"""
    # 準備
    history_path = _write(tmp_path, HISTORY_PATH, history_text)
    config_path = _write(tmp_path, CONFIG_PATH, config_text)
    # 実行
    changed = remove_confirmed.migrate(tmp_path)
    # 検証（無いファイルを作らない）
    assert changed == []
    assert _read(history_path) == history_text
    assert _read(config_path) == config_text


@pytest.mark.parametrize(
    ("broken", "message"),
    [
        pytest.param(HISTORY_PATH, r"history\.yaml", id="history"),
        pytest.param(CONFIG_PATH, r"config\.yaml", id="config"),
    ],
)
def test_migrate_when_unreadable(
    remove_confirmed: ModuleType, tmp_path: Path, broken: Path, message: str
) -> None:
    """読めないファイルは書き換えずに失敗する（異常系）。"""
    # 準備
    texts = {
        HISTORY_PATH: "items:\n  D-1:\n    confirmed: true\n",
        CONFIG_PATH: "summary: 題名\nconfirm_on_comment: false\n",
    }
    texts[broken] = "summary: [題名\n"
    history_path = _write(tmp_path, HISTORY_PATH, texts[HISTORY_PATH])
    config_path = _write(tmp_path, CONFIG_PATH, texts[CONFIG_PATH])
    # 実行・検証
    with pytest.raises(RuntimeError, match=message):
        remove_confirmed.migrate(tmp_path)
    assert history_path.read_text(encoding="utf-8") == texts[HISTORY_PATH]
    assert config_path.read_text(encoding="utf-8") == texts[CONFIG_PATH]
