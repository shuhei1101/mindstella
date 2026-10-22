// 保存待ちのパネル。保存待ちの編集を項目ごとに並べ、1 件ずつ取り消し、まとめて保存する。コメントの一覧と同じ左から出すパネル。

namespace MindmapPreview {
  /** 保存の状態（`offline` は直前の保存がサーバーに届かなかった） */
  export type SaveStatus = "idle" | "saving" | "offline";

  /** 保存待ちのパネルの引数 */
  export type PendingEditsPanelProps = {
    /** 保存待ちの編集 */
    edits: PendingEdit[];
    /** 直前の保存で書き込めなかった編集（無ければ空） */
    blocked: BlockedEdit[];
    /** 編集を当てる前の記録の索引（項目の種類・タイトルを引く） */
    index: RecordIndex;
    status: SaveStatus;
    /** 直前の保存をサーバーが断った理由（書き込めない編集の知らせとは別に、日本語の理由を出す）。無ければ出さない */
    rejected?: string | null;
    on: {
      close: () => void;
      /** まとまりの項目を開く（項目の ID・仮の ID・`settings`） */
      open: (target: string) => void;
      /** 1 件を取り消す（編集の ID） */
      undo: (id: string) => void;
      save: () => void;
    };
  };

  /** 編集の行の文言 */
  export type EditRowText = { what: string; before: string | null; after: string | null };

  /** 設定のキーの呼び名 */
  const SETTING_LABELS: Record<string, string> = {
    summary: "題名",
    description: "説明",
    playbooks: "プレイブック",
    phases: "フェーズ",
    target_label: "最上位の軸の呼び名",
    goal: "ゴール",
    targets: "対象",
    categories: "カテゴリー",
    tags: "タグの語彙",
    links: "関連する場所",
    history_limit: "保持する回数",
  };

  /** 項目のキーの呼び名（詳細パネルの見出しと同じ言葉） */
  export const KEY_LABELS: Record<string, string> = {
    status: "状態",
    title: "タイトル",
    target: "機能",
    category: "カテゴリー",
    phase: "フェーズ",
    tags: "タグ",
    depends_on: "依存先",
    answer: "決定内容",
    reason: "理由",
    body: "本文",
    result: "結果",
    kind: "種類",
    question: "問い",
    conclusion: "結論",
    confidence: "確からしさ",
    related: "関連",
    withdrawn: "取り下げ",
    meaning: "意味",
    aliases: "別名",
    content: "内容",
    date: "日付",
    deliverable: "納品物",
    description: "説明",
  };

  /** 値を 1 行の文字にする（空は「（空）」、配列は「、」でつなぐ） */
  function flat(value: unknown): string {
    if (value === undefined || value === null || value === "") return "（空）";
    if (Array.isArray(value)) return value.length === 0 ? "（空）" : value.map((entry) => flat(entry)).join("、");
    if (value === true) return "はい";
    if (value === false) return "いいえ";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value).replace(/\s+/g, " ");
  }

  /** 1 件の編集の「何を」と「前 → 後」。本文・削除は値を出さず、追加は前を持たない */
  export function editRowText(edit: PendingEdit): EditRowText {
    const key = edit.key ?? "";
    switch (edit.op) {
      case "item-add":
        return { what: "項目を追加", before: null, after: flat((edit.value as { title?: string } | null)?.title) };
      case "item-remove":
        return { what: "項目を削除", before: null, after: null };
      case "setting":
        return { what: SETTING_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
      case "option-add":
        return {
          what: `案 ${key} を追加`,
          before: null,
          after: flat((edit.value as { content?: string } | null)?.content),
        };
      case "option-remove":
        return { what: `案 ${key} を削除`, before: null, after: null };
      case "option-edit":
        return {
          what: `案 ${key}`,
          before: flat((edit.before as { content?: string } | null)?.content ?? edit.before),
          after: flat((edit.value as { content?: string } | null)?.content),
        };
      case "adopt":
        return { what: "採用する案", before: flat(edit.before ?? "なし"), after: flat(edit.value) };
      default:
        if (key === "body") return { what: "本文", before: null, after: null };
        return { what: KEY_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
    }
  }

  /** 編集を向け先ごとに、最初に溜めた順にまとめる */
  export function groupEdits(edits: readonly PendingEdit[]): { target: string; edits: PendingEdit[] }[] {
    const groups: { target: string; edits: PendingEdit[] }[] = [];
    for (const edit of edits) {
      const found = groups.find((group) => group.target === edit.target);
      if (found === undefined) groups.push({ target: edit.target, edits: [edit] });
      else found.edits.push(edit);
    }
    return groups;
  }

  /** まとまりの見出しに出す、項目の種類・ID・タイトル（設定は「設定」、追加する項目は「{種類}を追加」） */
  function describeTarget({
    target,
    edits,
    index,
  }: {
    target: string;
    edits: readonly PendingEdit[];
    index: RecordIndex;
  }): { kind: string; id: string | null; title: string } {
    if (target === SETTINGS_TARGET) return { kind: "設定", id: null, title: index.data.settings.summary };
    const added = edits.find((edit) => edit.op === "item-add");
    if (added !== undefined) {
      const kind = KIND_LABEL[(added.key ?? "") as Kind] ?? added.key ?? "";
      return { kind: `${kind}を追加`, id: null, title: (added.value as { title?: string }).title ?? "" };
    }
    const entry = index.byId.get(target);
    if (entry === undefined) return { kind: "項目", id: target, title: "" };
    return { kind: KIND_LABEL[entry.kind], id: target, title: entry.item.title };
  }

  /** 読み上げ用の「前:」「後:」を添えた前 → 後の値 */
  function changeView(text: EditRowText): HTMLElement | null {
    if (text.after === null) return null;
    if (text.before === null) {
      return h({ tag: "span", attrs: { class: "pe-change" }, children: [h({ tag: "ins", children: [text.after] })] });
    }
    return h({
      tag: "span",
      attrs: { class: "pe-change" },
      children: [
        h({ tag: "del", children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["前: "] }), text.before] }),
        h({ tag: "span", attrs: { class: "pe-arrow", "aria-hidden": "true" }, children: ["→"] }),
        h({ tag: "ins", children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["後: "] }), text.after] }),
      ],
    });
  }

  /** 保存待ちのパネル（開閉は使う側が `open` のクラスで決める） */
  export function pendingEditsPanel({ edits, blocked, index, status, rejected = null, on }: PendingEditsPanelProps): HTMLElement {
    const removals = edits.filter((edit) => edit.op === "item-remove").length;
    const saving = status === "saving";
    const blockedBy = new Map(blocked.map((entry) => [entry.id, entry]));
    const pendingEdits = edits.filter((edit) => blockedBy.has(edit.id));

    /** 書き込めない編集の行の名前（「{ID か種類} の{何を}」） */
    const nameOf = (edit: PendingEdit): string => {
      const who = describeTarget({
        target: edit.target,
        edits: edits.filter((other) => other.target === edit.target),
        index,
      });
      return `${who.id ?? who.kind} の${editRowText(edit).what}`;
    };

    const list = h({ tag: "div", attrs: { class: "comments-body pe-list" } });
    if (pendingEdits.length > 0) {
      list.append(
        h({
          tag: "div",
          attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
          children: [
            h({
              tag: "p",
              attrs: { class: "pe-alert-title" },
              children: [icon("alert"), `${pendingEdits.length} 件の編集を書き込めないため、何も保存していません。`],
            }),
            h({
              tag: "ul",
              children: pendingEdits.map((edit) =>
                h({
                  tag: "li",
                  children: [
                    h({
                      tag: "a",
                      attrs: {
                        href: `#pe-row-${edit.id}`,
                        onclick: (event: Event) => {
                          event.preventDefault();
                          document.getElementById(`pe-row-${edit.id}`)?.querySelector("button")?.focus();
                        },
                      },
                      children: [nameOf(edit)],
                    }),
                  ],
                }),
              ),
            }),
            h({
              tag: "p",
              attrs: { class: "pe-alert-next" },
              children: ["書き込めない編集を取り消してから、もう一度保存してください。"],
            }),
          ],
        }),
      );
    }
    if (rejected !== null) {
      list.append(
        h({
          tag: "div",
          attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
          children: [
            h({ tag: "p", attrs: { class: "pe-alert-title" }, children: [icon("alert"), `保存できませんでした。${rejected}`] }),
          ],
        }),
      );
    }
    if (status === "offline") {
      list.append(
        h({
          tag: "div",
          attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
          children: [
            h({
              tag: "p",
              attrs: { class: "pe-alert-title" },
              children: [icon("alert"), "サーバーにつながらないため、保存できませんでした。"],
            }),
            h({
              tag: "p",
              attrs: { class: "pe-alert-next" },
              children: ["保存待ちの編集は残っています。サーバーを立ち上げ直してから、もう一度保存してください。"],
            }),
          ],
        }),
      );
    }
    if (edits.length === 0) list.append(h({ tag: "p", attrs: { class: "comments-empty" }, children: [icon("layers"), "保存待ちの編集はありません。"] }));

    for (const group of groupEdits(edits)) {
      const who = describeTarget({ target: group.target, edits: group.edits, index });
      const isBlocked = group.edits.some((edit) => blockedBy.has(edit.id));
      list.append(
        h({
          tag: "section",
          attrs: { class: `pe-group${isBlocked ? " is-blocked" : ""}` },
          children: [
            h({
              tag: "h3",
              attrs: { class: "pe-group-head" },
              children: [
                h({
                  tag: "button",
                  attrs: {
                    class: "pe-open",
                    type: "button",
                    "aria-label": `${who.id ?? who.kind}「${who.title}」を開く`,
                    onclick: () => on.open(group.target),
                  },
                  children: [
                    h({ tag: "span", attrs: { class: "pe-kind" }, children: [who.kind] }),
                    who.id === null ? null : h({ tag: "span", attrs: { class: "mono" }, children: [who.id] }),
                    h({ tag: "span", attrs: { class: "pe-title" }, children: [who.title] }),
                  ],
                }),
              ],
            }),
            h({
              tag: "ul",
              attrs: { class: "pe-rows" },
              children: group.edits.map((edit) => editRow({ edit, who, blockedEdit: blockedBy.get(edit.id), index, on })),
            }),
          ],
        }),
      );
    }

    const label = saving ? "保存しています…" : removals > 0 ? `まとめて保存する（${removals} 件を削除）` : "まとめて保存する";
    return h({
      tag: "aside",
      attrs: { class: "pending-panel", "aria-label": "保存待ちの編集", id: "pending-panel" },
      children: [
        h({
          tag: "div",
          attrs: { class: "comments-head" },
          children: [
            h({
              tag: "h2",
              attrs: { tabindex: "-1" },
              children: ["保存待ち", h({ tag: "span", attrs: { class: "count" }, children: [`${edits.length} 件`] })],
            }),
            h({ tag: "span", attrs: { class: "spacer" } }),
            h({
              tag: "button",
              attrs: {
                class: "icon-btn",
                type: "button",
                "aria-label": "保存待ちの編集を閉じる",
                "data-focus": "close",
                onclick: () => on.close(),
              },
              children: [icon("x")],
            }),
          ],
        }),
        list,
        h({
          tag: "div",
          attrs: { class: "comments-free pe-foot" },
          children: [
            edits.length === 0
              ? null
              : h({
                  tag: "p",
                  attrs: { class: "pe-foot-sum" },
                  children: [`${edits.length} 件${removals > 0 ? `（うち削除 ${removals} 件）` : ""}をワークスペースに書きます`],
                }),
            h({
              tag: "button",
              attrs: {
                class: "btn primary pe-save",
                type: "button",
                disabled: saving || edits.length === 0,
                "aria-busy": saving ? "true" : null,
                onclick: () => on.save(),
              },
              children: [saving ? h({ tag: "span", attrs: { class: "pe-spin" }, children: [icon("spin")] }) : icon("save"), label],
            }),
          ],
        }),
      ],
    });
  }

  /** 編集の行（何を・前 → 後・書き込めない理由と、取り消すボタン） */
  function editRow({
    edit,
    who,
    blockedEdit,
    index,
    on,
  }: {
    edit: PendingEdit;
    who: { kind: string; id: string | null; title: string };
    blockedEdit: BlockedEdit | undefined;
    index: RecordIndex;
    on: PendingEditsPanelProps["on"];
  }): HTMLElement {
    const text = editRowText(edit);
    const name = `${who.id ?? who.kind} の${text.what}`;
    return h({
      tag: "li",
      attrs: {
        class: `pe-row${blockedEdit === undefined ? "" : " is-blocked"}${edit.op === "item-remove" ? " is-remove" : ""}`,
        id: `pe-row-${edit.id}`,
      },
      children: [
        h({
          tag: "div",
          attrs: { class: "pe-row-main" },
          children: [
            h({
              tag: "span",
              attrs: { class: "pe-what" },
              children: [edit.op === "item-remove" ? icon("trash") : null, text.what],
            }),
            changeView(text),
            blockedEdit === undefined
              ? null
              : blockedNote({
                  blocked: blockedEdit,
                  updated: index.byId.get(edit.target)?.item.updated ?? null,
                  onOpen: on.open,
                }),
          ],
        }),
        h({
          tag: "button",
          attrs: {
            class: "btn ghost pe-undo",
            type: "button",
            "data-focus": `undo:${edit.id}`,
            "aria-label": `${name}の編集を取り消す`,
            onclick: () => on.undo(edit.id),
          },
          children: [icon("undo"), h({ tag: "span", attrs: { class: "lbl" }, children: ["取り消す"] })],
        }),
      ],
    });
  }

  /** まとめて保存できたときに画面の下に出す知らせ（`role="status"`）。消すのは使う側 */
  export function savedNotice({ count }: { count: number }): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "pe-toast", role: "status" },
      children: [icon("check"), h({ tag: "span", children: [`${count} 件を保存しました。`] })],
    });
  }
}
