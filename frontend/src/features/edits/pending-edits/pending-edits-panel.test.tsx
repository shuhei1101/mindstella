import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { stubEdits } from "@/testing/msw/fixtures";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

const EDIT = { id: "E-1", target: "D-1", op: "set", key: "answer", value: "答え", before: null, created: "2026-11-01T00:00:00+00:00" };

describe("PendingEditsPanel", () => {
  // 取り消す（正常系）
  test("pending_edits_panel", async () => {
    // 準備
    stubEdits([EDIT]);
    const removed = vi.fn(() => HttpResponse.json({ removed: ["E-1"], count: 0 }));
    server.use(http.delete("/api/edits/E-1", removed));
    renderRoute("/spa/?tab=decisions&panel=pending");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /取り消す/ }));
    // 検証
    await waitFor(() => expect(removed).toHaveBeenCalled());
  });

  // 書き込めない編集（異常系）
  test("pending_edits_panel_when_blocked", async () => {
    // 準備
    stubEdits([EDIT]);
    server.use(http.post("/api/edits/save", () => HttpResponse.json({ type: "about:blank", title: "Conflict", status: 409, detail: "書き込めません", blocked: [{ id: "E-1", reason: "changed", detail: "溜めた後に書き換わりました", refs: [] }] }, { status: 409, headers: { "Content-Type": "application/problem+json" } })));
    renderRoute("/spa/?tab=decisions&panel=pending");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "まとめて保存する" }));
    // 検証
    expect(await screen.findByText("溜めた後に書き換わりました")).toBeInTheDocument();
  });
});
