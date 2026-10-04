"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable

from workspace_fixtures import (
    CallTool,
    MakeItem,
    MakeLegacyWorkspace,
    MakeSubmission,
    MakeVenv,
    MakeWorkspace,
    McpServer,
    SnapshotTree,
    StartServer,
    ToolResult,
    WriteSubmissions,
)

__all__ = [
    "CallTool",
    "FindOldPython",
    "LockDirs",
    "MakeItem",
    "MakeLegacyWorkspace",
    "MakeSubmission",
    "MakeVenv",
    "MakeWorkspace",
    "McpServer",
    "SnapshotTree",
    "StartServer",
    "ToolResult",
    "WriteSubmissions",
]

type LockDirs = Callable[..., None]
type FindOldPython = Callable[[], str]
