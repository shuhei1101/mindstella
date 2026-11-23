import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { Board } from "@/shared/components/board";
import type { Item } from "@/shared/core/records";

const ITEMS: Item[] = [
  { id: "T-1", title: "画面を作る" },
  { id: "T-2", title: "テストを書く" },
];

beforeEach(() => {
  // jsdom はポインターの捕捉を持たないため、捕捉の呼び出しだけを受ける
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
});

const renderBoard = (onOpen: (id: string) => void) =>
  render(
    <Board
      columns={[
        { status: "未着手", items: [ITEMS[0] as Item], excluded: false },
        { status: "進行中", items: [ITEMS[1] as Item], excluded: false },
      ]}
      card={(item) => (
        <button key={item.id} type="button" onClick={() => onOpen(item.id)}>
          {item.title}
        </button>
      )}
      emptyText="タスクはありません。"
    />,
  );

describe("Board", () => {
  // 背景のドラッグで横にスクロールする（正常系）
  test("board_when_drag_background", () => {
    // 準備
    const onOpen = vi.fn();
    renderBoard(onOpen);
    const region = screen.getByRole("region", { name: "ボード" });
    region.scrollLeft = 200;
    // 実行
    fireEvent.pointerDown(region, { pointerType: "mouse", button: 0, pointerId: 1, clientX: 300 });
    fireEvent.pointerMove(region, { pointerType: "mouse", pointerId: 1, clientX: 180 });
    fireEvent.pointerUp(region, { pointerType: "mouse", pointerId: 1, clientX: 180 });
    // 検証
    expect(region.scrollLeft).toBe(320);
    expect(onOpen).not.toHaveBeenCalled();
  });

  // カードの上からはドラッグしない（正常系）
  test("board_when_drag_starts_on_card", () => {
    // 準備
    renderBoard(vi.fn());
    const region = screen.getByRole("region", { name: "ボード" });
    region.scrollLeft = 200;
    const card = screen.getByRole("button", { name: "画面を作る" });
    // 実行
    fireEvent.pointerDown(card, { pointerType: "mouse", button: 0, pointerId: 1, clientX: 300 });
    fireEvent.pointerMove(card, { pointerType: "mouse", pointerId: 1, clientX: 180 });
    fireEvent.pointerUp(card, { pointerType: "mouse", pointerId: 1, clientX: 180 });
    // 検証
    expect(region.scrollLeft).toBe(200);
  });
});
