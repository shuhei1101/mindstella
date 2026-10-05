"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from workspace_fixtures import (
    MakeComment,
    MakeDraft,
    MakeItem,
    MakeLegacyItem,
    MakeLegacyWorkspace,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteDrafts,
    WriteSubmissions,
)

__all__ = [
    "FailingReplace",
    "FailingUnlink",
    "FailingWriteText",
    "MakeComment",
    "MakeDraft",
    "MakeItem",
    "MakeLegacyItem",
    "MakeLegacyWorkspace",
    "MakeSubmission",
    "MakeWorkspace",
    "PatchPluginVersion",
    "SnapshotTree",
    "WriteComments",
    "WriteDrafts",
    "WriteSubmissions",
]

type PatchPluginVersion = Callable[[str], None]
type FailingReplace = Callable[[str], Callable[[Any, Any], None]]
type FailingUnlink = Callable[[str], None]
type FailingWriteText = Callable[[str], None]
