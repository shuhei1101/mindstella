// 描いた Markdown の本文の見せ方。mdmark が描いた React の外の DOM に手を入れる。表は mdmark の表の機能のまま描き、見せ方を当てない
import { EMBEDDED_HTML_CLASS } from "@/shared/core/body-links";
import { h, markupIcon, type MarkupIconName } from "@/shared/core/dom-parts";

/** 本文のセクションの見せ方（表示の設定の切り替え） */
export type BodyView = {
  /** セクションの折りたたみ */
  fold: boolean;
};

/** 本文の見せ方の項目（表示の設定に並べる順） */
export const BODY_VIEW_KEYS: readonly (keyof BodyView)[] = ["fold"];

/** 表示の設定のチェックボックスと「この端末で変えている項目」に出す名前 */
export const BODY_VIEW_LABELS: Record<keyof BodyView, string> = {
  fold: "セクションの折りたたみ",
};

/** 個人の上書きが無いときの本文の見せ方（折りたたみはオン） */
export const BODY_VIEW_DEFAULT: BodyView = { fold: true };

/** 本文で使っている見出しの階層のうち、上からこの数の階層にだけ開閉を置く */
const FOLD_LEVELS = 2;

/** コードブロックのコピーのボタンを押した後、チェックのマーカーを出しておくミリ秒（図のコピーと同じ） */
const CODE_COPIED_MS = 1400;

/** mdmark が描いた Alert の囲みの種類（クラス `markdown-alert-{種類}`）→ 見出しの頭に置くアイコン */
const CALLOUT_KINDS: Record<string, MarkupIconName> = {
  note: "note",
  tip: "star",
  important: "flag",
  warning: "alert",
  caution: "alert",
};

/** 節の中身の入れ物の class（畳むと `hidden="until-found"` にする） */
const SECTION_BODY_CLASS = "md-section-body";

/** 節の中身の入れ物に振る id の通し番号 */
let sectionSeq = 0;

/** 見出しの階層（元の Markdown の階層。無ければ要素の階層） */
const headingLevel = (element: HTMLElement): number => {
  return Number(element.dataset["mdLevel"] ?? element.tagName.slice(1));
};

/** 見出しの要素か */
const isHeading = (element: Element): element is HTMLElement => {
  return /^H[1-6]$/.test(element.tagName);
};

/** 見出しの節の中身（次の同じか上の階層の見出しまで）を入れ物で包んで返す。中身が無ければ null */
const wrapSection = (heading: HTMLElement): HTMLElement | null => {
  const level = headingLevel(heading);
  const items: Element[] = [];
  for (
    let node = heading.nextElementSibling;
    node !== null && !(isHeading(node) && headingLevel(node) <= level);
    node = node.nextElementSibling
  ) {
    items.push(node);
  }
  if (items.length === 0) return null;
  const body = h({ tag: "div", attrs: { class: SECTION_BODY_CLASS, id: `md-section-${(sectionSeq += 1)}` } });
  heading.after(body);
  body.append(...items);
  return body;
};

/** 見出しを開く・畳む。畳んだ中身は `hidden="until-found"` にし、ページ内の検索の対象に残す */
const setFolded = ({ heading, folded }: { heading: HTMLElement; folded: boolean }): void => {
  const body = heading.nextElementSibling;
  if (body === null || !body.classList.contains(SECTION_BODY_CLASS)) return;
  heading.dataset["folded"] = String(folded);
  heading.querySelector(".md-fold")?.setAttribute("aria-expanded", String(!folded));
  if (folded) body.setAttribute("hidden", "until-found");
  else body.removeAttribute("hidden");
  // 本文の高さが変わったので、表の見出しの固定の位置を直す
  heading.closest(".panel-body")?.dispatchEvent(new Event("scroll"));
};

/** 本文の見出しの文言（# のリンクと開閉のボタンを除く） */
const headingLabel = (heading: HTMLElement): string => {
  return [...heading.childNodes]
    .filter((node) => !(node instanceof HTMLElement && node.matches(".h-link, .md-fold")))
    .map((node) => node.textContent ?? "")
    .join("")
    .trim();
};

/** 本文の見出しに開閉の矢印のボタンを置く（上位の `FOLD_LEVELS` 階層だけ）。節の中身を入れ物で包み、開いた状態で描く */
const addFoldButtons = (root: HTMLElement): void => {
  if (root.querySelector(".md-fold") !== null) return;
  const levels = [...new Set([...root.children].filter(isHeading).map(headingLevel))]
    .sort((a, b) => a - b)
    .slice(0, FOLD_LEVELS);
  // 上の階層から包む（下の階層の見出しは、上の階層の入れ物の中で包む）
  for (const level of levels) {
    for (const heading of root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")) {
      // その階層の見出しのうち、本文の直下か上の階層の入れ物の直下にあるものだけ
      const parent = heading.parentElement;
      if (headingLevel(heading) !== level || (parent !== root && parent?.classList.contains(SECTION_BODY_CLASS) !== true)) continue;
      const body = wrapSection(heading);
      if (body === null) continue;
      heading.dataset["folded"] = "false";
      heading.prepend(
        h({
          tag: "button",
          attrs: {
            class: "md-fold",
            type: "button",
            "aria-expanded": "true",
            "aria-controls": body.id,
            "aria-label": `${headingLabel(heading)}を開閉`,
            onclick: () => setFolded({ heading, folded: heading.dataset["folded"] !== "true" }),
          },
          children: [markupIcon("chev")],
        }),
      );
      // ページ内の検索・リンクで畳んだ中身に当たった: ブラウザが開く前に、見出しの開閉の状態を開いたにそろえる
      body.addEventListener("beforematch", () => setFolded({ heading, folded: false }));
    }
  }
};

/** 本文の中の見出しへ移る前に、その見出しを包む畳んだ入れ物を全て開く（開閉の矢印の `aria-expanded` も合わせる） */
export const revealHeading = ({ root, slug }: { root: ParentNode; slug: string }): void => {
  for (const target of root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)) {
    for (
      let body = target.closest<HTMLElement>(`.${SECTION_BODY_CLASS}`);
      body !== null;
      body = body.parentElement?.closest<HTMLElement>(`.${SECTION_BODY_CLASS}`) ?? null
    ) {
      const heading = body.previousElementSibling;
      if (heading instanceof HTMLElement && heading.dataset["folded"] === "true") setFolded({ heading, folded: false });
    }
  }
};

/** 要素が、埋め込んだ HTML の範囲（`.mdmark-html`）の中にあるか（範囲の中の要素には、表・コードブロック・Alert の見せ方を当てない） */
const inEmbeddedHtml = (element: Element): boolean => {
  return element.closest(`.${EMBEDDED_HTML_CLASS}`) !== null;
};

/** コードブロックを入れ物で包み、右上にコピーのボタン、言語を書いたものは左上に言語の札を置く（札とボタンはコードの文字に入れない） */
const decorateCodeBlocks = (root: HTMLElement): void => {
  for (const code of root.querySelectorAll<HTMLElement>("pre > code")) {
    const pre = code.parentElement as HTMLElement;
    if (pre.parentElement?.classList.contains("md-code") === true || inEmbeddedHtml(code)) continue;
    const lang = [...code.classList].find((name) => name.startsWith("language-"))?.slice("language-".length) ?? null;
    const status = h({ tag: "span", attrs: { class: "sr-only", role: "status" } });
    const copy = h({
      tag: "button",
      attrs: { class: "icon-btn code-copy", type: "button", "aria-label": "コードをコピー", title: "コピー" },
      children: [markupIcon("copy")],
    });
    copy.addEventListener("click", () => {
      void navigator.clipboard?.writeText(code.textContent ?? "").then(() => {
        copy.replaceChildren(markupIcon("check"));
        status.textContent = "コピーしました";
        window.setTimeout(() => {
          copy.replaceChildren(markupIcon("copy"));
          status.textContent = "";
        }, CODE_COPIED_MS);
      });
    });
    const box = h({ tag: "div", attrs: { class: lang === null ? "md-code" : "md-code has-lang" } });
    pre.replaceWith(box);
    box.append(...(lang === null ? [] : [h({ tag: "span", attrs: { class: "code-lang" }, children: [lang] })]), pre, copy, status);
  }
};

/** mdmark が描いた Alert の囲み（`div.markdown-alert`）の見出し（`p.markdown-alert-title`）の頭に、種類のアイコンを置く（置いてあれば重ねない） */
const decorateCallouts = (root: HTMLElement): void => {
  for (const callout of root.querySelectorAll<HTMLElement>("div.markdown-alert")) {
    if (inEmbeddedHtml(callout)) continue;
    const title = callout.querySelector<HTMLElement>(":scope > p.markdown-alert-title");
    const kind = [...callout.classList].find((name) => name.startsWith("markdown-alert-") && name !== "markdown-alert-title")?.slice("markdown-alert-".length);
    const name = kind === undefined ? undefined : CALLOUT_KINDS[kind];
    if (title === null || name === undefined || title.firstElementChild?.matches("svg.icon") === true) continue;
    title.prepend(markupIcon(name));
  }
};

/** 描いた本文に見せ方を当てる。`display` は表示の設定の値、`fold` は開閉を置ける本文か（本文の差分では偽にする）。表は `renderMarkdown` の `table` で mdmark の表の機能のまま描き、ここでは当てない */
export const decorateMarkdown = ({
  root,
  display = BODY_VIEW_DEFAULT,
  fold = true,
}: {
  root: HTMLElement;
  display?: BodyView;
  fold?: boolean;
}): void => {
  if (fold && display.fold) addFoldButtons(root);
  decorateCodeBlocks(root);
  decorateCallouts(root);
};
