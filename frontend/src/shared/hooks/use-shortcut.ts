// ショートカットの定義の ID からキーを引き、`@tanstack/react-hotkeys` で受ける薄いフック。部品から `useHotkey` を直接呼ばない
import { useHotkey } from "@tanstack/react-hotkeys";

import { SHORTCUTS, type ShortcutId } from "@/shared/core/shortcuts";
import { usePrefs } from "@/shared/stores/prefs-store";

export type ShortcutState = {
  /** 今キーを受けているか */
  active: boolean;
  /** `aria-keyshortcuts` の値 */
  keys: string;
  /** 画面に出すキーの文字 */
  label: string;
};

/** macOS か（`Mod` を Cmd として出す） */
const isMac = (): boolean => typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.userAgent);

/** IME の変換中・入力欄の中（1 文字のキー）・定義に無い修飾キーは、ライブラリの既定で受けない。1 文字のキーは個人の上書き `singleKeyShortcuts` が偽の間も受けない */
export const useShortcut = (id: ShortcutId, handler: () => void, enabled = true): ShortcutState => {
  const definition = SHORTCUTS[id];
  const singleKeyOff = usePrefs().singleKeyShortcuts === false;
  const active = enabled && !(definition.singleKey && singleKeyOff);
  useHotkey(definition.key, () => { handler(); }, { enabled: active });
  const mac = isMac();
  return {
    active,
    keys: definition.singleKey ? definition.key.toLowerCase() : definition.key.replace("Mod", mac ? "Meta" : "Control"),
    label: mac ? definition.key.replace("Mod+", "⌘") : definition.key.replace("Mod", "Ctrl"),
  };
};
