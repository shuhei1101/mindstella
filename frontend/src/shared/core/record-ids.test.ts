import { describe, expect, test } from "vitest";

import { findRecordIds, recordLookupOf, type LookupRecordId, type RecordIdTarget } from "@/shared/core/record-ids";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { threadLookupOf } from "@/shared/core/thread-ids";

/** 見本の記録にある ID と中身（D-99・XD-1・D-12a は記録に無い） */
const TARGETS: Record<string, RecordIdTarget> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
  "TH-1-2": { id: "TH-1-2", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

const lookup: LookupRecordId = (id) => TARGETS[id] ?? null;

describe("findRecordIds", () => {
  // 記録にある ID だけを位置つきで返却する（正常系）
  test("find_record_ids", () => {
    // 準備
    const text = "D-1 の比較（TH-1 の続き、TH-1-2 と D-99、XD-1・D-12a）";
    // 実行
    const found = findRecordIds({ text, lookup });
    // 検証
    expect(found.map(({ target }) => target.id)).toEqual(["D-1", "TH-1", "TH-1-2"]);
    for (const { start, end, target } of found) expect(text.slice(start, end)).toBe(target.id);
  });

  // ID を持たない文字は空（正常系）
  test("find_record_ids_none", () => {
    // 実行・検証
    expect(findRecordIds({ text: "保存先の比較", lookup })).toEqual([]);
  });
});

/** 見本の記録（未決定の検討事項 D-1 だけを持つ） */
const data = {
  decisions: [{ id: "D-1", title: "保存先の決め方", status: "未決定" }],
  tasks: [],
  research: [],
  docs: [],
  terms: [],
  notes: [],
  logs: [],
  derived: { ready: [] },
} as unknown as MindmapData;

/** 見本のスレッド（オープンの TH-1 と、その書き込み TH-1-1・TH-1-2） */
const threads = threadLookupOf([{ id: "TH-1", summary: "保存先の候補", status: "open", posts: [{ id: "TH-1-1" }, { id: "TH-1-2" }] }]);

describe("recordLookupOf", () => {
  // 項目・スレッド・書き込みの ID を記録に結ぶ（正常系）
  test.each([
    { id: "D-1", expected: { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" } },
    { id: "TH-1", expected: { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" } },
    { id: "TH-1-2", expected: { id: "TH-1-2", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" } },
    { id: "TH-1-9", expected: null },
    { id: "D-99", expected: null },
  ])("record_lookup_of", ({ id, expected }) => {
    // 準備
    const lookupOf = recordLookupOf({ index: buildIndex(data), threads });
    // 実行・検証
    expect(lookupOf(id)).toEqual(expected);
  });

  // 配る書き出しはスレッドの ID を結ばない（正常系）
  test("record_lookup_of_export", () => {
    // 準備
    const lookupOf = recordLookupOf({ index: buildIndex(data), threads: null });
    // 実行・検証
    expect(lookupOf("TH-1")).toBeNull();
    expect(lookupOf("D-1")?.title).toBe("保存先の決め方");
  });
});
