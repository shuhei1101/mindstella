import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { FilterChips } from "@/shared/components/filter-chips";

describe("FilterChips", () => {
  // タグの条件の式のチップ（正常系）
  test("filter_chips_when_tag_expr", async () => {
    // 準備
    const onClearTagExpr = vi.fn();
    render(<FilterChips filters={{ status: ["未着手"] }} labels={{ status: "状態", tags: "タグ" }} onFilter={vi.fn()} tagExprText="「画面」を含む かつ 「廃止」を含まない" onClearTagExpr={onClearTagExpr} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "タグ: 「画面」を含む かつ 「廃止」を含まない の条件を解除" }));
    // 検証
    expect(onClearTagExpr).toHaveBeenCalled();
  });
});
