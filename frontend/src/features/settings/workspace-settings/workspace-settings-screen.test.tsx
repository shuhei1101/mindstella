import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

describe("WorkspaceSettingsScreen", () => {
  // 題名を溜める（正常系）
  test("workspace_settings_screen", async () => {
    // 準備
    const posted = vi.fn((_body: unknown) => HttpResponse.json({ id: "E-1", target: "settings", count: 1 }, { status: 201 }));
    server.use(http.post("/api/edits", async ({ request }) => posted(await request.json())));
    renderRoute("/spa/?tab=settings");
    const title = await screen.findByRole("textbox", { name: "題名" });
    // 実行
    await userEvent.clear(title);
    await userEvent.type(title, "画面の編集");
    await userEvent.tab();
    // 検証
    await waitFor(() => expect(posted).toHaveBeenCalledWith({ op: "setting", target: "settings", key: "summary", value: "画面の編集" }));
  });
});
