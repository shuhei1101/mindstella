import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test } from "vitest";

import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

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
    renderRoute("/spa/?panel=comments&thread=TH-1");
    // 検証
    await screen.findByText("どちらにしますか");
    await waitFor(() => expect(calls).toBe(1));
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
    renderRoute("/spa/?panel=comments&thread=TH-1");
    await screen.findByText("どちらにしますか");
    await waitFor(() => expect(calls).toBe(1));
    // 実行
    await new Promise((resolve) => window.setTimeout(resolve, 300));
    const before = calls;
    await userEvent.click(screen.getByRole("button", { name: /一覧へ戻る/ }));
    await userEvent.click(await screen.findByRole("button", { name: /案の選び方/ }));
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
    renderRoute("/spa/?panel=comments&thread=TH-1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "クローズにする" }));
    await userEvent.type(screen.getByRole("textbox", { name: "理由（任意）" }), "決まった");
    await userEvent.click(screen.getAllByRole("button", { name: "クローズにする" }).at(-1) as HTMLElement);
    // 検証
    await waitFor(() => expect(bodies).toEqual([{ status: "closed", reason: "決まった" }]));
  });

  // 音声で返信を送る（正常系）
  test("thread_view_when_voice", async () => {
    // 準備
    installFakeMedia();
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
    renderRoute("/spa/?panel=comments&thread=TH-1");
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
});
