import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { requestPost } from "@/shared/core/thread-ids";
import { resetVoiceStore } from "@/shared/stores/voice-store";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { stubRecords } from "@/testing/msw/fixtures";
import { RECORDS } from "@/testing/msw/handlers";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

// 「レビューに追加」の後のフォーカスの移動先（テストごとに書き換える）
const focusTarget = vi.hoisted((): { current: "input" | "submit" } => ({ current: "input" }));
vi.mock("@/shared/stores/prefs-store", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/stores/prefs-store")>()),
  useFocusAfterAddTarget: () => focusTarget.current,
}));

// ThreadPost に渡った `fold` を書き込みの ID ごとに残す（本物の描画はそのまま）
const folds = vi.hoisted(() => new Map<string, boolean | undefined>());
vi.mock("@/features/comments/shared/thread-post", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/comments/shared/thread-post")>();
  const ThreadPost = (props: Parameters<typeof original.ThreadPost>[0]) => {
    if (props.post !== undefined && props.post !== null) folds.set(props.post.id, (props as { fold?: boolean }).fold);
    return original.ThreadPost(props);
  };
  return { ...original, ThreadPost };
});

const unseen = {
  threads: [
    {
      id: "TH-1",
      status: "open",
      summary: "案の選び方",
      tags: [],
      target: null,
      target_title: null,
      loc: null,
      events: [],
      posts: [{ id: "TH-1-1", author: "ai", body: "どちらにしますか", created: "2026-11-01T00:00:00+00:00", seen: false }],
    },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
  folds.clear();
  focusTarget.current = "input";
  resetVoiceStore();
  removeFakeWakeLock();
  vi.unstubAllGlobals();
});

describe("ThreadView", () => {
  // 既読にする（正常系）
  test("thread_view", async () => {
    // 準備
    let calls = 0;
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseen)),
      http.post("/api/threads/:id/seen", () => {
        calls += 1;
        return HttpResponse.json({ id: "TH-1", seen: ["TH-1-1"] });
      }),
    );
    // 実行
    renderRoute("/?panel=comments&thread=TH-1");
    // 検証
    await screen.findByText("どちらにしますか");
    await waitFor(() => expect(calls).toBe(1));
  });

  // 書き込みの並びをパネルの幅より広げない（正常系）
  test("thread_view_when_wide_table", async () => {
    // 準備
    server.use(http.get("/api/threads", () => HttpResponse.json(unseen)), http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: ["TH-1-1"] })));
    // 実行
    renderRoute("/?panel=comments&thread=TH-1");
    // 検証
    const post = await screen.findByText("どちらにしますか");
    const list = post.closest("ol");
    expect(list).toHaveClass("grid-cols-1");
    expect(post.closest("article")).toHaveClass("min-w-0");
  });

  // 失敗した後に呼び直さない（異常系）
  test("thread_view_when_seen_failed", async () => {
    // 準備
    let calls = 0;
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseen)),
      http.post("/api/threads/:id/seen", () => {
        calls += 1;
        return HttpResponse.json({ type: "about:blank", title: "Internal Server Error", status: 500, detail: "書けません" }, { status: 500, headers: { "Content-Type": "application/problem+json" } });
      }),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    await screen.findByText("どちらにしますか");
    await waitFor(() => expect(calls).toBe(1));
    // 実行
    await new Promise((resolve) => window.setTimeout(resolve, 300));
    const before = calls;
    await userEvent.click(screen.getByRole("button", { name: /一覧へ戻る/ }));
    await userEvent.click(await within(screen.getByRole("dialog", { name: "コメント" })).findByRole("button", { name: /案の選び方/ }));
    // 検証
    expect(before).toBe(1);
    await waitFor(() => expect(calls).toBe(2));
  });

  // クローズにする（正常系）
  test("thread_view_when_close", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseen)),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: [] })),
      http.patch("/api/threads/:id", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ id: "TH-1", status: "closed", changed: true });
      }),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "クローズにする" }));
    await userEvent.type(screen.getByRole("textbox", { name: "理由（任意）" }), "決まった");
    await userEvent.click(screen.getAllByRole("button", { name: "クローズにする" }).at(-1) as HTMLElement);
    // 検証
    await waitFor(() => expect(bodies).toEqual([{ status: "closed", reason: "決まった" }]));
  });

  // クローズにした後、描き直した「オープンに戻す」へフォーカスを戻す（正常系）
  test("thread_view_when_close_focus", async () => {
    // 準備（描き直しより先に次のコマが来る順にする）
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      queueMicrotask(() => {
        callback(0);
      });
      return 0;
    });
    let status = "open";
    server.use(
      http.get("/api/threads", () => HttpResponse.json({ threads: [{ ...unseen.threads[0], status }] })),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: [] })),
      http.patch("/api/threads/:id", () => {
        status = "closed";
        return HttpResponse.json({ id: "TH-1", status: "closed", changed: true });
      }),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    await userEvent.click(await screen.findByRole("button", { name: "クローズにする" }));
    await userEvent.type(screen.getByRole("textbox", { name: "理由（任意）" }), "決まった");
    // 実行
    await userEvent.click(screen.getAllByRole("button", { name: "クローズにする" }).at(-1) as HTMLElement);
    // 検証
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "オープンに戻す" })).toHaveFocus();
    });
  });

  // 音声で返信を送る（正常系）
  test("thread_view_when_voice", async () => {
    // 準備
    installFakeMedia();
    stubRecords({ settings: { ...RECORDS.settings, transcription: { action: "send" } } });
    const sent: unknown[] = [];
    let threadReads = 0;
    server.use(
      http.get("/api/threads", () => {
        threadReads += 1;
        return HttpResponse.json(unseen);
      }),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: [] })),
      http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: [], action: "send", preset: null })),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "x" })),
      http.post("/api/comments/send-now", async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json({ sent: "2026-11-09T00:00:00+00:00", thread: "TH-1", post: "TH-1-2", entered: true }, { status: 201 });
      }),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    await screen.findByText("どちらにしますか");
    const readsBefore = threadReads;
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    await userEvent.click(await screen.findByRole("button", { name: "文字起こし" }));
    // 検証
    await waitFor(() => expect(sent).toEqual([{ thread: "TH-1", body: "x" }]));
    await waitFor(() => expect(threadReads).toBeGreaterThan(readsBefore));
    removeFakeMedia();
  });

  // 既定の挙動で返信をレビュー中に溜める（正常系）
  test("thread_view_when_voice_reviewed", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    const added: unknown[] = [];
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseen)),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: [] })),
      http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: [], action: "review", preset: null })),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "x" })),
      http.post("/api/comments", async ({ request }) => {
        added.push(await request.json());
        return HttpResponse.json({ id: "C-1", created: "2026-11-14T00:00:00+00:00", count: 1 }, { status: 201 });
      }),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    await screen.findByText("どちらにしますか");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    await userEvent.click(await screen.findByRole("button", { name: "文字起こし" }));
    // 検証
    await waitFor(() => expect(added).toEqual([{ thread: "TH-1", body: "x" }]));
    expect(await screen.findByText("文字起こしの結果をレビュー中に追加しました。")).toBeInTheDocument();
    removeFakeMedia();
  });

  // 返信を溜めた後のフォーカスを移動先に従わせる（正常系）
  test.each([
    { target: "input" as const },
    { target: "submit" as const },
  ])("thread_view_when_focus_after_add ($target)", async ({ target }) => {
    // 準備
    focusTarget.current = target;
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseen)),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: [] })),
      http.post("/api/comments", () => HttpResponse.json({ id: "C-1", created: "2026-11-01T00:00:00+00:00", count: 1 }, { status: 201 })),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    await screen.findByText("どちらにしますか");
    const panel = await screen.findByRole("dialog", { name: "コメント" });
    // 実行（入力欄へ戻すかを確かめるときはボタンを押し、戻さないかを確かめるときは入力欄で Ctrl+Enter を押す）
    await userEvent.type(within(panel).getByRole("textbox"), "案 A にする");
    if (target === "submit") await userEvent.keyboard("{Control>}{Enter}{/Control}");
    else await userEvent.click(within(panel).getByRole("button", { name: /レビューに追加/ }));
    // 検証
    const focused = target === "submit" ? () => within(panel).getByRole("button", { name: "レビューに追加" }) : () => within(panel).getByRole("textbox");
    await waitFor(() => expect(focused()).toHaveFocus());
  });
});

describe("ThreadView の修正の音声入力", () => {
  // レビュー中の返信の修正の入力で録音し、設定によらず挿入だけにする（正常系）
  test("thread_view_when_edit_voice", async () => {
    // 準備
    installFakeMedia();
    stubRecords({ settings: { ...RECORDS.settings, transcription: { action: "send" } } });
    const sent: unknown[] = [];
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseen)),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: [] })),
      http.get("/api/comments", () => HttpResponse.json({ items: [{ id: "C-1", thread: "TH-1", target: null, target_title: null, loc: null, body: "確認: ", created: "2026-11-01T00:01:00+00:00" }], drafts: [] })),
      http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: [], action: "send", preset: null })),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "案 A にする" })),
      http.post("/api/comments/send-now", async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json({ sent: "2026-11-09T00:00:00+00:00", thread: "TH-1", post: "TH-1-2", entered: true }, { status: 201 });
      }),
    );
    renderRoute("/?panel=comments&thread=TH-1");
    await userEvent.click(await screen.findByRole("button", { name: "TH-1 への返信を修正" }));
    const edit = (await screen.findByRole("textbox", { name: "TH-1 への返信の本文" })).closest("form");
    if (edit === null) throw new Error("修正の入力が無い");
    // 実行
    await userEvent.click(within(edit).getByRole("button", { name: "音声で入力" }));
    await userEvent.click(await within(edit).findByRole("button", { name: "文字起こし" }));
    // 検証
    await waitFor(() => expect(within(edit).getByRole<HTMLTextAreaElement>("textbox").value).toContain("案 A にする"));
    expect(sent).toEqual([]);
    removeFakeMedia();
  });

  // 開いたら最新の書き込みへ移る（正常系）
  test("thread_view_when_open_latest", async () => {
    // 準備
    const three = {
      threads: [
        {
          ...unseen.threads[0],
          posts: [
            { id: "TH-1-1", author: "ai", body: "1 件目", created: "2026-11-01T00:00:00+00:00", seen: true },
            { id: "TH-1-2", author: "user", body: "2 件目", created: "2026-11-02T00:00:00+00:00", seen: true },
            { id: "TH-1-3", author: "ai", body: "3 件目", created: "2026-11-03T00:00:00+00:00", seen: true },
          ],
        },
      ],
    };
    server.use(http.get("/api/threads", () => HttpResponse.json(three)));
    vi.spyOn(HTMLElement.prototype, "offsetTop", "get").mockImplementation(function (this: HTMLElement) {
      return this.closest("article")?.textContent?.includes("3 件目") === true ? 400 : 0;
    });
    vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(1000);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(300);
    // 実行
    renderRoute("/?panel=comments&thread=TH-1");
    // 検証
    const latest = (await screen.findByText("3 件目")).closest("article");
    await waitFor(() => expect(latest).toHaveFocus());
    const list = latest?.closest("ol");
    expect(list?.scrollTop).toBe(400);
    expect(["TH-1-1", "TH-1-2", "TH-1-3"].map((id) => folds.get(id) === true)).toEqual([true, true, false]);
  });

  // スクロールしたらタイトルを 1 行にする（正常系）
  test("thread_view_when_title_collapsed", async () => {
    // 準備
    server.use(http.get("/api/threads", () => HttpResponse.json(unseen)), http.post("/api/threads/:id/seen", () => HttpResponse.json({ id: "TH-1", seen: ["TH-1-1"] })));
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0);
      return 0;
    });
    renderRoute("/?panel=comments&thread=TH-1");
    const post = await screen.findByText("どちらにしますか");
    const scroller = post.closest("ol") as HTMLElement;
    const title = () => document.querySelector("[data-part='thread-title']");
    const scrollTo = (top: number) => {
      scroller.scrollTop = top;
      fireEvent.scroll(scroller);
    };
    // 実行・検証
    expect(title()).not.toHaveAttribute("data-collapsed");
    scrollTo(120);
    await waitFor(() => expect(title()).toHaveAttribute("data-collapsed"));
    scrollTo(0);
    await waitFor(() => expect(title()).not.toHaveAttribute("data-collapsed"));
  });

  // 書き込みの ID のリンクで開いたときは最新の書き込みへ移らない（正常系）
  test("thread_view_when_open_post", async () => {
    // 準備
    const three = {
      threads: [
        {
          ...unseen.threads[0],
          posts: [
            { id: "TH-1-1", author: "ai", body: "1 件目", created: "2026-11-01T00:00:00+00:00", seen: true },
            { id: "TH-1-2", author: "user", body: "2 件目", created: "2026-11-02T00:00:00+00:00", seen: true },
            { id: "TH-1-3", author: "ai", body: "3 件目", created: "2026-11-03T00:00:00+00:00", seen: true },
          ],
        },
      ],
    };
    server.use(http.get("/api/threads", () => HttpResponse.json(three)));
    requestPost("TH-1-2");
    // 実行
    renderRoute("/?panel=comments&thread=TH-1");
    const second = (await screen.findByText("2 件目")).closest("article");
    second?.focus();
    // 検証
    await new Promise((resolve) => { requestAnimationFrame(() => { requestAnimationFrame(resolve); }); });
    expect(second).toHaveFocus();
    expect(second?.closest("ol")?.scrollTop).toBe(0);
  });
});
