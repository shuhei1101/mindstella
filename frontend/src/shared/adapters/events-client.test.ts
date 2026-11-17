import { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { checkVoiceDestination, connectEvents } from "@/shared/adapters/events-client";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { useDuplicateIdsStore } from "@/shared/stores/duplicate-ids-store";
import { useRefreshHoldStore } from "@/shared/stores/refresh-hold-store";
import { readVoiceState, resetVoiceStore, startVoice } from "@/shared/stores/voice-store";
import { FakeEventSource } from "@/testing/fake-event-source";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { stubRecords } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { http, HttpResponse } from "msw";

/** T-1 のコメントの入力 */
const T1 = { key: "T-1#", destination: { target: "T-1", loc: null }, view: "panel" as const, label: "T-1 へのコメント", selection: { start: 0, end: 0 } };

/** T-1 へ録音を始める */
const startRecording = async (): Promise<void> => {
  installFakeMedia();
  installFakeWakeLock();
  await startVoice(T1);
};

/** 記録の query の読み直しの回数 */
const recordsInvalidations = (invalidate: { mock: { calls: readonly (readonly unknown[])[] } }): number =>
  invalidate.mock.calls.filter((args) => JSON.stringify((args[0] as { queryKey?: unknown } | undefined)?.queryKey) === JSON.stringify(["/api/records"])).length;

afterEach(() => {
  document.body.replaceChildren();
  useRefreshHoldStore.setState({ focused: false, pending: false, anchor: null });
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
});

describe("connectEvents", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", FakeEventSource);
    useConnectionStore.setState({ connection: "online" });
  });

  // changed で読み直す（正常系）
  test("connect_events_when_changed", () => {
    // 準備
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const close = connectEvents(queryClient);
    // 実行
    FakeEventSource.last?.emit("changed");
    close();
    // 検証
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/api/records"] });
  });

  // 切れたら offline（正常系）
  test("connect_events_when_error", () => {
    // 準備
    const close = connectEvents(new QueryClient());
    // 実行
    FakeEventSource.last?.emit("error");
    const afterError = useConnectionStore.getState().connection;
    FakeEventSource.last?.emit("open");
    close();
    // 検証
    expect(afterError).toBe("offline");
    expect(useConnectionStore.getState().connection).toBe("online");
  });

  // duplicate_ids で重なった ID のストアを書き換える（正常系）
  test("connect_events_when_duplicate_ids", () => {
    // 準備
    const close = connectEvents(new QueryClient());
    // 実行
    FakeEventSource.last?.emit("duplicate_ids", JSON.stringify(["D-1"]));
    close();
    // 検証
    expect(useDuplicateIdsStore.getState().ids).toEqual(["D-1"]);
  });
  // 入力中の changed は保留し、離れたら 1 回だけ読み直す（正常系）
  test("connect_events_when_typing", () => {
    // 準備
    const textarea = document.createElement("textarea");
    const button = document.createElement("button");
    document.body.append(textarea, button);
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const close = connectEvents(queryClient);
    textarea.focus();
    // 実行
    FakeEventSource.last?.emit("changed");
    FakeEventSource.last?.emit("changed");
    const whileTyping = { count: recordsInvalidations(invalidate), pending: useRefreshHoldStore.getState().pending };
    button.focus();
    close();
    // 検証
    expect(whileTyping).toEqual({ count: 0, pending: true });
    expect(recordsInvalidations(invalidate)).toBe(1);
    expect(useRefreshHoldStore.getState().pending).toBe(false);
  });

  // 音声入力中の changed で行き先が無ければ録音を捨てる（正常系）
  test("connect_events_when_voice_target_removed", async () => {
    // 準備
    await startRecording();
    stubRecords({ tasks: [] });
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const close = connectEvents(queryClient);
    // 実行
    FakeEventSource.last?.emit("changed");
    const onChanged = recordsInvalidations(invalidate);
    // 検証
    await vi.waitFor(() => expect(readVoiceState().notice?.kind).toBe("discarded"));
    close();
    expect(onChanged).toBe(0);
    expect(readVoiceState().session).toBeNull();
    expect(recordsInvalidations(invalidate)).toBe(1);
  });
});

describe("checkVoiceDestination", () => {
  // 行き先があれば何もしない（正常系）
  test("check_voice_destination", async () => {
    // 準備
    await startRecording();
    // 実行
    await checkVoiceDestination();
    // 検証
    expect(readVoiceState().session?.key).toBe("T-1#");
    expect(readVoiceState().notice).toBeNull();
  });

  // 読めなければ何もしない（正常系）
  test("check_voice_destination_when_unreadable", async () => {
    // 準備
    await startRecording();
    server.use(http.get("/api/records", () => HttpResponse.json({ type: "about:blank", title: "Error", status: 422, detail: "x" }, { status: 422 })));
    // 実行
    await checkVoiceDestination();
    // 検証
    expect(readVoiceState().session?.key).toBe("T-1#");
    expect(readVoiceState().notice).toBeNull();
  });
});
