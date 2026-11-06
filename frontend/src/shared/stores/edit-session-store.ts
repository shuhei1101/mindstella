// 開いている追加の入力と、直前の保存で書き込めなかった編集。画面をまたいで参照する
import { create } from "zustand";

import type { BlockedEdit } from "@/shared/core/edits";
import type { Kind } from "@/shared/core/records";

/** 開いている追加の入力。`target` はタイトルを溜めるまで null */
export type AddSession = { kind: Kind; target: string | null };

type EditSessionState = {
  adding: AddSession | null;
  blocked: BlockedEdit[];
  /** まとめて保存した件数（通知を消すと null） */
  saved: number | null;
  startAdd: (kind: Kind) => void;
  openAdded: (kind: Kind, target: string) => void;
  closeAdd: () => void;
  setBlocked: (blocked: BlockedEdit[]) => void;
  setSaved: (saved: number | null) => void;
};

export const useEditSessionStore = create<EditSessionState>()((set) => ({
  adding: null,
  blocked: [],
  saved: null,
  startAdd: (kind) => { set({ adding: { kind, target: null } }); },
  openAdded: (kind, target) => { set({ adding: { kind, target } }); },
  closeAdd: () => { set({ adding: null }); },
  setBlocked: (blocked) => { set({ blocked }); },
  setSaved: (saved) => { set({ saved }); },
}));
