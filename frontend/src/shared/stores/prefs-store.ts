// 表の列・ピン留め・差分のミニマップ・本文の差分の並べ方・本文の見せ方・絞り込みの条件を、今の画面と同じ `localStorage` のキーで読み書きする（インターフェース定義『SPAを開く』の制約「端末の保存領域」）
import { useSyncExternalStore } from "react";
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

/** 詳細の本文をスクロールした位置を残す sessionStorage のキー（今の画面と同じ） */
export const BODY_SCROLL_KEY = "mindmap-body-scroll";

/** そのタブで詳細の本文をスクロールした位置を読む（項目の ID → 位置。0 以上の数だけを返す） */
export const readBodyScrolls = (): Record<string, number> => {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(BODY_SCROLL_KEY) ?? "{}");
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).filter((entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] >= 0));
  } catch {
    return {};
  }
};

/** 項目の本文をスクロールした位置を残す */
export const writeBodyScroll = (id: string, top: number): void => {
  try {
    sessionStorage.setItem(BODY_SCROLL_KEY, JSON.stringify({ ...readBodyScrolls(), [id]: top }));
  } catch {
    // 書けない保存領域では残さない
  }
};

/** 保存領域の JSON の文字列を読む（読めなければ空） */
const parsePrefs = (text: string | null): Record<string, unknown> => {
  try {
    const value: unknown = JSON.parse(text ?? "{}");
    return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
  } catch {
    return {};
  }
};

const readAll = (): Record<string, unknown> => parsePrefs(localStorage.getItem(PREFS_KEY));

/** 保存領域の JSON を読み、読めない項目は持たないものとして扱う */
export const readPrefs = (): Prefs => readAll();

const listeners = new Set<() => void>();

/** 変えた項目だけを書き、ほかの項目を残す */
export const writePrefs = (patch: Partial<Prefs>): void => {
  localStorage.setItem(PREFS_KEY, JSON.stringify({ ...readAll(), ...patch }));
  for (const listener of listeners) listener();
};

const subscribe = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** 描画の中で端末の保存領域を読む。書き換えると描き直す（`readPrefs` の結果は React Compiler が覚えるので描画では使わない） */
export const usePrefs = (): Prefs => parsePrefs(useSyncExternalStore(subscribe, () => localStorage.getItem(PREFS_KEY)));

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
