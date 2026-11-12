import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SearchDialog } from "@/features/search/search/search-dialog";
import { buildIndex, type MindmapData } from "@/shared/core/records";

const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { next: [] }, bodies: {} };
const index = buildIndex({
  ...empty,
  decisions: [
    { id: "D-1", title: "画面" },
    { id: "D-2", title: "画面の分け方" },
  ],
  tasks: [{ id: "T-1", title: "作業", body: "T-1.md" }],
  bodies: { "T-1.md": "画面を作る" },
} as unknown as MindmapData);

const props = (patch: Partial<Parameters<typeof SearchDialog>[0]> = {}) => ({ index, query: "", onQueryChange: vi.fn(), onOpen: vi.fn(), onClose: vi.fn(), ...patch });

describe("SearchDialog", () => {
  // 空のときの案内（正常系）
  test("search_dialog", () => {
    // 実行
    render(<SearchDialog {...props()} />);
    // 検証
    expect(screen.getByText("ID・タイトル・本文で、すべての項目を検索します。")).toBeInTheDocument();
  });

  // 段ごとの見出しで並べる（正常系）
  test("search_dialog_when_tiers", () => {
    // 実行
    render(<SearchDialog {...props({ query: "画面" })} />);
    // 検証
    const section = (name: string) => screen.getByRole("heading", { level: 2, name }).parentElement as HTMLElement;
    expect(within(section("完全に一致")).getByText("D-1")).toBeInTheDocument();
    expect(within(section("タイトルに一致")).getByText("D-2")).toBeInTheDocument();
    expect(within(section("ほかの所に一致")).getByText("T-1")).toBeInTheDocument();
  });

  // 矢印と Enter で開く（正常系）
  test("search_dialog_when_enter", async () => {
    // 準備
    const onOpen = vi.fn();
    render(<SearchDialog {...props({ query: "画面", onOpen })} />);
    // 実行
    await userEvent.keyboard("{ArrowDown}{Enter}");
    // 検証
    expect(onOpen).toHaveBeenCalledExactlyOnceWith("D-2");
  });

  // 当たらない（正常系）
  test("search_dialog_when_no_hit", () => {
    // 実行
    render(<SearchDialog {...props({ query: "無い言葉" })} />);
    // 検証
    expect(screen.getByText("該当する項目はありません。別の条件を試してください。")).toBeInTheDocument();
  });

  // 開いている間の Ctrl+K で言葉を選び直す（正常系）
  test("search_dialog_when_shortcut", () => {
    // 準備
    render(<SearchDialog {...props({ query: "画面" })} />);
    const input = screen.getByRole("textbox", { name: "検索キーワード" }) as HTMLInputElement;
    input.setSelectionRange(input.value.length, input.value.length);
    // 実行
    const event = new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true, cancelable: true });
    fireEvent(input, event);
    // 検証
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(input.value.length);
    expect(event.defaultPrevented).toBe(true);
  });
});
