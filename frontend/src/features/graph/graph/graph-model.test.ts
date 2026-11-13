import { describe, expect, test } from "vitest";

import { buildGraph, graphConditions, shownGraphIds } from "@/features/graph/graph/graph-model";
import { buildIndex, type MindmapData } from "@/shared/core/records";

/** 種類ごとの項目を持つ記録を作る（持たない種類は空） */
const indexOf = (items: Partial<Record<string, unknown[]>>) =>
  buildIndex({ decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { next: [] }, ...items } as unknown as MindmapData);

describe("buildGraph", () => {
  // 線の種類を分け、渡していない項目の線を落とす（正常系）
  test("build_graph", () => {
    // 準備
    const index = indexOf({
      decisions: [
        { id: "D-1", title: "前提" },
        { id: "D-2", title: "後続", depends_on: ["D-1"], sources: ["R-1"] },
      ],
      tasks: [{ id: "T-1", title: "作業", for: ["D-1"] }],
      research: [{ id: "R-1", title: "調査" }],
      notes: [{ id: "N-1", title: "メモ", related: ["D-1"] }],
    });
    // 実行
    const graph = buildGraph({ index, shownIds: new Set(["D-1", "D-2", "T-1", "R-1"]) });
    // 検証
    expect(graph.nodes.map((node) => node.id).sort()).toEqual(["D-1", "D-2", "R-1", "T-1"]);
    expect(graph.links).toHaveLength(3);
    expect(graph.links).toEqual(
      expect.arrayContaining([
        { source: "D-2", target: "D-1", type: "depends" },
        { source: "D-2", target: "R-1", type: "source" },
        { source: "T-1", target: "D-1", type: "for" },
      ]),
    );
  });
});

describe("graphConditions", () => {
  // 種類・状態・タグの値を取る（正常系）
  test("graph_conditions", () => {
    // 準備
    const index = indexOf({
      decisions: [{ id: "D-1", title: "前提", status: "未決定", tags: [{ name: "a", main: true }] }],
      notes: [{ id: "N-1", title: "メモ" }],
    });
    const conditions = graphConditions();
    const valueOf = (key: string, id: string) => {
      const entry = index.byId.get(id);
      if (entry === undefined) throw new Error(id);
      return conditions.find((condition) => condition.key === key)?.get(entry);
    };
    // 実行・検証
    expect(conditions.map((condition) => condition.key)).toEqual(["type", "status", "tags"]);
    expect(valueOf("type", "D-1")).toBe("検討事項");
    expect(valueOf("status", "D-1")).toBe("未決定");
    expect(valueOf("tags", "D-1")).toEqual(["a"]);
    expect(valueOf("type", "N-1")).toBe("メモ");
    expect(valueOf("status", "N-1") ?? null).toBeNull();
    expect(valueOf("tags", "N-1")).toEqual([]);
  });
});

describe("shownGraphIds", () => {
  // 状態を持たない項目は状態の条件で外れる（正常系）
  test("shown_graph_ids_when_status_filtered", () => {
    // 準備
    const index = indexOf({ decisions: [{ id: "D-1", title: "前提", status: "未決定" }], notes: [{ id: "N-1", title: "メモ" }] });
    // 実行
    const shown = shownGraphIds({ index, filters: { status: ["未決定"] } });
    // 検証
    expect([...shown]).toEqual(["D-1"]);
  });
});
