import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { CardSort, cardSortToParam, INITIAL_CARD_SORT, nextCardSort, type CardSortKey, type CardSortValue } from "@/shared/components/card-sort";

describe("nextCardSort", () => {
  // 向きを決める（正常系）
  test.each<{ current: CardSortValue; key: CardSortKey; expected: CardSortValue }>([
    { current: { key: "default", dir: "asc" }, key: "updated", expected: { key: "updated", dir: "desc" } },
    { current: { key: "updated", dir: "desc" }, key: "updated", expected: { key: "updated", dir: "asc" } },
    { current: { key: "updated", dir: "asc" }, key: "default", expected: { key: "default", dir: "asc" } },
  ])("next_card_sort", ({ current, key, expected }) => {
    // 実行・検証
    expect(nextCardSort(current, key)).toEqual(expected);
  });
});

describe("cardSortToParam", () => {
  // 既定と違うときだけ書く（正常系）
  test.each<{ value: CardSortValue; initial: CardSortValue; expected: string | undefined }>([
    { value: { key: "updated", dir: "desc" }, initial: INITIAL_CARD_SORT.docs, expected: undefined },
    { value: { key: "default", dir: "asc" }, initial: INITIAL_CARD_SORT.docs, expected: "id" },
    { value: { key: "created", dir: "asc" }, initial: INITIAL_CARD_SORT.other, expected: "created" },
  ])("card_sort_to_param", ({ value, initial, expected }) => {
    // 実行・検証
    expect(cardSortToParam(value, initial)).toBe(expected);
  });
});

describe("CardSort", () => {
  // 押したボタンで次の並びを知らせる（正常系）
  test("card_sort", async () => {
    // 準備
    const onChange = vi.fn();
    render(<CardSort value={{ key: "default", dir: "asc" }} onChange={onChange} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "更新日時" }));
    // 検証
    expect(onChange).toHaveBeenCalledWith({ key: "updated", dir: "desc" });
    expect(screen.getByRole("button", { name: "連番" })).toHaveAttribute("aria-pressed", "true");
  });
});
