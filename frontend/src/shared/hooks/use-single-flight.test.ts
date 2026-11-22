import { act, renderHook } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useSingleFlight } from "@/shared/hooks/use-single-flight";

describe("useSingleFlight", () => {
  // 再描画の前に 2 回呼んでも task は 1 回（正常系）
  test("use_single_flight_when_called_twice_before_render", async () => {
    // 準備
    let resolve: () => void = () => undefined;
    const task = vi.fn(() => new Promise<void>((done) => { resolve = done; }));
    const { result } = renderHook(() => useSingleFlight());
    // 実行（同じ同期の処理の中で 2 回）
    act(() => {
      result.current.run(task);
      result.current.run(task);
    });
    // 検証
    expect(task).toHaveBeenCalledTimes(1);
    expect(result.current.running).toBe(true);
    // 実行（解決した後に再び呼ぶ）
    await act(async () => { resolve(); await Promise.resolve(); });
    act(() => { result.current.run(task); });
    // 検証
    expect(task).toHaveBeenCalledTimes(2);
  });

  // 失敗してもフラグを戻す（異常系）
  test("use_single_flight_when_rejected", async () => {
    // 準備
    const task = vi.fn(() => Promise.reject(new Error("失敗")));
    const { result } = renderHook(() => useSingleFlight());
    // 実行
    await act(async () => { result.current.run(task); await Promise.resolve(); });
    // 検証
    expect(result.current.running).toBe(false);
    act(() => { result.current.run(task); });
    expect(task).toHaveBeenCalledTimes(2);
  });
});
