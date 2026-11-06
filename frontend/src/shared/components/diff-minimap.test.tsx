import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DiffMinimap } from "@/shared/components/diff-minimap";

describe("DiffMinimap", () => {
  // 印が無い（正常系）
  test("diff_minimap_when_no_marks", () => {
    // 実行
    render(<DiffMinimap shown><p>本文</p></DiffMinimap>);
    // 検証
    expect(screen.getByText("本文")).toBeInTheDocument();
    expect(screen.queryByRole("toolbar", { name: "変わった箇所" })).not.toBeInTheDocument();
  });
});
