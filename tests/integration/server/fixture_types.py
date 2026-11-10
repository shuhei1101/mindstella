"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable

from .transcriber_helpers import FakeMode, FakeTranscriber

from workspace_fixtures import (
    CallTool,
    MakeComment,
    MakeDraft,
    MakeEdit,
    MakeItem,
    MakeLegacyWorkspace,
    MakePost,
    MakeSubmission,
    MakeThread,
    MakeVenv,
    MakeWorkspace,
    McpServer,
    SnapshotTree,
    StartServer,
    ToolResult,
    WriteComments,
    WriteDrafts,
    WriteEdits,
    WriteSubmissions,
    WriteThreads,
)

__all__ = [
    "CallTool",
    "FindOldPython",
    "LockDirs",
    "MakeComment",
    "MakeDraft",
    "MakeEdit",
    "MakeItem",
    "MakeLegacyWorkspace",
    "MakePost",
    "MakeSubmission",
    "MakeThread",
    "MakeVenv",
    "MakeWorkspace",
    "McpServer",
    "SnapshotTree",
    "StartFakeTranscriber",
    "StartServer",
    "StartVoiceServer",
    "ToolResult",
    "WriteComments",
    "WriteDrafts",
    "WriteEdits",
    "WriteSubmissions",
    "WriteThreads",
]

type LockDirs = Callable[..., None]
type FindOldPython = Callable[[], str]
# 偽の文字起こしのサービスを振る舞いの種類で立てる
type StartFakeTranscriber = Callable[[FakeMode], FakeTranscriber]
# 文字起こしのサービスの URL（と差し替える定数）を渡して常駐サーバーを立てる
type StartVoiceServer = Callable[..., McpServer]
