import * as jsdiff from "diff";
import { marked } from "marked";
import { describe, expect, test } from "vitest";

import { buildVersions, diffLineParts, htmlChangedLines, removedOf, resolveDiffPoint, sideBySideRows, type DiffPoint } from "@/shared/core/diff";
import type { Changes, Item } from "@/shared/core/records";

const changes: Changes = {
  last_seq: 3,
  sets: [
    { id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 3, added: ["D-2"], changed: ["D-1"], removed: [{ id: "D-3", kind: "decision", title: "消した" }, { id: "T-1", kind: "task", title: "消したタスク" }] },
    { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: ["D-1"], changed: [] },
  ],
  pending: { added: [], changed: [] },
};
const since = { at: "2026-11-01T00:00:00+00:00", seq: 1 };

describe("resolveDiffPoint", () => {
  // まとまりを解決する（正常系）
  test("resolve_diff_point", () => {
    // 実行
    const point = resolveDiffPoint(changes, "V-2", since);
    // 検証
    expect(point?.added.has("D-2")).toBe(true);
    expect(point?.changed.has("D-1")).toBe(true);
    expect(point?.removed.has("D-3")).toBe(true);
  });

  // 記録に無い（正常系）
  test("resolve_diff_point_when_missing", () => {
    expect(resolveDiffPoint(changes, "V-99", since)).toBeNull();
  });

  // 空の pending（正常系）
  test("resolve_diff_point_when_pending_empty", () => {
    expect(resolveDiffPoint(changes, "pending", since)).toBeNull();
  });
});

const point = (): DiffPoint => resolveDiffPoint(changes, "V-2", since) as DiffPoint;

describe("buildVersions", () => {
  // キーと本文を戻す（正常系）
  test("build_versions", () => {
    // 準備
    const item = { id: "D-1", title: "新", status: "未決定", history: [{ seq: 3, at: "2026-11-02T00:00:00+00:00", before: { title: "旧" }, body_diff: [{ line: 1, now: ["今の行"], before: ["前の行"] }] }] } as unknown as Item;
    // 実行
    const versions = buildVersions(item, "今の行\n", point());
    // 検証
    expect(versions.before?.title).toBe("旧");
    expect(versions.beforeBody).toBe("前の行\n");
  });

  // 保持の回数を超えた（正常系）
  test("build_versions_when_dropped", () => {
    // 準備
    const item = { id: "D-1", title: "新", status: "未決定", history: [], history_dropped_seq: 3 } as unknown as Item;
    // 実行
    const versions = buildVersions(item, "", point());
    // 検証
    expect(versions.trimmed).toBe(true);
  });
});

describe("diffLineParts", () => {
  // 足した行と消した行（正常系）
  test("diff_line_parts", () => {
    // 実行
    const parts = diffLineParts("一\n二\n", "一\n三\n", jsdiff);
    // 検証
    expect(parts?.filter((part) => part.kind === "removed").flatMap((part) => part.lines)).toEqual(["二"]);
    expect(parts?.filter((part) => part.kind === "added").flatMap((part) => part.lines)).toEqual(["三"]);
  });
});

describe("sideBySideRows", () => {
  // 変えていない塊を揃える（正常系）
  test("side_by_side_rows", () => {
    // 実行
    const rows = sideBySideRows({ before: "同じ\n\n前\n\n後ろ\n", after: "同じ\n\n変えた\n\n後ろ\n", lexer: marked.lexer.bind(marked), jsdiff });
    // 検証
    expect(rows?.[0]).toMatchObject({ changed: false, left: [{ raw: "同じ" }], right: [{ raw: "同じ" }] });
    expect(rows?.[1]).toMatchObject({ changed: true, left: [{ raw: "前" }], right: [{ raw: "変えた" }] });
    expect(rows?.at(-1)).toMatchObject({ changed: false, left: [{ raw: "後ろ" }], right: [{ raw: "後ろ" }] });
  });
});

describe("htmlChangedLines", () => {
  // 足した行を返す（正常系）
  test("html_changed_lines", () => {
    // 実行
    const lines = htmlChangedLines("<p>一</p>\n", "<p>一</p>\n<p>二</p>\n", jsdiff);
    // 検証
    expect(lines?.added).toEqual([2]);
  });
});

describe("removedOf", () => {
  // 種類で絞る（正常系）
  test("removed_of", () => {
    expect(removedOf({ point: point(), kind: "decisions" }).map((item) => item.id)).toEqual(["D-3"]);
  });
});
