import { act, render } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { useGraphLock } from "@/features/graph/graph/store";

describe("useGraphLock", () => {
  // 画面を外しても残る（正常系）
  test("use_graph_lock", () => {
    // 準備
    const seen: (string | null)[] = [];
    let set: ((id: string | null) => void) | null = null;
    const Probe = () => {
      const [locked, setLocked] = useGraphLock();
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
});
