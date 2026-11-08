import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { cancelDisplaySave, clearDisplayNotice, displayChanged, expectDisplaySave, markDisplaySaved, useDisplayMessage, useDisplayNoticeAt } from "@/shared/stores/display-notice-store";

const AT = "2026-11-08T01:00:00+00:00";

const render = () => renderHook(() => ({ message: useDisplayMessage(), noticeAt: useDisplayNoticeAt() }));

afterEach(() => {
  act(() => {
    cancelDisplaySave();
    clearDisplayNotice();
  });
});

describe("displayChanged", () => {
  // 他の人が既定を変えた（正常系）
  test("display_changed", () => {
    // 準備
    const { result } = render();
    // 実行
    act(() => {
      displayChanged({ next: { network_look: "dust", visible_kinds: ["decisions"] }, at: AT });
    });
    // 検証
    expect(result.current.noticeAt).toBe(AT);
    expect(result.current.message?.kind).toBe("info");
    expect(result.current.message?.text).toMatch(/^ワークスペースの既定が変わりました（.+）。$/);
  });

  // 自分が既定にした値が届いた（正常系）
  test("display_changed_when_own_save", () => {
    // 準備
    const { result } = render();
    act(() => {
      expectDisplaySave({ network_look: "deep", visible_kinds: ["tasks"] });
      markDisplaySaved(AT);
    });
    // 実行
    act(() => {
      displayChanged({ next: { network_look: "deep", visible_kinds: ["tasks"] }, at: AT });
    });
    // 検証
    expect(result.current.noticeAt).toBeNull();
    expect(result.current.message?.text).toMatch(/^ワークスペースの既定にしました（.+）。$/);
  });
});
