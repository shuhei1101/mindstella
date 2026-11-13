import { fireEvent, render } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useSearchShortcut } from "@/features/search/search/use-search-shortcut";

const Host = ({ open, onOpen }: { open: boolean; onOpen: () => void }) => {
  useSearchShortcut({ open, onOpen });
  return null;
};

const pressCtrlK = (): KeyboardEvent => {
  const event = new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true, cancelable: true });
  fireEvent(window, event);
  return event;
};

describe("useSearchShortcut", () => {
  // Ctrl+K で開く（正常系）
  test("use_search_shortcut", () => {
    // 準備
    const onOpen = vi.fn();
    render(<Host open={false} onOpen={onOpen} />);
    // 実行
    const event = pressCtrlK();
    // 検証
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  // 開いている間は受けない（正常系）
  test("use_search_shortcut_when_open", () => {
    // 準備
    const onOpen = vi.fn();
    render(<Host open onOpen={onOpen} />);
    // 実行
    pressCtrlK();
    // 検証
    expect(onOpen).not.toHaveBeenCalled();
  });
});
