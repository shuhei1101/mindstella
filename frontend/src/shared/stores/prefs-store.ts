// 表の列・ピン留め・差分のミニマップ・本文の差分の並べ方・本文の見せ方・絞り込みの条件を、今の画面と同じ `localStorage` のキーで読み書きする（インターフェース定義『SPAを開く』の制約「端末の保存領域」）
import { create } from "zustand";

import type { Filters } from "@/shared/core/filters";
import type { Kind } from "@/shared/core/records";
import { PREFS_KEY } from "@/shared/stores/theme-store";

/** 種類ごとの表示する列とピン留め */
export type TablePrefs = { hidden: string[]; pinTo: string | null };

/** 移す画面が読み書きする、今の画面の `Prefs` の項目 */
export type Prefs = {
  columns?: Record<string, TablePrefs>;
  filters?: Record<string, Filters>;
  diffSel?: string | null;
  minimap?: false | null;
  bodyLayout?: "side" | null;
  tablePin?: false | null;
  tableHead?: false | null;
  tableStripes?: true | null;
  sectionFold?: false | null;
  kinds?: Kind[] | null;
};

/** 保存領域の値の JSON（読めなければ空） */
const readAll = (): Record<string, unknown> => {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}");
    return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
  } catch {
    return {};
  }
};

/** 保存領域の JSON を読み、読めない項目は持たないものとして扱う */
export const readPrefs = (): Prefs => readAll();

/** 変えた項目だけを書き、ほかの項目を残す */
export const writePrefs = (patch: Partial<Prefs>): void => {
  localStorage.setItem(PREFS_KEY, JSON.stringify({ ...readAll(), ...patch }));
};

type PrefsState = {
  prefs: Prefs;
  /** 項目を書き換え、保存領域に残す */
  update: (patch: Partial<Prefs>) => void;
};

export const usePrefsStore = create<PrefsState>()((set) => ({
  prefs: readPrefs(),
  update: (patch) => {
    writePrefs(patch);
    set({ prefs: readPrefs() });
  },
}));
