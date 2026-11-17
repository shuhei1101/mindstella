import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("HistoryScreen", () => {
  // 時点を選ぶ（正常系）
  test("history_screen", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: ["D-1"], changed: [] }], pending: { added: [], changed: [] } } });
    renderRoute("/spa/?tab=decisions");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "変更履歴" }));
    await userEvent.click(await screen.findByRole("button", { name: /1 回目/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toContain("diff=V-1"));
  });

  // 外部の変更のまとまりを札つきで出す（正常系）
  test("history_screen_when_external_set", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "ほかのセッションの書き込み", until_seq: 1, added: [], changed: ["D-1"], by: "external" }], pending: { added: [], changed: [] } } });
    renderRoute("/spa/?tab=decisions");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "変更履歴" }));
    // 検証
    expect(await screen.findByRole("button", { name: /ほかのセッションの書き込み/ })).toHaveTextContent("外部の変更");
  });
});
