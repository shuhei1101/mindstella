// コメントの一覧。見ている画面に重ねて左から出すパネルで、スレッドの一覧・スレッド 1 件・レビュー中の書き込みの 3 つの画面を切り替える。

namespace MindmapPreview {
  /** レビュー中の書き込み 1 件（新しいスレッドの最初の書き込みか、スレッドへの返信） */
  export type ReviewItem = ReviewState["items"][number];

  /** まとめて送った結果 */
  export type SendOutcome = {
    kind: "sending" | "sent" | "failed" | "stale";
    /** 送った件数・送れない件数 */
    count?: number;
    /** 送った日時 */
    at?: string;
    /** サーバーが返した理由（届かなかったときは無い） */
    detail?: string | null;
    /** 届いた件数を Claude Code へ入力し、会話の記録に入ったか（`sent` だけが持つ） */
    entered?: boolean;
  };

  /** スレッドの状態の絞り込み */
  export type ThreadFilter = "open" | "closed" | "all";

  /** パネルの中に出す画面 */
  export type PanelView = "list" | "thread" | "review";

  /** 開いているスレッド（`pending` が真なら `id` はまだ送っていない新しいスレッドのコメントの ID） */
  export type OpenedThread = { id: string; pending: boolean };

  /** 返信の入力の状態 */
  export type ReplyState = { body: string; status: ReplyStatus; count: number | null; detail: string | null };

  /** 理由の入力の状態（`failed` で `detail` が null なら届かなかった） */
  export type ReasonState = { open: boolean; body: string; status: "idle" | "saving" | "failed"; detail: string | null };

  /** コメントの一覧の引数 */
  export type CommentsPanelProps = {
    /** パネルの中に出す画面 */
    view: PanelView;
    /** レビュー中の書き込み（新しいスレッドと返信） */
    items: ReviewItem[];
    /** パネルを開いている間に消した書き込み（元の場所に「元に戻す」を出す） */
    removed: ReviewItem[];
    /** 最後に読めたスレッド */
    threads: Thread[];
    /** スレッドを読めなかったときの理由（届かなければ `detail` が null）。読めていれば null */
    threadsError: { detail: string | null } | null;
    /** 状態の絞り込み */
    filter: ThreadFilter;
    /** 絞っているタグ */
    tag: string | null;
    /** 開いているスレッド */
    opened: OpenedThread | null;
    /** 新しいスレッドの入力を出しているか */
    composing: boolean;
    /** 新しいスレッドの入力の引数（`target: null`・`label: "新しいスレッド"`） */
    free: SendFormProps;
    /** 開いているスレッドの返信の入力の引数 */
    reply: ReplyState;
    /** 理由の入力の状態 */
    reason: ReasonState;
    /** チェックした書き込みの ID */
    checked: Set<string>;
    /** 本文を書き換えている書き込みの ID */
    editing: string | null;
    /** `editing` の修正を始めた場所（既定は一覧）。詳細パネルで始めたときは、その行を本文だけで描いて「修正」「削除」を出さない */
    editingIn?: EditingIn;
    /** 本文を直せなかった理由 */
    editError?: string | null;
    /** 本文を直せなかったとき、入力欄に残す直していた中身（無ければ元の本文） */
    editBody?: string | null;
    /** 送れなかった書き込みの ID → 理由 */
    stale: Map<string, string>;
    result: SendOutcome | null;
    /** 行から開いて詳細パネルに出している書き込みの ID（選んだ見た目にする） */
    selected: string | null;
    /** スレッドの画面からレビュー中の書き込みを開いたときの、そのスレッドの ID（そのスレッドの書き込みの行を示す） */
    reviewFocus: string | null;
    /** 項目のタイトル（記録から消えていれば null。押せない ID だけを出し、箇所を外すを出さない） */
    titleOf: (id: string) => string | null;
    /** まとまりの説明（記録の `changes.sets` に無ければ null。あるまとまりを指す本文の `[文言](#diff=...)` を、まとまりのリンクにする） */
    changeSetOf: (id: string) => string | null;
    /** 本文を開いているレビュー中の書き込みの ID */
    expanded: Set<string>;
    on: {
      close: () => void;
      /** レビュー中の書き込みの画面を開く */
      review: () => void;
      /** 一覧（スレッドの画面から）か、開く前の画面（レビュー中の書き込みの画面から）へ戻る */
      back: () => void;
      /** 状態で絞る */
      filter: (filter: ThreadFilter) => void;
      /** タグで絞る（絞っているタグなら外す） */
      tag: (tag: string) => void;
      clearTag: () => void;
      /** 新しいスレッドの入力を出す（真）／畳む（偽） */
      compose: (open: boolean) => void;
      /** スレッドを開く（まだ送っていない新しいスレッドはコメントの ID と `pending: true`） */
      openThread: (id: string, pending: boolean) => void;
      /** 項目を開く（本文の中の ID・スレッドの向けた項目。向けた項目の箇所があれば渡す） */
      openId: (id: string, loc?: Location) => void;
      /** 本文の中のまとまりのリンクを押した（まとまりの ID） */
      changeSet: (id: string) => void;
      /** 返信を溜める（スレッドの ID と本文） */
      reply: (thread: string, body: string) => void;
      replyInput: (body: string) => void;
      /** 理由の入力を出す（真）／閉じる（偽） */
      reasonOpen: (open: boolean) => void;
      reasonInput: (body: string) => void;
      /** スレッドの状態を変える（変えた後の状態と理由） */
      setStatus: (status: "open" | "closed", reason: string) => void;
      check: (id: string, checked: boolean) => void;
      checkAll: (checked: boolean) => void;
      send: () => void;
      /** 行の向けた項目を開く（箇所があればその箇所を示す） */
      open: (item: ReviewItem) => void;
      edit: (id: string) => void;
      saveEdit: (id: string, body: string) => void;
      cancelEdit: () => void;
      remove: (id: string) => void;
      restore: (id: string) => void;
      unloc: (id: string) => void;
      /** 行の本文を開く（真）／畳む（偽）（書き込みの ID と、開くか） */
      fold: (id: string, open: boolean) => void;
    };
  };

  /** コメントの本文の長さの上限（サーバーが受け付ける文字数と同じ） */
  export const COMMENT_BODY_MAX_LENGTH = 10000;

  /** 状態を変える理由の長さの上限（サーバーが受け付ける文字数と同じ） */
  const REASON_MAX_LENGTH = 400;

  /** 本文の書き換えを始めた場所（入力欄はその場所だけに描き、もう一方は本文だけで描く） */
  export type EditingIn = "list" | "detail";

  /** 詳細パネルが行の修正・削除・元に戻すのために受け取る引数（コールバックはコメントの一覧と同じ形） */
  export type ReviewEditProps = {
    /** その項目へのコメントのうち、消したもの（元の場所に「元に戻す」を出す） */
    removed: ReviewItem[];
    /** 本文を書き換えているコメントの ID（一覧と詳細パネルで 1 つ） */
    editing: string | null;
    /** `editing` の修正を始めた場所 */
    editingIn: EditingIn;
    /** 本文を直せなかった理由 */
    editError: string | null;
    /** 本文を直せなかったとき、入力欄に残す書き換えていた中身（無ければ元の本文） */
    editBody: string | null;
    on: {
      edit: (id: string) => void;
      saveEdit: (id: string, body: string) => void;
      cancelEdit: () => void;
      remove: (id: string) => void;
      restore: (id: string) => void;
    };
  };

  /** コメントの ID の連番 */
  export function commentNumber(id: string): number {
    return Number(id.replace(/^\D+-/, ""));
  }

  /** スレッドの ID の連番 */
  function threadNumber(id: string): number {
    return Number(id.replace(/^\D+-/, ""));
  }

  /** 日時の前後（ISO 8601 を時刻として比べる） */
  function byTime(a: string, b: string): number {
    return Date.parse(a) - Date.parse(b);
  }

  /** スレッドの最後の書き込みの日時 */
  function lastCreated(thread: Thread): string {
    return thread.posts[thread.posts.length - 1].created;
  }

  /** スレッドを状態とタグで絞り、最後の書き込みの新しい順に並べる（渡した配列は変えない） */
  export function visibleThreads(threads: Thread[], filter: ThreadFilter, tag: string | null): Thread[] {
    return threads
      .filter((thread) => filter === "all" || thread.status === filter)
      .filter((thread) => tag === null || thread.tags.includes(tag))
      .sort((a, b) => byTime(lastCreated(b), lastCreated(a)) || threadNumber(b.id) - threadNumber(a.id));
  }

  /** タグで絞ったスレッドの、状態の絞り込みに出す件数 */
  export function threadCounts(threads: Thread[], tag: string | null): { open: number; closed: number; all: number } {
    const tagged = tag === null ? threads : threads.filter((thread) => thread.tags.includes(tag));
    const open = tagged.filter((thread) => thread.status === "open").length;
    return { open, closed: tagged.length - open, all: tagged.length };
  }

  /** レビュー中の書き込みのうち、一覧の先頭に出す新しいスレッドの最初の書き込み（クローズの絞り込みとタグの絞り込みでは出さない） */
  export function pendingThreads(items: ReviewItem[], filter: ThreadFilter, tag: string | null): ReviewItem[] {
    if (filter === "closed" || tag !== null) return [];
    return items.filter((item) => item.thread === null);
  }

  /** レビュー中の書き込みが、クローズのスレッドへの返信か（スレッドが見つからなければ偽。サーバーが 409 で返す） */
  export function isBlockedReply(item: ReviewItem, threads: Thread[]): boolean {
    if (item.thread === null) return false;
    return threads.find((thread) => thread.id === item.thread)?.status === "closed";
  }

  /** スレッドの書き込みと状態の記録を、日時の順の 1 本の並びにする（同じ日時は書き込みを先にし、それぞれの中の並びを保つ） */
  export function threadTimeline(thread: Thread): ({ post: Thread["posts"][number] } | { event: Thread["events"][number] })[] {
    const entries = [
      ...thread.posts.map((post) => ({ post, at: post.created, rank: 0 })),
      ...thread.events.map((event) => ({ event, at: event.created, rank: 1 })),
    ];
    return entries.sort((a, b) => byTime(a.at, b.at) || a.rank - b.rank);
  }

  /** 送った結果の文言（印と文）。結果が無いときは null */
  function outcomeContent({ result, checkedCount }: { result: SendOutcome | null; checkedCount: number }): Child[] | null {
    if (result === null) {
      // チェックが 0 件
      return checkedCount === 0 ? [icon("alert"), h({ tag: "span", children: ["送る書き込みにチェックを付けてください。"] })] : null;
    }
    if (result.kind === "sending") {
      return [h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), h({ tag: "span", children: ["送っています"] })];
    }
    if (result.kind === "sent") {
      const time = result.at === undefined ? "" : formatJst(result.at).slice(-5);
      const count = result.count ?? 0;
      // Claude Code に入力できなかった: 送った内容は残り、次の話し合いの取り込みに任せる
      if (result.entered !== true) {
        return [
          icon("alert"),
          h({
            tag: "span",
            children: [
              `${count} 件を送りましたが、Claude Code には入力できませんでした（${time}）。送った内容は保存されていて、次に話し合いを始めたときに取り込まれます。`,
            ],
          }),
        ];
      }
      return [icon("check"), h({ tag: "span", children: [`${count} 件を送り、Claude Code に入力しました（${time}）。`] })];
    }
    if (result.kind === "stale") {
      return [icon("alert"), h({ tag: "span", children: [`送れませんでした。送れない書き込みが ${result.count ?? 0} 件あります。`] })];
    }
    const detail = result.detail ?? null;
    return [
      icon("alert"),
      h({
        tag: "span",
        children: [
          detail === null
            ? "送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。"
            : `送れませんでした。${detail}`,
        ],
      }),
    ];
  }

  /** レビュー中の書き込みの読み上げの名前の頭（返信は「{スレッドの ID} への返信」、新しいスレッドは「{向けた項目の ID} へのコメント」） */
  function reviewLabel(item: ReviewItem): string {
    // 詳細パネルへ渡す行には `thread` を持たないものもある
    if (item.thread !== null && item.thread !== undefined) return `${item.thread} への返信`;
    return item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
  }

  /** 行の向けた項目（押すとその項目を開く。消えた項目は押せない。項目を指さないときは何も出さない） */
  function targetCell(item: ReviewItem, props: CommentsPanelProps): HTMLElement | null {
    // 項目を指さない
    if (item.target === null) return null;
    const title = props.titleOf(item.target);
    // 項目が消えた: 押せない ID だけを出す
    if (title === null) {
      return h({ tag: "span", attrs: { class: "row-target gone" }, children: [h({ tag: "span", attrs: { class: "mono" }, children: [item.target] })] });
    }
    return h({
      tag: "button",
      attrs: { class: "row-target idlink", type: "button", "data-focus": `open:${item.id}`, onclick: () => props.on.open(item) },
      children: [h({ tag: "span", attrs: { class: "mono" }, children: [item.target] }), h({ tag: "span", attrs: { class: "t" }, children: [title] })],
    });
  }

  /** 本文をその場で書き換える入力欄と「キャンセル」「修正」（コメントの一覧と詳細パネルが使う） */
  export function reviewEditForm({
    item,
    body,
    error,
    focus,
    on,
  }: {
    item: ReviewItem;
    body: string | null;
    error: string | null;
    focus: string;
    on: { saveEdit: (id: string, body: string) => void; cancelEdit: () => void };
  }): HTMLElement {
    const field = h({
      tag: "textarea",
      attrs: {
        name: "body",
        rows: 2,
        maxlength: COMMENT_BODY_MAX_LENGTH,
        "aria-label": `${item.id} へのコメントの本文`,
        "data-focus": `${focus}edit:${item.id}`,
        onkeydown: (event) => {
          if ((event as KeyboardEvent).key === "Escape") {
            // 詳細の全画面の `dialog` の `cancel` を起こさない
            event.preventDefault();
            event.stopPropagation();
            on.cancelEdit();
          }
        },
      },
      children: [body ?? item.body],
    });
    // 理由があるときだけ `role="alert"` を持たせる（空のまま警告として読み上げさせない）
    const message = h({ tag: "p", attrs: { class: "send-msg failed", role: error ? "alert" : null }, children: error ? [icon("alert"), error] : [] });
    return h({
      tag: "form",
      attrs: {
        class: "row-edit",
        novalidate: true,
        onsubmit: (event) => {
          event.preventDefault();
          // 空白だけは送らない
          if (field.value.trim() === "") {
            field.setAttribute("aria-invalid", "true");
            message.setAttribute("role", "alert");
            message.replaceChildren(icon("alert"), "コメントを入れてから直してください。");
            field.focus();
            return;
          }
          on.saveEdit(item.id, field.value);
        },
      },
      children: [
        field,
        message,
        h({
          tag: "div",
          attrs: { class: "row-edit-actions" },
          children: [
            h({ tag: "button", attrs: { class: "btn ghost", type: "button", onclick: on.cancelEdit }, children: ["キャンセル"] }),
            h({ tag: "button", attrs: { class: "btn primary", type: "submit" }, children: ["修正"] }),
          ],
        }),
      ],
    });
  }

  /** 行の右上に置く、鉛筆の印の「修正」とごみ箱の印の「削除」（コメントの一覧と詳細パネルが使う） */
  export function reviewRowActions({
    item,
    focus,
    on,
  }: {
    item: ReviewItem;
    focus: string;
    on: { edit: (id: string) => void; remove: (id: string) => void };
  }): HTMLElement {
    const label = reviewLabel(item);
    return h({
      tag: "div",
      attrs: { class: "row-actions" },
      children: [
        h({
          tag: "button",
          attrs: {
            class: "icon-btn",
            type: "button",
            "aria-label": `${label}を修正`,
            title: "修正",
            "data-focus": `${focus}edit-open:${item.id}`,
            onclick: () => on.edit(item.id),
          },
          children: [icon("edit")],
        }),
        h({
          tag: "button",
          attrs: {
            class: "icon-btn",
            type: "button",
            "aria-label": `${label}を削除`,
            title: "削除",
            "data-focus": `${focus}remove:${item.id}`,
            onclick: () => on.remove(item.id),
          },
          children: [icon("trash")],
        }),
      ],
    });
  }

  /** 消した行（元の場所に「コメントを削除しました。」と「元に戻す」を出す。コメントの一覧と詳細パネルが使う） */
  export function removedReviewRow({
    item,
    focus,
    on,
  }: {
    item: ReviewItem;
    focus: string;
    on: { restore: (id: string) => void };
  }): HTMLElement {
    return h({
      tag: "li",
      attrs: { class: "row removed", "data-comment": item.id },
      children: [
        h({ tag: "span", attrs: { class: "removed-msg", role: "status" }, children: ["コメントを削除しました。"] }),
        h({
          tag: "button",
          attrs: { class: "btn ghost", type: "button", "data-focus": `${focus}restore:${item.id}`, onclick: () => on.restore(item.id) },
          children: [icon("undo"), "元に戻す"],
        }),
      ],
    });
  }

  /** 行の頭（返信は返信先のスレッドの状態の札と題、新しいスレッドは向けた項目） */
  function rowHead(item: ReviewItem, props: CommentsPanelProps): HTMLElement {
    const thread = item.thread === null ? undefined : props.threads.find((entry) => entry.id === item.thread);
    // 新しいスレッド: 向けた項目
    if (item.thread === null) {
      return h({
        tag: "div",
        attrs: { class: "row-head" },
        children: [h({ tag: "span", attrs: { class: "row-kind" }, children: ["新しいスレッド"] }), targetCell(item, props)],
      });
    }
    // 返信: 返信先のスレッド（読めていなければ ID だけ）
    return h({
      tag: "div",
      attrs: { class: "row-head" },
      children: [
        h({ tag: "span", attrs: { class: "row-kind" }, children: ["返信"] }),
        thread === undefined
          ? h({ tag: "span", attrs: { class: "row-target gone" }, children: [h({ tag: "span", attrs: { class: "mono" }, children: [item.thread] })] })
          : h({
            tag: "button",
            attrs: {
              class: "row-target idlink-like",
              type: "button",
              "data-focus": `open:${item.id}`,
              onclick: () => props.on.openThread(thread.id, false),
            },
            children: [threadState(thread.status), h({ tag: "span", attrs: { class: "t" }, children: [threadTitle(thread)] })],
          }),
      ],
    });
  }

  /** 「スレッドを開く」の入口（新しいスレッドの行は、まだ送っていないそのスレッドを開く。クローズのスレッドへの返信の行は、そのスレッドを開く） */
  function openThreadButton({ item, id, pending, className }: { item: ReviewItem; id: string; pending: boolean; className: string }, props: CommentsPanelProps): HTMLElement {
    return h({
      tag: "button",
      attrs: { class: className, type: "button", "data-focus": `thread-open:${item.id}`, onclick: () => props.on.openThread(id, pending) },
      children: ["スレッドを開く"],
    });
  }

  /** レビュー中の書き込みの行 */
  function reviewRow(item: ReviewItem, props: CommentsPanelProps): HTMLElement {
    const reason = props.stale.get(item.id);
    const label = reviewLabel(item);
    const blocked = isBlockedReply(item, props.threads);
    // 詳細パネルで書き換えている行は、入力欄を出さず、「修正」「削除」も出さない
    const editingInDetail = props.editing === item.id && props.editingIn === "detail";
    const editingInList = props.editing === item.id && !editingInDetail;
    const focused = item.id === props.selected || (props.reviewFocus !== null && item.thread === props.reviewFocus);
    // 書き換えていない行の本文は、折り返した後の見た目の行で畳む
    const fold = editingInList
      ? null
      : reviewBodyFold({
        id: item.id,
        label,
        body: item.body,
        changeSets: props.changeSetOf,
        open: props.expanded.has(item.id),
        on: { toggle: props.on.fold, changeSet: props.on.changeSet },
      });
    return h({
      tag: "li",
      attrs: {
        class: `row${focused ? " selected" : ""}${reason === undefined ? "" : " stale"}${blocked ? " blocked" : ""}`,
        "data-comment": item.id,
      },
      children: [
        h({
          tag: "input",
          attrs: {
            type: "checkbox",
            class: "row-check",
            checked: !blocked && props.checked.has(item.id),
            disabled: blocked,
            "aria-label": `${label}を送る`,
            "data-focus": `check:${item.id}`,
            onchange: (event) => props.on.check(item.id, (event.target as HTMLInputElement).checked),
          },
        }),
        h({
          tag: "div",
          attrs: { class: "row-main" },
          children: [
            rowHead(item, props),
            item.loc === null
              ? null
              : h({
                tag: "div",
                attrs: { class: "review-loc" },
                children: [
                  h({ tag: "span", attrs: { class: "review-loc-name" }, children: [locationLabel(item.loc)] }),
                  h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [item.loc.text] }),
                ],
              }),
            editingInList
              ? reviewEditForm({
                item,
                body: props.editBody ?? null,
                error: props.editError ?? null,
                focus: "",
                on: { saveEdit: props.on.saveEdit, cancelEdit: props.on.cancelEdit },
              })
              : fold?.body ?? null,
            // クローズのスレッドへの返信: 送れない理由と、そのスレッドを開く入口
            blocked && item.thread !== null
              ? h({
                tag: "div",
                attrs: { class: "row-stale row-blocked" },
                children: [
                  icon("alert"),
                  h({ tag: "span", children: ["クローズのスレッドへの返信は送れません。オープンに戻すと送れます。"] }),
                  openThreadButton({ item, id: item.thread, pending: false, className: "btn ghost" }, props),
                ],
              })
              : null,
            // 新しいスレッド: 開閉のボタンと、まだ送っていないそのスレッドを開く入口
            item.thread === null
              ? h({
                tag: "div",
                attrs: { class: "row-thread-open" },
                children: [fold?.more ?? null, openThreadButton({ item, id: item.id, pending: true, className: "btn ghost" }, props)],
              })
              : null,
            // 返信: 開閉のボタンだけの行（ボタンを出さないときは行ごと出さない）
            item.thread !== null && fold !== null ? h({ tag: "div", attrs: { class: "review-more-row" }, children: [fold.more] }) : null,
            reason === undefined
              ? null
              : h({
                tag: "div",
                attrs: { class: "row-stale", role: "alert" },
                children: [
                  icon("alert"),
                  h({ tag: "span", children: [reason] }),
                  // 項目が記録にあるときだけ、箇所を外して項目へのコメントにできる
                  item.loc !== null && item.target !== null && props.titleOf(item.target) !== null
                    ? h({
                      tag: "button",
                      attrs: { class: "btn ghost", type: "button", "data-focus": `unloc:${item.id}`, onclick: () => props.on.unloc(item.id) },
                      children: ["箇所を外す"],
                    })
                    : null,
                ],
              }),
          ],
        }),
        editingInDetail ? null : reviewRowActions({ item, focus: "", on: { edit: props.on.edit, remove: props.on.remove } }),
      ],
    });
  }

  /** 送る帯の先頭に置く、文字を添えない三状態のチェックの箱。押すと、全てチェックしていれば全て外し、それ以外は全てチェックする */
  function selectAllBox({
    ids,
    checked,
    onChange,
  }: {
    ids: string[];
    checked: Set<string>;
    onChange: (all: boolean) => void;
  }): HTMLLabelElement {
    const count = ids.filter((id) => checked.has(id)).length;
    const checkbox = h({
      tag: "input",
      attrs: {
        type: "checkbox",
        checked: count === ids.length,
        "aria-label": "すべて選ぶ",
        onchange: () => onChange(count < ids.length),
      },
    });
    // 一部だけチェックしているときの横棒は、属性でなくプロパティで付ける
    checkbox.indeterminate = count > 0 && count < ids.length;
    return h({ tag: "label", attrs: { class: "legend-all-check", title: "すべて選ぶ" }, children: [checkbox] });
  }

  /** 見出しの帯（見出し・レビュー中の入口・閉じる） */
  function panelHead(props: CommentsPanelProps): HTMLElement {
    const count = props.items.length;
    return h({
      tag: "div",
      attrs: { class: "comments-head" },
      children: [
        h({ tag: "h2", children: ["コメント"] }),
        h({ tag: "span", attrs: { class: "spacer" } }),
        // レビュー中の書き込みの画面では、入口を出さない（押しても何も変わらない）
        props.view === "review"
          ? null
          : h({
            tag: "button",
            attrs: {
              class: `btn review-entry${count === 0 ? " zero" : ""}`,
              type: "button",
              "aria-label": `レビュー中の書き込みを確かめる（${count} 件）`,
              "data-focus": "review",
              onclick: () => props.on.review(),
            },
            children: ["レビュー中", h({ tag: "span", attrs: { class: "count", "aria-hidden": "true" }, children: [count] })],
          }),
        h({
          tag: "button",
          attrs: { class: "icon-btn", type: "button", "aria-label": "コメントの一覧を閉じる", "data-focus": "close", onclick: props.on.close },
          children: [icon("x")],
        }),
      ],
    });
  }

  /** 状態の絞り込みの選択肢 */
  const THREAD_FILTERS: { value: ThreadFilter; label: string }[] = [
    { value: "open", label: "オープン" },
    { value: "closed", label: "クローズ" },
    { value: "all", label: "すべて" },
  ];

  /** 0 件のときの文言 */
  function emptyThreadsText({ filter, tag }: { filter: ThreadFilter; tag: string | null }): string {
    const state = { open: "オープンの", closed: "クローズの", all: "" }[filter];
    return tag === null ? `${state}スレッドはありません。` : `タグ「${tag}」の${state}スレッドはありません。`;
  }

  /** スレッドを読めなかった理由の文言 */
  function threadsErrorText(error: { detail: string | null }): string {
    return `スレッドを読めませんでした。${error.detail ?? "サーバーが止まっています。立ち上げ直してから開いてください。"}`;
  }

  /** 一覧の下端の、新しいスレッドを立てる入口と入力 */
  function newThreadBox(props: CommentsPanelProps): HTMLElement {
    if (!props.composing) {
      return h({
        tag: "div",
        attrs: { class: "comments-free talk-new" },
        children: [
          h({
            tag: "button",
            attrs: { class: "btn", type: "button", "data-focus": "compose", onclick: () => props.on.compose(true) },
            children: [icon("plus"), "新しいスレッド"],
          }),
        ],
      });
    }
    return h({
      tag: "div",
      attrs: { class: "comments-free talk-new open" },
      children: [
        h({
          tag: "div",
          attrs: { class: "talk-new-head" },
          children: [
            h({ tag: "span", attrs: { class: "send-label" }, children: ["新しいスレッド"] }),
            h({
              tag: "button",
              attrs: { class: "icon-btn", type: "button", "aria-label": "新しいスレッドの入力を閉じる", "data-focus": "compose-close", onclick: () => props.on.compose(false) },
              children: [icon("x")],
            }),
          ],
        }),
        sendForm({ ...props.free, collapsed: false }),
      ],
    });
  }

  /** スレッドの一覧（絞り込みの帯・行・下端の新しいスレッド）を返す */
  export function threadListView(props: CommentsPanelProps): HTMLElement[] {
    const { threads, items, filter, tag, on } = props;
    const counts = threadCounts(threads, tag);
    const rows = visibleThreads(threads, filter, tag);
    const pending = pendingThreads(items, filter, tag);
    const total = threads.filter((thread) => filter === "all" || thread.status === filter).length;
    const empty = rows.length + pending.length === 0;
    return [
      h({
        tag: "div",
        attrs: { class: "talk-band" },
        children: [
          h({
            tag: "div",
            attrs: { class: "segment talk-filter", role: "group", "aria-label": "スレッドの状態で絞る" },
            children: THREAD_FILTERS.map((entry) =>
              h({
                tag: "button",
                attrs: {
                  type: "button",
                  "aria-pressed": String(entry.value === filter),
                  "data-focus": `filter:${entry.value}`,
                  onclick: () => on.filter(entry.value),
                },
                children: [entry.label, h({ tag: "span", attrs: { class: "count" }, children: [counts[entry.value]] })],
              }),
            ),
          }),
          tag === null
            ? null
            : h({
              tag: "div",
              attrs: { class: "chips talk-chips" },
              children: [
                h({
                  tag: "span",
                  attrs: { class: "chip" },
                  children: [
                    icon("hash"),
                    tag,
                    h({
                      tag: "button",
                      attrs: { type: "button", "aria-label": `タグ「${tag}」の絞り込みを外す`, "data-focus": "clear-tag", onclick: () => on.clearTag() },
                      children: [icon("x")],
                    }),
                  ],
                }),
                h({ tag: "span", attrs: { class: "hint" }, children: [`${rows.length} / ${total} 件`] }),
              ],
            }),
        ],
      }),
      h({
        tag: "div",
        attrs: { class: "comments-body" },
        children: [
          // 読めなかった理由は、並べる行の上に出す（まだ送っていない新しいスレッドは並べる）
          props.threadsError === null
            ? null
            : h({ tag: "p", attrs: { class: "send-msg failed", role: "alert" }, children: [icon("alert"), threadsErrorText(props.threadsError)] }),
          empty
            ? props.threadsError === null
              ? h({ tag: "p", attrs: { class: "comments-empty" }, children: [icon("comment"), emptyThreadsText({ filter, tag })] })
              : null
            : h({
              tag: "ul",
              attrs: { class: "th-list" },
              children: [
                ...pending.map((item) => threadRow({ pending: item, on: { open: on.openThread, tag: on.tag } })),
                ...rows.map((thread) =>
                  threadRow({
                    thread,
                    hasPendingReply: items.some((item) => item.thread === thread.id),
                    activeTag: tag,
                    on: { open: on.openThread, tag: on.tag },
                  }),
                ),
              ],
            }),
        ],
      }),
      newThreadBox(props),
    ];
  }

  /** スレッドの見出し（戻る・状態を変える・理由の入力と失敗の理由・題・向けた項目とタグ） */
  function threadHead({
    status,
    title,
    target,
    loc,
    tags,
    statusButton,
    extra,
    props,
  }: {
    status: ThreadStateKind;
    title: string;
    target: string | null;
    loc: Location | null;
    tags: string[];
    statusButton: HTMLElement | null;
    extra: (HTMLElement | null)[];
    props: CommentsPanelProps;
  }): HTMLElement {
    const targetTitle = target === null ? null : props.titleOf(target);
    return h({
      tag: "div",
      attrs: { class: "th-head" },
      children: [
        h({
          tag: "div",
          attrs: { class: "th-head-bar" },
          children: [
            h({
              tag: "button",
              attrs: { class: "btn ghost th-back", type: "button", "data-focus": "back", onclick: () => props.on.back() },
              children: [icon("back"), "一覧へ戻る"],
            }),
            h({ tag: "span", attrs: { class: "spacer" } }),
            statusButton,
          ],
        }),
        ...extra,
        h({ tag: "h3", attrs: { class: "th-heading" }, children: [threadState(status), h({ tag: "span", children: [title] })] }),
        target === null && tags.length === 0
          ? null
          : h({
            tag: "div",
            attrs: { class: "th-meta" },
            children: [
              target === null
                ? null
                : targetTitle === null
                  ? h({ tag: "span", attrs: { class: "row-target gone" }, children: [h({ tag: "span", attrs: { class: "mono" }, children: [target] })] })
                  : h({
                    tag: "button",
                    attrs: {
                      class: "row-target",
                      type: "button",
                      "data-focus": "target",
                      onclick: () => (loc === null ? props.on.openId(target) : props.on.openId(target, loc)),
                    },
                    children: [h({ tag: "span", attrs: { class: "mono" }, children: [target] }), h({ tag: "span", attrs: { class: "t" }, children: [targetTitle] })],
                  }),
              ...tags.map((entry) => h({ tag: "span", attrs: { class: "th-tag static" }, children: [icon("hash"), h({ tag: "span", children: [entry] })] })),
            ],
          }),
      ],
    });
  }

  /** 理由の入力（任意）。状態を変える前に出し、確定で変えた後の状態と理由を 1 回で送る */
  function reasonForm({ closing, props }: { closing: boolean; props: CommentsPanelProps }): HTMLElement {
    const { reason, on } = props;
    const saving = reason.status === "saving";
    const verb = closing ? "クローズにする" : "オープンに戻す";
    const field = h({
      tag: "textarea",
      attrs: {
        id: "reason-body",
        name: "reason",
        rows: 2,
        maxlength: REASON_MAX_LENGTH,
        "aria-keyshortcuts": "Control+Enter",
        "data-focus": "reason",
        readonly: saving,
        // 打つたびには知らせず、確定のときに中身を渡す（描き直すときは、入口が入力欄から読む）
        onchange: () => on.reasonInput(field.value),
        onkeydown: (event) => {
          const key = event as KeyboardEvent;
          // 変換の確定の Enter では確定しない
          if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
            key.preventDefault();
            form.requestSubmit();
          }
          // Esc は理由の入力をやめる（一覧へは戻らない）
          if (key.key === "Escape") {
            key.preventDefault();
            key.stopPropagation();
            on.reasonOpen(false);
          }
        },
      },
      children: [reason.body],
    });
    const form = h({
      tag: "form",
      attrs: {
        class: "th-reason",
        novalidate: true,
        onsubmit: (event) => {
          event.preventDefault();
          if (saving) return;
          on.setStatus(closing ? "closed" : "open", field.value);
        },
      },
      children: [
        h({ tag: "label", attrs: { class: "send-label", for: "reason-body" }, children: ["理由（任意）"] }),
        field,
        h({
          tag: "div",
          attrs: { class: "row-edit-actions" },
          children: [
            h({ tag: "button", attrs: { class: "btn ghost", type: "button", "data-focus": "reason-cancel", onclick: () => on.reasonOpen(false) }, children: ["キャンセル"] }),
            h({ tag: "button", attrs: { class: "btn primary", type: "submit", "data-focus": "reason-ok", disabled: saving }, children: [verb] }),
          ],
        }),
      ],
    });
    return form;
  }

  /** 状態を変えられなかった理由 */
  function statusFailure({ closing, detail }: { closing: boolean; detail: string | null }): HTMLElement {
    const head = closing ? "クローズにできませんでした。" : "オープンに戻せませんでした。";
    return h({
      tag: "p",
      attrs: { class: "send-msg failed th-action-msg", role: "alert" },
      children: [icon("alert"), `${head}${detail ?? "サーバーが止まっています。立ち上げ直してから押してください。"}`],
    });
  }

  /** レビュー中の書き込みの `li`（スレッドの中のレビュー中の書き込み） */
  function pendingPostItem(item: ReviewItem, props: CommentsPanelProps): HTMLElement {
    return threadPost({
      pending: item,
      titles: props.titleOf,
      changeSets: props.changeSetOf,
      editing: props.editing === item.id && props.editingIn !== "detail",
      editBody: props.editBody ?? null,
      editError: props.editError ?? null,
      on: {
        openId: (id) => props.on.openId(id),
        changeSet: props.on.changeSet,
        edit: props.on.edit,
        saveEdit: props.on.saveEdit,
        cancelEdit: props.on.cancelEdit,
        remove: props.on.remove,
      },
    });
  }

  /** まだ送っていない新しいスレッド（最初の書き込みをレビュー中の形で出し、状態を変えると返信の入力を出さない） */
  function pendingThreadView(commentId: string, props: CommentsPanelProps): HTMLElement[] {
    const item = props.items.find((entry) => entry.id === commentId);
    const gone = props.removed.find((entry) => entry.id === commentId);
    const shown = item ?? gone;
    return [
      threadHead({
        status: "pending",
        title: shown === undefined ? "" : shown.body.split("\n")[0],
        target: shown?.target ?? null,
        loc: shown?.loc ?? null,
        tags: [],
        statusButton: null,
        extra: [],
        props,
      }),
      h({
        tag: "div",
        attrs: { class: "comments-body th-body" },
        children: [
          h({
            tag: "ol",
            attrs: { class: "posts", "aria-label": "書き込み" },
            children: [
              item !== undefined
                ? pendingPostItem(item, props)
                : gone === undefined
                  ? null
                  : removedReviewRow({ item: gone, focus: "", on: { restore: props.on.restore } }),
            ],
          }),
        ],
      }),
      h({
        tag: "div",
        attrs: { class: "comments-free" },
        children: [h({ tag: "p", attrs: { class: "th-closed-note" }, children: [icon("edit"), "まだ送っていないスレッドです。"] })],
      }),
    ];
  }

  /** スレッド 1 件（見出し・書き込みの並び・下端）を返す。まだ送っていない新しいスレッドも開く */
  export function threadView(props: CommentsPanelProps): HTMLElement[] {
    const { opened } = props;
    if (opened !== null && opened.pending) return pendingThreadView(opened.id, props);
    const thread = props.threads.find((entry) => entry.id === opened?.id);
    // 開いているスレッドが無い（呼ぶ側が一覧へ戻す）
    if (thread === undefined) return [];
    const { reason, on } = props;
    const open = thread.status === "open";
    const saving = reason.status === "saving";
    // 理由の入力を出している間は、状態を変えるボタンを出さない
    const statusButton = reason.open
      ? null
      : h({
        tag: "button",
        attrs: { class: "btn", type: "button", "data-focus": "status", disabled: saving, onclick: () => on.reasonOpen(true) },
        children: open ? [icon("check"), "クローズにする"] : [icon("undo"), "オープンに戻す"],
      });
    // レビュー中の返信と、消した返信（元の場所に「元に戻す」を出す）を溜めた順に並べる
    const replies = [
      ...props.items.filter((item) => item.thread === thread.id).map((item) => ({ item, gone: false })),
      ...props.removed.filter((item) => item.thread === thread.id).map((item) => ({ item, gone: true })),
    ].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
    return [
      threadHead({
        status: thread.status,
        title: threadTitle(thread),
        target: thread.target,
        loc: thread.loc,
        tags: thread.tags,
        statusButton,
        extra: [
          reason.open ? reasonForm({ closing: open, props }) : null,
          reason.status === "failed" ? statusFailure({ closing: open, detail: reason.detail }) : null,
        ],
        props,
      }),
      h({
        tag: "div",
        attrs: { class: "comments-body th-body" },
        children: [
          h({
            tag: "ol",
            attrs: { class: "posts", "aria-label": "書き込み" },
            children: [
              ...threadTimeline(thread).map((entry) =>
                "post" in entry
                  ? threadPost({ post: entry.post, titles: props.titleOf, changeSets: props.changeSetOf, on: { openId: (id) => on.openId(id), changeSet: on.changeSet, edit: on.edit, saveEdit: on.saveEdit, cancelEdit: on.cancelEdit, remove: on.remove } })
                  : threadPost({ event: entry.event, on: { openId: (id) => on.openId(id), changeSet: on.changeSet, edit: on.edit, saveEdit: on.saveEdit, cancelEdit: on.cancelEdit, remove: on.remove } }),
              ),
              ...replies.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : pendingPostItem(item, props))),
            ],
          }),
        ],
      }),
      h({
        tag: "div",
        attrs: { class: "comments-free" },
        children: [
          open
            ? replyForm({ thread: thread.id, ...props.reply, on: { input: on.replyInput, save: on.reply } })
            : h({ tag: "p", attrs: { class: "th-closed-note" }, children: [icon("check"), "クローズにしたスレッドです。"] }),
        ],
      }),
    ];
  }

  /** レビュー中の書き込み（見出し・送る帯・行・空の状態）を返す */
  export function reviewView(props: CommentsPanelProps): HTMLElement[] {
    const { items, removed, checked, result, on } = props;
    // 送れる書き込み（クローズのスレッドへの返信を除く）
    const sendable = items.filter((item) => !isBlockedReply(item, props.threads));
    const checkedCount = sendable.filter((item) => checked.has(item.id)).length;
    const isEmpty = items.length === 0 && removed.length === 0;
    // 送る帯は一覧の上端に留める。送っている間とチェックが 0 件のときは押せない
    const sending = result?.kind === "sending";
    const message = outcomeContent({ result, checkedCount });
    // 送った直後は、送るものが無くなっても結果を出す
    const band = isEmpty && result === null
      ? null
      : h({
        tag: "div",
        attrs: { class: "send-band" },
        children: [
          sendable.length === 0
            ? null
            : selectAllBox({ ids: sendable.map((item) => item.id), checked, onChange: on.checkAll }),
          sendable.length === 0
            ? null
            : h({ tag: "span", attrs: { class: "send-count" }, children: [`${checkedCount} / ${sendable.length} 件`] }),
          isEmpty
            ? null
            : h({
              tag: "button",
              attrs: {
                class: "btn primary",
                type: "button",
                "data-focus": "send",
                disabled: checkedCount === 0 || sending,
                onclick: () => on.send(),
              },
              children: [icon("send"), `まとめて送る（${checkedCount} 件）`],
            }),
          h({ tag: "p", attrs: { class: `send-msg${result === null ? "" : ` ${result.kind}`}`, role: "status" }, children: message ?? [] }),
        ],
      });
    // 消した書き込みは元の場所（ID の連番の順）に出す
    const rows = [...items.map((item) => ({ item, gone: false })), ...removed.map((item) => ({ item, gone: true }))].sort(
      (a, b) => commentNumber(a.item.id) - commentNumber(b.item.id),
    );
    const nodes: (HTMLElement | null)[] = [
      h({
        tag: "div",
        attrs: { class: "th-head review-head" },
        children: [
          h({
            tag: "div",
            attrs: { class: "th-head-bar" },
            children: [
              h({
                tag: "button",
                attrs: { class: "btn ghost th-back", type: "button", "data-focus": "back", onclick: () => on.back() },
                children: [icon("back"), "戻る"],
              }),
              h({ tag: "h3", attrs: { class: "review-title" }, children: ["レビュー中の書き込み", h({ tag: "span", attrs: { class: "count" }, children: [items.length] })] }),
            ],
          }),
        ],
      }),
      band,
      h({
        tag: "div",
        attrs: { class: "comments-body" },
        children: [
          isEmpty
            ? h({ tag: "p", attrs: { class: "comments-empty" }, children: [icon("comment"), "レビュー中の書き込みはありません。"] })
            : h({
              tag: "ul",
              attrs: { class: "comments-list" },
              children: rows.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : reviewRow(item, props))),
            }),
        ],
      }),
    ];
    return nodes.filter((node): node is HTMLElement => node !== null);
  }

  /** コメントの一覧を返す */
  export function commentsPanel(props: CommentsPanelProps): HTMLElement {
    // 開いているスレッドが無いときは、スレッドの一覧を出す
    const threadScreen = props.view === "thread" ? threadView(props) : [];
    const screen =
      props.view === "review" ? reviewView(props) : threadScreen.length > 0 ? threadScreen : threadListView(props);
    return h({
      tag: "aside",
      attrs: { class: "comments-panel", "aria-label": "コメントの一覧" },
      children: [panelHead(props), ...screen],
    });
  }
}
