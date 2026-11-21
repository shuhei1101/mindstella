import { describe, expect, test } from "vitest";

import { normalizeSearch, parsePreviewSearch, parseSearchString, type PreviewSearch, type SearchContext } from "@/shared/core/preview-search";
import type { MindmapData } from "@/shared/core/records";
import { buildIndex } from "@/shared/core/records";

const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [] };
const data = {
  ...empty,
  derived: { ready: [] },
  decisions: [{ id: "D-1", title: "D-1の題", status: "未決定" }],
  tasks: [{ id: "T-1", title: "T-1の題", status: "進行中" }],
  docs: [{ id: "A-1", title: "A-1の題", body: "docs/A-1.html" }],
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

  // 削除したネットワーク・検討事項のマップを指す値は落とす（正常系）
  test.each([
    { name: "graph", raw: { tab: "graph" }, tab: undefined },
    { name: "map", raw: { tab: "decisions", view: "map" }, tab: "decisions" },
  ])("parse_preview_search_when_removed_view ($name)", ({ raw, tab }) => {
    // 実行
    const parsed = parsePreviewSearch(raw);
    // 検証
    expect(parsed.tab).toBe(tab);
    expect(parsed.view).toBeUndefined();
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
  // タグの式として読めない tx（正常系）
  test.each([["{"], ['{"field":"tags","op":"gt","values":[]}']])("normalize_search_when_tx_invalid %s", (tx) => {
    expect(normalizeSearch(search({ tab: "tasks", tx }), context()).tx).toBeUndefined();
  });

  // 画面が持たない形式（正常系）
  test("normalize_search_when_view_mismatched", () => {
    expect(normalizeSearch(search({ tab: "tasks", view: "cards" }), context()).view).toBeUndefined();
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

  // 記録に無い項目で絞る値と、コメントの一覧を開いていないときの値（正常系）
  test.each([
    { patch: { panel: "comments" as const, ttarget: "D-99" }, expected: { panel: "comments", ttarget: undefined } },
    { patch: { tab: "decisions" as const, ttarget: "D-1" }, expected: { panel: undefined, ttarget: undefined } },
    { patch: { panel: "comments" as const, ttarget: "D-1" }, expected: { panel: "comments", ttarget: "D-1" } },
  ])("normalize_search_when_target_missing $patch.ttarget", ({ patch, expected }) => {
    // 実行
    const result = normalizeSearch(search(patch), context());
    // 検証
    expect({ panel: result.panel, ttarget: result.ttarget }).toEqual(expected);
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

  // タグの条件が無い組み合わせ方（正常系）
  test("normalize_search_when_tagmatch_without_tags", () => {
    expect(normalizeSearch(search({ tab: "tasks", tagmatch: "any" }), context()).tagmatch).toBeUndefined();
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
