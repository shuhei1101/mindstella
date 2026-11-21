import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { TagExprEditor } from "@/shared/components/tag-expr-editor";
import type { PresetCondition } from "@/shared/core/presets";

const TAGS = [
  { value: "画面", count: 3 },
  { value: "廃止", count: 1 },
  { value: "保存", count: 1 },
];

const condition = (value: string): PresetCondition => ({ field: "tags", op: "eq", values: [value] });

describe("TagExprEditor", () => {
  // 「一致しない」への切り替えで条件を残す（正常系）
  test("tag_expr_editor_when_not", async () => {
    // 準備
    const onChange = vi.fn();
    const children = [condition("画面"), condition("廃止"), condition("保存")];
    const { rerender } = render(<TagExprEditor expr={{ and: children }} tags={TAGS} onChange={onChange} />);
    // 実行
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "条件の組み合わせ" }), "not");
    // 検証
    expect(onChange).toHaveBeenLastCalledWith({ not: { and: children } });
    // 実行
    rerender(<TagExprEditor expr={{ not: { and: children } }} tags={TAGS} onChange={onChange} />);
    await userEvent.selectOptions(screen.getAllByRole("combobox", { name: "条件の組み合わせ" })[0] as HTMLElement, "and");
    // 検証
    expect(onChange).toHaveBeenLastCalledWith({ and: children });
  });

  // 候補に無いタグ（異常系）
  test("tag_expr_editor_when_unknown_tag", async () => {
    // 準備
    const onChange = vi.fn();
    render(<TagExprEditor expr={{ and: [{ field: "tags", op: "eq", values: [] }] }} tags={TAGS} onChange={onChange} />);
    // 実行
    await userEvent.type(screen.getByRole("combobox", { name: "タグを追加" }), "通知{Enter}");
    // 検証
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByText(/該当するタグはありません/)).toBeInTheDocument();
  });
});
