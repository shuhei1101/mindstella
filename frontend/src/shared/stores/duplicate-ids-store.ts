// 変更の検知が知らせた重なった ID と、利用者が閉じたときの集まり（インターフェース定義『書き換えの知らせ』の `event: duplicate_ids`）
import { create } from "zustand";

type DuplicateIdsState = {
  /** 最後に受けた重なった ID */
  ids: string[];
  /** 閉じたときの ID の集まり。`ids` が同じ間は通知を出さない */
  dismissed: string[] | null;
  /** 受けた ID に書き換え、閉じたときの集まりと違えば `dismissed` を null に戻す */
  setIds: (ids: string[]) => void;
  /** 今の `ids` を `dismissed` にする */
  dismiss: () => void;
};

/** 2 つの ID の並びが同じか */
const sameIds = (a: readonly string[], b: readonly string[]): boolean => a.length === b.length && a.every((id, index) => id === b[index]);

export const useDuplicateIdsStore = create<DuplicateIdsState>()((set) => ({
  ids: [],
  dismissed: null,
  setIds: (ids) => {
    set((state) => ({ ids, dismissed: state.dismissed !== null && sameIds(state.dismissed, ids) ? state.dismissed : null }));
  },
  dismiss: () => {
    set((state) => ({ dismissed: [...state.ids] }));
  },
}));

/** トップバーの `duplicateIds` に渡す ID（閉じた集まりと同じ間は空） */
export const useShownDuplicateIds = (): string[] =>
  useDuplicateIdsStore((state) => (state.dismissed !== null && sameIds(state.dismissed, state.ids) ? EMPTY : state.ids));

/** 通知を出さないときに返す、同じ空の並び（描き直しを繰り返さない） */
const EMPTY: string[] = [];
