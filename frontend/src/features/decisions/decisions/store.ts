// 検討事項のマップのロック。タブを移っても残るように、ページを開いている間だけ画面の外に持つ（永続化しない）
import { create } from "zustand";

type DecisionMapLockState = {
  locked: string | null;
  setLocked: (id: string | null) => void;
};

const useDecisionMapLockStore = create<DecisionMapLockState>()((set) => ({
  locked: null,
  setLocked: (id) => {
    set({ locked: id });
  },
}));

/** ロックした節と、その書き換え */
export const useDecisionMapLock = (): [string | null, (id: string | null) => void] => {
  const locked = useDecisionMapLockStore((state) => state.locked);
  const setLocked = useDecisionMapLockStore((state) => state.setLocked);
  return [locked, setLocked];
};
