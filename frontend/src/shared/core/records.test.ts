import { describe, expect, test } from "vitest";

import { bodyFormatOf, buildIndex, compareIds, relatedItems, type MindmapData } from "@/shared/core/records";

const data = {
  decisions: [
    { id: "D-1", title: "前提", status: "決定済み" },
    { id: "D-2", title: "後続", status: "未決定", depends_on: ["D-1"] },
  ],
  tasks: [],
  research: [],
  docs: [],
  terms: [],
  notes: [],
  logs: [],
  derived: { next: [] },
} as unknown as MindmapData;

describe("buildIndex", () => {
  // 項目と逆向きを引ける（正常系）
  test("build_index", () => {
    // 実行
    const index = buildIndex(data);
    // 検証
    expect(index.byId.get("D-1")?.item.title).toBe("前提");
    expect(index.referencedBy.get("D-1")).toEqual(["D-2"]);
  });
});

describe("relatedItems", () => {
  // 前提と後続を返す（正常系）
  test("related_items", () => {
    // 準備
    const index = buildIndex(data);
    // 実行・検証
    expect(relatedItems({ id: "D-2", index }).prerequisites).toEqual(["D-1"]);
    expect(relatedItems({ id: "D-1", index }).successors).toEqual(["D-2"]);
  });
});

describe("compareIds", () => {
  // 数で比べる（正常系）
  test("compare_ids", () => {
    expect(compareIds("D-2", "D-10")).toBeLessThan(0);
  });
});

describe("bodyFormatOf", () => {
  // 拡張子で分ける（正常系）
  test("body_format_of", () => {
    expect(bodyFormatOf("A-1.html")).toBe("html");
  });
});
