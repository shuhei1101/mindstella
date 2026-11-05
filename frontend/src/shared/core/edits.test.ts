import { describe, expect, test } from "vitest";

import { applyEdits, pendingMarkOf, type PendingEdit } from "@/shared/core/edits";
import type { MindmapData } from "@/shared/core/records";

const data = { settings: {}, bodies: {}, decisions: [{ id: "D-1", title: "題", status: "未決定" }], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [] } as unknown as MindmapData;
const edit = (patch: Partial<PendingEdit>): PendingEdit => ({ id: "E-1", target: "D-1", op: "set", key: "answer", value: "答え", before: null, created: "2026-11-01T00:00:00+00:00", ...patch });

describe("applyEdits", () => {
  // キーの編集を重ねる（正常系）
  test("apply_edits", () => {
    expect(applyEdits(data, [edit({})]).decisions[0]?.answer).toBe("答え");
  });

  // 足す項目を差し込む（正常系）
  test("apply_edits_when_item_add", () => {
    // 実行
    const result = applyEdits(data, [edit({ op: "item-add", target: "new-1", key: "tasks", value: { title: "足す" } })]);
    // 検証
    expect(result.tasks.map((item) => item.id)).toEqual(["new-1"]);
  });
});

describe("pendingMarkOf", () => {
  // 削除（正常系）
  test("pending_mark_of_when_remove", () => {
    expect(pendingMarkOf({ edits: [edit({ op: "item-remove", key: null })], blocked: new Set(), target: "D-1" })).toBe("remove");
  });

  // 書き込めない（正常系）
  test("pending_mark_of_when_blocked", () => {
    expect(pendingMarkOf({ edits: [edit({})], blocked: new Set(["E-1"]), target: "D-1", key: "answer" })).toBe("blocked");
  });
});
