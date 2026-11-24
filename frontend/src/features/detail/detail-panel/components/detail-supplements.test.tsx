import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { DetailSupplements } from "@/features/detail/detail-panel/components/detail-supplements";

describe("DetailSupplements", () => {
  // タブを押して切り替える（正常系）
  test("detail_supplements", async () => {
    // 準備
    const onTabChange = vi.fn();
    render(<DetailSupplements tab="main" onTabChange={onTabChange} main={<p>本文の中身</p>} supplements={<p>関連の中身</p>} comments={<p>コメントの中身</p>} />);
    // 実行
    await userEvent.click(screen.getByRole("tab", { name: "関連" }));
    // 検証
    expect(screen.getByRole("tab", { name: "本文" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("本文の中身");
    expect(onTabChange).toHaveBeenCalledWith("related");
  });

  // 矢印で隣のタブへ移る（正常系）
  test("detail_supplements_when_arrow", async () => {
    // 準備
    const onTabChange = vi.fn();
    render(<DetailSupplements tab="main" onTabChange={onTabChange} main={<p>本文の中身</p>} supplements={<p>関連の中身</p>} comments={<p>コメントの中身</p>} />);
    screen.getByRole("tab", { name: "本文" }).focus();
    // 実行
    await userEvent.keyboard("{ArrowRight}");
    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");
    await userEvent.keyboard("{End}");
    // 検証
    expect(onTabChange.mock.calls.map(([tab]: [string]) => tab)).toEqual(["related", "comments", "comments"]);
  });

  // 配る書き出しではコメントのタブを出さない（正常系）
  test("detail_supplements_when_no_comments", () => {
    // 実行
    render(<DetailSupplements tab="main" onTabChange={vi.fn()} main={<p>本文の中身</p>} supplements={<p>関連の中身</p>} comments={null} />);
    // 検証
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["本文", "関連"]);
  });
});
