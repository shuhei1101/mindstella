import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ThreadTitle } from "@/shared/components/thread-title";

describe("ThreadTitle", () => {
  // 1 行にしたときだけ title を持つ（正常系）
  test.each([
    { collapsed: true, expected: true },
    { collapsed: false, expected: false },
  ])("thread_title", ({ collapsed, expected }) => {
    // 実行
    render(<ThreadTitle title="案の選び方を決めるスレッド" collapsed={collapsed} />);
    // 検証
    const title = screen.getByText("案の選び方を決めるスレッド");
    if (expected) {
      expect(title).toHaveAttribute("title", "案の選び方を決めるスレッド");
      expect(title).toHaveAttribute("data-collapsed");
    } else {
      expect(title).not.toHaveAttribute("title");
      expect(title).not.toHaveAttribute("data-collapsed");
    }
  });
});
