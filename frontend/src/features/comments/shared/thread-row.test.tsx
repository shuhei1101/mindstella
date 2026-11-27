import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ThreadRow } from "@/features/comments/shared/thread-row";
import type { Thread } from "@/shared/core/comments";
import { sampleRecordLookup } from "@/testing/record-lookup";

const thread = (seen: boolean, summary = "案の選び方"): Thread => ({
  id: "TH-1",
  status: "open",
  summary,
  tags: [],
  target: null,
  loc: null,
  events: [],
  posts: [{ id: "TH-1-1", author: "ai", body: "どちらにしますか", created: "2026-11-01T00:00:00+00:00", seen }],
});

describe("ThreadRow", () => {
  // 開く（正常系）
  test("thread_row", async () => {
    // 準備
    const onOpen = vi.fn();
    render(<ThreadRow thread={thread(true)} lookup={sampleRecordLookup} onOpen={onOpen} onTag={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /案の選び方/ }));
    // 検証
    expect(onOpen).toHaveBeenCalledWith("TH-1");
  });

  // 未読（正常系）
  test("thread_row_when_unread", () => {
    // 準備と実行
    render(<ThreadRow thread={thread(false)} lookup={sampleRecordLookup} onOpen={vi.fn()} onTag={vi.fn()} />);
    // 検証
    expect(screen.getByText("未読")).toBeInTheDocument();
  });

  // 行の中の ID にツールチップを出さない（正常系）
  test("thread_row_without_id_tooltip", () => {
    // 準備
    const { container } = render(<ThreadRow thread={thread(true, "D-1 の案の選び方")} lookup={sampleRecordLookup} onOpen={vi.fn()} onTag={vi.fn()} />);
    const button = screen.getByRole("button", { name: /案の選び方/ });
    const marker = container.querySelector<HTMLElement>('[data-record-id="D-1"]');
    // 実行
    act(() => {
      if (marker !== null) fireEvent.mouseEnter(marker);
      fireEvent.focus(button);
    });
    // 検証
    expect(document.querySelector('[role="tooltip"]')).toBeNull();
    expect(screen.getByRole("button", { name: /案の選び方/ })).toHaveAccessibleDescription(/保存先の決め方/);
  });
});
