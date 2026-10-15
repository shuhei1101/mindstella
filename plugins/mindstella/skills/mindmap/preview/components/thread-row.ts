// スレッドの行。スレッドの一覧に並べる 1 件で、状態の札・題・向けた項目・最後の書き手と日時・レビュー中の印・タグを出し、押すとそのスレッドを開く。

namespace MindmapPreview {
  /** 書き手の呼び名 */
  export const AUTHOR_LABELS = { user: "あなた", ai: "AI" } as const;

  /** 状態の札の種類（レビュー中は、まだ送っていない新しいスレッド） */
  export type ThreadStateKind = Thread["status"] | "pending";

  /** スレッドの行の引数 */
  export type ThreadRowProps = {
    /** 送ったスレッド。`pending` とどちらか片方 */
    thread?: Thread | null;
    /** まだ送っていない新しいスレッドの最初の書き込み（状態の札を「レビュー中」にし、タグを出さない） */
    pending?: ReviewState["items"][number] | null;
    /** レビュー中の返信を持つか（2 行目の末尾にレビュー中の印を出す） */
    hasPendingReply?: boolean;
    /** 一覧を絞っているタグ（同じタグの札を押した状態にする） */
    activeTag?: string | null;
    on: {
      /** 行を押した（スレッドの ID。まだ送っていないものはコメントの ID と `pending: true`） */
      open: (id: string, pending: boolean) => void;
      /** タグを押した（タグ） */
      tag: (tag: string) => void;
    };
  };

  /** 状態の札の印と文言 */
  const STATE_LABELS: Record<ThreadStateKind, { icon: IconName; label: string }> = {
    open: { icon: "changed", label: "オープン" },
    closed: { icon: "check", label: "クローズ" },
    pending: { icon: "edit", label: "レビュー中" },
  };

  /** 本文の 1 行目 */
  function firstLine(body: string): string {
    return body.split("\n")[0];
  }

  /** 行と見出しに出す題（要約。まだ無ければ最初の書き込みの 1 行目） */
  export function threadTitle(thread: Thread): string {
    return thread.summary ?? firstLine(thread.posts[0].body);
  }

  /** 状態の札（色に加えて印と文字で区別する） */
  export function threadState(status: ThreadStateKind): HTMLElement {
    const { icon: name, label } = STATE_LABELS[status];
    return h({ tag: "span", attrs: { class: `th-state ${status}` }, children: [icon(name), label] });
  }

  /** レビュー中の印（レビュー中の返信を持つスレッドの行と、スレッドの中のレビュー中の書き込みに出す） */
  export function pendingMark(): HTMLElement {
    return h({ tag: "span", attrs: { class: "th-pending" }, children: [icon("edit"), "レビュー中"] });
  }

  /** 利用者の未読の書き込み（`seen` が偽）を持つか。`seen` を持たない書き込みは未読にしない */
  export function hasUnseen(thread: Thread): boolean {
    return thread.posts.some((post) => post.seen === false);
  }

  /** トップバーの未読の点に渡す値（オープンのスレッドに利用者の未読があるか。クローズの未読は数えない） */
  export function anyOpenUnseen(threads: Thread[]): boolean {
    return threads.some((thread) => thread.status === "open" && hasUnseen(thread));
  }

  /** 指したスレッドの書き込みを全て既読にした新しい並び（渡した並びは書き換えない。ID が無ければ同じ中身の並び） */
  export function withSeen(threads: Thread[], id: string): Thread[] {
    return threads.map((thread) =>
      thread.id === id ? { ...thread, posts: thread.posts.map((post) => ({ ...post, seen: true })) } : thread,
    );
  }

  /** 未読の札（塗りつぶしの形・点の印・「未読」の文字で示す。状態の札の線の枠、レビュー中の印の破線の枠と形で見分ける） */
  function unseenMark(): HTMLElement {
    return h({
      tag: "span",
      attrs: { class: "th-unread" },
      children: [h({ tag: "span", attrs: { class: "dot", "aria-hidden": "true" } }), "未読"],
    });
  }

  /** タグの札（行を開くボタンとは別のボタン。押すとそのタグで絞る） */
  function tagButton({ thread, tag, active, onTag }: { thread: Thread; tag: string; active: boolean; onTag: (tag: string) => void }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: `th-tag${active ? " on" : ""}`,
        type: "button",
        "aria-pressed": String(active),
        "aria-label": `タグ「${tag}」で絞る`,
        "data-focus": `tag:${thread.id}:${tag}`,
        onclick: () => onTag(tag),
      },
      children: [icon("hash"), tag],
    });
  }

  /** スレッドの行（`li`）を返す。送ったスレッドと、まだ送っていない新しいスレッドのどちらも同じ形で描く */
  export function threadRow({ thread = null, pending = null, hasPendingReply = false, activeTag = null, on }: ThreadRowProps): HTMLElement {
    const last = thread === null ? null : thread.posts[thread.posts.length - 1];
    const sent = thread !== null && last !== null;
    const id = sent ? thread.id : (pending?.id ?? "");
    const target = sent ? thread.target : (pending?.target ?? null);
    const author = sent ? last.author : "user";
    const created = sent ? last.created : (pending?.created ?? "");
    const title = sent ? threadTitle(thread) : firstLine(pending?.body ?? "");
    const summarized = sent && thread.summary !== null;
    const status: ThreadStateKind = sent ? thread.status : "pending";
    const unseen = sent && hasUnseen(thread);
    // 未読の行は、読み上げの名前が状態の次に「未読」を読む
    const openLabel = unseen
      ? [STATE_LABELS[status].label, "未読", title, target, AUTHOR_LABELS[author], formatJst(created), hasPendingReply ? "レビュー中の返信あり" : null]
          .filter((part) => part !== null)
          .join("、")
      : null;
    return h({
      tag: "li",
      attrs: sent ? { class: `th-row${unseen ? " unread" : ""}`, "data-thread": id } : { class: "th-row pending", "data-pending": id },
      children: [
        h({
          tag: "button",
          attrs: {
            class: "th-open",
            type: "button",
            "aria-label": openLabel,
            "data-focus": sent ? `thread:${id}` : `thread:new:${id}`,
            onclick: () => on.open(id, !sent),
          },
          children: [
            h({
              tag: "span",
              attrs: { class: "th-line1" },
              children: [threadState(status), h({ tag: "span", attrs: { class: `th-title${summarized ? "" : " head"}` }, children: [title] })],
            }),
            h({
              tag: "span",
              attrs: { class: "th-line2" },
              children: [
                unseen ? unseenMark() : null,
                target === null ? null : h({ tag: "span", attrs: { class: "mono" }, children: [target] }),
                h({ tag: "span", attrs: { class: "th-author" }, children: [AUTHOR_LABELS[author]] }),
                h({ tag: "time", attrs: { datetime: created }, children: [formatJst(created)] }),
                hasPendingReply ? pendingMark() : null,
              ],
            }),
          ],
        }),
        !sent || thread.tags.length === 0
          ? null
          : h({
            tag: "span",
            attrs: { class: "th-tags" },
            children: thread.tags.map((tag) => tagButton({ thread, tag, active: tag === activeTag, onTag: on.tag })),
          }),
      ],
    });
  }
}
