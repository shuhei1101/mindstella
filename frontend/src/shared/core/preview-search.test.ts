import { describe, expect, test } from "vitest";

import { normalizeSearch, parsePreviewSearch, parseSearchString, toLegacyHash, type PreviewSearch, type SearchContext } from "@/shared/core/preview-search";
import type { MindmapData } from "@/shared/core/records";
import { buildIndex } from "@/shared/core/records";

const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [] };
const data = {
  ...empty,
  derived: { next: [] },
  tasks: [{ id: "T-1", title: "T-1の題", status: "進行中" }],
  docs: [{ id: "A-1", title: "A-1の題", body: "A-1.html" }],
  changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "", until_seq: 1, added: [], changed: [] }], pending: { added: [], changed: [] } },
} as unknown as MindmapData;

const context = (patch: Partial<SearchContext> = {}): SearchContext => ({
  index: buildIndex(data),
  pendingCount: 1,
  visibleKinds: ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"],
  diffActive: false,
  sortColumns: ["id", "title"],
  ...patch,
});

const search = (patch: Partial<PreviewSearch>): PreviewSearch => ({ f: {}, ...patch });

describe("parsePreviewSearch", () => {
  // 決めた値を受ける（正常系）
  test("parse_preview_search", () => {
    // 実行
    const parsed = parsePreviewSearch({ tab: "decisions", view: "table", "f.status": "要見直し" });
    // 検証
    expect(parsed.tab).toBe("decisions");
    expect(parsed.view).toBe("table");
    expect(parsed.f).toEqual({ status: "要見直し" });
  });

  // 決めた値以外は落とす（正常系）
  test("parse_preview_search_when_unknown", () => {
    // 実行
    const parsed = parsePreviewSearch({ tab: "unknown", full: "true" });
    // 検証
    expect(parsed.tab).toBeUndefined();
    expect(parsed.full).toBeUndefined();
  });
});

describe("parseSearchString", () => {
  // `f.{列}` を `f` に集める（正常系）
  test("parse_search_string", () => {
    // 実行
    const parsed = parseSearchString("?tab=decisions&f.status=%E4%BF%9D%E7%95%99");
    // 検証
    expect(parsed).toEqual({ tab: "decisions", f: { status: "保留" } });
  });
});

describe("normalizeSearch", () => {
  // 画面が持たない形式（正常系）
  test("normalize_search_when_view_mismatched", () => {
    expect(normalizeSearch(search({ tab: "tasks", view: "map" }), context()).view).toBeUndefined();
  });

  // 記録に無い項目（正常系）
  test("normalize_search_when_item_missing", () => {
    // 実行
    const result = normalizeSearch(search({ id: "T-99", full: "1", h: "決め方" }), context());
    // 検証
    expect(result.id).toBeUndefined();
    expect(result.full).toBeUndefined();
    expect(result.h).toBeUndefined();
  });

  // 記録に無い時点（正常系）
  test("normalize_search_when_diff_missing", () => {
    expect(normalizeSearch(search({ diff: "V-99" }), context()).diff).toBeUndefined();
  });

  // 保存待ちが 0 件（正常系）
  test("normalize_search_when_no_pending", () => {
    expect(normalizeSearch(search({ panel: "pending" }), context({ pendingCount: 0 })).panel).toBeUndefined();
  });

  // 表示しない種類（正常系）
  test("normalize_search_when_kind_hidden", () => {
    expect(normalizeSearch(search({ tab: "notes" }), context({ visibleKinds: ["decisions"] })).tab).toBeUndefined();
  });

  // 差分の表示中の設定の画面（正常系）
  test("normalize_search_when_settings_in_diff", () => {
    expect(normalizeSearch(search({ tab: "settings" }), context({ diffActive: true })).tab).toBeUndefined();
  });

  // 差分の表示中の保存待ちのパネル（正常系）
  test("normalize_search_when_panel_in_diff", () => {
    expect(normalizeSearch(search({ panel: "pending" }), context({ diffActive: true })).panel).toBeUndefined();
  });

  // 表に無い列（正常系）
  test("normalize_search_when_sort_unknown", () => {
    expect(normalizeSearch(search({ sort: "unknown" }), context()).sort).toBeUndefined();
  });

  // 本文が HTML の資料（正常系）
  test("normalize_search_when_html_body", () => {
    // 実行
    const result = normalizeSearch(search({ id: "A-1", h: "決め方" }), context());
    // 検証
    expect(result.id).toBe("A-1");
    expect(result.h).toBeUndefined();
  });
});

describe("toLegacyHash", () => {
  // 同じ名前で写す（正常系）
  test("to_legacy_hash", () => {
    // 実行
    const hash = toLegacyHash(search({ tab: "decisions", view: "table", id: "D-1", diff: "V-1" }));
    // 検証
    expect(hash).toEqual({ tab: "decisions", view: "table", id: "D-1", diff: "V-1" });
  });

  // ネットワークは view を写さない（正常系）
  test("to_legacy_hash_when_graph", () => {
    // 実行
    const hash = toLegacyHash(search({ tab: "decisions", view: "table", id: "D-1" }), "graph");
    // 検証
    expect(hash).toEqual({ tab: "graph", id: "D-1" });
  });
});
