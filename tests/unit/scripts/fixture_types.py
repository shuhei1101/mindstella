"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from workspace_fixtures import (
    MakeComment,
    MakeDraft,
    MakeEdit,
    MakeItem,
    MakeLegacyItem,
    MakeLegacyWorkspace,
    MakePost,
    MakeSubmission,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteDrafts,
    WriteEdits,
    WriteSubmissions,
    WriteThreads,
)

__all__ = [
    "FailingReplace",
    "FailingUnlink",
    "FailingWriteText",
    "MakeComment",
    "MakeDraft",
    "MakeEdit",
    "MakeItem",
    "MakeLegacyItem",
    "MakeLegacyWorkspace",
    "MakePost",
    "MakeSubmission",
    "MakeThread",
    "MakeWorkspace",
    "PatchPluginVersion",
    "SnapshotTree",
    "WriteComments",
    "WriteDrafts",
    "WriteEdits",
    "WriteSubmissions",
    "WriteThreads",
]

type PatchPluginVersion = Callable[[str], None]
type FailingReplace = Callable[[str], Callable[[Any, Any], None]]
type FailingUnlink = Callable[[str], None]
type FailingWriteText = Callable[[str], None]
