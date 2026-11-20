import { describe, expect, test } from "vitest";

import { workspaceKey, workspacePath } from "@/shared/core/workspace-path";

describe("workspacePath", () => {
  // パスの頭を返す（正常系）
  test.each([
    ["/w/mindstella-x-1/spa/", "/w/mindstella-x-1"],
    ["/w/a%20b/mindstella.html", "/w/a%20b"],
    ["/spa/", ""],
    ["/", ""],
  ])("workspace_path %s", (pathname, expected) => {
    // 実行
    const result = workspacePath(pathname);
    // 検証
    expect(result).toBe(expected);
  });
});

describe("workspaceKey", () => {
  // ワークスペースの ID を末尾に付ける（正常系）
  test.each([
    ["/w/mindstella-x-1/spa/", "mindmap-preview:mindstella-x-1"],
    ["/w/a%20b/spa/", "mindmap-preview:a b"],
    ["/spa/", "mindmap-preview"],
  ])("workspace_key %s", (pathname, expected) => {
    // 実行
    const result = workspaceKey("mindmap-preview", pathname);
    // 検証
    expect(result).toBe(expected);
  });
});
