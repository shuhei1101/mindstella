// 画面ごとの絞り込みの条件・タグの組み合わせ方・変更履歴で選んだ時点と、一覧のスクロール位置を、そのタブの `sessionStorage` で読み書きする
import { useSyncExternalStore } from "react";

import { isEmbedded } from "@/shared/core/embedded";
import type { Filters, TagMatch } from "@/shared/core/filters";
import { workspaceKey } from "@/shared/core/workspace-path";
import { PREFS_KEY } from "@/shared/stores/theme-store";

/** 絞り込みの条件・タグの組み合わせ方・選んだ時点を持つ sessionStorage のキー */
export const SCREEN_STATE_KEY = "mindmap-filters";

/** 一覧のスクロール位置を持つ sessionStorage のキー */
export const LIST_SCROLL_KEY = "mindmap-list-scroll";

/** 端末の保存領域から消す、前の版が持っていた項目 */
const LEGACY_KEYS = ["filters", "diffSel"] as const;

/** 画面の一時的な状態 */
export type ScreenState = {
  filters?: Record<string, Filters>;
  tagMatch?: Record<string, TagMatch>;
  diffSel?: string | null;
};

/** 一覧のスクロール位置 */
export type ListScroll = { top: number; left: number };

/** 保存領域を使えない環境・配る書き出しで、開いている間だけ持つ値 */
let memory: ScreenState = {};

const listeners = new Set<() => void>();

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

/** 読んだ値のうち、構造の合う項目だけを残す */
const sanitize = (value: unknown): ScreenState => {
  if (!isRecord(value)) return {};
  const state: ScreenState = {};
  if (isRecord(value["filters"])) {
    state.filters = Object.fromEntries(
      Object.entries(value["filters"]).filter((entry): entry is [string, Filters] => isRecord(entry[1]) && Object.values(entry[1]).every((values) => Array.isArray(values) && values.every((item) => typeof item === "string"))),
    );
  }
  if (isRecord(value["tagMatch"])) {
    state.tagMatch = Object.fromEntries(Object.entries(value["tagMatch"]).filter((entry): entry is [string, TagMatch] => entry[1] === "all" || entry[1] === "any"));
  }
  if (typeof value["diffSel"] === "string" || value["diffSel"] === null) state.diffSel = value["diffSel"];
  return state;
};

/** 保存領域の JSON の文字列を読む。読めない・使えないときは null */
const readText = (): string | null => {
  try {
    return sessionStorage.getItem(workspaceKey(SCREEN_STATE_KEY));
  } catch {
    return null;
  }
};

const parse = (text: string | null): ScreenState => {
  if (text === null) return {};
  try {
    return sanitize(JSON.parse(text));
  } catch {
    return {};
  }
};

/** 保存領域を使える環境か（配る書き出しでは使わない） */
const usesStorage = (): boolean => {
  if (isEmbedded()) return false;
  try {
    return typeof sessionStorage !== "undefined";
  } catch {
    return false;
  }
};

/** 画面の一時的な状態を読む。読めない項目は持たないものとして扱う */
export const readScreenState = (): ScreenState => (usesStorage() ? parse(readText()) : memory);

/** 変えた項目だけを書き、ほかの項目を残して購読へ知らせる */
export const writeScreenState = (patch: Partial<ScreenState>): void => {
  const next = { ...readScreenState(), ...patch };
  if (usesStorage()) {
    try {
      sessionStorage.setItem(workspaceKey(SCREEN_STATE_KEY), JSON.stringify(next));
    } catch {
      // 書けない保存領域: 開いている間だけ持つ
      memory = next;
    }
  } else {
    memory = next;
  }
  for (const listener of listeners) listener();
};

const subscribe = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** 購読の変化を見分ける値（保存領域の文字列とメモリの値の組）。配る書き出しかは描画の中で決める */
const snapshot = (): string => JSON.stringify([readText(), memory]);

/** 購読の値から画面の一時的な状態を取り出す */
const fromSnapshot = (value: string): ScreenState => {
  const [text, held] = JSON.parse(value) as [string | null, ScreenState];
  return usesStorage() ? parse(text) : held;
};

/** 描画の中で画面の一時的な状態を参照する。書き換えると描き直す（`readScreenState` の結果は React Compiler が覚えるので描画では使わない） */
export const useScreenState = (): ScreenState => fromSnapshot(useSyncExternalStore(subscribe, snapshot));

/** 端末の保存領域に残った絞り込みの条件と選んだ時点を、参照せずに削除する */
export const dropLegacyScreenState = (): void => {
  const key = workspaceKey(PREFS_KEY);
  try {
    const text = localStorage.getItem(key);
    if (text === null) return;
    const value: unknown = JSON.parse(text);
    if (!isRecord(value) || !LEGACY_KEYS.some((name) => name in value)) return;
    localStorage.setItem(key, JSON.stringify(Object.fromEntries(Object.entries(value).filter(([name]) => !(LEGACY_KEYS as readonly string[]).includes(name)))));
  } catch {
    // 読めない・書けない保存領域: 何もしない
  }
};

const isScroll = (value: unknown): value is ListScroll =>
  isRecord(value) && typeof value["top"] === "number" && typeof value["left"] === "number" && value["top"] >= 0 && value["left"] >= 0;

/** 一覧のスクロール位置の全てを読む（構造の合う位置だけ） */
const readScrolls = (): Record<string, ListScroll> => {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(workspaceKey(LIST_SCROLL_KEY)) ?? "{}");
    if (!isRecord(value)) return {};
    return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, ListScroll] => isScroll(entry[1])));
  } catch {
    return {};
  }
};

/** `{画面}:{表示形式}` のキーのスクロール位置を読む。無い・読めないときは null */
export const readListScroll = (key: string): ListScroll | null => readScrolls()[key] ?? null;

/** `{画面}:{表示形式}` のキーのスクロール位置を残し、ほかのキーの位置を残す */
export const writeListScroll = (key: string, position: ListScroll): void => {
  try {
    sessionStorage.setItem(workspaceKey(LIST_SCROLL_KEY), JSON.stringify({ ...readScrolls(), [key]: position }));
  } catch {
    // 書けない保存領域では残さない
  }
};
