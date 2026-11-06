import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { stubEdits } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

describe("TasksScreen", () => {
  // 既定はボード（正常系）
  test("tasks_screen", async () => {
    // 実行
    renderRoute("/spa/?tab=tasks");
    // 検証
    expect(await screen.findByRole("heading", { level: 2, name: /進行中/ })).toBeInTheDocument();
    expect(screen.getByText("T-1の題")).toBeInTheDocument();
  });

  // 足す項目を差し込む（正常系）
  test("tasks_screen_when_edit_added", async () => {
    // 準備
    stubEdits([{ id: "E-1", target: "new-1", op: "item-add", key: "tasks", value: { title: "足すタスク", status: "未着手" }, before: null, created: "2026-11-01T00:00:00+00:00" }]);
    // 実行
    renderRoute("/spa/?tab=tasks");
    // 検証
    expect(await screen.findByText("足すタスク")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "未着手" })).getByText("保存待ち")).toBeInTheDocument();
  });
});
