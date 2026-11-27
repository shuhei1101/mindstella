import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { Board, ItemCard } from "@/shared/components/board";
import { buildIndex, type Item, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";
import { sampleRecordLookup } from "@/testing/record-lookup";

const ITEMS: Item[] = [
  { id: "T-1", title: "画面を作る", created: "2026-11-01", updated: "2026-11-01" },
  { id: "T-2", title: "テストを書く", created: "2026-11-01", updated: "2026-11-01" },
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

  // 列の中を並べ替える（正常系）
  test("board_when_sorted", () => {
    // 準備
    const items: Item[] = [
      { id: "T-1", title: "古い", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-02T00:00:00+00:00" },
      { id: "T-2", title: "新しい", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-20T00:00:00+00:00" },
      { id: "T-3", title: "間", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-10T00:00:00+00:00" },
    ];
    // 実行
    render(<Board columns={[{ status: "未着手", items, excluded: false }]} sort="-updated" card={(item) => <button key={item.id} type="button">{item.title}</button>} emptyText="タスクはありません。" />);
    // 検証
    expect(screen.getAllByRole("button").map((button) => button.textContent)).toEqual(["新しい", "間", "古い"]);
  });

  // カードを押すとその列の並びが渡る（正常系）
  test("board_when_open_order", async () => {
    // 準備
    const onOpen = vi.fn();
    const items: Item[] = [
      { id: "T-1", title: "一", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-01T00:00:00+00:00" },
      { id: "T-2", title: "二", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-01T00:00:00+00:00" },
      { id: "T-3", title: "三", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-01T00:00:00+00:00" },
    ];
    render(
      <Board
        columns={[
          { status: "未着手", items: [items[0] as Item], excluded: false },
          { status: "進行中", items: [items[1] as Item, items[2] as Item], excluded: false },
        ]}
        card={(item, order) => (
          <button key={item.id} type="button" onClick={() => { onOpen(item.id, order); }}>
            {item.title}
          </button>
        )}
        emptyText="タスクはありません。"
      />,
    );
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "三" }));
    // 検証
    expect(onOpen).toHaveBeenCalledWith("T-3", ["T-2", "T-3"]);
  });
});

describe("ItemCard", () => {
  // 星を押すと onToggle だけを呼び、カードを開かない（正常系）
  test("item_card_when_favorite", async () => {
    // 準備
    const onToggle = vi.fn();
    const onOpen = vi.fn();
    const item: Item = { id: "T-1", title: "画面を作る", created: "2026-11-01", updated: "2026-11-01" };
    render(<ItemCard index={buildIndex(RECORDS as unknown as MindmapData)} lookup={sampleRecordLookup} item={item} meta={[]} links={[]} selected={false} marks={undefined} comments={{}} edit={null} onOpen={onOpen} favorite={{ on: true, onToggle }} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "画面を作るをお気に入りに登録" }));
    // 検証
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onOpen).not.toHaveBeenCalled();
  });
});
