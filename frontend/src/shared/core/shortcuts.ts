// ショートカットの定義（ID・キー・説明・スコープ）。部品にキーを書かず、`useShortcut` が ID から引く

export type ShortcutDefinition = {
  /** `@tanstack/react-hotkeys` の表記のキー */
  key: "Mod+K" | "K" | "J";
  description: string;
  scope: string;
  /** 修飾キーを持たない 1 文字のキーか（表示の設定の「1 文字のショートカット」でオフにできる） */
  singleKey: boolean;
};

export const SHORTCUTS = {
  "search.open": { key: "Mod+K", description: "全体の検索を開く", scope: "アプリ全体", singleKey: false },
  "item.prev": { key: "K", description: "一覧の前の項目", scope: "詳細", singleKey: true },
  "item.next": { key: "J", description: "一覧の次の項目", scope: "詳細", singleKey: true },
} as const satisfies Record<string, ShortcutDefinition>;

export type ShortcutId = keyof typeof SHORTCUTS;
