// ライト / ダーク。今の画面と同じ端末の保存領域のキーの `theme` だけを読み書きし、他のキーは残す
import { create } from "zustand";

export type Theme = "light" | "dark";

/** 端末の保存領域のキー（今の画面と同じ） */
export const PREFS_KEY = "mindmap-preview";

/** 保存領域の値の JSON（読めなければ空） */
const readPrefs = (): Record<string, unknown> => {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}");
    return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
  } catch {
    return {};
  }
};

/** 保存領域の `theme`、無ければ OS の設定 */
const initialTheme = (): Theme => {
  const saved = readPrefs()["theme"];
  if (saved === "light" || saved === "dark") return saved;
  // matchMedia を持たない環境（jsdom）はライト
  const prefersDark = typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
};

/** 文書にテーマを当てる */
const applyTheme = (theme: Theme): void => {
  document.documentElement.dataset["theme"] = theme;
};

type ThemeState = {
  theme: Theme;
  /** テーマを書き換え、保存領域の `theme` だけを書き換えて残す */
  setTheme: (theme: Theme) => void;
  /** 保存領域の `theme` を外し、OS の設定のテーマに戻す */
  clearTheme: () => void;
};

export const useThemeStore = create<ThemeState>()((set) => {
  const theme = initialTheme();
  applyTheme(theme);
  return {
    theme,
    setTheme: (next) => {
      localStorage.setItem(PREFS_KEY, JSON.stringify({ ...readPrefs(), theme: next }));
      applyTheme(next);
      set({ theme: next });
    },
    clearTheme: () => {
      localStorage.setItem(PREFS_KEY, JSON.stringify({ ...readPrefs(), theme: null }));
      const next = initialTheme();
      applyTheme(next);
      set({ theme: next });
    },
  };
});
