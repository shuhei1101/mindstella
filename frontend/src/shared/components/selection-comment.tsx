// 選んだ箇所のコメントの入口（部品設計『選んだ箇所のコメントの入口.tsx』）。本文の文章か項目の値を選び終えたときに、選んだ範囲の近くに出す印だけの丸いボタン
import type { KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";

export type SelectionCommentProps = {
  /** 選んだ範囲の最初と最後の矩形（`Range.getClientRects()`） */
  anchor: { first: DOMRect; last: DOMRect };
  /** 画面の大きさと、本文のスクロール領域の矩形 */
  area: { viewport: { width: number; height: number }; scroller: DOMRect };
  onOpen: () => void;
  onClose: () => void;
};

/** 入口の大きさ（位置を決めるため固定する）。押せる的は高さ 32px 以上 */
const BUTTON_SIZE = 32;

/** 選んだ範囲との間の空きと、画面の端から内側に収める幅 */
const BUTTON_GAP = 6;
const SCREEN_EDGE = 8;

/** 入口の名前（読み上げとツールチップ） */
const BUTTON_NAME = "選んだ箇所にコメント";

export const SelectionComment = ({ anchor, area, onOpen, onClose }: SelectionCommentProps) => {
  const above = anchor.first.top - BUTTON_GAP - BUTTON_SIZE;
  // 画面の端とスクロール領域の上端の内側に収まるか
  const fitsAbove = above >= Math.max(SCREEN_EDGE, area.scroller.top);
  const top = fitsAbove ? above : anchor.last.bottom + BUTTON_GAP;
  const edge = fitsAbove ? anchor.first.left : anchor.last.left;
  const left = Math.max(SCREEN_EDGE, Math.min(edge, area.viewport.width - SCREEN_EDGE - BUTTON_SIZE));
  const tipEnd = left + BUTTON_SIZE / 2 > area.viewport.width / 2;
  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>): void => {
    if (event.key !== "Escape") return;
    // 入口だけを閉じる。詳細パネルを閉じる Esc として受けさせない
    event.stopPropagation();
    event.preventDefault();
    onClose();
  };
  return (
    <button
      type="button"
      aria-label={BUTTON_NAME}
      data-side={fitsAbove ? "above" : "below"}
      data-tip={tipEnd ? "end" : "start"}
      className="group fixed z-50 grid size-8 cursor-pointer place-items-center rounded-full border border-border bg-card text-foreground shadow-md hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
      style={{ left: `${String(left)}px`, top: `${String(top)}px` }}
      // 押したときに選択が外れないよう、ポインターを押した既定の動き（選択の解除）を止める
      onPointerDown={(event) => {
        event.preventDefault();
      }}
      onClick={onOpen}
      onKeyDown={handleKeyDown}
    >
      <Icon name="comment" />
      <span aria-hidden="true" className={`pointer-events-none absolute ${fitsAbove ? "bottom-full mb-1" : "top-full mt-1"} ${tipEnd ? "right-0" : "left-0"} hidden rounded-control bg-popover px-2 py-1 text-small whitespace-nowrap text-popover-foreground shadow-md group-hover:block group-focus-visible:block`}>
        {BUTTON_NAME}
      </span>
    </button>
  );
};
