// スレッドの書き込み。スレッドの中に書いた順で並べる 1 件で、利用者と AI の書き込み・クローズとオープンへの戻しの記録・レビュー中の書き込みのどれか 1 つを出す。

namespace MindmapPreview {
  /** 書き込み・状態の記録・レビュー中の書き込みの引数（`post`・`event`・`pending` のどれか 1 つを渡す） */
  export type ThreadPostProps = {
    post?: Thread["posts"][number] | null;
    event?: Thread["events"][number] | null;
    pending?: ReviewState["items"][number] | null;
    /** 項目のタイトル（記録に無ければ null）。あるものだけ、本文の中の ID を項目を開くボタンにする */
    titles?: (id: string) => string | null;
    /** レビュー中の書き込みを書き換えているか */
    editing?: boolean;
    /** 直せなかったときに入力欄に残す中身 */
    editBody?: string | null;
    /** 直せなかった理由 */
    editError?: string | null;
    on: {
      /** 本文の中の項目の ID を押した */
      openId: (id: string) => void;
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

  /** 本文の切り分けの 1 部分（文字か、記録にある項目の ID） */
  export type PostBodyPart = { text: string } | { id: string; title: string };

  /** 本文の中の項目の ID（例 D-1・T-12・A-3） */
  const ITEM_ID_PATTERN = /\b[A-Z]{1,2}-\d+\b/g;

  /** 書き込みの本文を、文字の部分と記録にある項目の ID の部分に切り分ける（つなぐと元の本文になる） */
  export function splitPostBody(body: string, titles: (id: string) => string | null): PostBodyPart[] {
    const parts: PostBodyPart[] = [];
    let last = 0;
    for (const match of body.matchAll(ITEM_ID_PATTERN)) {
      const title = titles(match[0]);
      // 記録に無い ID（スレッドの ID を含む）は文字のまま残す
      if (title === null) continue;
      const before = body.slice(last, match.index);
      if (before !== "") parts.push({ text: before });
      parts.push({ id: match[0], title });
      last = match.index + match[0].length;
    }
    const rest = body.slice(last);
    // 残りの文字がある、または部分が 1 つも無い（空の本文）
    if (rest !== "" || parts.length === 0) parts.push({ text: rest });
    return parts;
  }

  /** 本文（改行を保った文字。項目の ID はその項目を開くボタン） */
  function postBody({ body, titles, onOpenId }: { body: string; titles: (id: string) => string | null; onOpenId: (id: string) => void }): HTMLElement {
    return h({
      tag: "p",
      attrs: { class: "post-body" },
      children: splitPostBody(body, titles).map((part) =>
        "id" in part
          ? h({
            tag: "button",
            attrs: { class: "idlink", type: "button", title: part.title, "data-focus": `post-id:${part.id}`, onclick: () => onOpenId(part.id) },
            children: [part.id],
          })
          : part.text,
      ),
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
    editing,
    editBody,
    editError,
    on,
  }: {
    item: ReviewState["items"][number];
    titles: (id: string) => string | null;
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
          : postBody({ body: item.body, titles, onOpenId: on.openId }),
      ],
    });
  }

  /** スレッドの書き込み・状態の記録・レビュー中の書き込みのどれか 1 つの `li` を返す */
  export function threadPost({
    post = null,
    event = null,
    pending = null,
    titles = () => null,
    editing = false,
    editBody = null,
    editError = null,
    on,
  }: ThreadPostProps): HTMLElement {
    // 状態の記録
    if (event !== null) return eventItem(event);
    // レビュー中の書き込み
    if (pending !== null) return pendingItem({ item: pending, titles, editing, editBody, editError, on });
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
        postBody({ body: post.body, titles, onOpenId: on.openId }),
      ],
    });
  }
}
