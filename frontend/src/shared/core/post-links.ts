// スレッドの書き込みとレビュー中の書き込みの描いた本文に、項目の ID のボタンとまとまりのリンクを付ける（今の画面の `components/thread-post.ts` と同じ振る舞い）
import { HTML_BLOCK_CLASS } from "@/shared/core/body-links";

/** 本文の中の項目の ID（例 D-1・T-12・A-3） */
const ITEM_ID_PATTERN = /\b[A-Z]{1,2}-\d+\b/g;

/** 項目の ID をボタンにしない文字の置き場所（コード・リンク・ボタン・図・HTML の本文の枠の中） */
const ITEM_ID_SKIPPED = `pre, code, a, button, figure.diagram, .${HTML_BLOCK_CLASS}`;

/** 引いた先の名前（記録に無ければ null） */
export type LookupTitle = (id: string) => string | null;

/** `#` で始まるリンクのうち、記録にあるまとまりを指すものをまとまりのリンクにし、それ以外は中の文字に置き換える */
export const linkChangeSets = ({ root, changeSets, onChangeSet }: { root: HTMLElement; changeSets: LookupTitle; onChangeSet: (id: string) => void }): void => {
  for (const link of root.querySelectorAll<HTMLAnchorElement>("a")) {
    const href = link.getAttribute("href") ?? "";
    if (!href.startsWith("#")) continue;
    // `diff` だけを読む（他の引数は無視する）
    const set = new URLSearchParams(href.slice(1)).get("diff");
    const summary = set === null ? null : changeSets(set);
    if (set === null || summary === null) {
      link.replaceWith(...link.childNodes);
      continue;
    }
    link.className = "setlink";
    link.setAttribute("href", `#${new URLSearchParams({ diff: set }).toString()}`);
    link.title = summary;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      onChangeSet(set);
    });
  }
};

/** 描いた本文の文字のうち、記録にある項目の ID をその項目を開くボタンにする（記録に無い ID とスレッドの ID は文字のまま） */
export const buttonizeItemIds = ({ root, titles, onOpen }: { root: HTMLElement; titles: LookupTitle; onOpen: (id: string) => void }): void => {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => (node.parentElement?.closest(ITEM_ID_SKIPPED) === null ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
  });
  const nodes: Text[] = [];
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) nodes.push(node as Text);
  for (const node of nodes) {
    const text = node.textContent ?? "";
    const parts: (Node | string)[] = [];
    let last = 0;
    for (const match of text.matchAll(ITEM_ID_PATTERN)) {
      const title = titles(match[0]);
      if (title === null) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "idlink";
      button.title = title;
      button.textContent = match[0];
      button.addEventListener("click", () => {
        onOpen(match[0]);
      });
      parts.push(text.slice(last, match.index), button);
      last = match.index + match[0].length;
    }
    if (parts.length === 0) continue;
    parts.push(text.slice(last));
    node.replaceWith(...parts.filter((part) => part !== ""));
  }
};
