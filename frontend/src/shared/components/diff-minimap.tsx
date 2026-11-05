// 差分のミニマップ（部品設計『差分のミニマップ.tsx』）。本文のスクロール領域を包み、変わった箇所の印の帯を並べる
import { useEffect, useRef, type ReactNode } from "react";

import { attachMinimap } from "@/shared/core/minimap";

export type DiffMinimapProps = { shown: boolean; children: ReactNode };

export const DiffMinimap = ({ shown, children }: DiffMinimapProps) => {
  const frame = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!shown || frame.current === null || body.current === null) return undefined;
    return attachMinimap({ frame: frame.current, body: body.current });
  }, [shown]);
  return (
    <div ref={frame} className="panel-scroll">
      <div ref={body} className="panel-body">
        {children}
      </div>
    </div>
  );
};
