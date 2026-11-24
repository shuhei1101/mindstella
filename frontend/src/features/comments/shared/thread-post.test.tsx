import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ThreadPost } from "@/features/comments/shared/thread-post";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

afterEach(() => {
  vi.restoreAllMocks();
});

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

  // 最新以外の長い書き込みを畳む（正常系）
  test.each([
    { fold: true, expected: true },
    { fold: false, expected: false },
  ])("thread_post_when_fold (fold: $fold)", async ({ fold, expected }) => {
    // 準備
    vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(8 * 20);
    const original = window.getComputedStyle.bind(window);
    vi.spyOn(window, "getComputedStyle").mockImplementation((element) => new Proxy(original(element), {
        get: (target, key) => {
          if (key === "lineHeight") return "20px";
          const value: unknown = Reflect.get(target, key);
          return typeof value === "function" ? (value as (...args: unknown[]) => unknown).bind(target) : value;
        },
      }));
    const body = ["1 行目", "2 行目", "3 行目", "4 行目", "5 行目", "6 行目", "7 行目", "8 行目"].join("\n\n");
    // 実行
    render(<ThreadPost post={{ id: "TH-1-1", author: "ai", body, created: "2026-11-01T00:00:00+00:00", seen: true }} fold={fold} />);
    await screen.findByRole("article");
    // 検証
    const button = screen.queryByRole("button", { name: /TH-1-1 の書き込みの続きを表示/ });
    if (expected) {
      expect(await screen.findByRole("button", { name: /TH-1-1 の書き込みの続きを表示/ })).toHaveAttribute("aria-expanded", "false");
    } else {
      expect(button).toBeNull();
    }
  });
});
