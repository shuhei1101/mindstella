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

  /** 本文の切り分けの 1 部分（文字か、記録にある項目の ID か、記録にあるまとまりを指すリンク） */
  export type PostBodyPart = { text: string } | { id: string; title: string } | { set: string; label: string; summary: string };

  /** 本文の中の項目の ID（例 D-1・T-12・A-3） */
  const ITEM_ID_PATTERN = /\b[A-Z]{1,2}-\d+\b/g;

  /** 本文の中の `[文言](#...)` のリンク（文言は 1 行、`#` の後ろは空白と `)` を含まない） */
  const HASH_LINK_PATTERN = /\[([^\]\n]+)\]\(#([^)\s]*)\)/g;

  /** 文字の中の項目の ID のうち、記録にあるものだけを切り出す（残りは文字のまま、前後の文字が無ければ部分を作らない） */
  function splitItemIds(text: string, titles: (id: string) => string | null): PostBodyPart[] {
    const parts: PostBodyPart[] = [];
    let last = 0;
    for (const match of text.matchAll(ITEM_ID_PATTERN)) {
      const title = titles(match[0]);
      // 記録に無い ID（スレッドの ID を含む）は文字のまま残す
      if (title === null) continue;
      const before = text.slice(last, match.index);
      if (before !== "") parts.push({ text: before });
      parts.push({ id: match[0], title });
      last = match.index + match[0].length;
    }
    const rest = text.slice(last);
    if (rest !== "") parts.push({ text: rest });
    return parts;
  }

  /** 書き込みの本文を、文字の部分・記録にある項目の ID の部分・記録にあるまとまりを指すリンクの部分に切り分ける（リンクの部分を `[文言](#...)` に戻してつなぐと元の本文になる） */
  export function splitPostBody(
    body: string,
    titles: (id: string) => string | null,
    changeSets: (id: string) => string | null = () => null,
  ): PostBodyPart[] {
    const parts: PostBodyPart[] = [];
    let last = 0;
    for (const match of body.matchAll(HASH_LINK_PATTERN)) {
      // `diff` だけを読む（他の引数は無視する）。記録にあるまとまりを指さないリンクは文字のまま残す
      const set = new URLSearchParams(match[2]).get("diff");
      const summary = set === null ? null : changeSets(set);
      if (set === null || summary === null) continue;
      parts.push(...splitItemIds(body.slice(last, match.index), titles));
      parts.push({ set, label: match[1], summary });
      last = match.index + match[0].length;
    }
    parts.push(...splitItemIds(body.slice(last), titles));
    // 部分が 1 つも無い（空の本文）
    if (parts.length === 0) parts.push({ text: "" });
    return parts;
  }

  /** 本文（改行を保った文字。項目の ID はその項目を開くボタン、記録にあるまとまりを指すリンクはまとまりのリンク） */
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
    return h({
      tag: "p",
      attrs: { class: className },
      children: splitPostBody(body, titles, changeSets).map((part) => {
        if ("id" in part) {
          return h({
            tag: "button",
            attrs: { class: "idlink", type: "button", title: part.title, "data-focus": `post-id:${part.id}`, onclick: () => on.openId(part.id) },
            children: [part.id],
          });
        }
        if ("set" in part) {
          return h({
            tag: "a",
            attrs: {
              class: "setlink",
              href: `#${new URLSearchParams({ diff: part.set }).toString()}`,
              title: part.summary,
              "data-focus": `post-set:${part.set}`,
              onclick: (event: Event) => {
                // ハッシュの書き換えは使う側に任せる
                event.preventDefault();
                on.changeSet(part.set);
              },
            },
            children: [part.label],
          });
        }
        return part.text;
      }),
    });
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
