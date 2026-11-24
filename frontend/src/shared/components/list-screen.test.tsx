import { act, screen, waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { useFilterCandidatesStore } from "@/shared/stores/filter-candidates-store";
import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("ListScreen", () => {
  // 絞り込みの値と値を加える処理をストアへ渡す（正常系）
  test("list_screen_when_candidates", async () => {
    // 準備
    stubRecords({ tasks: [{ id: "T-1", title: "作業 1", status: "保留", kind: "作業" }] });
    const { unmount } = renderRoute("/?tab=tasks");
    await screen.findByText("作業 1");
    await waitFor(() => expect(useFilterCandidatesStore.getState().apply).not.toBeNull());
    const before = window.history.length;
    // 実行
    act(() => {
      useFilterCandidatesStore.getState().apply?.("status", "保留");
    });
    // 検証
    const status = useFilterCandidatesStore.getState().groups.find(({ key }) => key === "status");
    expect(status?.values.map(({ value }) => value)).toContain("保留");
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("f.status")).toBe("保留"));
    expect(window.history.length).toBe(before + 1);
    // 実行
    unmount();
    // 検証
    expect(useFilterCandidatesStore.getState().groups).toEqual([]);
  });
});
