import { afterEach, describe, expect, test } from "vitest";

import { formatElapsed, insertAtCursor, micSupported, startRecording } from "@/shared/core/voice";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";

afterEach(() => {
  removeFakeMedia();
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
    const recording = await startRecording();
    const blob = await recording.stop();
    // 検証
    expect(blob.type).toBe("audio/webm;codecs=opus");
    expect(media.stoppedTracks()).toBe(1);
  });

  // 許可の拒否とそれ以外（異常系）
  test("start_recording_when_rejected", async () => {
    // 準備
    installFakeMedia("NotAllowedError");
    const denied = startRecording();
    // 実行・検証
    await expect(denied).rejects.toBe("denied");
    installFakeMedia("NotFoundError");
    await expect(startRecording()).rejects.toBe("no-microphone");
  });
});

describe("insertAtCursor", () => {
  // カーソルの位置と選んだ範囲（正常系）
  test("insert_at_cursor", () => {
    // 実行・検証
    expect(insertAtCursor("確認: ", 4, 4, "案 A")).toEqual({ value: "確認: 案 A", caret: 6 });
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
