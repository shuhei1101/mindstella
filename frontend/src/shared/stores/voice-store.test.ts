import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { VOICE_TEXT } from "@/shared/core/voice";
import {
  cancelVoice,
  discardVoice,
  dismissVoiceNotice,
  finishVoice,
  readVoiceState,
  resetVoiceStore,
  startVoice,
  takeVoiceResult,
} from "@/shared/stores/voice-store";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { server } from "@/testing/msw/server";

/** D-1 のコメントの入力 */
const D1 = { key: "D-1#", destination: { target: "D-1", loc: null }, view: "panel" as const, label: "D-1 へのコメント", selection: { start: 4, end: 4 } };

/** D-2 のコメントの入力 */
const D2 = { key: "D-2#", destination: { target: "D-2", loc: null }, view: "panel" as const, label: "D-2 へのコメント", selection: { start: 0, end: 0 } };

beforeEach(() => {
  resetVoiceStore();
});

afterEach(() => {
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
  vi.useRealTimers();
});

/** 文字起こしの応答を差し替え、レビュー中への追加・すぐ送る・書きかけの保存の本文を控える */
const stubVoiceApi = (options: { transcribe?: () => Response; comments?: number } = {}) => {
  const added: unknown[] = [];
  const sent: unknown[] = [];
  const drafts: unknown[] = [];
  server.use(
    http.post("/api/transcriptions", () => options.transcribe?.() ?? HttpResponse.json({ text: "案 A にする" })),
    http.post("/api/comments", async ({ request }) => {
      added.push(await request.json());
      const status = options.comments ?? 201;
      if (status !== 201) return HttpResponse.json({ type: "about:blank", title: "Error", status, detail: "x" }, { status });
      return HttpResponse.json({ id: "C-1", created: "2026-11-14T00:00:00+00:00", count: 1 }, { status: 201 });
    }),
    http.post("/api/comments/send-now", async ({ request }) => {
      sent.push(await request.json());
      return HttpResponse.json({ sent: "t", thread: "TH-1", post: "TH-1-1", entered: true }, { status: 201 });
    }),
    http.put("/api/drafts", async ({ request }) => {
      drafts.push(await request.json());
      return HttpResponse.json({ ok: true });
    }),
  );
  return { added, sent, drafts };
};

describe("startVoice", () => {
  // 1 つだけ録り、画面の消灯の抑止を求める（正常系）
  test("start_voice", async () => {
    // 準備
    installFakeMedia();
    const wakeLock = installFakeWakeLock();
    // 実行
    const first = await startVoice(D1);
    const second = await startVoice(D2);
    // 検証
    expect([first, second]).toEqual([null, null]);
    expect(readVoiceState().session?.key).toBe("D-1#");
    expect(readVoiceState().session?.phase).toBe("recording");
    expect(wakeLock.requested()).toEqual(["screen"]);
  });
});

describe("cancelVoice", () => {
  // 録音を捨てて抑止を解く（正常系）
  test("cancel_voice", async () => {
    // 準備
    const media = installFakeMedia();
    const wakeLock = installFakeWakeLock();
    await startVoice(D1);
    // 実行
    cancelVoice();
    await Promise.resolve();
    // 検証
    expect(media.stoppedTracks()).toBe(1);
    expect(wakeLock.released()).toBe(1);
    expect(readVoiceState().session).toBeNull();
  });
});

describe("finishVoice", () => {
  // 挙動で分ける（正常系）
  test("finish_voice", async () => {
    for (const [action, kind] of [
      ["review", "reviewed"],
      ["insert", "inserted"],
      ["send", "sent"],
    ] as const) {
      // 準備
      installFakeMedia();
      installFakeWakeLock();
      const api = stubVoiceApi();
      await startVoice(D1);
      // 実行
      const result = await finishVoice({ body: "確認: ", start: 4, end: 4, action, mounted: () => true });
      // 検証
      expect(result.kind).toBe(kind);
      expect(api.added).toEqual(action === "review" ? [{ target: "D-1", loc: null, body: "確認: 案 A にする" }] : []);
      expect(api.sent).toEqual(action === "send" ? [{ target: "D-1", loc: null, body: "確認: 案 A にする" }] : []);
      expect(result.body).toBe(action === "insert" ? "確認: 案 A にする" : "");
      if (action === "insert") expect(result.caret).toBe(11);
      expect(readVoiceState().session).toBeNull();
    }
  });

  // 入力欄が画面に無い間に終わったら書きかけへ当て、失敗だけ知らせる（正常系）
  test("finish_voice_when_unmounted", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    stubVoiceApi();
    await startVoice(D1);
    // 実行
    await finishVoice({ body: "確認: ", start: 4, end: 4, action: "review", mounted: () => false });
    // 検証
    expect(readVoiceState().results["D-1#"]?.kind).toBe("reviewed");
    expect(readVoiceState().notice).toBeNull();
    // 準備
    resetVoiceStore();
    const failing = stubVoiceApi({ comments: 500 });
    await startVoice(D1);
    // 実行
    await finishVoice({ body: "確認: ", start: 4, end: 4, action: "review", mounted: () => false });
    // 検証
    expect(failing.drafts).toEqual([{ target: "D-1", loc: null, body: "確認: 案 A にする" }]);
    expect(readVoiceState().notice).toEqual({ kind: "failed", text: VOICE_TEXT.awayReviewFailed("D-1 へのコメント"), key: "D-1#" });
  });

  // 文字起こしと追加・送信の失敗（異常系）
  test("finish_voice_when_failed", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    stubVoiceApi({
      transcribe: () => HttpResponse.json({ type: "about:blank", title: "Service Unavailable", status: 503, detail: "止まっています", reason: "stopped" }, { status: 503 }),
    });
    await startVoice(D1);
    // 実行
    const unavailable = await finishVoice({ body: "確認: ", start: 4, end: 4, action: "review", mounted: () => true });
    // 検証
    expect(unavailable).toMatchObject({ kind: "unavailable", reason: "stopped" });
    // 準備
    stubVoiceApi({ transcribe: () => HttpResponse.json({ type: "about:blank", title: "Bad Gateway", status: 502, detail: "失敗の理由" }, { status: 502 }) });
    await startVoice(D1);
    // 実行
    const failed = await finishVoice({ body: "確認: ", start: 4, end: 4, action: "review", mounted: () => true });
    // 検証
    expect(failed).toMatchObject({ kind: "failed", body: "確認: " });
    // 準備
    stubVoiceApi({ comments: 500 });
    await startVoice(D1);
    // 実行
    const reviewFailed = await finishVoice({ body: "確認: ", start: 4, end: 4, action: "review", mounted: () => true });
    // 検証
    expect(reviewFailed).toMatchObject({ kind: "failed", body: "確認: 案 A にする", detail: VOICE_TEXT.reviewFailed });
  });
});

describe("discardVoice", () => {
  // 行き先が無いときだけ捨てる（正常系）
  test("discard_voice", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    await startVoice(D1);
    // 実行
    discardVoice(() => true);
    const kept = readVoiceState().session?.key;
    discardVoice(() => false);
    // 検証
    expect(kept).toBe("D-1#");
    expect(readVoiceState().session).toBeNull();
    expect(readVoiceState().notice).toEqual({ kind: "discarded", text: VOICE_TEXT.discarded("D-1"), key: null });
  });
});

describe("dismissVoiceNotice", () => {
  // 知らせを消す（正常系）
  test("dismiss_voice_notice", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    await startVoice(D1);
    discardVoice(() => false);
    // 実行
    dismissVoiceNotice();
    // 検証
    expect(readVoiceState().notice).toBeNull();
  });
});

describe("takeVoiceResult", () => {
  // 1 回だけ受け取る（正常系）
  test("take_voice_result", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    stubVoiceApi();
    await startVoice(D1);
    await finishVoice({ body: "確認: ", start: 4, end: 4, action: "review", mounted: () => false });
    // 実行
    const first = takeVoiceResult("D-1#");
    const second = takeVoiceResult("D-1#");
    // 検証
    expect(first?.kind).toBe("reviewed");
    expect(second).toBeNull();
  });
});
