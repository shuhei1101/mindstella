import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { LookSelect } from "@/features/graph/graph/components/look-select";

describe("LookSelect", () => {
  // 既定に「（既定）」を添える（正常系）
  test("look_select", async () => {
    // 準備
    render(<LookSelect value="deep" defaultLook="deep" onChange={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("combobox", { name: "ネットワークの見た目" }));
    // 検証
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["グロウ", "星の光", "星図", "深宇宙（既定）", "星屑"]);
  });
});
