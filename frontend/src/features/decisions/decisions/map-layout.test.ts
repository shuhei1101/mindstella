import { describe, expect, test } from "vitest";

import { buildMapGraph } from "@/features/decisions/decisions/map-layout";
import type { Item, Settings } from "@/shared/core/records";

describe("buildMapGraph", () => {
  // 項目を持たない節を描かない（正常系）
  test("build_map_graph", () => {
    // 準備
    const settings = { targets: [{ name: "持つ" }, { name: "持たない" }], categories: [{ name: "記録", target: "持つ" }, { name: "空", target: "持たない" }], phases: ["目的"] } as unknown as Settings;
    const items = [{ id: "D-1", title: "題", status: "未決定", category: "記録", phase: "目的" }] as unknown as Item[];
    // 実行
    const graph = buildMapGraph(items, settings);
    // 検証
    expect(graph.nodes.some((node) => node.label === "持つ")).toBe(true);
    expect(graph.nodes.some((node) => node.label === "持たない")).toBe(false);
  });
});
