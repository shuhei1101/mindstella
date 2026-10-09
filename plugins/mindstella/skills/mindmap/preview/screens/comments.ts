// コメントの一覧。見ている画面に重ねて左から出すパネルに、レビュー中のコメントを並べ、チェックしたものだけをまとめて送る。

namespace MindmapPreview {
  /** レビュー中のコメント 1 件 */
  export type ReviewItem = ReviewState["items"][number];

  /** まとめて送った結果 */
  export type SendOutcome = {
    kind: "sending" | "sent" | "failed" | "stale";
    /** 送った件数・箇所が合わない件数 */
    count?: number;
    /** 送った日時 */
    at?: string;
    /** サーバーが返した理由（届かなかったときは無い） */
    detail?: string | null;
  };

  /** コメントの一覧の引数 */
  export type CommentsPanelProps = {
    /** レビュー中のコメント */
    items: ReviewItem[];
    /** 一覧を開いている間に消したコメント（元の場所に「元に戻す」を出す） */
    removed: ReviewItem[];
    /** チェックしたコメントの ID */
    checked: Set<string>;
    /** 本文を直しているコメントの ID */
    editing: string | null;
    /** 本文を直せなかった理由 */
    editError?: string | null;
    /** 本文を直せなかったとき、入力欄に残す直していた中身（無ければ元の本文） */
    editBody?: string | null;
    /** `editing` の修正を始めた場所（既定は一覧）。詳細パネルで始めたときは、その行を本文だけで描いて「修正」「削除」を出さない */
    editingIn?: EditingIn;
    /** 箇所が合わないコメントの ID → 理由 */
    stale: Map<string, string>;
    result: SendOutcome | null;
    /** 行から開いて詳細パネルに出しているコメントの ID（選んだ見た目にする） */
    selected: string | null;
    /** 項目のタイトル（記録から消えていれば null。押せない ID だけを出し、箇所を外すを出さない） */
    titleOf: (id: string) => string | null;
    /** 下端の項目を指さない入力の引数 */
    free: SendFormProps;
    on: {
      close: () => void;
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
    };
  };

  /** コメントの本文の長さの上限（サーバーが受け付ける文字数と同じ） */
  export const COMMENT_BODY_MAX_LENGTH = 10000;

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

  /** 送った結果の文言（印と文）。結果が無いときは null */
  function outcomeContent({ result, checkedCount }: { result: SendOutcome | null; checkedCount: number }): Child[] | null {
    if (result === null) {
      // チェックが 0 件
      return checkedCount === 0 ? [icon("alert"), h({ tag: "span", children: ["送るコメントにチェックを付けてください。"] })] : null;
    }
    if (result.kind === "sending") {
      return [h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), h({ tag: "span", children: ["送っています"] })];
    }
    if (result.kind === "sent") {
      const time = result.at === undefined ? "" : formatJst(result.at).slice(-5);
      return [icon("check"), h({ tag: "span", children: [`${result.count ?? 0} 件を送りました（${time}）。`] })];
    }
    if (result.kind === "stale") {
      return [icon("alert"), h({ tag: "span", children: [`送れませんでした。箇所が合わないコメントが ${result.count ?? 0} 件あります。`] })];
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

  /** 行の向けた項目（押すとその項目を開く。項目を指さない・消えた項目は押せない） */
  function targetCell(item: ReviewItem, props: CommentsPanelProps): HTMLElement {
    // 項目を指さない
    if (item.target === null) return h({ tag: "span", attrs: { class: "row-target none" }, children: ["項目を指さない"] });
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
    const message = h({ tag: "p", attrs: { class: "send-msg failed", role: "alert" }, children: error ? [icon("alert"), error] : [] });
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
    const label = item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
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

  /** コメントの行 */
  function commentRow(item: ReviewItem, props: CommentsPanelProps): HTMLElement {
    const reason = props.stale.get(item.id);
    const label = item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
    // 詳細パネルで書き換えている行は、入力欄を出さず、「修正」「削除」も出さない
    const editingInDetail = props.editing === item.id && props.editingIn === "detail";
    const editingInList = props.editing === item.id && !editingInDetail;
    return h({
      tag: "li",
      attrs: {
        class: `row${item.id === props.selected ? " selected" : ""}${reason === undefined ? "" : " stale"}`,
        "data-comment": item.id,
      },
      children: [
        h({
          tag: "input",
          attrs: {
            type: "checkbox",
            class: "row-check",
            checked: props.checked.has(item.id),
            "aria-label": `${label}を送る`,
            "data-focus": `check:${item.id}`,
            onchange: (event) => props.on.check(item.id, (event.target as HTMLInputElement).checked),
          },
        }),
        h({
          tag: "div",
          attrs: { class: "row-main" },
          children: [
            targetCell(item, props),
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
              : h({ tag: "p", attrs: { class: "review-body" }, children: [item.body] }),
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

  /** コメントの一覧を返す */
  export function commentsPanel(props: CommentsPanelProps): HTMLElement {
    const { items, removed, checked, result, on } = props;
    const checkedCount = items.filter((item) => checked.has(item.id)).length;
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
          items.length === 0
            ? null
            : selectAllBox({
              ids: items.map((item) => item.id),
              checked,
              onChange: on.checkAll,
            }),
          items.length === 0
            ? null
            : h({ tag: "span", attrs: { class: "send-count" }, children: [`${checkedCount} / ${items.length} 件`] }),
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
    // 消したコメントは元の場所（ID の連番の順）に出す
    const rows = [...items.map((item) => ({ item, gone: false })), ...removed.map((item) => ({ item, gone: true }))].sort(
      (a, b) => commentNumber(a.item.id) - commentNumber(b.item.id),
    );
    return h({
      tag: "aside",
      attrs: { class: "comments-panel", "aria-label": "コメントの一覧" },
      children: [
        h({
          tag: "div",
          attrs: { class: "comments-head" },
          children: [
            h({ tag: "h2", children: ["レビュー中のコメント", h({ tag: "span", attrs: { class: "count" }, children: [items.length] })] }),
            h({
              tag: "button",
              attrs: { class: "icon-btn", type: "button", "aria-label": "コメントの一覧を閉じる", "data-focus": "close", onclick: on.close },
              children: [icon("x")],
            }),
          ],
        }),
        band,
        h({
          tag: "div",
          attrs: { class: "comments-body" },
          children: [
            isEmpty
              ? h({ tag: "p", attrs: { class: "comments-empty" }, children: [icon("comment"), "レビュー中のコメントはありません。"] })
              : h({
                tag: "ul",
                attrs: { class: "comments-list" },
                children: rows.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : commentRow(item, props))),
              }),
          ],
        }),
        h({ tag: "div", attrs: { class: "comments-free" }, children: [sendForm(props.free)] }),
      ],
    });
  }
}
