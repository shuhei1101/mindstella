import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test } from "vitest";

import { resetVoiceStore } from "@/shared/stores/voice-store";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

const items = [
  { id: "C-1", target: "D-1", target_title: "D-1の題", loc: null, thread: null, body: "一つ目", created: "2026-11-01T00:00:00+00:00" },
  { id: "C-2", target: "D-1", target_title: "D-1の題", loc: null, thread: null, body: "二つ目", created: "2026-11-01T00:01:00+00:00" },
];

afterEach(() => {
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
});

describe("ReviewView", () => {
  // まとめて送信（正常系）
  test("review_view", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.get("/api/comments", () => HttpResponse.json({ items, drafts: [] })),
      http.post("/api/comments/send", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ sent: "2026-11-01T00:02:00+00:00", items: [], entered: true }, { status: 201 });
      }),
    );
    renderRoute("/spa/?panel=comments&review=1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /まとめて送信（2 件）/ }));
    // 検証
    await waitFor(() => expect(bodies).toEqual([{ ids: ["C-1", "C-2"] }]));
  });

  // 箇所が合わない（異常系）
  test("review_view_when_stale", async () => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "A-1の題", status: "下書き", body: "docs/A-1.md" }], bodies: { "docs/A-1.md": "一行" } });
    server.use(
      http.get("/api/comments", () => HttpResponse.json({ items: [{ ...items[0], target: "A-1", loc: { kind: "body", start: 3, end: 3, key: null, text: "三行目" } }], drafts: [] })),
      http.post("/api/comments/send", () =>
        HttpResponse.json(
          { type: "about:blank", title: "Conflict", status: 409, detail: "箇所が合いません", stale: [{ id: "C-1", reason: "本文の 3 行目がありません" }] },
          { status: 409, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    renderRoute("/spa/?panel=comments&review=1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /まとめて送信/ }));
    // 検証
    expect(await screen.findByRole("alert")).toHaveTextContent("本文の 3 行目がありません");
    expect(screen.getByRole("button", { name: "箇所を解除" })).toBeInTheDocument();
  });
});

describe("ReviewView の修正の音声入力", () => {
  // 修正の入力のマイクで録音して文字起こしの結果が入力欄に入る（正常系）
  test("review_view_when_edit_voice", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    const sent: unknown[] = [];
    server.use(
      http.get("/api/comments", () => HttpResponse.json({ items, drafts: [] })),
      http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: [], action: "send", preset: null })),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "案 A にする" })),
      http.post("/api/comments/send-now", async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json({ sent: "t", thread: "TH-1", post: "TH-1-1", entered: true }, { status: 201 });
      }),
    );
    renderRoute("/spa/?panel=comments&review=1");
    const [start] = await screen.findAllByRole("button", { name: "D-1 へのコメントを修正" });
    if (start === undefined) throw new Error("修正のボタンが無い");
    await userEvent.click(start);
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    await userEvent.click(await screen.findByRole("button", { name: "文字起こし" }));
    // 検証
    await waitFor(() => expect(screen.getByRole<HTMLTextAreaElement>("textbox", { name: /の本文$/ }).value).toContain("案 A にする"));
    expect(screen.getByText("文字起こしの結果を挿入しました。")).toBeInTheDocument();
    expect(sent).toEqual([]);
  });
});
