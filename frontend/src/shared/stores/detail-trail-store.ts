// 詳細パネルと全画面の中で見てきた項目の履歴。戻る・進むを押せるかを決める
import { create } from "zustand";

type DetailTrailState = {
  items: string[];
  position: number;
  /** 開いた項目を履歴に当てる。隣の項目なら位置だけを動かす */
  visit: (id: string | undefined) => void;
};

export const useDetailTrailStore = create<DetailTrailState>()((set) => ({
  items: [],
  position: -1,
  visit: (id) => {
    set(({ items, position }) => {
      if (id === undefined) return { items: [], position: -1 };
      if (items[position] === id) return { items, position };
      if (items[position - 1] === id) return { items, position: position - 1 };
      if (items[position + 1] === id) return { items, position: position + 1 };
      return { items: [...items.slice(0, position + 1), id], position: position + 1 };
    });
  },
}));
