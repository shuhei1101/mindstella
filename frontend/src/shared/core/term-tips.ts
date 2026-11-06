/* eslint-disable @typescript-eslint/no-non-null-assertion -- 今の画面のコードを写した箇所で、正規表現の捕捉と描いた直後の要素を指す */
// 本文の印のツールチップ（今の画面の `components/term-tip.ts`・`screens/detail.ts` の本文の印と同じ振る舞い）
import { HTML_BODY_ATTR } from "@/shared/core/body-render";
import { hashWith, LINE_ATTR, MARK_KINDS, TERM_TIP_ID, VALUE_KEY_ATTR } from "@/shared/core/body-links";
import { h } from "@/shared/core/dom-parts";
import { highlightFrameLine } from "@/shared/core/html-frame";
import { revealHeading } from "@/shared/core/markdown-decorate";
import { isRendered } from "@/shared/core/minimap";
import type { Item, Location, RecordIndex } from "@/shared/core/records";

/** ツールチップに並べる項目（種類と項目） */
export type TermTipEntry = { kind: (typeof MARK_KINDS)[number]; item: Item };

/** 本文の印のツールチップの引数 */
export type TermTipProps = {
  /** 印の語に一致した項目。用語 → 資料 → 調査の順。開いている項目自身と取り下げた資料・調査は含めない（取り下げた用語は含める） */
  entries: TermTipEntry[];
  /** 本文の印の要素。置き場所とフォーカスの戻し先 */
  anchor: HTMLElement;
  /** 押して残した状態か。真のときは外を押すと閉じる */
  pinned?: boolean;
  on: {
    /** 中の項目のリンクを押した（項目の ID）。使う側がツールチップを閉じ、その項目へ移る */
    open: (id: string) => void;
    /** 閉じる操作があった（Esc・押して残した状態での外の押下・中からフォーカスが外へ出た） */
    close: () => void;
  };
};

/** 種類ごとの見出しの名前 */
const KIND_LABELS: Record<TermTipEntry["kind"], string> = { terms: "用語", docs: "資料", research: "調査" };

/** 印との間の空きと、画面の端から内側に収める幅（px） */
const TIP_GAP = 6;
const SCREEN_EDGE = 8;

/** 要素の中のフォーカスできる要素 */
const focusablesIn = (parent: ParentNode): HTMLElement[] => {
  return [...parent.querySelectorAll<HTMLElement>("a[href], button, [tabindex]:not([tabindex='-1'])")].filter(
    (node) => node.closest("[hidden]") === null,
  );
};

/** 項目 1 件。用語は用語・ID・意味、資料・調査はタイトル・ID・説明（無ければ出さない） */
const tipItem = ({ entry }: { entry: TermTipEntry }): HTMLElement => {
  const { item } = entry;
  const text = entry.kind === "terms" ? item.meaning : item.description;
  return h({
    tag: "li",
    attrs: { class: "tt-item" },
    children: [
      h({
        tag: "span",
        attrs: { class: "tt-head" },
        children: [
          h({ tag: "a", attrs: { class: "tt-link", href: hashWith({ id: item.id, heading: null }), "data-id": item.id }, children: [item.title] }),
          h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
        ],
      }),
      text === undefined || text === "" ? null : h({ tag: "span", attrs: { class: "tt-body" }, children: [text] }),
    ],
  });
};

/** 用語と資料・調査を含むツールチップの中身。種類ごとの見出し（種類名と件数）とリストに分ける */
const groupedContent = (entries: TermTipEntry[]): HTMLElement[] => {
  return MARK_KINDS.map((kind) => ({ kind, entries: entries.filter((entry) => entry.kind === kind) }))
    .filter((group) => group.entries.length > 0)
    .map((group) =>
      h({
        tag: "div",
        attrs: { class: "tt-group" },
        children: [
          h({
            tag: "p",
            attrs: { class: "tt-kind", id: `tt-kind-${group.kind}` },
            children: [KIND_LABELS[group.kind], " ", h({ tag: "span", attrs: { class: "tt-n" }, children: [String(group.entries.length)] })],
          }),
          h({
            tag: "ul",
            attrs: { class: "tt-items", "aria-labelledby": `tt-kind-${group.kind}` },
            children: group.entries.map((entry) => tipItem({ entry })),
          }),
        ],
      }),
    );
};

/** ツールチップを返す。使う側が文書に入れて `showPopover()` で開く。開くと印の上に置き、上に収まらなければ下に、どちらにも収まらなければ広い側の高さに縮める */
export const termTip = ({ entries, anchor, pinned = false, on }: TermTipProps): HTMLElement => {
  // 用語 2 件以上か、資料・調査を含むときは、種類ごとの見出しとリンクで並べる
  const multi = entries.length > 1 || entries.some((entry) => entry.kind !== "terms");
  const tip = h({
    tag: "div",
    attrs: {
      id: TERM_TIP_ID,
      class: multi ? "term-tip is-multi" : "term-tip",
      // リンクを持たない用語 1 件だけのツールチップは tooltip の役割にし、リンクを持つ方は印の aria-details で指す
      role: multi ? null : "tooltip",
      popover: "manual",
    },
  });
  if (multi) {
    tip.append(...groupedContent(entries));
  } else {
    // 用語 1 件だけに一致した印は、用語・ID・意味だけを出す
    const term = entries[0]!.item;
    tip.append(
      h({ tag: "span", attrs: { class: "tt-head" }, children: [term.title, h({ tag: "span", attrs: { class: "mono" }, children: [term.id] })] }),
      h({ tag: "span", attrs: { class: "tt-body" }, children: [term.meaning ?? ""] }),
    );
  }

  /** 印の上に 6px 空けて下端を留める。上に収まらなければ下に出し、どちらにも収まらなければ広い側の余白（印との 6px と画面の端の 8px を除く）の高さに縮めて固定する */
  const place = (): void => {
    const rect = anchor.getBoundingClientRect();
    tip.style.height = "";
    tip.style.top = "auto";
    tip.style.bottom = "auto";
    const needed = tip.offsetHeight;
    const spaceAbove = rect.top - TIP_GAP - SCREEN_EDGE;
    const spaceBelow = innerHeight - rect.bottom - TIP_GAP - SCREEN_EDGE;
    const above = spaceAbove >= needed || (spaceBelow < needed && spaceAbove >= spaceBelow);
    const room = above ? spaceAbove : spaceBelow;
    // 収まらない: 縮めた高さで固定し、中身が変わっても大きさを変えない
    if (needed > room) tip.style.height = `${Math.max(room, 0)}px`;
    tip.style.left = `${Math.max(SCREEN_EDGE, Math.min(rect.left, innerWidth - tip.offsetWidth - SCREEN_EDGE))}px`;
    if (above) tip.style.bottom = `${innerHeight - rect.top + TIP_GAP}px`;
    else tip.style.top = `${rect.bottom + TIP_GAP}px`;
  };

  /** 押して残した状態で、ツールチップと印の外を押したら閉じる */
  const closeOnOutsidePress = (event: Event): void => {
    const target = event.target;
    if (target instanceof Node && (tip.contains(target) || anchor.contains(target))) return;
    on.close();
  };

  // 開いたとき（と、開いた直後の描画の前）に置き場所を決める。押して残した状態なら外の押下も見る
  tip.addEventListener("toggle", (event) => {
    if ((event).newState === "open") {
      place();
      if (pinned) document.addEventListener("pointerdown", closeOnOutsidePress, true);
    } else {
      document.removeEventListener("pointerdown", closeOnOutsidePress, true);
    }
  });
  requestAnimationFrame(() => {
    if (tip.matches(":popover-open")) place();
  });

  // 中の項目のリンクは、その項目へ移る
  tip.addEventListener("click", (event) => {
    const link = (event.target as Element).closest<HTMLElement>("a.tt-link");
    if (link === null) return;
    event.preventDefault();
    on.open(link.getAttribute("data-id") ?? "");
  });

  tip.addEventListener("keydown", (event) => {
    // Esc: ツールチップだけを閉じて印へフォーカスを戻す（全画面を閉じる Esc として受けさせない）
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      anchor.focus();
      on.close();
      return;
    }
    if (event.key !== "Tab") return;
    // 最初のリンクの Shift+Tab は印へ、最後のリンクの次は本文の印の次の要素へ移す
    const inside = focusablesIn(tip);
    const edge = event.shiftKey ? inside[0] : inside.at(-1);
    if (document.activeElement !== edge) return;
    event.preventDefault();
    if (event.shiftKey) {
      anchor.focus();
      return;
    }
    const after = focusablesIn(anchor.closest(".md") ?? document.body);
    const next = after[after.indexOf(anchor) + 1] ?? anchor;
    next.focus();
    // 印へ戻るときは focusout で閉じないため、ここで閉じる
    if (next === anchor) on.close();
  });

  // 中から印でもツールチップでもない所へフォーカスが出たら閉じる
  tip.addEventListener("focusout", (event) => {
    const to = event.relatedTarget;
    if (to instanceof Node && !tip.contains(to) && to !== anchor) on.close();
  });

  return tip;
};


/** 本文の見出しを、本文のスクロール領域の中で画面に入れる（見えている見出しが本文に無ければ false。左右に並べるときは同じ見出しが 3 か所にあるので、矩形を持つ最初のものへ送る） */
export const scrollToHeading = ({ root, slug }: { root: ParentNode; slug: string }): boolean => {
  // 畳んだ節の中の見出しは、包む入れ物を開いてから送る
  revealHeading({ root, slug });
  const target = [...root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)].find(isRendered);
  if (target === undefined) return false;
  target.scrollIntoView({ block: "start" });
  return true;
};

/** 本文の印のツールチップを隠すまで待つミリ秒（印からツールチップへポインターを動かす間に消さない） */
const TIP_HIDE_DELAY_MS = 150;

/** ツールチップを隠す待ちのタイマー */
let tipTimer = 0;

/** 今出している（出していた）ツールチップの印と、押して残しているか */
let tipState: { mark: HTMLElement; pinned: boolean } | null = null;

/** Esc で閉じて印へフォーカスを戻すとき、その印のフォーカスでツールチップを出し直さない */
let refocused: Element | null = null;

/** 今のツールチップの要素（使い回す 1 つ。隠していても文書に残る） */
const currentTip = (): HTMLElement | null => {
  return document.getElementById(TERM_TIP_ID);
};

/** 押して残しているか。ツールチップがまだ文書にあって開いているときに限る（詳細パネルの描き直しで外れたものは残していないとみなす） */
const isPinned = (): boolean => {
  return tipState?.pinned === true && currentTip()?.matches(":popover-open") === true;
};

/** ツールチップを隠す（`now` が偽のときは、少し待ってから） */
export const hideTermTip = (now: boolean): void => {
  window.clearTimeout(tipTimer);
  const hide = (): void => {
    const tip = currentTip();
    if (tip?.matches(":popover-open") === true) tip.hidePopover();
    tipState = null;
  };
  if (now) hide();
  else tipTimer = window.setTimeout(hide, TIP_HIDE_DELAY_MS);
};

/** 印の上に、一致した項目のツールチップを出す。重ねる面の上にも出せるよう、印のある詳細パネル・全画面のモーダルの中に置く（モーダルの外は操作できない） */
const showTermTip = ({
  mark,
  entries,
  pinned,
  onOpen,
}: {
  mark: HTMLElement;
  entries: TermTipEntry[];
  pinned: boolean;
  onOpen: (id: string) => void;
}): void => {
  window.clearTimeout(tipTimer);
  const previous = currentTip();
  // 同じ印を同じ出し方で出しているときは出し直さない（中のスクロールを保つ）
  if (tipState?.mark === mark && tipState.pinned === pinned && previous?.matches(":popover-open") === true) return;
  if (previous !== null) {
    if (previous.matches(":popover-open")) previous.hidePopover();
    previous.remove();
  }
  const tip = termTip({
    entries,
    anchor: mark,
    pinned,
    on: {
      open: (id) => {
        hideTermTip(true);
        onOpen(id);
      },
      close: () => hideTermTip(true),
    },
  });
  // ツールチップに乗せている間は消さない。押して残した間は、外れても消さない
  tip.addEventListener("mouseenter", () => window.clearTimeout(tipTimer));
  tip.addEventListener("mouseleave", () => {
    if (!pinned) hideTermTip(false);
  });
  (mark.closest("dialog, aside") ?? document.body).append(tip);
  tip.showPopover();
  tipState = { mark, pinned };
};

/** Esc でツールチップを隠す。中にフォーカスがあれば印へ戻し、全画面の Esc（元の大きさに戻す）を起こさない */
document.addEventListener(
  "keydown",
  (event) => {
    const tip = currentTip();
    // 詳細パネルが出したツールチップだけを対象にする
    if (event.key !== "Escape" || tipState === null || tip?.matches(":popover-open") !== true) return;
    const back = tip.contains(document.activeElement) ? tipState.mark : null;
    event.preventDefault();
    event.stopPropagation();
    hideTermTip(true);
    refocused = back;
    back?.focus();
    refocused = null;
  },
  true,
);

/** 本文の印に乗せる・フォーカスするとツールチップを出し、外れると隠す（本文の要素に委ねて付ける）。用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残し、Tab で中へ移れる */
export const attachTermTips = ({ root, index, onOpen }: { root: HTMLElement; index: RecordIndex; onOpen: (id: string) => void }): void => {
  /** イベントの先の印と、一致した項目（用語 → 資料 → 調査の順）。用語 2 件以上か、資料・調査を含むか */
  const markOf = (event: Event): { mark: HTMLElement; entries: TermTipEntry[]; multi: boolean } | null => {
    const mark = (event.target as Element).closest?.<HTMLElement>("a.term") ?? null;
    if (mark === null) return null;
    const ids = (mark.getAttribute("data-ids") ?? mark.getAttribute("data-id") ?? "").split(" ");
    const entries = ids.flatMap((id) => {
      const found = index.byId.get(id);
      return found === undefined ? [] : [{ kind: found.kind as TermTipEntry["kind"], item: found.item }];
    });
    return entries.length === 0 ? null : { mark, entries, multi: entries.length > 1 || entries.some((entry) => entry.kind !== "terms") };
  };
  root.addEventListener("mouseover", (event) => {
    const found = markOf(event);
    // 押して残している間は、ほかの印に乗せても替えない
    if (found !== null && !isPinned()) showTermTip({ ...found, pinned: false, onOpen });
  });
  root.addEventListener("focusin", (event) => {
    const found = markOf(event);
    if (found !== null && found.mark !== refocused) showTermTip({ ...found, pinned: false, onOpen });
  });
  root.addEventListener("mouseout", (event) => {
    if (markOf(event) !== null && !isPinned()) hideTermTip(false);
  });
  root.addEventListener("focusout", (event) => {
    const to = (event).relatedTarget;
    // ツールチップの中へ移るときは残す。押して残している間は、フォーカスの行き先が無い（余白を押した）ときも残す
    if (markOf(event) === null || (to instanceof Node && currentTip()?.contains(to) === true)) return;
    if (to === null && isPinned()) return;
    hideTermTip(true);
  });
  // 用語 2 件以上か、資料・調査にも一致した印から Tab で、ツールチップの中の最初のリンクへ移る
  root.addEventListener("keydown", (event) => {
    const found = markOf(event);
    const tip = currentTip();
    if (event.key !== "Tab" || event.shiftKey || found === null || !found.multi || tip?.matches(":popover-open") !== true) return;
    const first = tip.querySelector<HTMLElement>("a[href]");
    if (first === null) return;
    event.preventDefault();
    first.focus();
  });
  root.addEventListener("click", (event) => {
    const found = markOf(event);
    if (found === null) return;
    // 用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残す（移る先は中のリンクで選ぶ）
    if (found.multi) {
      showTermTip({ ...found, pinned: true, onOpen });
      return;
    }
    // 用語 1 件だけに一致した印を押して項目へ移るときは、ツールチップを残さない
    hideTermTip(true);
  });
};

/** コメントの一覧から開いたとき、そのコメントの箇所に印の色の地を付け、描いた後にその箇所までスクロールする。合わなければ示さず、項目の先頭を出す */
export const applyHighlight = ({ root, loc }: { root: ParentNode; loc: Location }): void => {
  let hits: Element[] = [];
  if (loc.kind === "value") {
    hits = [...root.querySelectorAll(`[${VALUE_KEY_ATTR}]`)].filter((element) => element.getAttribute(VALUE_KEY_ATTR) === loc.key);
  } else {
    const start = loc.start ?? 0;
    const end = loc.end ?? start;
    // HTML の本文: 枠の中で、始まりの行を含む最も内側の要素を示す
    const frame = root.querySelector<HTMLIFrameElement>(`iframe[${HTML_BODY_ATTR}]`);
    if (frame !== null) {
      highlightFrameLine({ frame, line: start, scroller: root.querySelector<HTMLElement>(".panel-body") });
      return;
    }
    const blocks = [...root.querySelectorAll(`.md [${LINE_ATTR}]`)];
    const lineOf = (element: Element): number => Number(element.getAttribute(LINE_ATTR));
    // 始まりの行を含む（始まりの行以前で最も後ろの）ブロックから、終わりの行までのブロック
    const first = blocks.filter((element) => lineOf(element) <= start).at(-1);
    if (first !== undefined) hits = blocks.filter((element) => lineOf(element) >= lineOf(first) && lineOf(element) <= end);
  }
  for (const element of hits) element.classList.add("loc-hit");
  // 文書に入れた後でないとスクロールできない
  const target = hits[0];
  if (target !== undefined) requestAnimationFrame(() => target.scrollIntoView({ block: "center" }));
};
