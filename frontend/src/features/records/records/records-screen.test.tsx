import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("RecordsScreen", () => {
  // 種類ごとの表（正常系）
  test("records_screen", async () => {
    // 準備
    stubRecords({ terms: [{ id: "G-1", title: "用語の題", meaning: "意味" }] });
    // 実行
    renderRoute("/spa/?tab=terms");
    // 検証
    expect(await screen.findByRole("cell", { name: "用語の題" })).toBeInTheDocument();
  });
});
