import { describe, expect, test } from "vitest";

import {
  choiceOf,
  commentNumber,
  hasUnseen,
  isBlockedReply,
  itemThreadCount,
  pendingThreads,
  reviewLabel,
  threadCounts,
  threadTimeline,
  threadTitle,
  visibleThreads,
  withSeen,
  type ReviewItem,
  type Thread,
} from "@/shared/core/comments";

const post = (patch: Partial<Thread["posts"][number]> = {}): Thread["posts"][number] => ({ id: "TH-1-1", author: "ai", created: "2026-11-01T00:00:00+00:00", body: "最初の行\n二行目", seen: true, ...patch });
const thread = (patch: Partial<Thread> = {}): Thread => ({ id: "TH-1", status: "open", summary: "", tags: [], target: null, loc: null, posts: [post()], events: [], ...patch });
const item = (patch: Partial<ReviewItem> = {}): ReviewItem => ({ id: "C-1", target: "D-1", loc: null, thread: null, body: "本文", created: "2026-11-01T00:00:00+00:00", ...patch });

describe("commentNumber", () => {
  // 番号を返す（正常系）
  test("comment_number", () => {
    expect(commentNumber("C-12")).toBe(12);
  });
});

describe("threadTitle", () => {
  // 要約が無い（正常系）
  test("thread_title_when_no_summary", () => {
    expect(threadTitle(thread({ summary: "" }))).toBe("最初の行");
  });
});

describe("visibleThreads", () => {
  // 状態とタグで絞る（正常系）
  test("visible_threads", () => {
    // 準備
    const threads = [
      thread({ id: "TH-1", tags: ["画面"] }),
      thread({ id: "TH-2" }),
      thread({ id: "TH-3", status: "closed", tags: ["画面"] }),
    ];
    // 実行
    const result = visibleThreads({ threads, filter: "open", tag: "画面", target: null });
    // 検証
    expect(result.map((entry) => entry.id)).toEqual(["TH-1"]);
  });
});

describe("threadCounts", () => {
  // 件数を数える（正常系）
  test("thread_counts", () => {
    // 準備
    const threads = [thread({ id: "TH-1" }), thread({ id: "TH-2" }), thread({ id: "TH-3", status: "closed" })];
    // 実行と検証
    expect(threadCounts({ threads, tag: null, target: null })).toEqual({ open: 2, closed: 1, all: 3 });
  });
});

describe("pendingThreads", () => {
  // タグで絞っている（正常系）
  test("pending_threads_when_tagged", () => {
    expect(pendingThreads({ items: [item()], filter: "open", tag: "画面", target: null })).toEqual([]);
  });
});

// 項目で絞るときのスレッド（D-1 へ向けたオープンの TH-1・D-2 へ向けたオープンの TH-2・D-1 へ向けたクローズの TH-5）
const targetThreads = (): Thread[] => [
  thread({ id: "TH-1", target: "D-1", tags: ["画面"], posts: [post({ created: "2026-11-01T01:00:00+00:00" })] }),
  thread({ id: "TH-2", target: "D-2", tags: ["画面"], posts: [post({ created: "2026-11-01T02:00:00+00:00" })] }),
  thread({ id: "TH-5", status: "closed", target: "D-1", posts: [post({ created: "2026-11-01T03:00:00+00:00" })] }),
];

describe("visibleThreads（項目）", () => {
  // 項目で絞る（正常系）
  test.each([
    { filter: "open" as const, target: "D-1", expected: ["TH-1"] },
    { filter: "all" as const, target: "D-1", expected: ["TH-5", "TH-1"] },
    { filter: "all" as const, target: "D-9", expected: [] },
  ])("visible_threads_when_target $filter $target", ({ filter, target, expected }) => {
    // 実行
    const result = visibleThreads({ threads: targetThreads(), filter, tag: null, target });
    // 検証
    expect(result.map((entry) => entry.id)).toEqual(expected);
  });
});

describe("threadCounts（項目）", () => {
  // 項目で絞った件数を数える（正常系）
  test.each([
    { tag: null, expected: { open: 1, closed: 1, all: 2 } },
    { tag: "画面", expected: { open: 1, closed: 0, all: 1 } },
  ])("thread_counts_when_target $tag", ({ tag, expected }) => {
    // 実行と検証
    expect(threadCounts({ threads: targetThreads(), tag, target: "D-1" })).toEqual(expected);
  });
});

describe("pendingThreads（項目）", () => {
  // 項目で絞ると、その項目への新規スレッドだけを出す（正常系）
  test.each([
    { filter: "open" as const, tag: null, expected: ["C-41"] },
    { filter: "closed" as const, tag: null, expected: [] },
    { filter: "open" as const, tag: "画面", expected: [] },
  ])("pending_threads_when_target $filter $tag", ({ filter, tag, expected }) => {
    // 準備
    const items = [
      item({ id: "C-41", target: "D-1" }),
      item({ id: "C-42", target: null }),
      item({ id: "C-43", target: null, thread: "TH-1" }),
      item({ id: "C-44", target: "D-1", body: null, choice: { key: "B" } }),
    ];
    // 実行
    const result = pendingThreads({ items, filter, tag, target: "D-1" });
    // 検証
    expect(result.map((entry) => entry.id)).toEqual(expected);
  });
});

describe("isBlockedReply", () => {
  // クローズのスレッド（正常系）
  test("is_blocked_reply", () => {
    expect(isBlockedReply({ item: item({ target: null, thread: "TH-1" }), threads: [thread({ status: "closed" })] })).toBe(true);
  });
});

describe("threadTimeline", () => {
  // 日時の順（正常系）
  test("thread_timeline", () => {
    // 準備
    const target = thread({
      posts: [post({ id: "TH-1-1", created: "2026-11-01T00:00:00+00:00" }), post({ id: "TH-1-2", created: "2026-11-03T00:00:00+00:00" })],
      events: [{ kind: "closed", author: "user", created: "2026-11-02T00:00:00+00:00", reason: null }],
    });
    // 実行
    const result = threadTimeline(target);
    // 検証
    expect(result.map((entry) => ("post" in entry ? entry.post.id : "event"))).toEqual(["TH-1-1", "event", "TH-1-2"]);
  });
});

describe("reviewLabel", () => {
  // 項目を指さない（正常系）
  test("review_label_when_no_target", () => {
    expect(reviewLabel(item({ target: null, thread: null }))).toBe("項目を指さないコメント");
  });

  // 案の選択（正常系）
  test("review_label_when_choice", () => {
    expect(reviewLabel(item({ target: "D-1", choice: { key: "B" } }))).toBe("D-1 への案の選択");
  });
});

describe("hasUnseen", () => {
  // 未読の書き込み（正常系）
  test("has_unseen", () => {
    expect(hasUnseen(thread({ posts: [post(), post({ id: "TH-1-2", seen: false })] }))).toBe(true);
  });
});

describe("withSeen", () => {
  // 開いたスレッドだけ既読（正常系）
  test("with_seen", () => {
    // 準備
    const threads = [thread({ id: "TH-1", posts: [post({ seen: false })] }), thread({ id: "TH-2", posts: [post({ id: "TH-2-1", seen: false })] })];
    // 実行
    const result = withSeen({ threads, id: "TH-1" });
    // 検証
    expect(result.map((entry) => entry.posts.every((one) => one.seen))).toEqual([true, false]);
  });
});

describe("choiceOf", () => {
  // その検討事項への案の選択だけを返却する（正常系）
  test("choice_of", () => {
    // 準備
    const items = [item({ id: "C-1" }), item({ id: "C-2", body: null, choice: { key: "B" } }), item({ id: "C-3", target: "D-2", body: null, choice: { key: "A" } })];
    // 実行・検証
    expect(choiceOf(items, "D-1")?.id).toBe("C-2");
    expect(choiceOf(items, "D-9")).toBeUndefined();
  });
});

describe("itemThreadCount", () => {
  // 項目に向けたスレッドと新規スレッドを数える（正常系）
  test.each([
    { id: "D-1", expected: 3 },
    { id: "D-3", expected: 0 },
  ])("item_thread_count: $id", ({ id, expected }) => {
    // 準備
    const threads = [thread({ id: "TH-1", target: "D-1" }), thread({ id: "TH-2", target: "D-1", status: "closed" }), thread({ id: "TH-3", target: "D-2" })];
    const pending = [item({ id: "C-1", target: "D-1" }), item({ id: "C-2", target: "D-1", thread: "TH-1" }), item({ id: "C-3", target: "D-1", choice: { key: "A" } })];
    // 実行・検証
    expect(itemThreadCount({ threads, pending, id })).toBe(expected);
  });
});
