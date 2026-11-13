import { act, render, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { useDecisionMapLock } from "@/features/decisions/decisions/store";
import { useGraphLock } from "@/features/graph/graph/store";

describe("useDecisionMapLock", () => {
  // 画面を外しても残る（正常系）
  test("use_decision_map_lock", () => {
    // 準備
    const seen: (string | null)[] = [];
    let set: ((id: string | null) => void) | null = null;
    const Probe = () => {
      const [locked, setLocked] = useDecisionMapLock();
      seen.push(locked);
      set = setLocked;
      return null;
    };
    const first = render(<Probe />);
    act(() => {
      set?.("D-1");
    });
    first.unmount();
    // 実行
    render(<Probe />);
    // 検証
    expect(seen.at(-1)).toBe("D-1");
  });

  // ネットワークのロックと別に持つ（正常系）
  test("use_decision_map_lock_apart_from_graph", () => {
    // 準備
    const map = renderHook(() => useDecisionMapLock());
    act(() => {
      map.result.current[1]("D-1");
    });
    // 実行
    const graph = renderHook(() => useGraphLock());
    // 検証
    expect(graph.result.current[0]).toBeNull();
  });
});
