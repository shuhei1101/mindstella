import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("DocsScreen", () => {
  // 既定はカード（正常系）
  test("docs_screen", async () => {
    // 準備
    stubRecords({ docs: [{ id: "A-10", title: "後の資料", status: "完成" }, { id: "A-2", title: "前の資料", status: "下書き" }] });
    // 実行
    renderRoute("/?tab=docs");
    // 検証
    const titles = (await screen.findAllByRole("heading", { level: 2 })).map((heading) => heading.textContent);
    expect(titles).toEqual([expect.stringContaining("前の資料"), expect.stringContaining("後の資料")]);
  });
});
