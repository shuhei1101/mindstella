// スレッドの書き込み。スレッドの中に書いた順で並べる 1 件で、利用者と AI の書き込み・クローズとオープンへの戻しの記録・レビュー中の書き込みのどれか 1 つを出す。

namespace MindmapPreview {
  /** 書き込み・状態の記録・レビュー中の書き込みの引数（`post`・`event`・`pending` のどれか 1 つを渡す） */
  export type ThreadPostProps = {
    post?: Thread["posts"][number] | null;
    event?: Thread["events"][number] | null;
    pending?: ReviewState["items"][number] | null;
    /** 項目のタイトル（記録に無ければ null）。あるものだけ、本文の中の ID を項目を開くボタンにする */
    titles?: (id: string) => string | null;
    /** まとまりの説明（記録に無ければ null）。あるまとまりを指す本文の `[文言](#diff=...)` を、まとまりのリンクにする */
    changeSets?: (id: string) => string | null;
    /** レビュー中の書き込みを書き換えているか */
    editing?: boolean;
    /** 直せなかったときに入力欄に残す中身 */
    editBody?: string | null;
    /** 直せなかった理由 */
    editError?: string | null;
    on: {
      /** 本文の中の項目の ID を押した */
      openId: (id: string) => void;
      /** 本文の中のまとまりのリンクを押した（まとまりの ID） */
      changeSet: (id: string) => void;
      /** レビュー中の書き込みの修正を始める */
      edit: (id: string) => void;
      /** 書き換えを送る */
      saveEdit: (id: string, body: string) => void;
      /** 書き換えをやめる */
      cancelEdit: () => void;
      /** レビュー中の書き込みを消す */
      remove: (id: string) => void;
    };
  };

  /** 本文の中の項目の ID（例 D-1・T-12・A-3） */
  const ITEM_ID_PATTERN = /\b[A-Z]{1,2}-\d+\b/g;

  /** 項目の ID をボタンにしない文字の置き場所（コード・リンク・ボタン・図・HTML の本文の枠の中） */
  const ITEM_ID_SKIPPED = `pre, code, a, button, figure.diagram, .${HTML_BLOCK_CLASS}`;

  /** 描いた本文の中の `#` で始まるリンクのうち、記録にあるまとまりを指すもの（`diff` の値を `changeSets` で引けたもの）をまとまりのリンクにし、それ以外は中の文字に置き換える。押したときは既定の動作を止め、まとまりの ID を `onChangeSet` に知らせる。`#` で始まらないリンクは触らない */
  function linkChangeSets({
    root,
    changeSets,
    onChangeSet,
  }: {
    root: HTMLElement;
    changeSets: (id: string) => string | null;
    onChangeSet: (id: string) => void;
  }): void {
    for (const link of root.querySelectorAll<HTMLAnchorElement>("a")) {
      const href = link.getAttribute("href") ?? "";
      if (!href.startsWith("#")) continue;
      // `diff` だけを読む（他の引数は無視する）
      const set = new URLSearchParams(href.slice(1)).get("diff");
      const summary = set === null ? null : changeSets(set);
      // 記録にあるまとまりを指さないリンクは、リンクにせず文言だけを出す
      if (set === null || summary === null) {
        link.replaceWith(...link.childNodes);
        continue;
      }
      link.className = "setlink";
      link.setAttribute("href", `#${new URLSearchParams({ diff: set }).toString()}`);
      link.title = summary;
      link.setAttribute("data-focus", `post-set:${set}`);
      link.addEventListener("click", (event) => {
        // ハッシュの書き換えは使う側に任せる
        event.preventDefault();
        onChangeSet(set);
      });
    }
  }

  /** 描いた本文の文字のうち、記録にある項目の ID を、その項目を開くボタンにする（コード・リンク・ボタン・図・HTML の本文の枠の中は飛ばす。記録に無い ID とスレッドの ID は文字のまま） */
  function buttonizeItemIds({
    root,
    titles,
    onOpen,
  }: {
    root: HTMLElement;
    titles: (id: string) => string | null;
    onOpen: (id: string) => void;
  }): void {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => (node.parentElement?.closest(ITEM_ID_SKIPPED) !== null ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    const nodes: Text[] = [];
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) nodes.push(node as Text);
    for (const node of nodes) {
      const text = node.textContent ?? "";
      const parts: (Node | string)[] = [];
      let last = 0;
      for (const match of text.matchAll(ITEM_ID_PATTERN)) {
        const title = titles(match[0]);
        // 記録に無い ID（スレッドの ID を含む）は文字のまま残す
        if (title === null) continue;
        parts.push(
          text.slice(last, match.index),
          h({
            tag: "button",
            attrs: { class: "idlink", type: "button", title, "data-focus": `post-id:${match[0]}`, onclick: () => onOpen(match[0]) },
            children: [match[0]],
          }),
        );
        last = match.index + match[0].length;
      }
      if (parts.length === 0) continue;
      parts.push(text.slice(last));
      node.replaceWith(...parts.filter((part) => part !== ""));
    }
  }

  /** 本文を、段落の中の改行を強制改行にして Markdown として描いた要素（項目の ID はその項目を開くボタン、記録にあるまとまりを指すリンクはまとまりのリンク）。mdmark が読めないときは、本文を文字のまま改行を保って持つ要素 */
  export function postBody({
    body,
    titles,
    changeSets,
    className,
    on,
  }: {
    body: string;
    titles: (id: string) => string | null;
    changeSets: (id: string) => string | null;
    className: "post-body" | "review-body";
    on: { openId: (id: string) => void; changeSet: (id: string) => void };
  }): HTMLElement {
    // 読めない: 知らせは出さず、項目の ID とまとまりのリンクも作らない
    if (missingLibraries(["mdmark"]).length > 0) return h({ tag: "p", attrs: { class: className }, children: [body] });
    const root = withoutLineMarks(renderMarkdown(withHardBreaks(body)));
    root.classList.add(className);
    // 図は描き終えるのを待たずに返す
    void renderDiagrams(root);
    for (const block of root.querySelectorAll<HTMLElement>(`.${HTML_BLOCK_CLASS}`)) {
      const frame = htmlBodyFrame({ source: block.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "", selectable: false, label: "html のコードブロック" });
      frame.classList.add(HTML_BLOCK_CLASS);
      block.replaceWith(frame);
    }
    decorateMarkdown({ root, fold: false, tables: false });
    linkChangeSets({ root, changeSets, onChangeSet: on.changeSet });
    buttonizeItemIds({ root, titles, onOpen: on.openId });
    return root;
  }

  /** 状態の記録（枠の無い 1 行に、書き手・したこと・日時と、あれば理由） */
  function eventItem(event: Thread["events"][number]): HTMLElement {
    const closed = event.kind === "closed";
    const who = event.author === "ai" ? "AI が" : "あなたが";
    return h({
      tag: "li",
      attrs: { class: `th-event ${event.author}`, "data-event": event.kind },
      children: [
        h({
          tag: "div",
          attrs: { class: "th-event-line" },
          children: [
            icon(closed ? "check" : "undo"),
            h({ tag: "span", children: [`${who}${closed ? "クローズにしました" : "オープンに戻しました"}`] }),
            h({ tag: "time", attrs: { datetime: event.created }, children: [formatJst(event.created)] }),
          ],
        }),
        event.reason === null ? null : h({ tag: "p", attrs: { class: "th-event-reason" }, children: [event.reason] }),
      ],
    });
  }

  /** レビュー中の書き込み（破線の枠と「レビュー中」の印を付け、右上に「修正」「削除」を置く） */
  function pendingItem({
    item,
    titles,
    changeSets,
    editing,
    editBody,
    editError,
    on,
  }: {
    item: ReviewState["items"][number];
    titles: (id: string) => string | null;
    changeSets: (id: string) => string | null;
    editing: boolean;
    editBody: string | null;
    editError: string | null;
    on: ThreadPostProps["on"];
  }): HTMLElement {
    return h({
      tag: "li",
      attrs: { class: "post user pending", "data-comment": item.id },
      children: [
        h({
          tag: "div",
          attrs: { class: "post-head" },
          children: [
            h({ tag: "span", attrs: { class: "post-author" }, children: [AUTHOR_LABELS.user] }),
            pendingMark(),
            h({ tag: "span", attrs: { class: "spacer" } }),
            editing ? null : reviewRowActions({ item, focus: "", on: { edit: on.edit, remove: on.remove } }),
          ],
        }),
        editing
          ? reviewEditForm({ item, body: editBody, error: editError, focus: "", on: { saveEdit: on.saveEdit, cancelEdit: on.cancelEdit } })
          : postBody({ body: item.body, titles, changeSets, className: "post-body", on: { openId: on.openId, changeSet: on.changeSet } }),
      ],
    });
  }

  /** スレッドの書き込み・状態の記録・レビュー中の書き込みのどれか 1 つの `li` を返す */
  export function threadPost({
    post = null,
    event = null,
    pending = null,
    titles = () => null,
    changeSets = () => null,
    editing = false,
    editBody = null,
    editError = null,
    on,
  }: ThreadPostProps): HTMLElement {
    // 状態の記録
    if (event !== null) return eventItem(event);
    // レビュー中の書き込み
    if (pending !== null) return pendingItem({ item: pending, titles, changeSets, editing, editBody, editError, on });
    // 書き込みが無い（渡し方の誤り）
    if (post === null) throw new Error("threadPost には post・event・pending のどれか 1 つを渡す");
    return h({
      tag: "li",
      attrs: { class: `post ${post.author}` },
      children: [
        h({
          tag: "div",
          attrs: { class: "post-head" },
          children: [
            h({ tag: "span", attrs: { class: "post-author" }, children: [AUTHOR_LABELS[post.author]] }),
            h({ tag: "time", attrs: { datetime: post.created }, children: [formatJst(post.created)] }),
          ],
        }),
        postBody({ body: post.body, titles, changeSets, className: "post-body", on: { openId: on.openId, changeSet: on.changeSet } }),
      ],
    });
  }
}
