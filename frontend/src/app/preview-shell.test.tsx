import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { resetVoiceStore } from "@/shared/stores/voice-store";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { stubRecords } from "@/testing/msw/fixtures";
import { RECORDS } from "@/testing/msw/handlers";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

afterEach(() => {
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
});

/** 音声入力を使える状態にする */
const enableVoice = (): void => {
  installFakeMedia();
  installFakeWakeLock();
  server.use(http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: [], action: "review", preset: null })));
};

// キャンバスは jsdom で描けないため、ネットワークの描画を差し替える
vi.mock("@/features/graph/graph/components/graph-canvas", () => ({
  GraphCanvas: () => <canvas id="graph-canvas" aria-label="ネットワーク" />,
}));

describe("PreviewShell", () => {
  // tab の画面を描く（正常系）
  test("preview_shell", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks");
    // 検証
    expect(await screen.findByRole("group", { name: "表示形式" })).toBeInTheDocument();
    expect(await screen.findByText("T-1の題")).toBeInTheDocument();
  });

  // id で詳細パネルを重ねる（正常系）
  test("preview_shell_when_item", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks&id=T-1");
    // 検証
    expect(await screen.findByRole("complementary", { name: /詳細/ })).toBeInTheDocument();
  });

  // full で全画面にする（正常系）
  test("preview_shell_when_full", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks&id=T-1&full=1");
    // 検証
    expect(await screen.findByRole("dialog", { name: /T-1の題/ })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /詳細/ })).not.toBeInTheDocument();
  });

  // 設定の画面を開く（正常系）
  test("preview_shell_when_settings", async () => {
    // 実行
    renderRoute("/spa/?tab=settings");
    // 検証
    expect(await screen.findByRole("heading", { name: "設定", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("link", { current: "page" })).not.toBeInTheDocument();
  });

  // 記録に合わない値を外す（正常系）
  test("preview_shell_when_search_mismatched", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks&view=map&id=T-99");
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=tasks"));
  });
  // コメントの一覧を開く（正常系）
  test("preview_shell_when_comments", async () => {
    // 準備
    renderRoute("/spa/?tab=tasks");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /コメント/ }));
    // 検証
    expect(await screen.findByRole("dialog", { name: "コメント" })).toBeInTheDocument();
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("panel")).toBe("comments"));
  });

  // 表示の設定を開く（正常系）
  test("preview_shell_when_display", async () => {
    // 実行
    renderRoute("/spa/?panel=display");
    // 検証
    expect(await screen.findByRole("dialog", { name: "表示の設定" })).toBeInTheDocument();
  });

  // ネットワークの入口で SPA の中のネットワークを開く（正常系）
  test("preview_shell_when_graph", async () => {
    // 準備
    renderRoute("/spa/?tab=decisions&id=D-1");
    // 実行
    await userEvent.click(await screen.findByRole("link", { name: /ネットワーク/ }));
    // 検証
    expect(await screen.findByLabelText("ネットワーク")).toBeInTheDocument();
    await waitFor(() => expect(window.location.search).toBe("?tab=graph&id=D-1"));
    expect(window.location.pathname).toBe("/spa/");
  });

  // 検索の結果から項目を開く（正常系）
  test("preview_shell_when_search", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "", until_seq: 1, added: ["D-1"], changed: [], removed: [] }], pending: { added: [], changed: [] } } });
    renderRoute("/spa/?tab=tasks&search=1&q=D-1%E3%81%AE%E9%A1%8C&diff=V-1");
    const before = window.history.length;
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /D-1の題/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=decisions&id=D-1&diff=V-1"));
    expect(screen.queryByRole("dialog", { name: /検索/ })).not.toBeInTheDocument();
    expect(window.history.length).toBe(before + 1);
  });

  // 同じ画面の項目は履歴に積まずに詳細パネルを開く（正常系）
  test("preview_shell_when_search_same_tab", async () => {
    // 準備
    renderRoute("/spa/?tab=decisions&view=table&search=1&q=D-1%E3%81%AE%E9%A1%8C");
    const before = window.history.length;
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /D-1の題/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=decisions&id=D-1"));
    expect(window.history.length).toBe(before);
  });

  // 表示しない種類の項目は概要で開く（正常系）
  test("preview_shell_when_search_hidden_kind", async () => {
    // 準備
    stubRecords({ settings: { ...RECORDS.settings, display: { visible_kinds: ["decisions", "tasks"] } }, notes: [{ id: "N-1", title: "N-1のメモ" }] });
    renderRoute("/spa/?tab=tasks&search=1&q=N-1%E3%81%AE%E3%83%A1%E3%83%A2");
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /N-1のメモ/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?id=N-1"));
    expect(await screen.findByRole("complementary", { name: /詳細/ })).toBeInTheDocument();
  });

  // 録音中にほかの画面へ移り、トップバーから録音中の入力欄へ戻る（正常系）
  test("preview_shell_when_voice", async () => {
    // 準備
    enableVoice();
    renderRoute("/spa/?tab=tasks&id=T-1");
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /^コメント（/ }));
    expect(await screen.findByRole("dialog", { name: "コメント" })).toBeInTheDocument();
    const voice = screen.getByRole("button", { name: /^音声入力中（T-1 へのコメント）/ });
    await userEvent.click(voice);
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("id")).toBe("T-1"));
    expect(new URLSearchParams(window.location.search).get("panel")).toBeNull();
    await waitFor(() => expect(screen.getByRole("button", { name: "文字起こし" })).toHaveFocus());
  });

  // 録音中に行き先の項目が無くなったら録音を捨てて帯を出す（正常系）
  test("preview_shell_when_voice_target_removed", async () => {
    // 準備
    enableVoice();
    const view = renderRoute("/spa/?tab=tasks&id=T-1");
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    await screen.findByRole("button", { name: /^音声入力中（T-1 へのコメント）/ });
    stubRecords({ tasks: [] });
    // 実行
    await act(() => view.queryClient.invalidateQueries());
    // 検証
    expect(await screen.findByText("T-1 が削除されたため、録音を破棄しました。")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^音声入力中/ })).toBeNull();
  });
});
