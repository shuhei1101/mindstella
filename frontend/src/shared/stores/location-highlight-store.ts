// コメントの一覧（レビュー中の書き込みの行・スレッドの向けた項目）から開いた項目の中で示す箇所
import { create } from "zustand";

import type { Location } from "@/shared/core/records";

type LocationHighlightState = {
  /** 示す箇所と、その箇所を持つ項目の ID */
  highlight: { target: string; loc: Location } | null;
};

const useLocationHighlightStore = create<LocationHighlightState>()(() => ({ highlight: null }));

/** 開いている項目の中で示す箇所（別の項目の箇所は返さない） */
export const useLocationHighlight = (id: string): Location | null => useLocationHighlightStore((state) => (state.highlight?.target === id ? state.highlight.loc : null));

/** 項目を開く前に、その項目の中で示す箇所を控える（箇所を持たない書き込みは控えを外す） */
export const showLocation = ({ target, loc }: { target: string; loc: Location | null }): void => {
  useLocationHighlightStore.setState({ highlight: loc === null ? null : { target, loc } });
};
