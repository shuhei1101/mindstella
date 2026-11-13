import { describe, expect, test } from "vitest";

import { normalizeSearch, parsePreviewSearch, parseSearchString, type PreviewSearch, type SearchContext } from "@/shared/core/preview-search";
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
  threadIds: ["TH-1", "C-1"],
  threadTags: ["画面"],
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

  // 無いスレッド（正常系）
  test("normalize_search_when_thread_missing", () => {
    expect(normalizeSearch(search({ panel: "comments", thread: "TH-99" }), context())).toEqual(search({ panel: "comments" }));
  });

  // コメントの一覧を開いていない（正常系）
  test("normalize_search_when_comments_closed", () => {
    // 実行
    const result = normalizeSearch(search({ tab: "decisions", thread: "TH-1", review: "1" }), context());
    // 検証
    expect(result.thread).toBeUndefined();
    expect(result.review).toBeUndefined();
  });

  // 無いタグ（正常系）
  test("normalize_search_when_tag_missing", () => {
    expect(normalizeSearch(search({ panel: "comments", ttag: "無いタグ" }), context()).ttag).toBeUndefined();
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

  // ネットワークは表示する種類によらず開き、表示形式を持たない（正常系）
  test("normalize_search_when_graph", () => {
    // 実行
    const result = normalizeSearch(search({ tab: "graph", view: "table" }), context({ visibleKinds: ["decisions"] }));
    // 検証
    expect(result.tab).toBe("graph");
    expect(result.view).toBeUndefined();
  });

  // 検索を開いていない言葉（正常系）
  test("normalize_search_when_query_without_search", () => {
    expect(normalizeSearch(search({ q: "画面" }), context()).q).toBeUndefined();
  });

  // 空白だけの言葉（正常系）
  test("normalize_search_when_query_blank", () => {
    // 実行
    const result = normalizeSearch(search({ search: "1", q: " " }), context());
    // 検証
    expect(result.search).toBe("1");
    expect(result.q).toBeUndefined();
  });
});
