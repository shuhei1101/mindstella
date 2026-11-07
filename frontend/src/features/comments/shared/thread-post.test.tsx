import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ThreadPost } from "@/features/comments/shared/thread-post";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

describe("ThreadPost", () => {
  // AI の書き込み（正常系）
  test("thread_post", async () => {
    // 準備と実行
    render(<ThreadPost post={{ id: "TH-1-1", author: "ai", body: "どちらにしますか", created: "2026-11-01T00:00:00+00:00", seen: true }} />);
    // 検証
    const article = await screen.findByRole("article");
    expect(article).toHaveAttribute("data-author", "ai");
    expect(article).toHaveTextContent("どちらにしますか");
  });

  // 書き換え（正常系）
  test("thread_post_when_pending_editing", () => {
    // 準備と実行
    render(
      <ThreadPost
        pending={{ id: "C-1", target: null, loc: null, thread: "TH-1", body: "返信", created: "2026-11-01T00:00:00+00:00" }}
        editing
        editBody="返信"
        onEditSubmit={vi.fn()}
        onEditCancel={vi.fn()}
      />,
    );
    // 検証
    expect(screen.getByRole("textbox")).toHaveValue("返信");
    expect(screen.getByRole("button", { name: "キャンセル" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "修正" })).toBeInTheDocument();
  });
});
