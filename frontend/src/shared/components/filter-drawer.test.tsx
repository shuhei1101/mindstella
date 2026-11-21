import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { FilterDrawer } from "@/shared/components/filter-drawer";

describe("FilterDrawer", () => {
  // 値を選ぶ（正常系）
  test("filter_drawer", async () => {
    // 準備
    const onToggleValue = vi.fn();
    render(<FilterDrawer groups={[{ key: "status", label: "状態", values: [{ value: "保留", count: 2 }] }]} selected={{}} total={2} shown={2} onToggleValue={onToggleValue} onClearGroup={vi.fn()} onClearAll={vi.fn()} onClose={vi.fn()} onTextChange={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("checkbox", { name: /保留/ }));
    // 検証
    expect(onToggleValue).toHaveBeenCalledWith("status", "保留");
  });

  // プリセットを選ぶ（正常系）
  test("filter_drawer_when_preset", async () => {
    // 準備
    const onApplyPreset = vi.fn();
    render(<FilterDrawer groups={[]} selected={{}} total={4} shown={4} presets={[{ name: "画面の設計", count: 2, applied: false }, { name: "通知", count: 0, applied: false }]} onApplyPreset={onApplyPreset} onToggleValue={vi.fn()} onClearGroup={vi.fn()} onClearAll={vi.fn()} onClose={vi.fn()} onTextChange={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /画面の設計/ }));
    // 検証
    expect(onApplyPreset).toHaveBeenCalledWith("画面の設計");
    const empty = screen.getByRole("button", { name: /通知/ });
    expect(empty).toHaveTextContent("0 件");
    expect(empty).toHaveAttribute("aria-pressed", "false");
  });

  // 簡易で表せない式は詳細で出す（正常系）
  test("filter_drawer_when_tag_detail", () => {
    // 実行
    render(
      <FilterDrawer
        groups={[{ key: "tags", label: "タグ", values: [{ value: "画面", count: 3 }, { value: "廃止", count: 1 }] }]}
        selected={{}}
        total={4}
        shown={1}
        tagExpr={{ and: [{ field: "tags", op: "eq", values: ["画面"] }, { field: "tags", op: "ne", values: ["廃止"] }] }}
        onTagExprChange={vi.fn()}
        onTagMatchChange={vi.fn()}
        onToggleValue={vi.fn()}
        onClearGroup={vi.fn()}
        onClearAll={vi.fn()}
        onClose={vi.fn()}
        onTextChange={vi.fn()}
      />,
    );
    // 検証
    expect(screen.getByRole("radio", { name: "詳細" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "簡易" })).toBeDisabled();
    expect(screen.queryByRole("checkbox", { name: /画面/ })).toBeNull();
    expect(screen.getByRole("combobox", { name: "条件の組み合わせ" })).toBeInTheDocument();
  });
});

