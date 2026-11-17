"use strict";
// 入力中・音声入力中に、書き換えの通知による描き直しを保留する。
var MindmapPreview;
(function (MindmapPreview) {
    /** 文字を入力する欄とみなす input の type */
    const TEXT_INPUT_TYPES = ["text", "search", "email", "url", "tel", "password", "number"];
    /** 要素が文字を入力する欄（文字の input・textarea・contenteditable）か */
    MindmapPreview.isTextEntry = (element) => {
        if (element === null)
            return false;
        if (element instanceof HTMLTextAreaElement)
            return true;
        if (element instanceof HTMLInputElement)
            return TEXT_INPUT_TYPES.includes(element.type);
        return element instanceof HTMLElement && element.isContentEditable;
    };
    /** 要素の最も近いスクロールする祖先（無ければ文書のスクロール） */
    const scrollerOf = (element) => {
        for (let parent = element.parentElement; parent !== null; parent = parent.parentElement) {
            const { overflowY } = getComputedStyle(parent);
            if (overflowY === "auto" || overflowY === "scroll")
                return parent;
        }
        return element.ownerDocument.scrollingElement;
    };
    /** 基準の要素の画面の上の位置が控えた位置と同じになるよう、スクロールする祖先を差の分だけ送る */
    const restoreHoldAnchor = (anchor) => {
        if (anchor === null || !anchor.element.isConnected)
            return;
        const shift = anchor.element.getBoundingClientRect().top - anchor.top;
        const scroller = scrollerOf(anchor.element);
        if (shift !== 0 && scroller !== null)
            scroller.scrollTop += shift;
    };
    /** 要素とその画面の上の位置 */
    const holdAnchorOf = (element) => (element === null ? null : { element, top: element.getBoundingClientRect().top });
    /** 文書のフォーカスを見張り、入力中・音声入力中は描き直しの依頼を保留して、離れたときに 1 回だけ描き直す */
    MindmapPreview.createRefreshHold = ({ doc, isVoiceActive, reload, onStaleChange }) => {
        let typing = MindmapPreview.isTextEntry(doc.activeElement);
        let pending = false;
        /** 保留を始めたときにフォーカスがあった要素 */
        let heldElement = null;
        /** フォーカスのある要素（文書の本体を除く） */
        const focusedElement = () => {
            const active = doc.activeElement;
            return active instanceof HTMLElement && active !== doc.body && active !== doc.documentElement ? active : null;
        };
        const holding = () => typing || isVoiceActive();
        const request = () => {
            if (!holding()) {
                reload();
                return;
            }
            if (pending)
                return;
            // 帯を出す前の位置を控え、帯を出して描いた後に戻す
            heldElement = focusedElement();
            const anchor = holdAnchorOf(heldElement);
            pending = true;
            onStaleChange(true);
            restoreHoldAnchor(anchor);
        };
        const release = () => {
            if (!pending || holding())
                return;
            // 帯を消す前の位置を控え、帯を消して描いた後に戻す
            const anchor = holdAnchorOf(focusedElement() ?? heldElement);
            pending = false;
            heldElement = null;
            onStaleChange(false);
            restoreHoldAnchor(anchor);
            reload();
        };
        const onFocusIn = (event) => {
            typing = MindmapPreview.isTextEntry(event.target);
        };
        const onFocusOut = (event) => {
            // 入力欄から入力欄へ移るときは離れたとみなさない
            if (MindmapPreview.isTextEntry(event.relatedTarget))
                return;
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
})(MindmapPreview || (MindmapPreview = {}));
