import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const decision = {
  id: "D-1",
  title: "D-1の題",
  status: "未決定",
  body: "docs/D-1.md",
  options: [{ key: "A", content: "案 A" }],
  history: [{ seq: 2, at: "2026-11-02T00:00:00+00:00", before: {}, body_diff: [{ line: 1, now: ["今の行"], before: ["前の行"] }] }],
};
const changes = { last_seq: 2, sets: [{ id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 2, added: [], changed: ["D-1"] }, { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: [] }], pending: { added: [], changed: [] } };

describe("DetailPanel", () => {
  // 項目を描く（正常系）
  test("detail_panel", async () => {
    // 準備
    stubRecords({ decisions: [decision, { id: "D-2", title: "D-2の題", status: "未決定", depends_on: ["D-1"] }], bodies: { "docs/D-1.md": "本文の文" } });
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1");
    // 検証
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    expect(panel).toHaveTextContent("D-1の題");
    expect(panel).toHaveTextContent("案 A");
    expect(panel).toHaveTextContent("本文の文");
    expect(panel).toHaveTextContent("D-2の題");
  });

  // 本文の差分（正常系）
  test("detail_panel_when_diff", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "今の行\n" }, changes });
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1&diff=V-2");
    // 検証
    expect(await screen.findByText(/前の行/)).toBeInTheDocument();
  });

  // 本文のスクロール位置へ戻す（正常系）
  test("detail_panel_when_body_scroll_saved", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    sessionStorage.setItem("mindmap-body-scroll", '{"D-1":80}');
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    const body = panel.querySelector<HTMLElement>(".panel-body");
    // 検証
    await waitFor(() => expect(body?.scrollTop).toBe(80));
    sessionStorage.clear();
  });

  // 編集の表示（正常系）
  test("detail_panel_when_editing", async () => {
    // 準備
    stubRecords({ decisions: [decision], bodies: { "docs/D-1.md": "本文" } });
    renderRoute("/spa/?tab=decisions&id=D-1");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "編集する" }));
    // 検証
    expect(await screen.findByRole("textbox", { name: "タイトル" })).toHaveValue("D-1の題");
  });

  // 下端にコメント（正常系）
  test("detail_panel_when_comments", async () => {
    // 準備
    stubRecords({ decisions: [decision], changes });
    // 実行
    renderRoute("/spa/?tab=decisions&id=D-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    // 検証
    expect(await within(panel).findByRole("textbox", { name: /D-1 へのコメント/ })).toBeInTheDocument();
    expect(within(panel).queryByRole("link", { name: "今の画面でコメントする" })).not.toBeInTheDocument();
  });
});
