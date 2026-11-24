import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { DocCards, type DocCardsProps } from "@/features/docs/docs/components/doc-cards";
import type { Item } from "@/shared/core/records";

const DOCS: Item[] = [
  { id: "A-1", title: "古い資料", status: "下書き", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-02T00:00:00+00:00" },
  { id: "A-2", title: "新しい資料", status: "完成", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-20T00:00:00+00:00" },
  { id: "A-3", title: "間の資料", status: "確認中", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-10T00:00:00+00:00" },
];

const props = (patch: Partial<DocCardsProps> = {}): DocCardsProps => ({
  docs: DOCS,
  selectedId: null,
  marks: undefined,
  comments: {},
  edit: null,
  onOpen: vi.fn(),
  ...patch,
});

describe("DocCards", () => {
  // 既定は更新日時の新しい順（正常系）
  test("doc_cards_when_default_sort", () => {
    // 実行
    const { container } = render(<DocCards {...props()} />);
    // 検証
    const cards = [...container.querySelectorAll<HTMLElement>("[data-card]")];
    expect(cards.map((card) => card.dataset["card"])).toEqual(["A-2", "A-3", "A-1"]);
    for (const card of cards) {
      expect(card).toHaveTextContent(/作成/);
      expect(card).toHaveTextContent(/更新/);
      expect(card.querySelectorAll("time")).toHaveLength(2);
    }
  });

  // 開いたときに今の並びを通知する（正常系）
  test("doc_cards_when_open_order", async () => {
    // 準備
    const onOpen = vi.fn();
    render(<DocCards {...props({ onOpen })} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "間の資料" }));
    // 検証
    expect(onOpen).toHaveBeenCalledWith("A-3", ["A-2", "A-3", "A-1"]);
  });
});
