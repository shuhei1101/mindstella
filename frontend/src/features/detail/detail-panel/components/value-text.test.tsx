import { render, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ValueText } from "@/features/detail/detail-panel/components/value-text";
import { buildIndex, type MindmapData } from "@/shared/core/records";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const DATA = { decisions: [{ id: "D-1", title: "保存先", status: "未決定" }], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] }, settings: {}, bodies: {} } as unknown as MindmapData;

describe("ValueText", () => {
  // 値の中の項目の ID をリンクにする（正常系）
  test("value_text_when_item_id", async () => {
    // 準備
    const onOpen = vi.fn();
    // 実行
    const { container } = render(<ValueText value="D-1 と D-99 を比べる" index={buildIndex(DATA)} selfId="T-1" onOpen={onOpen} threads={null} />);
    // 検証
    const link = await waitFor(() => {
      const found = container.querySelector<HTMLElement>("[data-id='D-1']");
      if (found === null) throw new Error("D-1 のリンクがまだ無い");
      return found;
    });
    link.click();
    expect(onOpen).toHaveBeenCalledWith("D-1");
    expect(container.querySelector("[data-id='D-99']")).toBeNull();
    expect(container).toHaveTextContent("D-1 と D-99 を比べる");
  });
});
