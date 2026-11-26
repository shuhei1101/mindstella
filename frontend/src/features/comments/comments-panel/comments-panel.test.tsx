import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { usePanelWidthStore } from "@/shared/stores/panel-width-store";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

// 「レビューに追加」の後のフォーカスの移動先（テストごとに書き換える）
const focusTarget = vi.hoisted((): { current: "input" | "submit" } => ({ current: "input" }));
vi.mock("@/shared/stores/prefs-store", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/stores/prefs-store")>()),
  useFocusAfterAddTarget: () => focusTarget.current,
}));

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
  focusTarget.current = "input";
  vi.unstubAllGlobals();
});

describe("CommentsPanel", () => {
  // スレッドを並べる（正常系）
  test("comments_panel", async () => {
    // 準備
    server.use(http.get("/api/threads", () => HttpResponse.json({ threads: [thread("TH-1", "open", "一つ目"), thread("TH-2", "open", "二つ目"), thread("TH-3", "closed", "三つ目")] })));
    // 実行
    renderRoute("/?panel=comments");
    // 検証
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    await waitFor(() => expect(within(panel).getAllByRole("listitem")).toHaveLength(2));
    expect(panel).toHaveTextContent("一つ目");
    expect(panel).not.toHaveTextContent("三つ目");
  });

  // 新規スレッドを溜める（正常系）
  test("comments_panel_when_new_thread", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.post("/api/comments", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ id: "C-3", created: "2026-11-01T00:00:00+00:00", count: 3 }, { status: 201 });
      }),
    );
    renderRoute("/?panel=comments");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    // 実行
    await userEvent.click(within(panel).getByRole("button", { name: "新規スレッド" }));
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
    renderRoute("/?panel=comments&thread=TH-2");
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
    renderRoute("/?panel=comments&thread=TH-2");
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

  // クローズにして戻った後、行が消えれば次の行へフォーカスを移す（一覧の並びは新しい順で TH-3・TH-2・TH-1）（正常系）
  test.each([
    { name: "all", search: "&tstatus=all", ids: ["TH-1", "TH-2", "TH-3"], close: "TH-2", focus: "thread:TH-2" },
    { name: "open-middle", search: "", ids: ["TH-1", "TH-2", "TH-3"], close: "TH-2", focus: "thread:TH-1" },
    { name: "open-last", search: "", ids: ["TH-1", "TH-2", "TH-3"], close: "TH-1", focus: "thread:TH-2" },
    { name: "open-only", search: "", ids: ["TH-1"], close: "TH-1", focus: null },
  ])("comments_panel_when_closed_focus ($name)", async ({ search, ids, close, focus }) => {
    // 準備
    const statuses = new Map<string, "open" | "closed">(ids.map((id) => [id, "open"]));
    server.use(
      transcription,
      http.get("/api/threads", () => HttpResponse.json({ threads: ids.map((id) => thread(id, statuses.get(id) ?? "open", `${id} の話`)) })),
      http.post("/api/threads/:id/seen", ({ params }) => HttpResponse.json({ id: params["id"], seen: [] })),
      http.patch("/api/threads/:id", ({ params }) => {
        statuses.set(String(params["id"]), "closed");
        return HttpResponse.json({ id: params["id"], status: "closed", changed: true });
      }),
    );
    renderRoute(`/?panel=comments&thread=${close}${search}`);
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    const before = window.history.length;
    // 実行
    await userEvent.click(await within(panel).findByRole("button", { name: "クローズにする" }));
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).has("thread")).toBe(false));
    expect(window.history.length).toBe(before);
    await waitFor(() => {
      const target = focus === null ? within(panel).getByText("オープンのスレッドはありません。") : panel.querySelector(`[data-focus="${focus}"]`);
      expect(target).toHaveFocus();
    });
  });

  // スレッドが読めない（異常系）
  test("comments_panel_when_threads_failed", async () => {
    // 準備
    server.use(http.get("/api/threads", () => HttpResponse.json({ type: "about:blank", title: "Internal Server Error", status: 500, detail: "読めません" }, { status: 500, headers: { "Content-Type": "application/problem+json" } })));
    // 実行
    renderRoute("/?panel=comments");
    // 検証
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    expect(await within(panel).findByRole("alert")).toHaveTextContent("スレッドを読めませんでした。");
  });
  // 項目で絞ったスレッドを並べ、チップの × で外す（正常系）
  test("comments_panel_when_target", async () => {
    // 準備
    server.use(
      http.get("/api/threads", () =>
        HttpResponse.json({ threads: [{ ...thread("TH-1", "open", "D-1 の話"), target: "D-1" }, { ...thread("TH-2", "open", "D-2 の話"), target: "D-2" }] }),
      ),
      http.get("/api/comments", () =>
        HttpResponse.json({ items: [{ id: "C-41", target: "D-1", loc: null, thread: null, body: "D-1 への新規スレッド", created: "2026-11-01T00:00:00+00:00" }], drafts: [] }),
      ),
    );
    renderRoute("/?panel=comments&ttarget=D-1");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    const before = window.history.length;
    // 実行
    await waitFor(() => expect(within(panel).getAllByRole("listitem")).toHaveLength(2));
    const rows = within(panel).getAllByRole("listitem").map((row) => row.textContent);
    await userEvent.click(within(panel).getByRole("button", { name: "項目「D-1」の絞り込みを外す" }));
    // 検証
    expect(rows[0]).toContain("D-1 への新規スレッド");
    expect(rows[1]).toContain("D-1 の話");
    expect(panel).not.toHaveTextContent(/\d+ 件/);
    await waitFor(() => expect(within(panel).getAllByRole("listitem")).toHaveLength(3));
    expect(window.location.search).not.toContain("ttarget");
    expect(window.history.length).toBe(before);
  });
  // 項目で絞っている間の新規スレッドは、その項目へ向けて溜める（正常系）
  test("comments_panel_when_target_new_thread", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.post("/api/comments", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ id: "C-3", created: "2026-11-01T00:00:00+00:00", count: 3 }, { status: 201 });
      }),
    );
    renderRoute("/?panel=comments&ttarget=D-1");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    // 実行
    await userEvent.click(within(panel).getByRole("button", { name: "新規スレッド" }));
    await userEvent.type(within(panel).getByRole("textbox"), "D-1 の進め方");
    await userEvent.click(within(panel).getByRole("button", { name: /レビューに追加/ }));
    // 検証
    expect(within(panel).getByRole("heading", { name: "D-1 への新規スレッド" })).toBeInTheDocument();
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ target: "D-1" });
    expect(bodies[0]).not.toHaveProperty("loc");
  });

  // 新規スレッドを溜めた後のフォーカスを移動先に従わせる（正常系）
  test.each([
    { target: "input" as const },
    { target: "submit" as const },
  ])("comments_panel_when_focus_after_add ($target)", async ({ target }) => {
    // 準備
    focusTarget.current = target;
    server.use(http.post("/api/comments", () => HttpResponse.json({ id: "C-3", created: "2026-11-01T00:00:00+00:00", count: 3 }, { status: 201 })));
    renderRoute("/?panel=comments");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    // 実行（入力欄へ戻すかを確かめるときはボタンを押し、戻さないかを確かめるときは入力欄で Ctrl+Enter を押す）
    await userEvent.click(within(panel).getByRole("button", { name: "新規スレッド" }));
    await userEvent.type(within(panel).getByRole("textbox"), "全体の進め方");
    if (target === "submit") await userEvent.keyboard("{Control>}{Enter}{/Control}");
    else await userEvent.click(within(panel).getByRole("button", { name: /レビューに追加/ }));
    // 検証
    const focused = target === "submit" ? () => within(panel).getByRole("button", { name: "レビューに追加" }) : () => within(panel).getByRole("textbox");
    await waitFor(() => expect(focused()).toHaveFocus());
  });

  // スレッドの一覧・スレッド・レビュー中の書き込みで同じ幅を使用する（正常系）
  test.each(["/?panel=comments", "/?panel=comments&thread=TH-1", "/?panel=comments&review=1"])(
    "comments_panel_when_width_shared: %s",
    async (path) => {
      // 準備
      window.innerWidth = 1440;
      usePanelWidthStore.setState({ leftWidth: 520 });
      server.use(
        transcription,
        http.get("/api/threads", () => HttpResponse.json({ threads: [thread("TH-1", "open", "一つ目")] })),
        http.get("/api/comments", () => HttpResponse.json({ items: [], drafts: [] })),
      );
      // 実行
      renderRoute(path);
      // 検証
      const panel = await screen.findByRole("dialog", { name: "コメント" });
      expect(panel.style.width).toBe("520px");
      expect(within(panel).getAllByRole("separator", { name: "コメントの一覧の幅" })).toHaveLength(1);
      usePanelWidthStore.setState({ leftWidth: null });
    },
  );
});
