// 変更履歴の既読のまとまりの ID を、ワークスペースごとに端末の保存領域（localStorage）に持つ。保存領域を使用できないときはメモリの上だけで持つ
import { useMemo } from "react";
import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import { unreadSetIds } from "@/shared/core/diff";

/** 既読のまとまりを持つ端末の保存領域のキー */
export const READ_CHANGES_KEY = "mindmap-read-changes";

type ReadChangesState = {
  /** ワークスペースの ID ごとの既読のまとまりの ID（重なりを持たない） */
  read: Record<string, string[]>;
};

/** 参照・保存できない保存領域を、例外を出さずに素通りさせる（メモリの上の状態はそのまま使用する） */
const safeStorage: StateStorage = {
  getItem: (name) => {
    try {
      return localStorage.getItem(name);
    } catch {
      return null;
    }
  },
  setItem: (name, value) => {
    try {
      localStorage.setItem(name, value);
    } catch {
      // 保存できない: このタブの中だけで既読を持つ
    }
  },
  removeItem: (name) => {
    try {
      localStorage.removeItem(name);
    } catch {
      // 削除できない: 次に保存できたときに上書きする
    }
  },
};

const useReadChangesStore = create<ReadChangesState>()(persist(() => ({ read: {} }), { name: READ_CHANGES_KEY, storage: createJSONStorage(() => safeStorage) }));

// ほかのタブが既読を書き換えたら読み直す（書き込みで相手の既読を上書きしない）
window.addEventListener("storage", (event) => {
  if (event.key === READ_CHANGES_KEY) void useReadChangesStore.persist.rehydrate();
});

/** 指定したまとまりの ID をそのワークスペースの既読に加える */
export const markRead = (workspace: string, ids: readonly string[]): void => {
  useReadChangesStore.setState((state) => {
    const current = state.read[workspace] ?? [];
    const added = ids.filter((id, index) => !current.includes(id) && ids.indexOf(id) === index);
    if (added.length === 0) return state;
    return { read: { ...state.read, [workspace]: [...current, ...added] } };
  });
};

/** 記録に無いまとまりの ID をそのワークスペースの既読から削除する（変わらなければ書き換えない） */
export const prune = (workspace: string, ids: readonly string[]): void => {
  useReadChangesStore.setState((state) => {
    const current = state.read[workspace];
    if (current === undefined) return state;
    const known = new Set(ids);
    const kept = current.filter((id) => known.has(id));
    if (kept.length === current.length) return state;
    return { read: { ...state.read, [workspace]: kept } };
  });
};

/** 記録のまとまり（新しい順）のうち、既読に無いものの ID を並びの順で返却する */
export const useUnreadSetIds = (workspace: string, setIds: readonly string[]): string[] => {
  const read = useReadChangesStore((state) => state.read[workspace]);
  return useMemo(() => unreadSetIds(setIds, read ?? []), [setIds, read]);
};
