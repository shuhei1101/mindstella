import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

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

describe("ListScreen favorites", () => {
  afterEach(() => {
    localStorage.clear();
  });

  // カードでお気に入りが先頭、お気に入りだけでチップが出る（正常系）
  test.each([
    { stored: { favorites: ["A-3"] }, expected: ["A-3", "A-2", "A-1"], chip: false },
    { stored: { favorites: ["A-3"], favoritesOnly: true }, expected: ["A-3"], chip: true },
  ])("list_screen_when_favorites $stored", async ({ stored, expected, chip }) => {
    // 準備
    localStorage.setItem("mindmap-preview", JSON.stringify(stored));
    stubRecords({
      docs: [
        { id: "A-1", title: "資料 1", status: "下書き", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-01T00:00:00+00:00" },
        { id: "A-2", title: "資料 2", status: "下書き", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-03T00:00:00+00:00" },
        { id: "A-3", title: "資料 3", status: "下書き", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-02T00:00:00+00:00" },
      ],
    });
    // 実行
    const { container } = renderRoute("/?tab=docs");
    await screen.findByText("資料 3");
    // 検証
    await waitFor(() => expect([...container.querySelectorAll<HTMLElement>("[data-card]")].map((card) => card.dataset["card"])).toEqual(expected));
    expect(screen.queryByRole("button", { name: "お気に入りのみ の条件を解除" }) !== null).toBe(chip);
  });
});
