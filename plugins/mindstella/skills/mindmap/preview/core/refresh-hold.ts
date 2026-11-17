// 入力中・音声入力中に、書き換えの通知による描き直しを保留する。

namespace MindmapPreview {
  /** 文字を入力する欄とみなす input の type */
  const TEXT_INPUT_TYPES: readonly string[] = ["text", "search", "email", "url", "tel", "password", "number"];

  /** 要素が文字を入力する欄（文字の input・textarea・contenteditable）か */
  export const isTextEntry = (element: Element | null): boolean => {
    if (element === null) return false;
    if (element instanceof HTMLTextAreaElement) return true;
    if (element instanceof HTMLInputElement) return TEXT_INPUT_TYPES.includes(element.type);
    return element instanceof HTMLElement && element.isContentEditable;
  };

  /** 描き直しの保留の依存 */
  export type RefreshHoldDeps = {
    /** 見張る文書 */
    doc: Document;
    /** 音声入力（録音・文字起こし中）があるか */
    isVoiceActive: () => boolean;
    /** 描き直し */
    reload: () => void;
    /** 保留が変わったときの知らせ（帯を出す・消す） */
    onStaleChange: (stale: boolean) => void;
  };

  /** 描き直しの保留の操作 */
  export type RefreshHold = {
    /** 書き換えの通知・つなぎ直しで呼ぶ */
    request: () => void;
    /** 音声入力が終わったときに呼ぶ */
    release: () => void;
    /** 保留しているか */
    stale: () => boolean;
    /** 見張りをやめる */
    dispose: () => void;
  };

  /** 基準の要素と、その画面の上の位置 */
  type HoldAnchor = { element: HTMLElement; top: number };

  /** 要素の最も近いスクロールする祖先（無ければ文書のスクロール） */
  const scrollerOf = (element: HTMLElement): Element | null => {
    for (let parent = element.parentElement; parent !== null; parent = parent.parentElement) {
      const { overflowY } = getComputedStyle(parent);
      if (overflowY === "auto" || overflowY === "scroll") return parent;
    }
    return element.ownerDocument.scrollingElement;
  };

  /** 基準の要素の画面の上の位置が控えた位置と同じになるよう、スクロールする祖先を差の分だけ送る */
  const restoreHoldAnchor = (anchor: HoldAnchor | null): void => {
    if (anchor === null || !anchor.element.isConnected) return;
    const shift = anchor.element.getBoundingClientRect().top - anchor.top;
    const scroller = scrollerOf(anchor.element);
    if (shift !== 0 && scroller !== null) scroller.scrollTop += shift;
  };

  /** 要素とその画面の上の位置 */
  const holdAnchorOf = (element: HTMLElement | null): HoldAnchor | null => (element === null ? null : { element, top: element.getBoundingClientRect().top });

  /** 文書のフォーカスを見張り、入力中・音声入力中は描き直しの依頼を保留して、離れたときに 1 回だけ描き直す */
  export const createRefreshHold = ({ doc, isVoiceActive, reload, onStaleChange }: RefreshHoldDeps): RefreshHold => {
    let typing = isTextEntry(doc.activeElement);
    let pending = false;
    /** 保留を始めたときにフォーカスがあった要素 */
    let heldElement: HTMLElement | null = null;

    /** フォーカスのある要素（文書の本体を除く） */
    const focusedElement = (): HTMLElement | null => {
      const active = doc.activeElement;
      return active instanceof HTMLElement && active !== doc.body && active !== doc.documentElement ? active : null;
    };
    const holding = (): boolean => typing || isVoiceActive();

    const request = (): void => {
      if (!holding()) {
        reload();
        return;
      }
      if (pending) return;
      // 帯を出す前の位置を控え、帯を出して描いた後に戻す
      heldElement = focusedElement();
      const anchor = holdAnchorOf(heldElement);
      pending = true;
      onStaleChange(true);
      restoreHoldAnchor(anchor);
    };

    const release = (): void => {
      if (!pending || holding()) return;
      // 帯を消す前の位置を控え、帯を消して描いた後に戻す
      const anchor = holdAnchorOf(focusedElement() ?? heldElement);
      pending = false;
      heldElement = null;
      onStaleChange(false);
      restoreHoldAnchor(anchor);
      reload();
    };

    const onFocusIn = (event: FocusEvent): void => {
      typing = isTextEntry(event.target as Element | null);
    };
    const onFocusOut = (event: FocusEvent): void => {
      // 入力欄から入力欄へ移るときは離れたとみなさない
      if (isTextEntry(event.relatedTarget as Element | null)) return;
      typing = false;
      release();
    };
    doc.addEventListener("focusin", onFocusIn);
    doc.addEventListener("focusout", onFocusOut);

    return {
      request,
      release,
      stale: () => pending,
      dispose: () => {
        doc.removeEventListener("focusin", onFocusIn);
        doc.removeEventListener("focusout", onFocusOut);
      },
    };
  };
}
