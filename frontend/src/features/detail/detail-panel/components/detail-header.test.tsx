import { screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

describe("DetailHeader", () => {
  // 見出しがあるときだけ目次のボタンを描く（正常系）
  test.each([
    { body: "# 目的\n\n本文\n\n## 保存先", expected: true },
    { body: "見出しの無い本文", expected: false },
  ])("detail_header_when_toc", async ({ body, expected }) => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "目次の資料の題", status: "確認中", body: "docs/A-1.md" }], bodies: { "docs/A-1.md": body } });
    // 実行
    renderRoute("/?tab=docs&id=A-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    await within(panel).findAllByText("目次の資料の題");
    // 検証
    const button = within(panel).queryByRole("button", { name: "本文の目次" });
    if (expected) expect(button).toBeInTheDocument();
    else expect(button).toBeNull();
  });
});
