import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { DiagramViewer } from "@/features/detail/diagram-viewer/diagram-viewer";

describe("DiagramViewer", () => {
  // 図を大きく出す（正常系）
  test("diagram_viewer", () => {
    // 実行
    render(<DiagramViewer svg="<svg><title>図の題</title></svg>" onClose={vi.fn()} />);
    // 検証
    expect(screen.getByRole("dialog", { name: "図の拡大" })).toHaveTextContent("図の題");
  });

  // 外側の幕を押すと閉じる（正常系）
  test("diagram_viewer_when_outside_pressed", async () => {
    // 準備
    const onClose = vi.fn();
    const { unmount } = render(<DiagramViewer svg="<svg><title>図の題</title></svg>" onClose={onClose} />);
    expect(screen.queryByRole("button", { name: "本文へ戻る" })).toBeNull();
    // 実行（外側の幕を押す）
    await userEvent.click(document.body);
    // 検証
    expect(onClose).toHaveBeenCalledTimes(1);
    // 実行（開き直して Esc を押す）
    unmount();
    render(<DiagramViewer svg="<svg><title>図の題</title></svg>" onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    // 検証
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
