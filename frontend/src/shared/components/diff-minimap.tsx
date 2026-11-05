// 差分のミニマップ（部品設計『差分のミニマップ.tsx』）。本文のスクロール領域を包み、変わった箇所の印の帯を並べる
import { useEffect, useRef, type ReactNode } from "react";

import { attachMinimap } from "@/shared/core/minimap";

export type DiffMinimapProps = {
  shown: boolean;
  children: ReactNode;
  /** 開いたときに戻す本文のスクロール位置 */
  initialScrollTop?: number | undefined;
  /** 本文をスクロールした */
  onBodyScroll?: ((top: number) => void) | undefined;
};

export const DiffMinimap = ({ shown, children, initialScrollTop, onBodyScroll }: DiffMinimapProps) => {
  const frame = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!shown || frame.current === null || body.current === null) return undefined;
    return attachMinimap({ frame: frame.current, body: body.current });
  }, [shown]);
  // 本文を描いた次のコマで戻す
  useEffect(() => {
    if (initialScrollTop === undefined) return undefined;
    const handle = requestAnimationFrame(() => {
      if (body.current !== null) body.current.scrollTop = initialScrollTop;
    });
    return () => {
      cancelAnimationFrame(handle);
    };
    // 開いたときに 1 度だけ戻す
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div ref={frame} className="panel-scroll">
      <div ref={body} className="panel-body" onScroll={(event) => { onBodyScroll?.(event.currentTarget.scrollTop); }}>
        {children}
      </div>
    </div>
  );
};
