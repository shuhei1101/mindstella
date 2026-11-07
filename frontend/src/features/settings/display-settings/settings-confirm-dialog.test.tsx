import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test } from "vitest";

import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

afterEach(() => {
  localStorage.clear();
});

const openConfirm = async () => {
  localStorage.setItem("mindmap-preview", JSON.stringify({ kinds: ["decisions", "tasks"] }));
  renderRoute("/spa/?panel=display");
  await userEvent.click(await screen.findByRole("button", { name: "ワークスペースの既定にする" }));
  return screen.findByRole("dialog", { name: /既定/ });
};

describe("SettingsConfirmDialog", () => {
  // 保存する（正常系）
  test("settings_confirm_dialog", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.put("/api/config/display", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ display: { network_look: "deep", visible_kinds: ["decisions", "tasks"] } });
      }),
    );
    const dialog = await openConfirm();
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "保存する" }));
    // 検証
    await waitFor(() => expect(bodies).toEqual([{ network_look: "deep", visible_kinds: ["decisions", "tasks"] }]));
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
  });

  // 書けない（異常系）
  test("settings_confirm_dialog_when_error", async () => {
    // 準備
    server.use(
      http.put("/api/config/display", () =>
        HttpResponse.json({ type: "about:blank", title: "Forbidden", status: 403, detail: "config.yaml に書けません" }, { status: 403, headers: { "Content-Type": "application/problem+json" } }),
      ),
    );
    const dialog = await openConfirm();
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "保存する" }));
    // 検証
    expect(await screen.findByText(/config.yaml に書けません/)).toBeInTheDocument();
    expect(dialog).toBeInTheDocument();
  });
});
