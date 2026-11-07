import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test } from "vitest";

import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

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
