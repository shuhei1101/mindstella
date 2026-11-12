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
    const posted = vi.fn<(body: unknown) => Response>(() => HttpResponse.json({ id: "E-1", target: "settings", count: 1 }, { status: 201 }));
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

  // 音声入力のまとまり（正常系）
  test("workspace_settings_screen_when_transcription", async () => {
    // 準備
    const posted = vi.fn<(body: unknown) => Response>(() => HttpResponse.json({ id: "E-1", target: "settings", count: 1 }, { status: 201 }));
    server.use(
      http.post("/api/edits", async ({ request }) => posted(await request.json())),
      http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: ["一般", "開発"], action: "send", preset: null })),
    );
    const { unmount } = renderRoute("/spa/?tab=settings");
    // 実行
    await userEvent.click(await screen.findByRole("radio", { name: "送信する" }));
    await waitFor(() => expect(posted).toHaveBeenCalledWith({ op: "setting", target: "settings", key: "transcription", value: { action: "send", preset: null } }));
    unmount();
    server.use(http.get("/api/transcription", () => HttpResponse.json({ available: false, reason: "stopped", detail: "x", presets: [], action: "send", preset: null })));
    renderRoute("/spa/?tab=settings");
    const select = await screen.findByRole("combobox", { name: "用語集のプリセット" });
    // 検証
    await waitFor(() => expect(select).toBeDisabled());
    expect(screen.getByText("文字起こしのサービスが起動していないため、候補を取得できません。サービスを起動してから設定の画面を開き直してください。")).toBeInTheDocument();
  });
});
