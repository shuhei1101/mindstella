import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { SiblingNav } from "@/shared/components/sibling-nav";

describe("SiblingNav", () => {
  // 先頭・末尾でその向きを押せない（正常系）
  test.each([
    { position: 1, disabled: "一覧の前の項目", enabled: "一覧の次の項目" },
    { position: 3, disabled: "一覧の次の項目", enabled: "一覧の前の項目" },
  ])("sibling_nav_when_edge", ({ position, disabled, enabled }) => {
    // 実行
    render(<SiblingNav position={position} total={3} onPrev={vi.fn()} onNext={vi.fn()} />);
    // 検証
    expect(screen.getByRole("button", { name: disabled })).toBeDisabled();
    expect(screen.getByRole("button", { name: enabled })).toBeEnabled();
  });

  // キーを添える（正常系）
  test("sibling_nav_when_keys", () => {
    // 実行
    render(<SiblingNav position={2} total={3} onPrev={vi.fn()} onNext={vi.fn()} keys={{ prev: "k", next: "j" }} />);
    // 検証
    const prev = screen.getByRole("button", { name: "一覧の前の項目" });
    const next = screen.getByRole("button", { name: "一覧の次の項目" });
    expect(prev).toHaveAttribute("aria-keyshortcuts", "k");
    expect(next).toHaveAttribute("aria-keyshortcuts", "j");
    expect(prev).toHaveAttribute("title", "一覧の前の項目（K）");
    expect(next).toHaveAttribute("title", "一覧の次の項目（J）");
  });
});
