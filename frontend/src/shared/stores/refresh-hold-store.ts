// 入力中・音声入力中に、書き換えの通知による画面への反映を保留する
import { create } from "zustand";

import { readVoiceState } from "@/shared/stores/voice-store";

/** 文字を入力する欄とみなす input の type */
export const TEXT_INPUT_TYPES: readonly string[] = ["text", "search", "email", "url", "tel", "password", "number"];

/** 帯を出す・消す直前の基準の要素と、その画面の上の位置 */
type Anchor = { element: HTMLElement; top: number };

type RefreshHoldState = {
  /** 文字を入力する欄にフォーカスがあるか */
  focused: boolean;
  /** 画面への反映を保留しているか */
  pending: boolean;
  /** 保留を始めたときにフォーカスがあった要素（帯を消すときの基準。`restoreAnchor` では消さない） */
  heldElement: HTMLElement | null;
  /** 帯を出す・消して描いた後に位置を戻す基準 */
  anchor: Anchor | null;
};

export const useRefreshHoldStore = create<RefreshHoldState>()(() => ({ focused: false, pending: false, heldElement: null, anchor: null }));

/** 要素が文字を入力する欄（文字の input・textarea・contenteditable）か */
export const isTextEntry = (element: Element | null): boolean => {
  if (element === null) return false;
  if (element instanceof HTMLTextAreaElement) return true;
  if (element instanceof HTMLInputElement) return TEXT_INPUT_TYPES.includes(element.type);
  // jsdom は isContentEditable を持たないため、属性でも確かめる
  return element instanceof HTMLElement && (element.isContentEditable || element.getAttribute("contenteditable") === "true");
};

/** 文書の focusin・focusout を受けて `focused` を書き換え、見張りをやめる関数を返す */
export const watchTextFocus = (doc: Document): (() => void) => {
  useRefreshHoldStore.setState({ focused: isTextEntry(doc.activeElement) });
  const onFocusIn = (event: FocusEvent): void => {
    useRefreshHoldStore.setState({ focused: isTextEntry(event.target as Element | null) });
  };
  const onFocusOut = (event: FocusEvent): void => {
    // 入力欄から入力欄へ移るときは離れたとみなさない
    if (!isTextEntry(event.relatedTarget as Element | null)) useRefreshHoldStore.setState({ focused: false });
  };
  doc.addEventListener("focusin", onFocusIn);
  doc.addEventListener("focusout", onFocusOut);
  return () => {
    doc.removeEventListener("focusin", onFocusIn);
    doc.removeEventListener("focusout", onFocusOut);
  };
};

/** 文字を入力する欄にフォーカスがあるか、音声入力（録音・文字起こし中）があるか */
export const isHolding = (): boolean => useRefreshHoldStore.getState().focused || readVoiceState().session !== null;

/** フォーカスのある要素（文書の本体を除く） */
const focusedElement = (): HTMLElement | null => {
  const active = document.activeElement;
  return active instanceof HTMLElement && active !== document.body && active !== document.documentElement ? active : null;
};

/** 要素とその画面の上の位置 */
const anchorOf = (element: HTMLElement | null): Anchor | null => (element === null ? null : { element, top: element.getBoundingClientRect().top });

/** 保留する間なら `pending` を立てて読み直さず、そうでなければすぐ読み直す */
export const requestRefresh = (refresh: () => void): void => {
  if (!isHolding()) {
    refresh();
    return;
  }
  const { pending } = useRefreshHoldStore.getState();
  // 保留を始めるときだけ、帯を出す前の位置を控える
  if (!pending) {
    const element = focusedElement();
    useRefreshHoldStore.setState({ heldElement: element, anchor: anchorOf(element) });
  }
  useRefreshHoldStore.setState({ pending: true });
};

/** 保留していて、保留する間でなくなっていれば、`pending` を下ろして 1 回だけ読み直す */
export const releaseRefresh = (refresh: () => void): void => {
  const { pending, heldElement } = useRefreshHoldStore.getState();
  if (!pending || isHolding()) return;
  // 入力欄から離れた直後はフォーカスのある要素が無いため、保留を始めたときの要素を基準にする
  useRefreshHoldStore.setState({ anchor: anchorOf(focusedElement() ?? heldElement), pending: false, heldElement: null });
  refresh();
};

/** 要素の最も近いスクロールする祖先（無ければ文書のスクロール） */
const scrollerOf = (element: HTMLElement): Element | null => {
  for (let parent = element.parentElement; parent !== null; parent = parent.parentElement) {
    const { overflowY } = getComputedStyle(parent);
    if (overflowY === "auto" || overflowY === "scroll") return parent;
  }
  return document.scrollingElement;
};

/** 帯を出した後と消した後、基準の要素の画面の上の位置が出す・消す直前と同じになるよう、スクロールする祖先を差の分だけ送る */
export const restoreAnchor = (): void => {
  const { anchor } = useRefreshHoldStore.getState();
  if (anchor === null || !anchor.element.isConnected) return;
  const shift = anchor.element.getBoundingClientRect().top - anchor.top;
  const scroller = scrollerOf(anchor.element);
  if (shift !== 0 && scroller !== null) scroller.scrollTop += shift;
  useRefreshHoldStore.setState({ anchor: null });
};

/** 反映を保留しているか（トップバーの `stale`） */
export const useStale = (): boolean => useRefreshHoldStore((state) => state.pending);
