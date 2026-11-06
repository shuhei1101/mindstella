import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("DecisionsScreen", () => {
  // 既定はボード（正常系）
  test("decisions_screen", async () => {
    // 実行
    renderRoute("/spa/?tab=decisions");
    // 検証
    expect(await screen.findByRole("heading", { level: 2, name: /未決定/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ボード", pressed: true })).toBeInTheDocument();
  });

  // 表で開く（正常系）
  test("decisions_screen_when_table", async () => {
    // 実行
    renderRoute("/spa/?tab=decisions&view=table");
    // 検証
    expect(await screen.findByRole("cell", { name: "D-1の題" })).toBeInTheDocument();
  });

  // 消した項目の帯（正常系）
  test("decisions_screen_when_diff", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 2, sets: [{ id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 2, added: [], changed: [], removed: [{ id: "D-9", kind: "decision", title: "消した検討事項" }] }], pending: { added: [], changed: [] } } });
    // 実行
    renderRoute("/spa/?tab=decisions&diff=V-2");
    // 検証
    expect(await screen.findByText("消した検討事項")).toBeInTheDocument();
  });
});
