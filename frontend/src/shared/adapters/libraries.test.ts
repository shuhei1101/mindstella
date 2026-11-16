import { afterEach, describe, expect, test, vi } from "vitest";

import {
  loadLibrary,
  mdmarkMapConfig,
  mdmarkUrls,
  resetLibrariesForTest,
  setMdmarkImportForTest,
  setMdmarkSettings,
} from "@/shared/adapters/libraries";

const MDMARK_CDN = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark";

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

describe("setMdmarkSettings", () => {
  // バージョンから URL を決め、無ければ develop（正常系）
  test.each([
    { name: "unset", settings: undefined, ref: "develop", map: undefined },
    { name: "latest", settings: { version: "latest" }, ref: "develop", map: undefined },
    {
      name: "tag",
      settings: { version: "v0.13.0", map: { kinds: { llm: {} } } },
      ref: "v0.13.0",
      map: { kinds: { llm: {} } },
    },
  ])("set_mdmark_settings ($name)", ({ settings, ref, map }) => {
    // 実行
    setMdmarkSettings(settings);
    // 検証
    expect(mdmarkUrls().js).toBe(`${MDMARK_CDN}@${ref}/dist/index.js`);
    expect(mdmarkMapConfig()).toEqual(map);
  });
});

describe("loadLibrary (mdmark)", () => {
  // mdmark は設定のバージョンの URL から integrity なしで読む（正常系）
  test("load_library_when_mdmark", async () => {
    // 準備
    setMdmarkSettings({ version: "v0.13.0" });
    const append = vi.spyOn(document.head, "appendChild").mockImplementation((node) => node);
    const importModule = vi.fn().mockResolvedValue({ version: () => "v0.13.0" });
    setMdmarkImportForTest(importModule);
    // 実行
    await loadLibrary("mdmark");
    // 検証
    expect(importModule).toHaveBeenCalledWith(`${MDMARK_CDN}@v0.13.0/dist/index.js`);
    const link = append.mock.calls[0]?.[0] as HTMLLinkElement;
    expect(link.href).toBe(`${MDMARK_CDN}@v0.13.0/dist/index.css`);
    expect(link.getAttribute("integrity")).toBeNull();
  });
});
