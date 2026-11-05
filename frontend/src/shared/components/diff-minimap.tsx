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
  // 利用者が動かすまで、本文が描き直されても位置を戻し続ける（ライブラリや図の読み込みで本文は後から伸び縮みする）
  const restoring = useRef(initialScrollTop !== undefined);
  useEffect(() => {
    const element = body.current;
    const outer = frame.current;
    if (initialScrollTop === undefined || element === null || outer === null) return undefined;
    const restore = (): void => {
      element.scrollTop = initialScrollTop;
    };
    const resized = new ResizeObserver(restore);
    const watchChildren = (): void => {
      for (const child of element.querySelectorAll(":scope > *, :scope > * > *")) resized.observe(child);
      restore();
    };
    const mutated = new MutationObserver(watchChildren);
    const stop = (): void => {
      restoring.current = false;
      resized.disconnect();
      mutated.disconnect();
      outer.removeEventListener("wheel", stop);
      outer.removeEventListener("pointerdown", stop);
      outer.removeEventListener("keydown", stop);
    };
    mutated.observe(element, { childList: true, subtree: true });
    outer.addEventListener("wheel", stop, { passive: true });
    outer.addEventListener("pointerdown", stop);
    outer.addEventListener("keydown", stop);
    const handle = requestAnimationFrame(watchChildren);
    return () => {
      cancelAnimationFrame(handle);
      stop();
    };
    // 開いたときに 1 度だけ始める
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div ref={frame} className="panel-scroll">
      <div ref={body} className="panel-body" onScroll={(event) => { if (!restoring.current) onBodyScroll?.(event.currentTarget.scrollTop); }}>
        {children}
      </div>
    </div>
  );
};
