import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId, RecordIdTarget } from "@/shared/core/record-ids";

/** 見本の記録にある ID と中身（D-99 は記録に無い） */
const TARGETS: Record<string, RecordIdTarget> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

const lookup: LookupRecordId = (id) => TARGETS[id] ?? null;

describe("RecordText", () => {
  // 記録にある ID だけをリンクにし、押すと onOpen を呼ぶ（正常系）
  test("record_text_link", async () => {
    // 準備
    const onOpen = vi.fn();
    const { container } = render(<RecordText text="D-1 の比較（TH-1 の続き、D-99 は除く）" mode="link" lookup={lookup} onOpen={onOpen} />);
    // 実行
    await userEvent.click(screen.getByRole("link", { name: "D-1" }));
    // 検証
    expect(screen.getByRole("link", { name: "D-1" })).toHaveAttribute("href", "#id=D-1");
    expect(screen.getByRole("link", { name: "TH-1" })).toHaveAttribute("href", "#id=TH-1");
    expect(screen.queryByRole("link", { name: "D-99" })).toBeNull();
    expect(container).toHaveTextContent("D-1 の比較（TH-1 の続き、D-99 は除く）");
    expect(onOpen).toHaveBeenCalledWith("D-1");
  });

  // マーカーはフォーカスできる要素にせず、説明を描く（正常系）
  test("record_text_marker", () => {
    // 実行
    const { container } = render(<RecordText text="D-1 の比較（D-99 は除く）" mode="marker" lookup={lookup} descriptionId="ids" />);
    // 検証
    const marker = container.querySelector('[data-record-id="D-1"]');
    expect(marker?.tagName).toBe("SPAN");
    expect(container.querySelector("a, button, [tabindex]")).toBeNull();
    const description = container.querySelector("#ids");
    for (const text of ["保存先の決め方", "D-1", "検討事項", "未決定"]) expect(description).toHaveTextContent(text);
  });

  // 記録にある ID が無いときは文字だけ（正常系）
  test("record_text_no_ids", () => {
    // 実行
    const { container } = render(<RecordText text="保存先の比較" mode="marker" lookup={lookup} descriptionId="ids" />);
    // 検証
    expect(container).toHaveTextContent("保存先の比較");
    expect(container.querySelector("[data-record-id]")).toBeNull();
    expect(container.querySelector("#ids")).toBeNull();
  });
  // カードのボタンの外のマーカーを押すと、カードのボタンを押したことにする（正常系）
  test("record_text_marker_card_click", async () => {
    // 準備
    const onCard = vi.fn();
    const { container } = render(
      <div data-card="T-1">
        <button type="button" onClick={onCard}>
          題
        </button>
        <span>
          <RecordText text="D-1 の比較" mode="marker" lookup={lookup} />
        </span>
      </div>,
    );
    const marker = container.querySelector<HTMLElement>('[data-record-id="D-1"]');
    if (marker === null) throw new Error("マーカーがありません");
    // 実行
    await userEvent.click(marker);
    // 検証
    expect(onCard).toHaveBeenCalledTimes(1);
  });
  // カードの先頭にお気に入りの星があっても、マーカーはカードのタイトルのボタン（data-id）を押す（正常系）
  test("record_text_marker_card_click_when_favorite", async () => {
    // 準備
    const onCard = vi.fn();
    const onStar = vi.fn();
    const { container } = render(
      <div data-card="T-1">
        <button type="button" aria-pressed={false} onClick={onStar}>
          星
        </button>
        <button type="button" data-id="T-1" onClick={onCard}>
          題
        </button>
        <span>
          <RecordText text="D-1 の比較" mode="marker" lookup={lookup} />
        </span>
      </div>,
    );
    const marker = container.querySelector<HTMLElement>('[data-record-id="D-1"]');
    if (marker === null) throw new Error("マーカーがありません");
    // 実行
    await userEvent.click(marker);
    // 検証
    expect(onCard).toHaveBeenCalledTimes(1);
    expect(onStar).not.toHaveBeenCalled();
  });
  // 指で押したときはツールチップを出さず 1 回で開く（正常系）
  test("record_text_when_touch", () => {
    // 準備
    const onOpen = vi.fn();
    render(<RecordText text="D-1 の比較" mode="link" lookup={lookup} onOpen={onOpen} />);
    const link = screen.getByRole("link", { name: "D-1" });
    // 実行（jsdom は PointerEvent を持たないため、pointerType を持つ Event を送信する）
    const down = new Event("pointerdown", { bubbles: true });
    Object.defineProperty(down, "pointerType", { value: "touch" });
    act(() => {
      link.dispatchEvent(down);
      fireEvent.mouseEnter(link);
      fireEvent.focus(link);
    });
    const tipShown = document.querySelector('[role="tooltip"]') !== null;
    fireEvent.click(link);
    // 検証
    expect(tipShown).toBe(false);
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith("D-1");
  });

  // tooltip が偽のマーカーはツールチップを出さない（正常系）
  test("record_text_marker_without_tooltip", () => {
    // 準備
    const { container } = render(
      <button type="button">
        <RecordText text="D-1 の決め方" mode="marker" lookup={lookup} descriptionId="ids" tooltip={false} />
      </button>,
    );
    const marker = container.querySelector<HTMLElement>('[data-record-id="D-1"]');
    // 実行
    act(() => {
      if (marker !== null) fireEvent.mouseEnter(marker);
      fireEvent.focus(screen.getByRole("button"));
    });
    // 検証
    expect(document.querySelector('[role="tooltip"]')).toBeNull();
    expect(marker?.tagName).toBe("SPAN");
    expect(container.querySelector("#ids")).toHaveTextContent("保存先の決め方");
  });
});
