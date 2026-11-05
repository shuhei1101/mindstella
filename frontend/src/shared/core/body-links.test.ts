import { describe, expect, test, vi } from "vitest";

import { linkBody, linkHeadings } from "@/shared/core/body-links";
import { buildIndex, type MindmapData } from "@/shared/core/records";

describe("linkHeadings", () => {
  // 同じ文言に番号（正常系）
  test("link_headings", () => {
    // 準備
    const root = document.createElement("div");
    root.innerHTML = "<h2>決め方</h2><h2>決め方</h2>";
    // 実行
    linkHeadings({ root, onHeading: vi.fn(), onChangeSet: vi.fn() });
    // 検証
    expect(root.querySelectorAll("h2")[1]?.dataset["heading"]).toBe("決め方-1");
  });
});

describe("linkBody", () => {
  // ID をリンクにする（正常系）
  test("link_body", () => {
    // 準備
    const data = { decisions: [{ id: "D-1", title: "題", status: "未決定" }], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { next: [] } } as unknown as MindmapData;
    const root = document.createElement("div");
    root.innerHTML = "<p>D-1 を見る</p>";
    const onOpen = vi.fn();
    // 実行
    linkBody({ root, index: buildIndex(data), selfId: "D-9", onOpen, source: "D-1 を見る" });
    root.querySelector<HTMLElement>("[data-id='D-1']")?.click();
    // 検証
    expect(onOpen).toHaveBeenCalledWith("D-1");
  });
});
