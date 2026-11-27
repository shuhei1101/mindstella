import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { OptionList, type OptionChoice } from "@/features/detail/detail-panel/components/option-list";
import type { Option } from "@/shared/core/records";

// 案 A・B を持つ未決定の検討事項の案
const OPTIONS: Option[] = [
  { key: "A", content: "案 A の中身" },
  { key: "B", content: "案 B の中身" },
];

/** 案の記号のカードを返却する（記号の読み上げ「案 {記号}」を持つカード） */
const cardOf = (key: string): HTMLElement => {
  const label = screen.getByText((_, element) => element?.textContent === `案 ${key}` && element.tagName === "SPAN");
  const card = label.closest<HTMLElement>(".rounded-control");
  if (card === null) throw new Error(`案 ${key} のカードがありません`);
  return card;
};

describe("OptionList", () => {
  // この案を選ぶから一言を添えて確定する（正常系）
  test("option_list_when_choose", async () => {
    // 準備
    const user = userEvent.setup();
    const onChoose = vi.fn<(choice: OptionChoice) => void>();
    render(<OptionList options={OPTIONS} previous={null} onChoose={onChoose} />);
    // 実行
    await user.click(within(cardOf("B")).getByRole("button", { name: /選ぶ/ }));
    const input = within(cardOf("B")).getByRole("textbox");
    // 検証（入力欄にフォーカスが移る）
    expect(input).toHaveFocus();
    // 実行
    await user.type(input, "  費用を優先する ");
    await user.click(within(cardOf("B")).getByRole("button", { name: "この案を選ぶ" }));
    // 検証
    expect(onChoose).toHaveBeenCalledTimes(1);
    expect(onChoose).toHaveBeenCalledWith({ key: "B", note: "費用を優先する" });
  });

  // 空白だけの一言は note を持たない（正常系）
  test("option_list_when_choose_without_note", async () => {
    // 準備
    const user = userEvent.setup();
    const onChoose = vi.fn<(choice: OptionChoice) => void>();
    render(<OptionList options={OPTIONS} previous={null} onChoose={onChoose} />);
    // 実行
    await user.click(within(cardOf("B")).getByRole("button", { name: /選ぶ/ }));
    await user.type(within(cardOf("B")).getByRole("textbox"), "   ");
    await user.click(within(cardOf("B")).getByRole("button", { name: "この案を選ぶ" }));
    // 検証
    expect(onChoose).toHaveBeenCalledWith({ key: "B" });
  });

  // 送信前の選択は破線で、一言を編集・選択を取り消すを出す（正常系）
  test("option_list_when_chosen", async () => {
    // 準備
    const user = userEvent.setup();
    const onCancelChoice = vi.fn<() => void>();
    render(<OptionList options={OPTIONS} previous={null} choice={{ key: "B" }} onChoose={vi.fn()} onCancelChoice={onCancelChoice} />);
    const card = cardOf("B");
    // 検証
    expect(card).toHaveClass("border-dashed");
    expect(within(card).getByText("選択済み")).toBeInTheDocument();
    expect(within(card).getByText("（未送信）")).toHaveClass("sr-only");
    expect(within(card).getByText("一言なし")).toBeInTheDocument();
    // 実行
    await user.click(within(card).getByRole("button", { name: "選択を取り消す" }));
    // 検証
    expect(onCancelChoice).toHaveBeenCalledTimes(1);
  });

  // 送信済みの選択は実線で、一言を編集・選択を取り消すを出さない（正常系）
  test("option_list_when_sent", () => {
    // 準備・実行
    render(<OptionList options={OPTIONS} previous={null} choice={{ key: "B", note: "費用を優先する", sent: true }} onChoose={vi.fn()} onCancelChoice={vi.fn()} />);
    const card = cardOf("B");
    // 検証
    expect(card).not.toHaveClass("border-dashed");
    expect(within(card).getByText("（送信済み）")).toHaveClass("sr-only");
    expect(within(card).queryByRole("button", { name: "一言を編集" })).not.toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: "選択を取り消す" })).not.toBeInTheDocument();
    expect(within(cardOf("A")).getByRole("button", { name: "案 A を選ぶ" })).toBeInTheDocument();
  });

  // onChoose を指定しないときと差分の表示の間は選ぶ操作を出さない（正常系）
  test.each([
    { name: "without_on_choose", previous: null, onChoose: undefined },
    { name: "diff", previous: OPTIONS, onChoose: vi.fn() },
  ])("option_list_when_not_choosable ($name)", ({ previous, onChoose }) => {
    // 準備・実行
    render(<OptionList options={OPTIONS} previous={previous} {...(onChoose === undefined ? {} : { onChoose })} />);
    // 検証
    expect(screen.queryByRole("button", { name: /選ぶ/ })).not.toBeInTheDocument();
  });
});
