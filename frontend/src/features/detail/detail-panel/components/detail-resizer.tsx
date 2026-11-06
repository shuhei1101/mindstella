// 詳細パネルの左端に置く幅の区切り。ドラッグと矢印キーで幅を変え、幅を端末に残す
import { useRef, useState } from "react";

/** 詳細パネルの幅の決まり（px） */
export const PANEL_WIDTH = { default: 640, min: 480, keepBody: 400, keepLeft: 160, step: 16, resizableFrom: 901, sideFrom: 1100 } as const;

/** 本文に残す幅を引いた上限 */
export const panelWidthMax = (viewport: number): number => viewport - (viewport >= PANEL_WIDTH.sideFrom ? PANEL_WIDTH.keepBody : PANEL_WIDTH.keepLeft);

/** 幅を下限以上・上限以下に収める */
export const clampPanelWidth = (width: number, max: number): number => Math.round(Math.max(PANEL_WIDTH.min, Math.min(width, max)));

export type DetailResizerProps = { width: number; onChange: (width: number) => void };

export const DetailResizer = ({ width, onChange }: DetailResizerProps) => {
  const drag = useRef<{ startX: number; startWidth: number } | null>(null);
  const [active, setActive] = useState(false);
  return (
    // 幅を変えられる区切りは `separator` がフォーカスと操作を持つ
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="詳細パネルの幅"
      aria-valuenow={width}
      aria-valuemin={PANEL_WIDTH.min}
      aria-valuemax={panelWidthMax(window.innerWidth)}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      className={active ? "absolute inset-y-0 left-0 w-1 cursor-col-resize bg-mark max-lg:hidden" : "absolute inset-y-0 left-0 w-1 cursor-col-resize hover:bg-mark-line max-lg:hidden"}
      onPointerDown={(event) => {
        drag.current = { startX: event.clientX, startWidth: width };
        event.currentTarget.setPointerCapture(event.pointerId);
        setActive(true);
      }}
      onPointerMove={(event) => {
        if (drag.current === null) return;
        onChange(clampPanelWidth(drag.current.startWidth + drag.current.startX - event.clientX, panelWidthMax(window.innerWidth)));
      }}
      onPointerUp={() => {
        drag.current = null;
        setActive(false);
      }}
      onKeyDown={(event) => {
        const step = { ArrowLeft: PANEL_WIDTH.step, ArrowRight: -PANEL_WIDTH.step }[event.key];
        if (step === undefined) return;
        event.preventDefault();
        onChange(clampPanelWidth(width + step, panelWidthMax(window.innerWidth)));
      }}
    />
  );
};
