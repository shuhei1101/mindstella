import { act, waitFor } from "@testing-library/react";
import { useState } from "react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { VOICE_TEXT } from "@/shared/core/voice";
import { useTranscriptionStatus, useVoiceInput } from "@/shared/hooks/use-voice-input";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { RECORDS } from "@/testing/msw/handlers";
import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const AVAILABLE = { available: true, reason: null, detail: null, presets: [], action: "send", preset: null };

afterEach(() => {
  removeFakeMedia();
});

/** D-1 へ向けた音声入力の hook を、中身の書き換えを控えて描く */
const renderVoice = async (body: string, destination: { target: string; loc: null } = { target: "D-1", loc: null }) => {
  const onBodyChange = vi.fn();
  const rendered = await renderPreviewHook("/", () =>
    useVoiceInput({ destination, body, onBodyChange, getSelection: () => ({ start: body.length, end: body.length }) }),
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
    const sent: unknown[] = [];
    server.use(
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE)),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "案 A にする" })),
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
      http.post("/api/transcriptions", () => HttpResponse.json({ detail: "対応していません", reason: "unsupported" }, { status: 503 })),
    );
    const noMicrophone = await renderVoice("");
    // 実行・検証
    expect(noMicrophone.result.current.voice).toBe("disabled");
    expect(noMicrophone.result.current.voiceReason).toBe(VOICE_TEXT.noMicrophone);
    noMicrophone.unmount();
    installFakeMedia();
    const unsupported = await renderVoice("");
    await act(() => unsupported.result.current.onVoiceStart());
    await act(() => unsupported.result.current.onVoiceDone());
    await waitFor(() => expect(unsupported.result.current.voice).toBe("disabled"));
    expect(unsupported.result.current.voiceReason).toBe("対応していません");
  });

  // 向けた先が変わったら録音を捨てる（正常系）
  test("use_voice_input_when_destination_changed", async () => {
    // 準備
    const media = installFakeMedia();
    const sent: unknown[] = [];
    server.use(
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE)),
      http.post("/api/transcriptions", () => HttpResponse.json({ text: "x" })),
      http.post("/api/comments/send-now", async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json({ sent: "t", thread: "TH-1", post: "TH-1-1", entered: true }, { status: 201 });
      }),
    );
    const onBodyChange = vi.fn();
    const control: { setDestination?: (value: { target: string; loc: null }) => void } = {};
    const { result, unmount } = await renderPreviewHook("/", () => {
      const [destination, setDestination] = useState({ target: "D-1", loc: null });
      control.setDestination = setDestination;
      return useVoiceInput({ destination, body: "", onBodyChange, getSelection: () => ({ start: 0, end: 0 }) });
    });
    // 実行
    await act(() => result.current.onVoiceStart());
    act(() => control.setDestination?.({ target: "D-2", loc: null }));
    // 検証
    await waitFor(() => expect(result.current.voice).toBe("idle"));
    expect(media.stoppedTracks()).toBe(1);
    await act(() => result.current.onVoiceStart());
    const done = result.current.onVoiceDone();
    unmount();
    await act(async () => {
      await done;
    });
    expect(sent).toEqual([]);
    expect(onBodyChange).not.toHaveBeenCalled();
  });
});
