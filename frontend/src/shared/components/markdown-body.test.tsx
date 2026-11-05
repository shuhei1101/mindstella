import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { MarkdownBody } from "@/shared/components/markdown-body";

const { useLibrary } = vi.hoisted(() => ({ useLibrary: vi.fn() }));
vi.mock("@/shared/adapters/libraries", () => ({ useLibrary }));

describe("MarkdownBody", () => {
  beforeEach(() => useLibrary.mockReset());

  // mount で描く（正常系）
  test("markdown_body", async () => {
    // 準備
    const destroy = vi.fn();
    const mount = vi.fn<(root: HTMLElement, options: { markdown: string }) => { destroy: () => void }>(() => ({ destroy }));
    useLibrary.mockReturnValue({ status: "ready", library: { mount } });
    // 実行
    const { unmount } = render(<MarkdownBody source="# 見出し" />);
    await waitFor(() => expect(mount).toHaveBeenCalled());
    unmount();
    // 検証
    expect(mount.mock.calls[0]?.[1]).toMatchObject({ markdown: "# 見出し" });
    expect(destroy).toHaveBeenCalled();
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
