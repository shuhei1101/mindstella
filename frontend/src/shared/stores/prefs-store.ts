// 表の列・ピン留め・差分のミニマップ・本文の見せ方・絞り込みの条件・表示する種類・コメントの一覧のピン止め・レビュー中のコメントの並び・詳細のコメントの入力の開閉・「レビューに追加」の後のフォーカスを、`localStorage` のキーで読み書きする（インターフェース定義『SPAを開く』の制約「端末の保存領域」）
import { useSyncExternalStore } from "react";
import { create } from "zustand";

import { focusAfterAddTarget } from "@/shared/core/display";
import type { Filters } from "@/shared/core/filters";
import type { Kind } from "@/shared/core/records";
import { workspaceKey } from "@/shared/core/workspace-path";
import { PREFS_KEY } from "@/shared/stores/theme-store";

/** 種類ごとの表示する列とピン留め */
export type TablePrefs = { hidden: string[]; pinTo: string | null };

/** 画面が読み書きする `mindmap-preview` の値の項目 */
export type Prefs = {
  columns?: Record<string, TablePrefs>;
  filters?: Record<string, Filters>;
  diffSel?: string | null;
  minimap?: false | null;
  sectionFold?: false | null;
  kinds?: Kind[] | null;
  commentsPinned?: true | null;
  reviewOrder?: "oldest" | null;
  commentFormClosed?: true | null;
  /** 「レビューに追加」の後のフォーカスの上書き。null・無しは自動（端末の主な入力で決める） */
  focusAfterAdd?: "input" | "none" | null;
  /** 1 文字のショートカット（一覧の並びの前後の `j`・`k`）を使用しない上書き。null・無しは使用する */
  singleKeyShortcuts?: false | null;
};

/** 詳細の本文をスクロールした位置を残す sessionStorage のキー */
export const BODY_SCROLL_KEY = "mindmap-body-scroll";

/** そのタブで詳細の本文をスクロールした位置を読む（項目の ID → 位置。0 以上の数だけを返す） */
export const readBodyScrolls = (): Record<string, number> => {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(workspaceKey(BODY_SCROLL_KEY)) ?? "{}");
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).filter((entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] >= 0));
  } catch {
    return {};
  }
};

/** 項目の本文をスクロールした位置を残す */
export const writeBodyScroll = (id: string, top: number): void => {
  try {
    sessionStorage.setItem(workspaceKey(BODY_SCROLL_KEY), JSON.stringify({ ...readBodyScrolls(), [id]: top }));
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

const readAll = (): Record<string, unknown> => parsePrefs(localStorage.getItem(workspaceKey(PREFS_KEY)));

/** 保存領域の JSON を読み、読めない項目は持たないものとして扱う */
export const readPrefs = (): Prefs => readAll();

const listeners = new Set<() => void>();

/** 変えた項目だけを書き、ほかの項目を残す */
export const writePrefs = (patch: Partial<Prefs>): void => {
  localStorage.setItem(workspaceKey(PREFS_KEY), JSON.stringify({ ...readAll(), ...patch }));
  for (const listener of listeners) listener();
};

const subscribe = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** 描画の中で端末の保存領域を読む。書き換えると描き直す（`readPrefs` の結果は React Compiler が覚えるので描画では使わない） */
export const usePrefs = (): Prefs => parsePrefs(useSyncExternalStore(subscribe, () => localStorage.getItem(workspaceKey(PREFS_KEY))));

/** 端末の主な入力がタッチかのメディアクエリ */
const COARSE_QUERY = "(pointer: coarse)";

const subscribeCoarse = (listener: () => void): (() => void) => {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const media = window.matchMedia(COARSE_QUERY);
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
};

/** 端末の主な入力がタッチか。変わったら描き直す（matchMedia を持たない環境はタッチでない） */
export const usePointerCoarse = (): boolean =>
  useSyncExternalStore(subscribeCoarse, () => typeof window.matchMedia === "function" && window.matchMedia(COARSE_QUERY).matches);

/** 溜めた・送った後のフォーカスの移動先（上書きと端末の主な入力で決める） */
export const useFocusAfterAddTarget = (): "input" | "submit" => focusAfterAddTarget(usePrefs(), usePointerCoarse());

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
