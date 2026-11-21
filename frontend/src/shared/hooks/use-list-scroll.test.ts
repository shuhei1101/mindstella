import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { useListScroll } from "@/shared/hooks/use-list-scroll";

beforeEach(() => {
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    callback(0);
    return 0;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

/** スクロールできる要素を作り、ref に渡す */
const attach = (ref: (element: HTMLElement | null) => void): HTMLElement => {
  const element = document.createElement("div");
  Object.defineProperty(element, "scrollHeight", { value: 2000 });
  Object.defineProperty(element, "clientHeight", { value: 300 });
  ref(element);
  return element;
};

describe("useListScroll", () => {
  // 離れる前の位置へ戻す（正常系）
  test("use_list_scroll", () => {
    // 準備
    const first = renderHook(() => useListScroll("tasks:board", true));
    const before = attach(first.result.current);
    before.scrollTop = 400;
    before.dispatchEvent(new Event("scroll"));
    first.unmount();
    // 実行
    const second = renderHook(({ ready }) => useListScroll("tasks:board", ready), { initialProps: { ready: false } });
    const after = attach(second.result.current);
    second.rerender({ ready: true });
    // 検証
    expect(after.scrollTop).toBe(400);
  });

  // 再描画では位置を変えない（正常系）
  test("use_list_scroll_when_rerendered", () => {
    // 準備
    sessionStorage.setItem("mindmap-list-scroll", JSON.stringify({ "tasks:board": { top: 400, left: 0 } }));
    const view = renderHook(() => useListScroll("tasks:board", true));
    const element = attach(view.result.current);
    element.scrollTop = 120;
    element.dispatchEvent(new Event("scroll"));
    // 実行
    view.rerender();
    // 検証
    expect(element.scrollTop).toBe(120);
  });
});
