"""記録を project-index で配信する設定（`.mindstella/dev-docs.yaml`）とスキーマの複製を置く（v0.13.0 の移し替え）。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import yaml
from store import (
    RECORD_DIR,
    SCHEMA_DIR,
    SETTINGS_FILE,
    SOURCE_CONFIG_FILE,
    SOURCE_SCHEMA_DIR,
    build_source_config,
    dump_yaml,
    remove_files,
    source_schema_files,
    write_temp,
)
from workspaces import workspace_id_for


def migrate(root: Path) -> list[str]:
    """設定が無ければ作り、スキーマの複製をプラグインのスキーマで置き換え、書いたファイルを返す。"""
    records = root / RECORD_DIR
    written: list[str] = []
    config_path = records / SOURCE_CONFIG_FILE
    # 利用者が書き換えたかもしれない設定は、あれば書き換えない
    if not config_path.exists():
        settings = _read_settings(records / SETTINGS_FILE)
        workspace_id = str(settings.get("id") or workspace_id_for(root))
        config = build_source_config(workspace_id, str(settings.get("summary", "")))
        temp = write_temp(config_path, dump_yaml(config))
        try:
            os.replace(temp, config_path)
        except OSError:
            remove_files([temp])
            raise
        written.append(f"{RECORD_DIR}/{SOURCE_CONFIG_FILE}")
    schema_dir = records / SOURCE_SCHEMA_DIR
    schema_dir.mkdir(exist_ok=True)
    for name in source_schema_files():
        source = SCHEMA_DIR / name
        target = schema_dir / name
        # 中身が同じファイルは書かない
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        shutil.copyfile(source, target)
        written.append(f"{RECORD_DIR}/{SOURCE_SCHEMA_DIR}/{name}")
    return written


def _read_settings(path: Path) -> dict[str, Any]:
    """`config.yaml` を読む（読めなければ空）。"""
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}
