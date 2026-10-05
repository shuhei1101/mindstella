"""変更履歴・書き換えのまとまりを持つワークスペースを、実際のツールを呼んで作る関数（結合テストの共通の関数）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .fixture_types import CallTool

# 検討事項として足す問い
DECISION_ITEM: dict[str, Any] = {
    "title": "キーを種類ごとに分けるか",
    "status": "未決定",
    "lead": "キーを種類ごとに分けるか",
    "weight": "大",
}


def add_item(call_tool: CallTool, root: Path, kind: str, item: dict[str, Any]) -> str:
    """`add` で項目を足し、付いた ID を返す。エラーならテストを止める。"""
    result = call_tool("add", workspace=str(root), kind=kind, item=item)
    assert result.is_error is False, result.text
    assert result.data is not None
    return str(result.data["id"])


def commit(call_tool: CallTool, root: Path, summary: str) -> dict[str, Any]:
    """`commit` でまとめた結果を返す。エラーならテストを止める。"""
    result = call_tool("commit", workspace=str(root), summary=summary)
    assert result.is_error is False, result.text
    assert result.data is not None
    return result.data


def update_item(call_tool: CallTool, root: Path, item_id: str, item: dict[str, Any]) -> None:
    """`update` で項目を直す。エラーならテストを止める。"""
    result = call_tool("update", workspace=str(root), id=item_id, item=item)
    assert result.is_error is False, result.text


def read_changes(root: Path) -> dict[str, Any]:
    """`changes.yaml` を読む。"""
    return yaml.safe_load((root / "changes.yaml").read_text(encoding="utf-8"))


def read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """種類ごとの YAML の項目の並びを読む。"""
    return yaml.safe_load((root / file_name).read_text(encoding="utf-8"))["items"]


def write_settings(root: Path, **overrides: Any) -> None:
    """`mindmap.yaml` に渡したキーを書き足す（保持する回数を変えるなど）。"""
    path = root / "mindmap.yaml"
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    settings.update(overrides)
    path.write_text(yaml.safe_dump(settings, allow_unicode=True, sort_keys=False), encoding="utf-8")
