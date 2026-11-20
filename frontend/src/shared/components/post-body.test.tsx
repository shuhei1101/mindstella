import { render, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { PostBody } from "@/shared/components/post-body";

const { useLibrary, renderMarkdown } = vi.hoisted(() => ({ useLibrary: vi.fn(), renderMarkdown: vi.fn() }));
vi.mock("@/shared/adapters/libraries", () => ({ useLibrary }));
vi.mock("@/shared/core/body-links", async (importOriginal) => ({ ...(await importOriginal<object>()), renderMarkdown, renderDiagrams: vi.fn() }));

describe("PostBody", () => {
  // 表を横スクロールの入れ物で包み、本文の入れ物は幅を詰められる（正常系）
  test("post_body_when_wide_table", async () => {
    // 準備
    useLibrary.mockReturnValue({ status: "ready", library: {} });
    renderMarkdown.mockImplementation(() => {
      const root = document.createElement("div");
      root.className = "md md-value";
      root.innerHTML = "<p>段落</p><table><tr><td>a</td><td>b</td></tr></table>";
      return root;
    });
    // 実行
    const { container } = render(<PostBody body={"段落\n\n| a | b |\n| - | - |"} />);
    // 検証
    await waitFor(() => expect(container.querySelector("table")).not.toBeNull());
    const table = container.querySelector("table");
    expect(table?.parentElement).toHaveClass("post-table-scroll");
    expect(container.querySelector("[data-part=body]")).toHaveClass("min-w-0");
  });
});
