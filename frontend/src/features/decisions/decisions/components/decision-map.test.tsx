import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { DecisionMap } from "@/features/decisions/decisions/components/decision-map";

const { useLibrary } = vi.hoisted(() => ({ useLibrary: vi.fn() }));
vi.mock("@/shared/adapters/libraries", () => ({ useLibrary }));

describe("DecisionMap", () => {
  // elkjs が読めない（異常系）
  test("decision_map_when_library_failed", () => {
    // 準備
    useLibrary.mockReturnValue({ status: "failed", library: null });
    // 実行
    render(<DecisionMap items={[]} settings={{ targets: [], categories: [], phases: [] }} onOpen={vi.fn()} selectedId={undefined} />);
    // 検証
    expect(screen.getByText(/elkjs/)).toBeInTheDocument();
  });
});
