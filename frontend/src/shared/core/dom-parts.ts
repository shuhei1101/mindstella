// mdmark が描いた本文の中へ足す要素の組み立て（React の外の DOM に手を入れる処理だけが使う）

type Attr = string | boolean | null | ((event: Event) => void);

/** 要素を作り、属性とイベントのリスナーを付け、子を並べる */
export const h = ({ tag, attrs = {}, children = [] }: { tag: string; attrs?: Record<string, Attr>; children?: (Node | string)[] }): HTMLElement => {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (typeof value === "function") element.addEventListener(name.slice(2), value);
    else if (value === true) element.setAttribute(name, "");
    else if (value !== null && value !== false) element.setAttribute(name, value);
  }
  element.append(...children);
  return element;
};

/** 本文の中の道具のアイコン（`shared/components/icon.tsx` と同じ絵） */
const MARKUP_ICONS = {
  hash: '<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
  expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="1"/><path d="M5 15V4a1 1 0 0 1 1-1h11"/>',
} as const;

/** 装飾のアイコンの SVG を作る */
export const markupIcon = (name: keyof typeof MARKUP_ICONS): SVGSVGElement => {
  const holder = document.createElement("template");
  holder.innerHTML = `<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${MARKUP_ICONS[name]}</svg>`;
  return holder.content.firstElementChild as SVGSVGElement;
};
