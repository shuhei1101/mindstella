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
    const radios = await screen.findAllByRole("radio", { name: /レビュー中に追加する|入力欄へ挿入する|送信する/ });
    expect(radios.map((radio) => radio.getAttribute("value"))).toEqual(["review", "insert", "send"]);
    expect(screen.getByRole("radio", { name: "レビュー中に追加する" })).toBeChecked();
    await userEvent.click(screen.getByRole("radio", { name: "送信する" }));
    await waitFor(() => expect(posted).toHaveBeenCalledWith({ op: "setting", target: "settings", key: "transcription", value: { action: "send", preset: null } }));
    unmount();
    server.use(http.get("/api/transcription", () => HttpResponse.json({ available: false, reason: "stopped", detail: "x", presets: [], action: "send", preset: null })));
    renderRoute("/spa/?tab=settings");
    const select = await screen.findByRole("combobox", { name: "用語集のプリセット" });
    // 検証
    await waitFor(() => expect(select).toBeDisabled());
    expect(screen.getByText("文字起こしのサービスが起動していないため、候補を取得できません。サービスを起動してから設定の画面を開き直してください。")).toBeInTheDocument();
  });

  // 挙動とプリセットを続けて選ぶ（正常系）
  test("workspace_settings_screen_when_transcription_chosen_in_a_row", async () => {
    // 準備（保存待ちの編集の一覧は空のままにし、記録の値が変わらない間に続けて選ぶ）
    const posted = vi.fn<(body: unknown) => Response>(() => HttpResponse.json({ id: "E-1", target: "settings", count: 1 }, { status: 201 }));
    server.use(
      http.post("/api/edits", async ({ request }) => posted(await request.json())),
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE_TRANSCRIPTION)),
    );
    renderRoute("/spa/?tab=settings");
    const select = await screen.findByRole("combobox", { name: "用語集のプリセット" });
    await waitFor(() => expect(select).toBeEnabled());
    // 実行
    await userEvent.click(screen.getByRole("radio", { name: "送信する" }));
    await userEvent.selectOptions(select, "一般");
    // 検証
    await waitFor(() => expect(posted).toHaveBeenCalledTimes(2));
    expect(posted).toHaveBeenLastCalledWith({ op: "setting", target: "settings", key: "transcription", value: { action: "send", preset: "一般" } });
  });

  // 保存待ちの編集が変わった後の選択（正常系）
  test("workspace_settings_screen_when_transcription_choice_outdated", async () => {
    // 準備（溜めた transcription を保存待ちの編集の一覧に入れ、題名を溜めると取り消した後の空の一覧にする）
    let items: unknown[] = [];
    const posted = vi.fn<(body: unknown) => Response>((body) => {
      const edit = body as { key: string; value: unknown };
      items = edit.key === "transcription" ? [{ id: "E-1", target: "settings", op: "setting", key: "transcription", value: edit.value, before: null, created: "2026-11-12T00:00:00+00:00" }] : [];
      return HttpResponse.json({ id: "E-1", target: "settings", count: items.length }, { status: 201 });
    });
    server.use(
      http.post("/api/edits", async ({ request }) => posted(await request.json())),
      http.get("/api/edits", () => HttpResponse.json({ items, count: items.length })),
      http.get("/api/transcription", () => HttpResponse.json(AVAILABLE_TRANSCRIPTION)),
    );
    renderRoute("/spa/?tab=settings");
    const select = await screen.findByRole("combobox", { name: "用語集のプリセット" });
    await waitFor(() => expect(select).toBeEnabled());
    await userEvent.click(screen.getByRole("radio", { name: "送信する" }));
    // 文字起こし後の挙動の名前の右に保存待ちの印が付くまで待つ
    const actionField = () => document.querySelector('[data-key="transcription"]');
    await waitFor(() => expect(actionField()).toHaveTextContent("保存待ち"));
    const title = screen.getByRole("textbox", { name: "題名" });
    await userEvent.clear(title);
    await userEvent.type(title, "画面の編集");
    await userEvent.tab();
    await waitFor(() => expect(actionField()).not.toHaveTextContent("保存待ち"));
    // 実行
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "用語集のプリセット" }), "一般");
    // 検証
    await waitFor(() => expect(posted).toHaveBeenLastCalledWith({ op: "setting", target: "settings", key: "transcription", value: { action: "review", preset: "一般" } }));
  });
});

/** 文字起こしのサービスが使用でき、用語集のプリセットの候補を持つ『文字起こしの可否』 */
const AVAILABLE_TRANSCRIPTION = { available: true, reason: null, detail: null, presets: ["一般", "開発"], action: "send", preset: null };
