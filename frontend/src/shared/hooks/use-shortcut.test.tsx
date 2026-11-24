import { fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { useShortcut } from "@/shared/hooks/use-shortcut";
import type { ShortcutId } from "@/shared/core/shortcuts";
import { writePrefs } from "@/shared/stores/prefs-store";

type Result = ReturnType<typeof useShortcut>;

const Host = ({ id, handler, enabled, onResult }: { id: ShortcutId; handler: () => void; enabled?: boolean; onResult: (result: Result) => void }) => {
  onResult(useShortcut(id, handler, enabled));
  return <input aria-label="入力欄" />;
};

const press = (target: Element | Document, init: KeyboardEventInit & { keyCode?: number }) => {
  fireEvent.keyDown(target, { bubbles: true, cancelable: true, ...init });
};

afterEach(() => {
  localStorage.clear();
});

describe("useShortcut", () => {
  // 1 文字のキーの判定（正常系）
  test.each([
    { name: "j", called: true, active: true },
    { name: "Shift+j", init: { key: "J", code: "KeyJ", shiftKey: true }, called: false, active: true },
    { name: "isComposing の j", init: { key: "j", code: "KeyJ", isComposing: true }, called: false, active: true },
    { name: "keyCode 229 の j", init: { key: "j", code: "KeyJ", keyCode: 229 }, called: false, active: true },
    { name: "入力欄の j", inInput: true, called: false, active: true },
    { name: "enabled が偽", enabled: false, called: false, active: false },
    { name: "singleKeyShortcuts が偽", singleKeyOff: true, called: false, active: false },
  ])("use_shortcut_when_single_key: $name", ({ init = { key: "j", code: "KeyJ" }, inInput = false, enabled = true, singleKeyOff = false, called, active }) => {
    // 準備
    if (singleKeyOff) writePrefs({ singleKeyShortcuts: false });
    const handler = vi.fn();
    let result: Result | undefined;
    const { getByRole } = render(<Host id="item.next" handler={handler} enabled={enabled} onResult={(value) => { result = value; }} />);
    const input = getByRole("textbox", { name: "入力欄" });
    if (inInput) input.focus();
    // 実行
    press(inInput ? input : document, init);
    // 検証
    expect(handler).toHaveBeenCalledTimes(called ? 1 : 0);
    expect(result?.active).toBe(active);
  });

  // 修飾キーつきのキーは設定によらず受ける（正常系）
  test("use_shortcut_when_mod_key", () => {
    // 準備
    writePrefs({ singleKeyShortcuts: false });
    const handler = vi.fn();
    const { getByRole } = render(<Host id="search.open" handler={handler} onResult={vi.fn()} />);
    const input = getByRole("textbox", { name: "入力欄" });
    input.focus();
    // 実行
    press(input, { key: "k", code: "KeyK", ctrlKey: true });
    // 検証
    expect(handler).toHaveBeenCalledTimes(1);
  });
});
