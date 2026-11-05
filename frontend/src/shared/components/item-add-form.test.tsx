import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { ItemAddForm } from "@/shared/components/item-add-form";
import { server } from "@/testing/msw/server";

const wrap = (node: ReactNode) => render(<QueryClientProvider client={createQueryClient()}>{node}</QueryClientProvider>);

describe("ItemAddForm", () => {
  // 足す項目を溜める（正常系）
  test("item_add_form", async () => {
    // 準備
    const posted = vi.fn((_body: unknown) => HttpResponse.json({ id: "E-1", target: "new-1", count: 1 }, { status: 201 }));
    server.use(http.post("/api/edits", async ({ request }) => posted(await request.json())));
    wrap(<ItemAddForm kind="tasks" onClose={vi.fn()} />);
    // 実行
    await userEvent.type(screen.getByRole("textbox", { name: "タイトル" }), "足す");
    await userEvent.click(screen.getByRole("button", { name: "追加" }));
    // 検証
    await waitFor(() => expect(posted).toHaveBeenCalledWith({ op: "item-add", key: "tasks", value: { title: "足す" } }));
  });

  // 空のタイトル（異常系）
  test("item_add_form_when_title_empty", async () => {
    // 準備
    const posted = vi.fn(() => HttpResponse.json({}, { status: 201 }));
    server.use(http.post("/api/edits", posted));
    wrap(<ItemAddForm kind="tasks" onClose={vi.fn()} />);
    // 実行
    await userEvent.type(screen.getByRole("textbox", { name: "タイトル" }), "  ");
    await userEvent.click(screen.getByRole("button", { name: "追加" }));
    // 検証
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(posted).not.toHaveBeenCalled();
  });
});
