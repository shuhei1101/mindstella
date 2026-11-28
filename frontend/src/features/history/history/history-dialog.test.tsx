import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test } from "vitest";

import { markRead, prune } from "@/shared/stores/read-changes-store";
import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

// まとまり V-1・V-2 を持つ変更履歴
const TWO_SETS = {
  last_seq: 2,
  sets: [
    { id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 2, added: [], changed: ["D-1"] },
    { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: ["D-1"], changed: [] },
  ],
  pending: { added: [], changed: [] },
};

beforeEach(() => {
  // 前のテストの既読を持ち越さない
  prune("", []);
});

describe("HistoryScreen", () => {
  // 時点を選ぶ（正常系）
  test("history_screen", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: ["D-1"], changed: [] }], pending: { added: [], changed: [] } } });
    renderRoute("/?tab=decisions");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /^変更履歴/ }));
    await userEvent.click(await screen.findByRole("button", { name: /1 回目/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toContain("diff=V-1"));
  });

  // 外部の変更のまとまりを札つきで出す（正常系）
  test("history_screen_when_external_set", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "ほかのセッションの書き込み", until_seq: 1, added: [], changed: ["D-1"], by: "external" }], pending: { added: [], changed: [] } } });
    renderRoute("/?tab=decisions");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "変更履歴（過去の差分を表示中）" }));
    // 検証
    expect(await screen.findByRole("button", { name: /ほかのセッションの書き込み/ })).toHaveTextContent("外部の変更");
  });

  // 先頭を最新にし、既読でないまとまりに未読のマーカーを付ける（正常系）
  test("history_screen_when_unread", async () => {
    // 準備
    stubRecords({ changes: TWO_SETS });
    markRead("", ["V-1"]);
    renderRoute("/?tab=decisions");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /^変更履歴/ }));
    // 検証
    const latest = await screen.findByRole("button", { name: /最新/ });
    const second = screen.getByRole("button", { name: /2 回目/ });
    const first = screen.getByRole("button", { name: /1 回目/ });
    expect(latest.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(second.compareDocumentPosition(first) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByRole("button", { name: /前回開いてから/ })).toBeNull();
    expect(second).toHaveTextContent("未読");
    expect(first).not.toHaveTextContent("未読");
    expect(screen.getByText("未読 1 件")).toBeInTheDocument();
  });

  // すべて既読にするで全てのまとまりを既読にする（正常系）
  test("history_screen_when_mark_all_read", async () => {
    // 準備
    stubRecords({ changes: TWO_SETS });
    renderRoute("/?tab=decisions");
    await userEvent.click(await screen.findByRole("button", { name: /^変更履歴/ }));
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "すべて既読にする" }));
    // 検証
    expect(await screen.findByText("未読はありません")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2 回目/ })).not.toHaveTextContent("未読");
    expect(screen.getByRole("button", { name: /1 回目/ })).not.toHaveTextContent("未読");
  });
  // 最新の次に今回の差分を並べ、選ぶと diff が turn になる（正常系）
  test("history_screen_when_turn", async () => {
    // 準備
    stubRecords({ changes: { ...TWO_SETS, turn_seq: 1, turn_at: "2026-10-04T05:50:00+00:00" } });
    renderRoute("/?tab=decisions");
    await userEvent.click(await screen.findByRole("button", { name: /^変更履歴/ }));
    const latest = await screen.findByRole("button", { name: /最新/ });
    const turn = screen.getByRole("button", { name: /今回の差分/ });
    const second = screen.getByRole("button", { name: /2 回目/ });
    // 実行
    await userEvent.click(turn);
    // 検証
    expect(latest.compareDocumentPosition(turn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(turn.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(turn).toHaveTextContent("10/04 14:50 の送信より後の書き換え");
    expect(turn).toHaveTextContent("1");
    await waitFor(() => expect(window.location.search).toContain("diff=turn"));
  });
});
