// 図の拡大（画面設計『図の拡大.tsx』）。ホイールで拡大・縮小し、枠のスクロールで動かす。図の文字は選んでコピーできる
import { useState } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";

const WHEEL_FACTOR = 1.12;
const SCALE = { min: 0.25, max: 8 };

export type DiagramViewerProps = { svg: string; onClose: () => void };

export const DiagramViewer = ({ svg, onClose }: DiagramViewerProps) => {
  const [scale, setScale] = useState(1);
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="flex h-full max-w-none flex-col gap-2">
        <div className="flex items-center gap-2">
          <DialogTitle className="text-small font-semibold">図の拡大</DialogTitle>
          <Button variant="ghost" size="icon" aria-label="閉じる" className="ml-auto" onClick={onClose}>
            <Icon name="x" />
          </Button>
        </div>
        <div
          className="min-h-0 flex-1 overflow-auto"
          onWheel={(event) => {
            if (event.deltaY === 0) return;
            setScale(Math.min(SCALE.max, Math.max(SCALE.min, scale * (event.deltaY < 0 ? WHEEL_FACTOR : 1 / WHEEL_FACTOR))));
          }}
        >
          {/* mermaid が描いた SVG をそのまま置く */}
          <div className="origin-top-left select-text" style={{ transform: `scale(${String(scale)})` }} dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      </DialogContent>
    </Dialog>
  );
};
