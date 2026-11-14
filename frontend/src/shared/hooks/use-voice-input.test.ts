import { act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { VOICE_TEXT, WAVE_SAMPLE_MS } from "@/shared/core/voice";
import { useTranscriptionStatus, useVoiceInput } from "@/shared/hooks/use-voice-input";
import { finishVoice, resetVoiceStore, startVoice } from "@/shared/stores/voice-store";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { RECORDS } from "@/testing/msw/handlers";
import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const AVAILABLE = { available: true, reason: null, detail: null, presets: [], action: "send", preset: null };

afterEach(() => {
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
  vi.useRealTimers();
});

/** D-1 のコメントの入力の音声入力の hook を、中身の書き換えを控えて描く */
const renderVoice = async (body: string, key = "D-1#") => {
  const onBodyChange = vi.fn();
  const rendered = await renderPreviewHook("/", () =>
    useVoiceInput({
      key,
      destination: { target: "D-1", loc: null },
      view: "panel",
      label: "D-1 へのコメント",
      body,
      onBodyChange,
      getSelection: () => ({ start: body.length, end: body.length }),
    }),
  );
  return { ...rendered, onBodyChange };
};

describe("useTranscriptionStatus", () => {
  // 可否を読む（正常系）
  test("use_transcription_status", async () => {
    // 準備
    server.use(http.get("/api/transcription", () => HttpResponse.json({ ...AVAILABLE, available: false, reason: "stopped", detail: "x" })));
    // 実行
    const { result } = await renderPreviewHook("/", useTranscriptionStatus);
    // 検証
    await waitFor(() => expect(result.current.data?.reason).toBe("stopped"));
  });
});

describe("useVoiceInput", () => {
  // 録音して挙動で分ける（正常系）
  test("use_voice_input", async () => {
    // 準備
    installFakeMedia();
    installFakeWakeLock();
    const sent: unknown[] = [];
    const added: unknown[] = [];
    server.use(
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE)),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "案 A にする" })),
      http.post("/api/comments", async ({ request }) => {
        added.push(await request.json());
        return HttpResponse.json({ id: "C-1", created: "2026-11-14T00:00:00+00:00", count: 1 }, { status: 201 });
      }),
      http.post("/api/comments/send-now", async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json({ sent: "t", thread: "TH-1", post: "TH-1-1", entered: true }, { status: 201 });
      }),
    );
    stubRecords({ settings: { ...RECORDS.settings, transcription: { action: "insert" } } });
    const inserting = await renderVoice("確認: ");
    // 実行
    await act(() => inserting.result.current.onVoiceStart());
    await act(() => inserting.result.current.onVoiceDone());
    // 検証
    await waitFor(() => expect(inserting.onBodyChange).toHaveBeenCalledWith("確認: 案 A にする"));
    expect(inserting.result.current.status).toBe("inserted");
    expect(sent).toEqual([]);
    inserting.unmount();
    stubRecords({});
    const defaulted = await renderVoice("確認: ");
    await act(() => defaulted.result.current.onVoiceStart());
    await act(() => defaulted.result.current.onVoiceDone());
    await waitFor(() => expect(added).toEqual([{ target: "D-1", loc: null, body: "確認: 案 A にする" }]));
    expect(defaulted.onBodyChange).toHaveBeenLastCalledWith("");
    expect(defaulted.result.current.status).toBe("reviewed");
    expect(sent).toEqual([]);
    defaulted.unmount();
    stubRecords({ settings: { ...RECORDS.settings, transcription: { action: "send" } } });
    const sending = await renderVoice("確認: ");
    await act(() => sending.result.current.onVoiceStart());
    await act(() => sending.result.current.onVoiceDone());
    await waitFor(() => expect(sent).toEqual([{ target: "D-1", loc: null, body: "確認: 案 A にする" }]));
    expect(sending.onBodyChange).toHaveBeenLastCalledWith("");
    expect(sending.result.current.status).toBe("sent");
  });

  // 押せない理由と 503（異常系）
  test("use_voice_input_when_unavailable", async () => {
    // 準備
    server.use(
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE)),
      http.post("/api/transcriptions", () => HttpResponse.json({ type: "about:blank", title: "Service Unavailable", status: 503, detail: "対応していません", reason: "unsupported" }, { status: 503 })),
    );
    const noMicrophone = await renderVoice("");
    // 実行・検証
    expect(noMicrophone.result.current.voice).toBe("disabled");
    expect(noMicrophone.result.current.voiceReason).toBe(VOICE_TEXT.noMicrophone);
    noMicrophone.unmount();
    installFakeMedia();
    installFakeWakeLock();
    const unsupported = await renderVoice("");
    await act(() => unsupported.result.current.onVoiceStart());
    await act(() => unsupported.result.current.onVoiceDone());
    await waitFor(() => expect(unsupported.result.current.voice).toBe("disabled"));
    expect(unsupported.result.current.voiceReason).toBe("対応していません");
  });

  // 録音中の音量を levels に持ち、終えたら空にする（正常系）
  test("use_voice_input_levels", async () => {
    // 準備
    vi.useFakeTimers({ shouldAdvanceTime: true });
    installFakeMedia(undefined, [160, 224]);
    installFakeWakeLock();
    server.use(http.get("/api/transcription", () => HttpResponse.json(AVAILABLE)));
    const { result } = await renderVoice("");
    // 実行
    await act(() => result.current.onVoiceStart());
    act(() => {
      vi.advanceTimersByTime(WAVE_SAMPLE_MS * 2);
    });
    const recorded = result.current.levels;
    act(() => result.current.onVoiceCancel());
    // 検証
    expect(recorded).toEqual([0.25, 0.75]);
    expect(result.current.levels).toEqual([]);
  });

  // 部品が外れても録音を続け、付き直したら結果を受け取る（正常系）
  test("use_voice_input_when_unmounted", async () => {
    // 準備
    const media = installFakeMedia();
    installFakeWakeLock();
    server.use(
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE)),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "x" })),
      http.post("/api/comments", () => HttpResponse.json({ id: "C-1", created: "2026-11-14T00:00:00+00:00", count: 1 }, { status: 201 })),
      http.put("/api/drafts", () => HttpResponse.json({ ok: true })),
    );
    const first = await renderVoice("");
    await act(() => first.result.current.onVoiceStart());
    // 実行
    first.unmount();
    const stoppedWhileAway = media.stoppedTracks();
    await act(async () => {
      await finishVoice({ body: "", start: 0, end: 0, action: "review", mounted: () => false });
    });
    const again = await renderVoice("");
    // 検証
    expect(stoppedWhileAway).toBe(0);
    await waitFor(() => expect(again.result.current.status).toBe("reviewed"));
    again.unmount();
    await startVoice({ key: "D-2#", destination: { target: "D-2", loc: null }, view: "panel", label: "D-2 へのコメント", selection: { start: 0, end: 0 } });
    const other = await renderVoice("");
    expect(other.result.current.voice).toBe("disabled");
    expect(other.result.current.voiceReason).toBe(VOICE_TEXT.busy);
  });
});
