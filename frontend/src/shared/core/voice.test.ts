import { afterEach, describe, expect, test, vi } from "vitest";

import {
  acquireWakeLock,
  formatElapsed,
  insertAtCursor,
  micSupported,
  pushLevel,
  startRecording,
  WAVE_LEVELS_MAX,
  WAVE_SAMPLE_MS,
} from "@/shared/core/voice";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";

afterEach(() => {
  removeFakeMedia();
  removeFakeWakeLock();
  vi.useRealTimers();
});

describe("micSupported", () => {
  // 両方があるときだけ真（正常系）
  test("mic_supported", () => {
    // 準備
    installFakeMedia();
    // 実行
    const supported = micSupported();
    removeFakeMedia();
    const unsupported = micSupported();
    // 検証
    expect([supported, unsupported]).toEqual([true, false]);
  });
});

describe("startRecording", () => {
  // 止めると音声を返し、トラックを止める（正常系）
  test("start_recording", async () => {
    // 準備
    const media = installFakeMedia();
    // 実行
    const recording = await startRecording(() => {});
    const blob = await recording.stop();
    // 検証
    expect(blob.type).toBe("audio/webm;codecs=opus");
    expect(media.stoppedTracks()).toBe(1);
  });

  // 許可の拒否とそれ以外（異常系）
  test("start_recording_when_rejected", async () => {
    // 準備
    installFakeMedia("NotAllowedError");
    const denied = startRecording(() => {});
    // 実行・検証
    await expect(denied).rejects.toMatchObject({ name: "RecordingError", reason: "denied" });
    installFakeMedia("NotFoundError");
    await expect(startRecording(() => {})).rejects.toMatchObject({ name: "RecordingError", reason: "no-microphone" });
  });
});

describe("startRecording の音量", () => {
  // 間隔ごとに音量を知らせ、止めたら知らせない（正常系）
  test("start_recording_levels", async () => {
    // 準備
    vi.useFakeTimers();
    const media = installFakeMedia(undefined, [192]);
    const levels: number[] = [];
    // 実行
    const recording = await startRecording((level) => levels.push(level));
    vi.advanceTimersByTime(WAVE_SAMPLE_MS * 2);
    await recording.stop();
    vi.advanceTimersByTime(WAVE_SAMPLE_MS);
    // 検証
    expect(levels).toEqual([0.5, 0.5]);
    expect(media.closedContexts()).toBe(1);
  });
});

describe("pushLevel", () => {
  // 末尾に足し、上限を超えた古いものを捨てる（正常系）
  test("push_level", () => {
    // 準備
    const full = Array.from({ length: WAVE_LEVELS_MAX }, (_, index) => index / 1000);
    const original = [0.1, 0.2];
    // 実行
    const pushedFull = pushLevel(full, 0.3);
    // 検証
    expect(pushLevel([], 0.5)).toEqual([0.5]);
    expect(pushLevel(original, 1.4)).toEqual([0.1, 0.2, 1]);
    expect(original).toEqual([0.1, 0.2]);
    expect(pushedFull).toHaveLength(WAVE_LEVELS_MAX);
    expect([pushedFull[0], pushedFull.at(-1)]).toEqual([0.001, 0.3]);
    expect(full).toHaveLength(WAVE_LEVELS_MAX);
  });
});

describe("insertAtCursor", () => {
  // カーソルの位置と選んだ範囲（正常系）
  test("insert_at_cursor", () => {
    // 実行・検証
    expect(insertAtCursor("確認: ", 4, 4, "案 A")).toEqual({ value: "確認: 案 A", caret: 7 });
    expect(insertAtCursor("abc", 1, 2, "x")).toEqual({ value: "axc", caret: 2 });
    expect(insertAtCursor("ab", 9, 9, "x")).toEqual({ value: "abx", caret: 3 });
  });
});

describe("formatElapsed", () => {
  // 分と秒（正常系）
  test("format_elapsed", () => {
    // 実行・検証
    expect(formatElapsed(0)).toBe("0:00");
    expect(formatElapsed(72)).toBe("1:12");
  });
});

describe("acquireWakeLock", () => {
  // 求めて解く（正常系）
  test("acquire_wake_lock", async () => {
    // 準備
    const wakeLock = installFakeWakeLock();
    // 実行
    const release = await acquireWakeLock();
    release();
    release();
    await Promise.resolve();
    // 検証
    expect(wakeLock.requested()).toEqual(["screen"]);
    expect(wakeLock.released()).toBe(1);
  });

  // 持たない・断られたときは何もしない（異常系）
  test("acquire_wake_lock_when_unavailable", async () => {
    for (const mode of ["missing", "denied"] as const) {
      // 準備
      const wakeLock = installFakeWakeLock(mode);
      // 実行
      const release = await acquireWakeLock();
      // 検証
      expect(() => release()).not.toThrow();
      expect(wakeLock.released()).toBe(0);
    }
  });
});
