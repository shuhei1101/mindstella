// 左のパネルと詳細パネルの幅と開いているか。確定した幅だけをそのタブの sessionStorage に残す
import { create } from "zustand";

import { clampWidth } from "@/shared/components/panel-resizer";
import { workspaceKey } from "@/shared/core/workspace-path";

/** 左のパネル（コメントの一覧・保存待ちのパネル・表示の設定）の幅の決まり（px） */
export const LEFT_PANEL_WIDTH = { default: 384, min: 320, keepBody: 400, step: 16, resizableFrom: 901 } as const;

/** 詳細パネルの幅の決まり（px） */
export const DETAIL_PANEL_WIDTH = { default: 640, min: 480, keepBody: 400, keepLeft: 160, step: 16, resizableFrom: 901, sideFrom: 1100 } as const;

/** 左のパネルの幅を残す sessionStorage のキー（workspaceKey で末尾にワークスペースの ID を付ける） */
export const LEFT_PANEL_WIDTH_KEY = "mindmap-left-panel-width";

/** 詳細パネルの幅を残す sessionStorage のキー（workspaceKey で末尾にワークスペースの ID を付ける） */
export const PANEL_WIDTH_KEY = "mindmap-panel-width";

/** sessionStorage の値が正の整数ならその数、無いか正の整数でなければ fallback */
export const readStoredWidth = (key: string, fallback: number): number => {
  const saved = sessionStorage.getItem(workspaceKey(key));
  return saved !== null && /^[1-9]\d*$/.test(saved) ? Number(saved) : fallback;
};

/** 確定した幅を残す。保存できない（容量・権限）ときは画面に適用した幅だけで続ける */
const storeWidth = (key: string, width: number): void => {
  try {
    sessionStorage.setItem(workspaceKey(key), String(width));
  } catch (error) {
    console.warn("パネルの幅を保存できませんでした", error);
  }
};

/** 詳細パネルの上限（表示の幅が sideFrom 以上なら本文と開いている左のパネルの幅を残し、未満なら左に keepLeft を残す） */
export const detailPanelMax = (viewport: number, leftWidth: number, leftOpen: boolean): number => {
  const max = viewport >= DETAIL_PANEL_WIDTH.sideFrom ? viewport - DETAIL_PANEL_WIDTH.keepBody - (leftOpen ? leftWidth : 0) : viewport - DETAIL_PANEL_WIDTH.keepLeft;
  return Math.max(max, DETAIL_PANEL_WIDTH.min);
};

/** 左のパネルの上限（本文の幅を残し、表示の幅が sideFrom 以上で詳細パネルを開いていれば、左のパネルを引かない上限で収めた詳細パネルの幅も残す） */
export const leftPanelMax = (viewport: number, detailWidth: number, detailOpen: boolean): number => {
  const beside = viewport >= DETAIL_PANEL_WIDTH.sideFrom && detailOpen;
  const detail = beside ? clampWidth(detailWidth, DETAIL_PANEL_WIDTH.min, detailPanelMax(viewport, 0, false)) : 0;
  return Math.max(viewport - LEFT_PANEL_WIDTH.keepBody - detail, LEFT_PANEL_WIDTH.min);
};

type PanelSide = "left" | "detail";

type PanelWidthState = {
  /** このタブで適用した左のパネルの幅（null の間は保存領域の値） */
  leftWidth: number | null;
  /** このタブで適用した詳細パネルの幅（null の間は保存領域の値） */
  detailWidth: number | null;
  leftOpen: boolean;
  detailOpen: boolean;
  setLeftWidth: (width: number) => void;
  commitLeftWidth: (width: number) => void;
  setDetailWidth: (width: number) => void;
  commitDetailWidth: (width: number) => void;
  setOpen: (side: PanelSide, open: boolean) => void;
};

export const usePanelWidthStore = create<PanelWidthState>()((set) => ({
  leftWidth: null,
  detailWidth: null,
  leftOpen: false,
  detailOpen: false,
  setLeftWidth: (width) => set({ leftWidth: width }),
  commitLeftWidth: (width) => {
    set({ leftWidth: width });
    storeWidth(LEFT_PANEL_WIDTH_KEY, width);
  },
  setDetailWidth: (width) => set({ detailWidth: width }),
  commitDetailWidth: (width) => {
    set({ detailWidth: width });
    storeWidth(PANEL_WIDTH_KEY, width);
  },
  setOpen: (side, open) => set(side === "left" ? { leftOpen: open } : { detailOpen: open }),
}));

/** 左のパネルの今の幅（まだ適用していなければ保存領域の値） */
export const currentLeftWidth = (state: Pick<PanelWidthState, "leftWidth">): number => state.leftWidth ?? readStoredWidth(LEFT_PANEL_WIDTH_KEY, LEFT_PANEL_WIDTH.default);

/** 詳細パネルの今の幅（まだ適用していなければ保存領域の値） */
export const currentDetailWidth = (state: Pick<PanelWidthState, "detailWidth">): number => state.detailWidth ?? readStoredWidth(PANEL_WIDTH_KEY, DETAIL_PANEL_WIDTH.default);
