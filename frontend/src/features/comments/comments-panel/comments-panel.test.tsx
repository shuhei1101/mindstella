import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

// スレッドの画面が読む文字起こしの状態（使わない）
const transcription = http.get("/api/transcription", () => HttpResponse.json({ available: false, reason: null, detail: null, presets: [], action: "send", preset: null }));

const thread = (id: string, status: "open" | "closed", summary: string) => ({
  id,
  status,
  summary,
  tags: [],
  target: null,
  target_title: null,
  loc: null,
  events: [],
  posts: [{ id: `${id}-1`, author: "ai", body: "質問", created: "2026-11-01T00:00:00+00:00", seen: true }],
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CommentsPanel", () => {
  // スレッドを並べる（正常系）
  test("comments_panel", async () => {
    // 準備
    server.use(http.get("/api/threads", () => HttpResponse.json({ threads: [thread("TH-1", "open", "一つ目"), thread("TH-2", "open", "二つ目"), thread("TH-3", "closed", "三つ目")] })));
    // 実行
    renderRoute("/spa/?panel=comments");
    // 検証
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    await waitFor(() => expect(within(panel).getAllByRole("listitem")).toHaveLength(2));
    expect(panel).toHaveTextContent("一つ目");
    expect(panel).not.toHaveTextContent("三つ目");
  });

  // 新しいスレッドを溜める（正常系）
  test("comments_panel_when_new_thread", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.post("/api/comments", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ id: "C-3", created: "2026-11-01T00:00:00+00:00", count: 3 }, { status: 201 });
      }),
    );
    renderRoute("/spa/?panel=comments");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    // 実行
    await userEvent.click(within(panel).getByRole("button", { name: "新しいスレッド" }));
    await userEvent.type(within(panel).getByRole("textbox"), "全体の進め方");
    await userEvent.click(within(panel).getByRole("button", { name: /レビューに追加/ }));
    // 検証
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).not.toHaveProperty("target");
  });

  // スレッドから一覧へ戻った後、開いていた行へフォーカスを戻す（正常系）
  test("comments_panel_when_back_focus", async () => {
    // 準備（描き直しより先に次のコマが来る順にする）
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      queueMicrotask(() => {
        callback(0);
      });
      return 0;
    });
    server.use(transcription, http.get("/api/threads", () => HttpResponse.json({ threads: [thread("TH-1", "open", "一つ目"), thread("TH-2", "open", "二つ目")] })));
    renderRoute("/spa/?panel=comments&thread=TH-2");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    // 実行
    await userEvent.click(await within(panel).findByRole("button", { name: "一覧へ戻る" }));
    // 検証
    await waitFor(() => {
      expect(panel.querySelector('[data-focus="thread:TH-2"]')).toHaveFocus();
    });
  });

  // 戻す先の行が一覧に無いとき、フォーカスを移さない（正常系）
  test("comments_panel_when_back_without_row", async () => {
    // 準備（絞り込みはオープンのまま、クローズのスレッドを開く）
    server.use(transcription, http.get("/api/threads", () => HttpResponse.json({ threads: [thread("TH-1", "open", "一つ目"), thread("TH-2", "closed", "二つ目")] })));
    renderRoute("/spa/?panel=comments&thread=TH-2");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    await userEvent.click(await within(panel).findByRole("button", { name: "一覧へ戻る" }));
    await within(panel).findByRole("group", { name: "スレッドの状態で絞る" });
    // 実行
    const closedFilter = within(within(panel).getByRole("group", { name: "スレッドの状態で絞る" })).getByRole("button", { name: /^クローズ/ });
    await userEvent.click(closedFilter);
    // 検証
    await waitFor(() => expect(panel.querySelector('[data-focus="thread:TH-2"]')).not.toBeNull());
    expect(closedFilter).toHaveFocus();
  });

  // スレッドが読めない（異常系）
  test("comments_panel_when_threads_failed", async () => {
    // 準備
    server.use(http.get("/api/threads", () => HttpResponse.json({ type: "about:blank", title: "Internal Server Error", status: 500, detail: "読めません" }, { status: 500, headers: { "Content-Type": "application/problem+json" } })));
    // 実行
    renderRoute("/spa/?panel=comments");
    // 検証
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    expect(await within(panel).findByRole("alert")).toHaveTextContent("スレッドを読めませんでした。");
  });
});
