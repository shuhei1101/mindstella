"""migrations/v0.13.0/scripts/mdmark_documents.py（資料を mdmark の今の書き方へ移す変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import MakeWorkspace
from workspace_fixtures import RECORD_DIR

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.13.0" / "scripts" / "mdmark_documents.py"

# 代わりのコマンドが書き換える資料の、ワークスペースからの相対パス
DOC_PATH = f"{RECORD_DIR}/docs/A-1.md"

# 代わりのコマンドが出す移行の報告の行
REPORT_LINE = "  docs/A-1.md:5: flow: scope: 範囲: map の範囲に写す先がありません"

# mdmark の CLI の代わり。`--config` の設定のフォルダの docs/A-1.md を書き換え、設定に map.kinds.llm を書き足し、報告の行を出す
FAKE_UPGRADE = f"""\
import sys
from pathlib import Path

import yaml

config = Path(sys.argv[sys.argv.index("--config") + 1])
(config.parent / "docs" / "A-1.md").write_text("# 移した本文\\n", encoding="utf-8")
data = yaml.safe_load(config.read_text(encoding="utf-8"))
data["map"] = {{"kinds": {{"llm": {{"label": "LLM"}}}}}}
config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
(config.parent / ".mdmark" / "backup").mkdir(parents=True)
print({REPORT_LINE!r})
"""

# 理由を出して終了コード 1 で終わる mdmark の CLI の代わり
FAILING_UPGRADE = """\
import sys

print("変換できません: docs/A-1.md")
sys.exit(1)
"""


@pytest.fixture
def mdmark_documents(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_13_0_mdmark_documents", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _use_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str) -> None:
    """mdmark の CLI の代わりのスクリプトを置き、環境変数で差し替える。"""
    fake = tmp_path / "fake_mdmark.py"
    fake.write_text(body, encoding="utf-8")
    monkeypatch.setenv("MINDSTELLA_MDMARK_COMMAND", f"{sys.executable} {fake}")


def _read_config(root: Path) -> dict[str, Any]:
    """ワークスペースの config.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))


def _leftovers(root: Path) -> list[Path]:
    """一時の mdmark の設定と mdmark のバックアップのうち、残っているもの。"""
    record = root / RECORD_DIR
    return [p for p in (record / "mdmark.config.yaml", record / ".mdmark") if p.exists()]


def test_mdmark_documents_migrate(
    mdmark_documents: ModuleType,
    make_workspace: MakeWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """map の種類を config.yaml へ移し、一時のファイルを消す（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs/A-1.md": "# 前の本文\n"})
    version_before = _read_config(root).get("mdmark", {}).get("version")
    _use_command(monkeypatch, tmp_path, FAKE_UPGRADE)
    # 実行
    changed, report = mdmark_documents.migrate(root)
    # 検証
    assert sorted(changed) == sorted([DOC_PATH, f"{RECORD_DIR}/config.yaml"])
    assert report == [REPORT_LINE]
    config = _read_config(root)
    assert config["mdmark"]["map"] == {"kinds": {"llm": {"label": "LLM"}}}
    assert config["mdmark"].get("version") == version_before
    assert _leftovers(root) == []


def test_mdmark_documents_migrate_when_command_fails(
    mdmark_documents: ModuleType,
    make_workspace: MakeWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI が失敗したら理由つきで送り、一時のファイルを残さない（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs/A-1.md": "# 前の本文\n"})
    _use_command(monkeypatch, tmp_path, FAILING_UPGRADE)
    # 実行・検証
    with pytest.raises(RuntimeError, match="変換できません"):
        mdmark_documents.migrate(root)
    assert _leftovers(root) == []


def test_mdmark_documents_migrate_when_version_set(
    mdmark_documents: ModuleType,
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """設定のタグの mdmark を呼ぶ（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "mdmark": {"version": "v0.13.0"}})
    monkeypatch.delenv("MINDSTELLA_MDMARK_COMMAND", raising=False)
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(mdmark_documents.subprocess, "run", fake_run)
    # 実行
    mdmark_documents.migrate(root)
    # 検証
    assert calls[0][:5] == ["npx", "-y", "github:shuhei1101/mdmark#v0.13.0", "upgrade", "--yes"]
    assert "--config" in calls[0]
