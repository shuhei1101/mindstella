// mdmark が描いた本文の中へ足す要素の組み立て（React の外の DOM に手を入れる処理だけが使う）

type Attr = string | number | boolean | null | undefined | ((event: MouseEvent) => void);

/** 要素を作り、属性とイベントのリスナーを付け、子を並べる */
export const h = ({ tag, attrs = {}, children = [] }: { tag: string; attrs?: Record<string, Attr>; children?: (Node | string | null | undefined)[] }): HTMLElement => {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (typeof value === "function") element.addEventListener(name.slice(2), value as EventListener);
    else if (value === true) element.setAttribute(name, "");
    else if (value !== null && value !== undefined && value !== false) element.setAttribute(name, String(value));
  }
  element.append(...children.filter((child) => child !== null && child !== undefined));
  return element;
};

/** 本文の中の道具のアイコン（`shared/components/icon.tsx` と同じ絵） */
const MARKUP_ICONS = {
  hash: '<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
  expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="1"/><path d="M5 15V4a1 1 0 0 1 1-1h11"/>',
  check: '<path d="m5 12 5 5L20 7"/>',
  chev: '<path d="m9 6 6 6-6 6"/>',
  pin: '<path d="M12 17v5M9 3h6l-1 7 3 4H7l3-4z"/>',
  note: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  star: '<path d="m12 3 2.7 5.8 6.3.8-4.6 4.3 1.2 6.2-5.6-3.1-5.6 3.1 1.2-6.2L3 9.6l6.3-.8z"/>',
  flag: '<path d="M5 21V4h13l-3 4 3 4H5"/>',
  alert: '<path d="M12 3 2 20h20zM12 10v4M12 17h.01"/>',
  changed: '<circle cx="12" cy="12" r="4"/>',
} as const;

/** 本文の中の道具のアイコンの名前 */
export type MarkupIconName = keyof typeof MARKUP_ICONS;

/** 装飾のアイコンの SVG を作る */
export const markupIcon = (name: MarkupIconName): SVGSVGElement => {
  const holder = document.createElement("template");
  holder.innerHTML = `<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${MARKUP_ICONS[name]}</svg>`;
  return holder.content.firstElementChild as SVGSVGElement;
};
