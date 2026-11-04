import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { Topbar } from "@/shared/components/topbar";

const TABS = [
  { key: "overview", label: "概要", icon: "overview" },
  { key: "decisions", label: "検討事項", icon: "decisions", count: 2 },
] as const;

describe("Topbar", () => {
  // タブを押すと onNavigate（正常系）
  test("topbar_when_navigate", async () => {
    // 準備
    const onNavigate = vi.fn();
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" onNavigate={onNavigate} />);
    // 実行
    await userEvent.click(screen.getByRole("link", { name: /検討事項/ }));
    // 検証
    expect(onNavigate).toHaveBeenCalledTimes(1);
    expect(onNavigate).toHaveBeenCalledWith("decisions");
  });

  // offline で接続の状態を出す（正常系）
  test("topbar_when_offline", () => {
    // 実行
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" connection="offline" readAt="2026-10-04T02:21:00+00:00" />);
    // 検証
    expect(screen.getByText(/サーバーにつながりません/)).toBeInTheDocument();
  });

  // 100 件以上は 99+（正常系）
  test("topbar_when_many_comments", () => {
    // 実行
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" comments commentCount={120} />);
    // 検証
    const button = screen.getByRole("button", { name: /120/ });
    expect(button).toHaveTextContent("99+");
  });
});
