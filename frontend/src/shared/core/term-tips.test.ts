import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { TERM_TIP_ID } from "@/shared/core/body-links";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { attachTermTips, hideTermTip } from "@/shared/core/term-tips";

/** 検討事項 D-3 と用語 G-1 だけを持つ記録 */
const DATA = {
  decisions: [{ id: "D-3", title: "保存先の決め方", status: "未決定" }],
  tasks: [],
  research: [],
  docs: [],
  terms: [{ id: "G-1", title: "ワークスペース", meaning: "記録を置くフォルダ" }],
  notes: [],
  logs: [],
  derived: { ready: [] },
} as unknown as MindmapData;

/** 文書へポインターのイベントを送信する（jsdom は PointerEvent を持たないため、pointerType を持つ Event を作る） */
const pointerDown = (target: Element, pointerType: "touch" | "mouse"): void => {
  const event = new Event("pointerdown", { bubbles: true });
  Object.defineProperty(event, "pointerType", { value: pointerType });
  target.dispatchEvent(event);
};

/** 本文に D-3 の ID のリンクと G-1 の用語のマーカーを描き、ツールチップを付ける。G-1 のマーカーには移動のリスナーを付ける */
const setUp = (): { root: HTMLElement; idref: HTMLElement; term: HTMLElement; navigate: ReturnType<typeof vi.fn> } => {
  const root = document.createElement("div");
  root.innerHTML = '<p><a class="idref" href="#id=D-3" data-id="D-3">D-3</a> と <a class="term" href="#id=G-1" data-id="G-1">ワークスペース</a></p>';
  document.body.append(root);
  attachTermTips({ root, index: buildIndex(DATA), onOpen: vi.fn() });
  const term = root.querySelector<HTMLElement>("a.term");
  const idref = root.querySelector<HTMLElement>("a.idref");
  if (term === null || idref === null) throw new Error("本文のリンクが描かれていない");
  const navigate = vi.fn();
  term.addEventListener("click", (event) => {
    event.preventDefault();
    navigate();
  });
  return { root, idref, term, navigate };
};

/** ツールチップが開いているか */
const tipOpen = (): boolean => document.getElementById(TERM_TIP_ID)?.hasAttribute("data-test-open") === true;

describe("attachTermTips", () => {
  beforeEach(() => {
    // jsdom は popover を開かないため、開いた状態を属性で持つ
    vi.spyOn(HTMLElement.prototype, "showPopover").mockImplementation(function (this: HTMLElement) {
      this.setAttribute("data-test-open", "");
    });
    vi.spyOn(HTMLElement.prototype, "hidePopover").mockImplementation(function (this: HTMLElement) {
      this.removeAttribute("data-test-open");
    });
    const matches = Object.getOwnPropertyDescriptor(Element.prototype, "matches")?.value as (this: Element, selector: string) => boolean;
    vi.spyOn(Element.prototype, "matches").mockImplementation(function (this: Element, selector: string) {
      return selector === ":popover-open" ? this.hasAttribute("data-test-open") : matches.call(this, selector);
    });
  });

  afterEach(() => {
    hideTermTip(true);
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  // 指で押した ID のリンクにツールチップを出さない（正常系）
  test("attach_term_tips_when_touch_id", () => {
    // 準備
    const { idref } = setUp();
    // 実行
    pointerDown(idref, "touch");
    idref.dispatchEvent(new Event("mouseover", { bubbles: true }));
    idref.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
    // 検証
    expect(tipOpen()).toBe(false);
  });

  // 指で押した用語のマーカーは 1 回目でツールチップ、2 回目で移る（正常系）
  test("attach_term_tips_when_touch_term", () => {
    // 準備
    const { term, navigate } = setUp();
    // 実行（1 回目）
    pointerDown(term, "touch");
    term.click();
    // 検証（1 回目）
    expect(tipOpen()).toBe(true);
    expect(navigate).not.toHaveBeenCalled();
    // 実行（2 回目）
    pointerDown(term, "touch");
    term.click();
    // 検証（2 回目）
    expect(tipOpen()).toBe(false);
    expect(navigate).toHaveBeenCalledTimes(1);
  });

  // マウスでは今までどおり乗せると出し、1 回で移る（正常系）
  test("attach_term_tips_when_mouse", () => {
    // 準備
    const { idref, term, navigate } = setUp();
    // 実行
    pointerDown(idref, "mouse");
    idref.dispatchEvent(new Event("mouseover", { bubbles: true }));
    const opened = tipOpen();
    term.click();
    // 検証
    expect(opened).toBe(true);
    expect(navigate).toHaveBeenCalledTimes(1);
  });
});
