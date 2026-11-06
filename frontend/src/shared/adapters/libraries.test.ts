import { afterEach, describe, expect, test, vi } from "vitest";

import { loadLibrary, resetLibrariesForTest } from "@/shared/adapters/libraries";

const fireOn = (succeed: boolean) =>
  vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
    const element = node as HTMLScriptElement;
    queueMicrotask(() => element.dispatchEvent(new Event(succeed ? "load" : "error")));
    return node;
  });

afterEach(() => {
  vi.restoreAllMocks();
  resetLibrariesForTest();
  vi.unstubAllGlobals();
});

describe("loadLibrary", () => {
  // 1 度だけ読む（正常系）
  test("load_library", async () => {
    // 準備
    vi.stubGlobal("ELK", class {});
    const append = fireOn(true);
    // 実行
    await loadLibrary("elkjs");
    await loadLibrary("elkjs");
    // 検証
    expect(append).toHaveBeenCalledTimes(1);
  });

  // 読めない（異常系）
  test("load_library_when_failed", async () => {
    // 準備
    fireOn(false);
    // 実行・検証
    await expect(loadLibrary("elkjs")).resolves.toBeNull();
  });
});
