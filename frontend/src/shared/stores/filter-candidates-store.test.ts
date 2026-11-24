import { act } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useFilterCandidatesStore } from "@/shared/stores/filter-candidates-store";

describe("useFilterCandidatesStore", () => {
  // 登録と消去（正常系）
  test("publish", () => {
    // 準備
    const groups = [{ key: "tags", label: "タグ", values: [{ value: "廃止", count: 1 }] }];
    const apply = vi.fn();
    // 実行
    act(() => {
      useFilterCandidatesStore.getState().publish(groups, apply);
    });
    const published = useFilterCandidatesStore.getState();
    act(() => {
      useFilterCandidatesStore.getState().clear();
    });
    // 検証
    expect(published.groups).toEqual(groups);
    expect(published.apply).toBe(apply);
    expect(useFilterCandidatesStore.getState().groups).toEqual([]);
    expect(useFilterCandidatesStore.getState().apply).toBeNull();
  });
});
