// 表・ボード・カードが今描いている並び（ボードは列ごと）。詳細の一覧の並びの前後に使い、URL には持たせない
import { create } from "zustand";

type ListOrderState = {
  /** 今描いている並び。表・カードは 1 つ、ボードは列の数だけ。一覧を描いていないときは空 */
  orders: readonly (readonly string[])[];
  /** 描いた並びで置き換える */
  setOrders: (orders: readonly (readonly string[])[]) => void;
  /** 画面を離れたときに空にする */
  clear: () => void;
};

export const useListOrderStore = create<ListOrderState>()((set) => ({
  orders: [],
  setOrders: (orders) => {
    set({ orders });
  },
  clear: () => {
    set({ orders: [] });
  },
}));

/** 並びの中の位置と前後 */
export type Sibling = { position: number; total: number; prev: string | null; next: string | null };

/** 開いている項目を含む並びを探し、位置・件数・前後の ID を返す。含む並びが無ければ null */
export const siblingOf = (orders: readonly (readonly string[])[], id: string): Sibling | null => {
  for (const order of orders) {
    const index = order.indexOf(id);
    if (index < 0) continue;
    return { position: index + 1, total: order.length, prev: order[index - 1] ?? null, next: order[index + 1] ?? null };
  }
  return null;
};
