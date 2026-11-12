// ネットワークのロック。画面を離れても残るように、ページを開いている間だけ画面の外に持つ（永続化しない）
import { create } from "zustand";

type GraphLockState = {
  locked: string | null;
  setLocked: (id: string | null) => void;
};

const useGraphLockStore = create<GraphLockState>()((set) => ({
  locked: null,
  setLocked: (id) => {
    set({ locked: id });
  },
}));

/** ロックした項目と、その書き換え */
export const useGraphLock = (): [string | null, (id: string | null) => void] => {
  const locked = useGraphLockStore((state) => state.locked);
  const setLocked = useGraphLockStore((state) => state.setLocked);
  return [locked, setLocked];
};
