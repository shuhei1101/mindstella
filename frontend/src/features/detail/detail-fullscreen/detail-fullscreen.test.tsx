import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { renderRoute } from "@/testing/render";

describe("DetailFullscreen", () => {
  // モーダルで開く（正常系）
  test("detail_fullscreen", async () => {
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1&full=1");
    // 検証
    expect(await screen.findByRole("dialog", { name: /D-1の題/ })).toBeInTheDocument();
  });
  // 下端にコメント（正常系）
  test("detail_fullscreen_when_comments", async () => {
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1&full=1");
    const dialog = await screen.findByRole("dialog", { name: /D-1の題/ });
    // 検証
    expect(await within(dialog).findByRole("textbox", { name: /D-1 へのコメント/ })).toBeInTheDocument();
    expect(within(dialog).queryByRole("link", { name: "今の画面でコメントする" })).not.toBeInTheDocument();
  });
});
