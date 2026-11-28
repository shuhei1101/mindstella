import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

import type { Filters } from "@/shared/core/filters";
import type { PresetFilter } from "@/shared/core/presets";
import { FilterDrawer } from "@/shared/components/filter-drawer";

afterEach(() => {
  vi.useRealTimers();
});

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

  // 列の文字の条件を打ち終えたときに知らせる（正常系）
  test.each([
    { name: "idle", finish: (input: HTMLElement) => { void input; act(() => { vi.advanceTimersByTime(500); }); } },
    { name: "enter", finish: (input: HTMLElement) => { fireEvent.keyDown(input, { key: "Enter" }); } },
    { name: "blur", finish: (input: HTMLElement) => { fireEvent.blur(input); } },
  ])("filter_drawer_when_text_commit ($name)", ({ finish }) => {
    // 準備
    vi.useFakeTimers();
    const onTextChange = vi.fn();
    const onTextCommit = vi.fn();
    render(<FilterDrawer groups={[]} selected={{}} total={2} shown={2} texts={[{ key: "title", label: "タイトル", value: "" }]} onToggleValue={vi.fn()} onClearGroup={vi.fn()} onClearAll={vi.fn()} onClose={vi.fn()} onTextChange={onTextChange} onTextCommit={onTextCommit} />);
    const input = screen.getByRole("searchbox", { name: "タイトル" });
    // 実行
    fireEvent.change(input, { target: { value: "画" } });
    fireEvent.change(input, { target: { value: "画面" } });
    act(() => {
      vi.advanceTimersByTime(499);
    });
    // 検証（打つたびに知らせ、500ms の前には区切らない）
    expect(onTextChange).toHaveBeenNthCalledWith(1, "title", "画");
    expect(onTextChange).toHaveBeenNthCalledWith(2, "title", "画面");
    expect(onTextCommit).not.toHaveBeenCalled();
    // 実行
    finish(input);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    // 検証
    expect(onTextCommit).toHaveBeenCalledTimes(1);
  });
  // タグの条件の有無で保存を押せるかが変わる（正常系）
  test.each<{ selected: Filters; tagExpr: PresetFilter | null; disabled: boolean }>([
    { selected: {}, tagExpr: null, disabled: true },
    { selected: { tags: ["画面"] }, tagExpr: null, disabled: false },
    { selected: {}, tagExpr: { field: "tags", op: "eq", values: ["画面"] }, disabled: false },
  ])("filter_drawer_when_preset_save", ({ selected, tagExpr, disabled }) => {
    // 実行
    render(<FilterDrawer groups={[]} selected={selected} total={2} shown={2} tagExpr={tagExpr} onTagExprChange={vi.fn()} presetSave={{ hasOtherConditions: false, onSave: vi.fn() }} onToggleValue={vi.fn()} onClearGroup={vi.fn()} onClearAll={vi.fn()} onClose={vi.fn()} onTextChange={vi.fn()} />);
    // 検証
    const button = screen.getByRole("button", { name: "プリセットとして保存" });
    if (disabled) expect(button).toHaveAttribute("aria-disabled", "true");
    else expect(button).not.toHaveAttribute("aria-disabled", "true");
  });
  // 変更の条件の値に未読の丸を付ける（正常系）
  test("filter_drawer_when_changed_mark", async () => {
    // 準備
    const onToggleValue = vi.fn();
    const { container } = render(<FilterDrawer groups={[{ key: "changed", label: "変更", mark: "change", values: [{ value: "未読の変更あり", count: 0 }] }]} selected={{}} total={2} shown={2} onToggleValue={onToggleValue} onClearGroup={vi.fn()} onClearAll={vi.fn()} onClose={vi.fn()} onTextChange={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("checkbox", { name: /未読の変更あり/ }));
    // 検証
    expect(container.querySelector(".bg-topbar-unread")).not.toBeNull();
    expect(onToggleValue).toHaveBeenCalledTimes(1);
  });
});
