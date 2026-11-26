// コメントの一覧・保存待ちのパネル・表示の設定が共有する左のパネルの外側の要素。幅と、指定したときは右端の幅の区切りを持つ
import { useEffect } from "react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { clampWidth, PanelResizer } from "@/shared/components/panel-resizer";
import { useViewportWidth } from "@/shared/hooks/use-viewport-width";
import { currentDetailWidth, currentLeftWidth, LEFT_PANEL_WIDTH, leftPanelMax, usePanelWidthStore } from "@/shared/stores/panel-width-store";

export type LeftPanelProps = Omit<ComponentPropsWithoutRef<"aside">, "children"> & {
  /** 描く要素。role="dialog" を持つパネルは section（aside は dialog の role を持てない） */
  as?: "aside" | "section";
  /** 幅の区切りの読み上げの名前。省くと区切りを描かず、幅だけを適用する */
  resizerLabel?: string;
  children: ReactNode;
};

export const LeftPanel = ({ as: Element = "aside", resizerLabel, children, style, ...rest }: LeftPanelProps) => {
  const viewport = useViewportWidth();
  const storedLeft = usePanelWidthStore((state) => state.leftWidth);
  const storedDetail = usePanelWidthStore((state) => state.detailWidth);
  const detailOpen = usePanelWidthStore((state) => state.detailOpen);
  const setLeftWidth = usePanelWidthStore((state) => state.setLeftWidth);
  const commitLeftWidth = usePanelWidthStore((state) => state.commitLeftWidth);
  const setOpen = usePanelWidthStore((state) => state.setOpen);

  // 描いている間だけ、左のパネルを開いているとストアへ知らせる（詳細パネルの上限が左のパネルの幅を引く）
  useEffect(() => {
    setOpen("left", true);
    return () => setOpen("left", false);
  }, [setOpen]);

  const resizable = viewport >= LEFT_PANEL_WIDTH.resizableFrom;
  const max = leftPanelMax(viewport, currentDetailWidth({ detailWidth: storedDetail }), detailOpen);
  const width = clampWidth(currentLeftWidth({ leftWidth: storedLeft }), LEFT_PANEL_WIDTH.min, max);

  return (
    <Element {...rest} style={resizable ? { ...style, width } : style}>
      {children}
      {resizable && resizerLabel !== undefined ? (
        <PanelResizer side="right" width={width} min={LEFT_PANEL_WIDTH.min} max={max} step={LEFT_PANEL_WIDTH.step} label={resizerLabel} onChange={setLeftWidth} onCommit={commitLeftWidth} />
      ) : null}
    </Element>
  );
};
