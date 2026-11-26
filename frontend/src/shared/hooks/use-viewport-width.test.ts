import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { useViewportWidth } from "@/shared/hooks/use-viewport-width";

const initialWidth = window.innerWidth;

describe("useViewportWidth", () => {
  afterEach(() => {
    window.innerWidth = initialWidth;
  });

  // 窓の幅が変わると変わった後の幅を返却する（正常系）
  test("use_viewport_width", () => {
    // 準備
    window.innerWidth = 1440;
    const { result } = renderHook(() => useViewportWidth());
    expect(result.current).toBe(1440);
    // 実行
    act(() => {
      window.innerWidth = 1100;
      window.dispatchEvent(new Event("resize"));
    });
    // 検証
    expect(result.current).toBe(1100);
  });
});
