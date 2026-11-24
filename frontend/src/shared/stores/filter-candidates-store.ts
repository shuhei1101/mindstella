// 今の画面の絞り込みの値と、値を絞り込みに加える処理を、全体の検索へ渡すストア
import { create } from "zustand";

import type { FilterGroup } from "@/shared/components/filter-drawer";

type FilterCandidatesState = {
  /** 今の画面の絞り込みの条件。並びはドロワーと同じ */
  groups: readonly FilterGroup[];
  /** 値を今の画面の絞り込みに加え、履歴に 1 つ積む処理 */
  apply: ((key: string, value: string) => void) | null;
  /** `groups` と `apply` を置き換える */
  publish: (groups: readonly FilterGroup[], apply: (key: string, value: string) => void) => void;
  /** `groups` を空、`apply` を null にする */
  clear: () => void;
};

export const useFilterCandidatesStore = create<FilterCandidatesState>()((set) => ({
  groups: [],
  apply: null,
  publish: (groups, apply) => {
    set({ groups, apply });
  },
  clear: () => {
    set({ groups: [], apply: null });
  },
}));
