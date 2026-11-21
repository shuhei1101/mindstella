"""プリセットのツールの結合テストが共有する、タグ・式・設定の組み立て。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import RECORD_DIR


def tags(*names: str) -> list[dict[str, str]]:
    """タグの名前の並びを項目の `tags` にする。"""
    return [{"name": name} for name in names]


def eq(*values: str) -> dict[str, Any]:
    """タグが値のどれかを持つ条件を作る。"""
    return {"field": "tags", "op": "eq", "values": list(values)}


def ne(*values: str) -> dict[str, Any]:
    """タグが値をどれも持たない条件を作る。"""
    return {"field": "tags", "op": "ne", "values": list(values)}


def with_presets(settings: dict[str, Any], *entries: dict[str, Any]) -> dict[str, Any]:
    """設定に presets を加えた辞書を返す。"""
    return {**settings, "presets": list(entries)}


def read_settings(root: Path) -> dict[str, Any]:
    """config.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))


def config_text(root: Path) -> str:
    """config.yaml の中身をそのまま読む。"""
    return (root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8")
