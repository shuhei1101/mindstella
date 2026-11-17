import { act } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { useDuplicateIdsStore } from "@/shared/stores/duplicate-ids-store";

afterEach(() => {
  act(() => {
    useDuplicateIdsStore.setState({ ids: [], dismissed: null });
  });
});

describe("setIds", () => {
  // 閉じた集まりと違う ID を受けたら出し直す（正常系）
  test("set_ids", () => {
    // 準備
    const { setIds, dismiss } = useDuplicateIdsStore.getState();
    act(() => {
      setIds(["D-1"]);
      dismiss();
    });
    // 実行
    act(() => {
      setIds(["D-1"]);
    });
    const sameSet = useDuplicateIdsStore.getState();
    act(() => {
      setIds(["D-1", "T-2"]);
    });
    // 検証
    expect(sameSet.dismissed).toEqual(["D-1"]);
    expect(useDuplicateIdsStore.getState().ids).toEqual(["D-1", "T-2"]);
    expect(useDuplicateIdsStore.getState().dismissed).toBeNull();
  });
});
