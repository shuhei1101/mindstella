// パネルの端に置く幅の区切り。ドラッグとキーで幅を変え、変えた幅と確定した幅を通知する
import { useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";

import { cn } from "@/shared/lib/cn";

/** 区切りを置くパネルの端 */
export type PanelResizerSide = "left" | "right";

export type PanelResizerProps = {
  side: PanelResizerSide;
  width: number;
  min: number;
  max: number;
  step?: number;
  label: string;
  /** ドラッグ中（1 フレームに 1 回）とキーで幅を変えたときの幅 */
  onChange: (width: number) => void;
  /** ドラッグを終えたときとキーで幅を変えたときの幅 */
  onCommit: (width: number) => void;
};

/** キー 1 回で変える既定の幅（px） */
const DEFAULT_STEP = 16;

/** 幅を min 以上・max 以下に収めて整数に丸める（max が min より小さいときは min） */
export const clampWidth = (width: number, min: number, max: number): number => Math.round(Math.max(min, Math.min(width, max)));

type Drag = { startX: number; startWidth: number; latest: number; frame: number | null };

/** 下限・上限で止まっている間は、動かせる向きだけのカーソルにする */
const cursorOf = (side: PanelResizerSide, width: number, min: number, max: number): string => {
  // 下限: 広げる向きだけ動かせる（左端は左、右端は右）
  if (width <= min) return side === "left" ? "cursor-w-resize" : "cursor-e-resize";
  // 上限: 狭める向きだけ動かせる
  if (width >= max) return side === "left" ? "cursor-e-resize" : "cursor-w-resize";
  return "cursor-col-resize";
};

export const PanelResizer = ({ side, width, min, max, step = DEFAULT_STEP, label, onChange, onCommit }: PanelResizerProps) => {
  const drag = useRef<Drag | null>(null);
  const [active, setActive] = useState(false);

  /** ポインターの位置から幅を求める（左端は左へ、右端は右へ動いた分だけ広げる） */
  const widthAt = (current: Drag, clientX: number): number => {
    const moved = side === "left" ? current.startX - clientX : clientX - current.startX;
    return clampWidth(current.startWidth + moved, min, max);
  };

  /** ドラッグを終え、まだ通知していない幅を通知してから確定する */
  const endDrag = () => {
    const current = drag.current;
    // ドラッグ中でない（pointerup の後の lostpointercapture など）: 何もしない
    if (current === null) return;
    drag.current = null;
    setActive(false);
    // 次のフレームを待っている幅がある: 先に変更として通知する
    if (current.frame !== null) {
      cancelAnimationFrame(current.frame);
      onChange(current.latest);
    }
    onCommit(current.latest);
  };

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    drag.current = { startX: event.clientX, startWidth: width, latest: width, frame: null };
    event.currentTarget.setPointerCapture(event.pointerId);
    setActive(true);
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const current = drag.current;
    if (current === null) return;
    current.latest = widthAt(current, event.clientX);
    // このフレームで既に通知を待っている: 最後の幅だけを通知する
    if (current.frame !== null) return;
    current.frame = requestAnimationFrame(() => {
      current.frame = null;
      onChange(current.latest);
    });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const grow = side === "left" ? "ArrowLeft" : "ArrowRight";
    const shrink = side === "left" ? "ArrowRight" : "ArrowLeft";
    const next = { [grow]: width + step, [shrink]: width - step, Home: min, End: max }[event.key];
    // 幅を変えないキー: 既定の動作のまま
    if (next === undefined) return;
    event.preventDefault();
    const clamped = clampWidth(next, min, max);
    onChange(clamped);
    onCommit(clamped);
  };

  return (
    // 幅を変えられる区切りは `separator` がフォーカスと操作を持つ
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={width}
      aria-valuemin={min}
      aria-valuemax={max}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      data-side={side}
      // 帯は 24px でパネルの内側に置き、指の端末は 44px にしてパネルの端の線を帯の中央に挟む
      className={cn(
        "group absolute inset-y-0 z-10 w-6 touch-none outline-none select-none max-lg:hidden pointer-coarse:w-11",
        side === "left" ? "left-0 pointer-coarse:-left-5.5" : "right-0 pointer-coarse:-right-5.5",
        cursorOf(side, width, min, max),
      )}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onLostPointerCapture={endDrag}
      onKeyDown={onKeyDown}
    >
      {/* パネルの端の線。乗せると濃く、ドラッグ中はアクセントの色にする */}
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-y-0 w-px",
          side === "left" ? "left-0 pointer-coarse:left-5.5" : "right-0 pointer-coarse:right-5.5",
          active ? "bg-mark" : "bg-transparent group-hover:bg-mark-line",
        )}
      />
      {/* 縦の中央のつまみ。ふだんは薄く、乗せると濃く、ドラッグ中とキーボードのフォーカスではアクセントの色にし、フォーカスはつまみの周りだけを囲む */}
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute top-1/2 h-8 w-1 -translate-y-1/2 rounded-full group-focus-visible:outline-2 group-focus-visible:outline-offset-2 group-focus-visible:outline-ring",
          side === "left" ? "left-1 pointer-coarse:left-5" : "right-1 pointer-coarse:right-5",
          active ? "bg-mark" : "bg-border group-hover:bg-mark-line group-focus-visible:bg-mark",
        )}
      />
    </div>
  );
};
