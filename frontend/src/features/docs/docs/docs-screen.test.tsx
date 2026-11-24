import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import { useListOrderStore } from "@/shared/stores/list-order-store";
import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

const DOCS = [
  { id: "A-10", title: "後の資料", status: "完成", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-20T00:00:00+00:00" },
  { id: "A-2", title: "前の資料", status: "下書き", created: "2026-11-02T00:00:00+00:00", updated: "2026-11-05T00:00:00+00:00" },
];

const cardTitles = async (): Promise<(string | null)[]> => (await screen.findAllByRole("heading", { level: 2 })).map((heading) => heading.textContent);

describe("DocsScreen", () => {
  // 既定はカードで、更新日時の新しい順（正常系）
  test("docs_screen", async () => {
    // 準備
    stubRecords({ docs: DOCS });
    // 実行
    renderRoute("/?tab=docs");
    // 検証
    expect(await cardTitles()).toEqual([expect.stringContaining("後の資料"), expect.stringContaining("前の資料")]);
    const sort = screen.getByRole("group", { name: "並べ替え" });
    expect(sort.querySelector("[aria-pressed='true']")).toHaveTextContent("更新日時");
  });

  // 連番を押すと sort=id（正常系）
  test("docs_screen_when_card_sort_id", async () => {
    // 準備
    stubRecords({ docs: DOCS });
    renderRoute("/?tab=docs");
    await cardTitles();
    const before = window.history.length;
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "連番" }));
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("sort")).toBe("id"));
    expect(window.history.length).toBe(before + 1);
    expect(await cardTitles()).toEqual([expect.stringContaining("前の資料"), expect.stringContaining("後の資料")]);
  });

  // カードから開くと一覧の並びを持つ（正常系）
  test("docs_screen_when_open_from_list", async () => {
    // 準備
    stubRecords({ docs: DOCS });
    renderRoute("/?tab=docs");
    await cardTitles();
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "前の資料" }));
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("id")).toBe("A-2"));
    expect(useListOrderStore.getState().orders).toEqual([["A-10", "A-2"]]);
    expect((window.history.state as { fromList?: boolean }).fromList).toBe(true);
  });
});
