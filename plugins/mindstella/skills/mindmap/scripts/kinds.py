"""ワークスペースの項目の種類の定義と状態の分類。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type Kind = Literal["decision", "task", "research", "doc", "term", "note", "log"]

# ワークスペースの直下に置く、設定・YAML・本文・リリース・版・ロックなど全ての記録をまとめるフォルダ名
RECORD_DIR = ".mindstella"

# MCP のツールが項目の `updated_by` と変更履歴の `by` に書く値（ツールを呼ぶのは AI）
EDITOR = "ai"

# ワークスペースの設定のファイル名（`records_root` の下）
SETTINGS_FILE = "config.yaml"

# v0.6.0 より前の版の設定のファイル名（直下にあってもワークスペースとしては扱わず、移し替えが見分ける）
LEGACY_SETTINGS_FILE = "mindmap.yaml"

# 本文の Markdown を置くフォルダ名（`records_root` の下）
BODY_DIR = "docs"

# ゴール判定でリリースの資料を書き出すフォルダ名（`records_root` の下）
RELEASE_DIR = "release"

# `{英大文字}-{正の整数}` の形の ID
ID_PATTERN = re.compile(r"^([A-Z])-([1-9][0-9]*)$")


@dataclass(frozen=True, slots=True, kw_only=True)
class KindSpec:
    """1 種類のファイル・ID の頭の文字・スキーマ・状態の有無（本文はどの種類も持てる）。"""

    kind: Kind
    # ワークスペースの中の YAML のファイル名
    file: str
    # ID の頭の文字
    prefix: str
    # `schemas/` のスキーマのファイル名
    schema: str
    # 決着とみなす状態。状態を持たない種類は空
    settled_statuses: frozenset[str]


# 種類 → 種類の定義。並びは D・T・R・A・G・N・L の順で、一覧を出す並びにも使う
KINDS: dict[Kind, KindSpec] = {
    "decision": KindSpec(
        kind="decision",
        file="decisions.yaml",
        prefix="D",
        schema="decisions.schema.json",
        settled_statuses=frozenset({"決定済み", "対象外", "取り下げ"}),
    ),
    "task": KindSpec(
        kind="task",
        file="tasks.yaml",
        prefix="T",
        schema="tasks.schema.json",
        settled_statuses=frozenset({"完了", "中止"}),
    ),
    "research": KindSpec(
        kind="research",
        file="research.yaml",
        prefix="R",
        schema="research.schema.json",
        settled_statuses=frozenset(),
    ),
    "doc": KindSpec(
        kind="doc",
        file="docs.yaml",
        prefix="A",
        schema="docs.schema.json",
        settled_statuses=frozenset(),
    ),
    "term": KindSpec(
        kind="term",
        file="terms.yaml",
        prefix="G",
        schema="terms.schema.json",
        settled_statuses=frozenset(),
    ),
    "note": KindSpec(
        kind="note",
        file="notes.yaml",
        prefix="N",
        schema="notes.schema.json",
        settled_statuses=frozenset(),
    ),
    "log": KindSpec(
        kind="log",
        file="logs.yaml",
        prefix="L",
        schema="logs.schema.json",
        settled_statuses=frozenset(),
    ),
}


def kind_of_id(item_id: str) -> Kind | None:
    """ID の頭の文字から種類を引く。形が合わない・頭の文字が無ければ None を返す。"""
    # `{英大文字}-{数字}` の形かを確かめる
    matched = ID_PATTERN.match(item_id)
    # 形が合わない: どの種類にも当たらない
    if matched is None:
        return None
    # 頭の文字が一致する種類を引く（無ければ None）
    for spec in KINDS.values():
        if spec.prefix == matched.group(1):
            return spec.kind
    return None


def id_number(item_id: str) -> int:
    """ID の連番を返す。形が合わない ID は 0 を返す（並べ替えで先頭に置く）。"""
    matched = ID_PATTERN.match(item_id)
    # 形が合わない ID は連番を持たない
    if matched is None:
        return 0
    return int(matched.group(2))


def records_root(root: Path) -> Path:
    """ワークスペースのフォルダから記録のフォルダ（`root / RECORD_DIR`）を返す。フォルダは作らない。"""
    return root / RECORD_DIR
