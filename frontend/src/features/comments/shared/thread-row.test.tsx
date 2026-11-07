import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ThreadRow } from "@/features/comments/shared/thread-row";
import type { Thread } from "@/shared/core/comments";

const thread = (seen: boolean): Thread => ({
  id: "TH-1",
  status: "open",
  summary: "案の選び方",
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
    render(<ThreadRow thread={thread(true)} onOpen={onOpen} onTag={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /案の選び方/ }));
    // 検証
    expect(onOpen).toHaveBeenCalledWith("TH-1");
  });

  // 未読（正常系）
  test("thread_row_when_unread", () => {
    // 準備と実行
    render(<ThreadRow thread={thread(false)} onOpen={vi.fn()} onTag={vi.fn()} />);
    // 検証
    expect(screen.getByText("未読")).toBeInTheDocument();
  });
});
