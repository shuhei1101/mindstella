// 図の拡大（画面設計『図の拡大.tsx』）。ホイールで拡大・縮小し、背景のドラッグで動かす。Raw で記法を出し、差分の表示の間は詳細パネルと同じ色・凡例・行の差分を出す
import { useCallback, useEffect, useRef, useState, type PointerEvent } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { DomHost } from "@/shared/components/dom-host";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import { rawDiffLines } from "@/shared/core/body-render";
import { diffLineParts, LINE_DIFF_TIMEOUT_MS, type JsDiff } from "@/shared/core/diff";
import { h } from "@/shared/core/dom-parts";
import { cn } from "@/shared/lib/cn";

const SCALE = { min: 0.2, max: 6, button: 1.25, wheel: 1.12, fitMax: 3 };

/** 開いたときに図の周りに空ける余白（px） */
const FIT_MARGIN = 64;

/** 図の文字・ボタンの上では、ドラッグの代わりに選択とクリックを受ける */
const NO_DRAG_SELECTOR = "button, text, foreignObject, .nodeLabel, .edgeLabel, .label";

const withNewline = (text: string): string => (text.endsWith("\n") ? text : `${text}\n`);

export type DiagramViewerProps = {
  svg: string;
  /** 図の記法。あるとき Raw を置く */
  source?: string | null;
  /** 差分の表示の間、その図の前の版の記法 */
  beforeSource?: string | null;
  /** 詳細パネルの図の凡例と「消したもの」の HTML（プレビューが組み立てる） */
  notes?: string | null;
  /** 色を付けない種類の図に枠を付けるか */
  framed?: boolean;
  onClose: () => void;
};

export const DiagramViewer = ({ svg, source = null, beforeSource = null, notes = null, framed = false, onClose }: DiagramViewerProps) => {
  const { status, library } = useLibrary("jsdiff");
  // Dialog は portal へ描くので、窓の要素を受け取ってから配置する
  const [canvas, setCanvas] = useState<HTMLDivElement | null>(null);
  const stage = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const [raw, setRaw] = useState(false);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const zoomAt = useCallback((factor: number, originX: number, originY: number): void => {
    setView((current) => {
      const scale = Math.max(SCALE.min, Math.min(SCALE.max, current.scale * factor));
      return { scale, x: originX - (originX - current.x) * (scale / current.scale), y: originY - (originY - current.y) * (scale / current.scale) };
    });
  }, []);
  const centerZoom = (factor: number): void => {
    const box = canvas?.getBoundingClientRect();
    if (box !== undefined) zoomAt(factor, box.width / 2, box.height / 2);
  };
  useEffect(() => {
    const element = canvas;
    if (element === null) return undefined;
    const onWheel = (event: WheelEvent): void => {
      event.preventDefault();
      const box = element.getBoundingClientRect();
      zoomAt(event.deltaY < 0 ? SCALE.wheel : 1 / SCALE.wheel, event.clientX - box.left, event.clientY - box.top);
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    // 開いたときは、窓に収まる大きさで中央に置く
    const copy = stage.current?.querySelector("svg");
    const box = copy?.viewBox.baseVal;
    if (copy !== null && copy !== undefined && box !== undefined && box.width > 0) {
      copy.removeAttribute("style");
      copy.setAttribute("width", String(box.width));
      copy.setAttribute("height", String(box.height));
    }
    let placed = false;
    const observer = new ResizeObserver(() => {
      if (placed || element.clientWidth === 0 || copy === null || copy === undefined) return;
      placed = true;
      const frame = element.getBoundingClientRect();
      const width = box?.width ?? copy.clientWidth;
      const height = box?.height ?? copy.clientHeight;
      if (width === 0 || height === 0) return;
      const scale = Math.min(SCALE.fitMax, (frame.width - FIT_MARGIN) / width, (frame.height - FIT_MARGIN) / height);
      setView({ scale, x: (frame.width - width * scale) / 2, y: (frame.height - height * scale) / 2 });
    });
    observer.observe(element);
    return () => {
      element.removeEventListener("wheel", onWheel);
      observer.disconnect();
    };
  }, [canvas, zoomAt]);
  const createRaw = useCallback(() => {
    const pre = h({ tag: "pre", attrs: { class: "dg-raw", tabindex: "0", role: "region", "aria-label": "図の記法" }, children: [source ?? ""] });
    if (beforeSource === null || status !== "ready" || source === null) return { node: pre };
    const parts = diffLineParts(withNewline(beforeSource), withNewline(source), library as JsDiff);
    if (parts === null) return { node: pre };
    pre.classList.add("df-raw");
    pre.replaceChildren(...rawDiffLines({ parts, deadline: performance.now() + LINE_DIFF_TIMEOUT_MS }));
    return { node: pre };
  }, [source, beforeSource, status, library]);
  const onPointerDown = (event: PointerEvent<HTMLDivElement>): void => {
    if ((event.target as Element).closest(NO_DRAG_SELECTOR) !== null) return;
    event.preventDefault();
    drag.current = { x: event.clientX - view.x, y: event.clientY - view.y };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: PointerEvent<HTMLDivElement>): void => {
    const start = drag.current;
    if (start !== null) setView({ ...view, x: event.clientX - start.x, y: event.clientY - start.y });
  };
  const release = (): void => {
    drag.current = null;
  };
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className={cn("flex h-full max-w-none flex-col gap-2", framed && "df-frame")}>
        <DialogTitle className="sr-only">図の拡大</DialogTitle>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label="縮小" onClick={() => { centerZoom(1 / SCALE.button); }}>
            −
          </Button>
          <span className="w-12 text-center font-mono text-small">{`${String(Math.round(view.scale * 100))}%`}</span>
          <Button variant="ghost" size="icon" aria-label="拡大" onClick={() => { centerZoom(SCALE.button); }}>
            ＋
          </Button>
          {source === null ? null : (
            <Button variant="ghost" aria-pressed={raw} className="ml-auto" onClick={() => { setRaw(!raw); }}>
              Raw
            </Button>
          )}
          <Button variant="ghost" aria-label="本文へ戻る" className={cn(source === null && "ml-auto")} onClick={onClose}>
            <Icon name="back" />
            <span className="max-xs:hidden">本文へ戻る</span>
          </Button>
        </div>
        {/* 背景のドラッグはポインターの操作で、拡大と Raw のボタンがキーボードの手段になる */}
        { }
        <div ref={setCanvas} hidden={raw} className="relative min-h-0 flex-1 cursor-grab touch-none overflow-hidden" onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={release} onPointerCancel={release}>
          {/* mermaid が描いた SVG をそのまま置く */}
          <div ref={stage} className="absolute top-0 left-0 origin-top-left select-text" style={{ transform: `translate(${String(view.x)}px, ${String(view.y)}px) scale(${String(view.scale)})` }} dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
        {raw ? <DomHost create={createRaw} className="min-h-0 flex-1 overflow-auto" /> : null}
        {notes === null ? null : <div dangerouslySetInnerHTML={{ __html: notes }} />}
      </DialogContent>
    </Dialog>
  );
};
