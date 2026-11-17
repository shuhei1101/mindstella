import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  isHolding,
  isTextEntry,
  releaseRefresh,
  requestRefresh,
  restoreAnchor,
  useRefreshHoldStore,
  watchTextFocus,
} from "@/shared/stores/refresh-hold-store";
import { readVoiceState, resetVoiceStore, startVoice } from "@/shared/stores/voice-store";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";

/** T-1 のコメントの入力 */
const T1 = { key: "T-1#", destination: { target: "T-1", loc: null }, view: "panel" as const, label: "T-1 へのコメント", selection: { start: 0, end: 0 } };

/** 文書の末尾に要素を足して返す */
const append = <K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string> = {}): HTMLElementTagNameMap[K] => {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
  document.body.append(element);
  return element;
};

/** 画面の上の位置だけを返す矩形 */
const rectAt = (top: number): DOMRect => ({ top, bottom: top + 20, left: 0, right: 100, width: 100, height: 20, x: 0, y: top, toJSON: () => ({}) });

/** 音声入力の録音を始める */
const startRecording = async (): Promise<void> => {
  installFakeMedia();
  installFakeWakeLock();
  await startVoice(T1);
};

beforeEach(() => {
  useRefreshHoldStore.setState({ focused: false, pending: false, anchor: null });
  resetVoiceStore();
});

afterEach(() => {
  document.body.replaceChildren();
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
  vi.restoreAllMocks();
});

describe("isTextEntry", () => {
  // 文字を入力する欄を見分ける（正常系）
  test("is_text_entry", () => {
    // 準備
    const editable = append("div", { contenteditable: "true" });
    const elements = [append("textarea"), append("input", { type: "text" }), append("input", { type: "search" }), editable, append("input", { type: "checkbox" }), append("button"), null];
    // 実行
    const results = elements.map((element) => isTextEntry(element));
    // 検証
    expect(results).toEqual([true, true, true, true, false, false, false]);
  });
});

describe("watchTextFocus", () => {
  // 入力欄に入る・離れる（正常系）
  test("watch_text_focus", () => {
    // 準備
    const textarea = append("textarea");
    const button = append("button");
    const stop = watchTextFocus(document);
    // 実行
    textarea.focus();
    const entered = useRefreshHoldStore.getState().focused;
    button.focus();
    const left = useRefreshHoldStore.getState().focused;
    stop();
    // 検証
    expect([entered, left]).toEqual([true, false]);
  });

  // 入力欄から入力欄へ移る（正常系）
  test("watch_text_focus_when_moved_between_entries", () => {
    // 準備
    const textarea = append("textarea");
    const input = append("input", { type: "text" });
    textarea.focus();
    const stop = watchTextFocus(document);
    const seen: boolean[] = [];
    const unsubscribe = useRefreshHoldStore.subscribe((state) => seen.push(state.focused));
    // 実行
    input.focus();
    unsubscribe();
    stop();
    // 検証
    expect(useRefreshHoldStore.getState().focused).toBe(true);
    expect(seen).not.toContain(false);
  });
});

describe("isHolding", () => {
  // フォーカスと音声入力で保留する（正常系）
  test("is_holding", async () => {
    // 準備・実行
    const none = isHolding();
    useRefreshHoldStore.setState({ focused: true });
    const focusedOnly = isHolding();
    useRefreshHoldStore.setState({ focused: false });
    await startRecording();
    const voiceOnly = isHolding();
    // 検証
    expect(readVoiceState().session).not.toBeNull();
    expect([none, focusedOnly, voiceOnly]).toEqual([false, true, true]);
  });
});

describe("requestRefresh", () => {
  // 入力中でなければすぐ読み直す（正常系）
  test("request_refresh", () => {
    // 準備
    const refresh = vi.fn();
    // 実行
    requestRefresh(refresh);
    // 検証
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(useRefreshHoldStore.getState().pending).toBe(false);
  });

  // 入力中は保留する（正常系）
  test("request_refresh_when_holding", () => {
    // 準備
    const textarea = append("textarea");
    textarea.focus();
    useRefreshHoldStore.setState({ focused: true });
    const refresh = vi.fn();
    // 実行
    requestRefresh(refresh);
    requestRefresh(refresh);
    // 検証
    expect(refresh).not.toHaveBeenCalled();
    expect(useRefreshHoldStore.getState().pending).toBe(true);
    expect(useRefreshHoldStore.getState().anchor?.element).toBe(textarea);
  });
});

describe("releaseRefresh", () => {
  // 離れたら 1 回だけ読み直す（正常系）
  test("release_refresh", () => {
    // 準備
    const textarea = append("textarea");
    useRefreshHoldStore.setState({ pending: true, focused: false, anchor: { element: textarea, top: 0 } });
    const refresh = vi.fn();
    // 実行
    releaseRefresh(refresh);
    releaseRefresh(refresh);
    // 検証
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(useRefreshHoldStore.getState().pending).toBe(false);
    expect(useRefreshHoldStore.getState().anchor?.element).toBe(textarea);
  });

  // まだ入力中なら読み直さない（正常系）
  test("release_refresh_when_holding", async () => {
    // 準備
    await startRecording();
    useRefreshHoldStore.setState({ pending: true });
    const refresh = vi.fn();
    // 実行
    releaseRefresh(refresh);
    // 検証
    expect(refresh).not.toHaveBeenCalled();
    expect(useRefreshHoldStore.getState().pending).toBe(true);
  });
});

describe("restoreAnchor", () => {
  /** スクロールする祖先の中に、今の top を返す要素を置く */
  const placeInScroller = (now: number): { scroller: HTMLDivElement; element: HTMLTextAreaElement } => {
    const scroller = append("div", { style: "overflow-y: auto; height: 100px" });
    const element = document.createElement("textarea");
    scroller.append(element);
    scroller.scrollTop = 50;
    vi.spyOn(element, "getBoundingClientRect").mockReturnValue(rectAt(now));
    return { scroller, element };
  };

  // ずれた分だけ送る（正常系）
  test("restore_anchor", () => {
    // 準備
    const { scroller, element } = placeInScroller(130);
    useRefreshHoldStore.setState({ anchor: { element, top: 100 } });
    // 実行
    restoreAnchor();
    // 検証
    expect(scroller.scrollTop).toBe(80);
    expect(useRefreshHoldStore.getState().anchor).toBeNull();
  });

  // 帯を消して上へずれた分だけ戻す（正常系）
  test("restore_anchor_when_released", () => {
    // 準備
    const { scroller, element } = placeInScroller(100);
    useRefreshHoldStore.setState({ anchor: { element, top: 130 } });
    // 実行
    restoreAnchor();
    // 検証
    expect(scroller.scrollTop).toBe(20);
    expect(useRefreshHoldStore.getState().anchor).toBeNull();
  });
});
