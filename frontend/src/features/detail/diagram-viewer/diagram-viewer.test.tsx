import { render, screen } from "@testing-library/react";
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
});
