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
  // 本文を描いた次のコマで戻す。ライブラリや図の読み込みで本文が後から伸びるので、位置に届くまで伸びるたびに戻し直す。利用者が動かしたら戻すのをやめる
  useEffect(() => {
    const element = body.current;
    if (initialScrollTop === undefined || element === null) return undefined;
    const restore = (): void => {
      element.scrollTop = initialScrollTop;
      if (Math.abs(element.scrollTop - initialScrollTop) < 1) stop();
    };
    const resized = new ResizeObserver(restore);
    const stop = (): void => {
      resized.disconnect();
      element.removeEventListener("wheel", stop);
      element.removeEventListener("pointerdown", stop);
      element.removeEventListener("keydown", stop);
    };
    for (const child of element.children) resized.observe(child);
    element.addEventListener("wheel", stop, { passive: true });
    element.addEventListener("pointerdown", stop);
    element.addEventListener("keydown", stop);
    const handle = requestAnimationFrame(restore);
    return () => {
      cancelAnimationFrame(handle);
      stop();
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
