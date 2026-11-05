import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("DocsScreen", () => {
  // 既定はカード（正常系）
  test("docs_screen", async () => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "普通の資料", status: "下書き" }, { id: "A-2", title: "納品物の資料", status: "完成", deliverable: true }] });
    // 実行
    renderRoute("/spa/?tab=docs");
    // 検証
    const titles = (await screen.findAllByRole("heading", { level: 3 })).map((heading) => heading.textContent);
    expect(titles[0]).toContain("納品物の資料");
  });
});
