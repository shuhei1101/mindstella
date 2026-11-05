import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { ItemAddPanel } from "@/features/detail/detail-panel/components/item-add-panel";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";
import { server } from "@/testing/msw/server";

const open = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ItemAddPanel kind="tasks" target={null} index={buildIndex(RECORDS as unknown as MindmapData)} edits={[]} />
    </QueryClientProvider>,
  );

describe("ItemAddPanel", () => {
  // タイトルを離れたときに溜める（正常系）
  test("item_add_panel", async () => {
    // 準備
    const posted = vi.fn<(body: unknown) => Response>(() => HttpResponse.json({ id: "E-1", target: "new-1", count: 1 }, { status: 201 }));
    server.use(http.post("/api/edits", async ({ request }) => posted(await request.json())));
    open();
    const title = screen.getByRole("textbox", { name: "タイトル" });
    // 実行
    await userEvent.type(title, "足す");
    await userEvent.tab();
    // 検証
    await waitFor(() => { expect(posted).toHaveBeenCalledWith({ op: "item-add", key: "tasks", value: { status: "未着手", kind: "作業", title: "足す" } }); });
  });

  // 空のタイトル（異常系）
  test("item_add_panel_when_title_empty", async () => {
    // 準備
    const posted = vi.fn(() => HttpResponse.json({}, { status: 201 }));
    server.use(http.post("/api/edits", posted));
    open();
    // 実行
    await userEvent.type(screen.getByRole("textbox", { name: "タイトル" }), "  ");
    await userEvent.tab();
    // 検証
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(posted).not.toHaveBeenCalled();
  });
});
