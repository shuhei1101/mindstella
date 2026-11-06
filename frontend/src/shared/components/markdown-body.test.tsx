import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { MarkdownBody } from "@/shared/components/markdown-body";

const { useLibrary, renderMarkdown } = vi.hoisted(() => ({ useLibrary: vi.fn(), renderMarkdown: vi.fn() }));
vi.mock("@/shared/adapters/libraries", () => ({ useLibrary }));
vi.mock("@/shared/core/body-links", async (importOriginal) => ({ ...(await importOriginal<object>()), renderMarkdown }));

describe("MarkdownBody", () => {
  beforeEach(() => {
    useLibrary.mockReset();
    renderMarkdown.mockReset();
  });

  // mdmark で描いた本文を置き、外すと片付ける（正常系）
  test("markdown_body", async () => {
    // 準備
    useLibrary.mockReturnValue({ status: "ready", library: {} });
    renderMarkdown.mockImplementation(() => {
      const root = document.createElement("div");
      root.innerHTML = "<h1>見出し</h1>";
      return root;
    });
    // 実行
    const { container, unmount } = render(<MarkdownBody source="# 見出し" />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "見出し" })).toBeInTheDocument());
    const host = container.firstElementChild;
    unmount();
    // 検証
    expect(renderMarkdown).toHaveBeenCalledWith("# 見出し");
    expect(host?.childNodes).toHaveLength(0);
  });

  // 読めない（異常系）
  test("markdown_body_when_library_failed", () => {
    // 準備
    useLibrary.mockReturnValue({ status: "failed", library: null });
    // 実行
    render(<MarkdownBody source="# 見出し" />);
    // 検証
    expect(screen.getByText("# 見出し")).toBeInTheDocument();
    expect(screen.getByText(/mdmark/)).toBeInTheDocument();
  });
});
