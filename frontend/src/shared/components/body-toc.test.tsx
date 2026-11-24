import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { BodyToc } from "@/shared/components/body-toc";

const ENTRIES = [
  { level: 1, text: "目的", slug: "目的" },
  { level: 2, text: "保存先", slug: "保存先" },
];

describe("BodyToc", () => {
  // 見出しを押すと知らせて閉じる（正常系）
  test("body_toc", async () => {
    // 準備
    const onHeading = vi.fn();
    render(<BodyToc entries={ENTRIES} onHeading={onHeading} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "本文の目次" }));
    await userEvent.click(screen.getByRole("button", { name: "保存先" }));
    // 検証
    expect(onHeading).toHaveBeenCalledWith("保存先");
    expect(screen.queryByRole("navigation", { name: "本文の目次" })).not.toBeInTheDocument();
  });

  // Esc で閉じてボタンへ戻る（正常系）
  test("body_toc_when_escape", async () => {
    // 準備
    render(<BodyToc entries={ENTRIES} onHeading={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "本文の目次" });
    await userEvent.click(trigger);
    // 実行
    await userEvent.keyboard("{Escape}");
    // 検証
    expect(screen.queryByRole("navigation", { name: "本文の目次" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
