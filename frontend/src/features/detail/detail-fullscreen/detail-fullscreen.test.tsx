import { screen } from "@testing-library/react";
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
});
