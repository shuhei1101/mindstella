import { screen, waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { renderRoute } from "@/testing/render";

describe("PreviewShell", () => {
  // tab の画面を描く（正常系）
  test("preview_shell", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks");
    // 検証
    expect(await screen.findByRole("group", { name: "表示形式" })).toBeInTheDocument();
    expect(await screen.findByText("T-1の題")).toBeInTheDocument();
  });

  // id で詳細パネルを重ねる（正常系）
  test("preview_shell_when_item", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks&id=T-1");
    // 検証
    expect(await screen.findByRole("complementary", { name: /詳細/ })).toBeInTheDocument();
  });

  // full で全画面にする（正常系）
  test("preview_shell_when_full", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks&id=T-1&full=1");
    // 検証
    expect(await screen.findByRole("dialog", { name: /T-1の題/ })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /詳細/ })).not.toBeInTheDocument();
  });

  // 設定の画面を開く（正常系）
  test("preview_shell_when_settings", async () => {
    // 実行
    renderRoute("/spa/?tab=settings");
    // 検証
    expect(await screen.findByRole("heading", { name: "設定", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("link", { current: "page" })).not.toBeInTheDocument();
  });

  // 記録に合わない値を外す（正常系）
  test("preview_shell_when_search_mismatched", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks&view=map&id=T-99");
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=tasks"));
  });
});
