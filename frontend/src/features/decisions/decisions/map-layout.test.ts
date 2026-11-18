import { describe, expect, test } from "vitest";

import { buildMapGraph } from "@/features/decisions/decisions/map-layout";
import type { Item, Settings } from "@/shared/core/records";

describe("buildMapGraph", () => {
  // 検討事項を根の直下に置く（正常系）
  test("build_map_graph", () => {
    // 準備
    const settings = { summary: "話し合い", links: [] } as unknown as Settings;
    const items = [
      { id: "D-1", title: "題 1", status: "未決定" },
      { id: "D-2", title: "題 2", status: "決定済み" },
    ] as unknown as Item[];
    // 実行
    const graph = buildMapGraph(items, settings);
    // 検証
    const roots = graph.nodes.filter((node) => node.kind !== "item");
    expect(roots).toHaveLength(1);
    expect(graph.nodes.filter((node) => node.kind === "item").map((node) => node.id)).toEqual(["D-1", "D-2"]);
    expect(graph.edges.map((edge) => [edge.sources, edge.targets])).toEqual([
      [[roots[0]?.id], ["D-1"]],
      [[roots[0]?.id], ["D-2"]],
    ]);
  });
});
