// 保存待ちの印。保存待ちの編集がある項目・キー・案に、破線の枠と印と文字の札を出す。

namespace MindmapPreview {
  /** 保存待ちの印の引数 */
  export type PendingEditMarkProps = {
    /** 書き換え・追加は pending、削除は remove、保存で書き込めなかった編集は blocked */
    kind: PendingMarkKind;
    /** 印だけにするか。場所が狭いところで使う。文字は読み上げと title に残す */
    compact?: boolean;
  };

  /** 種類 → 札の文字とアイコン */
  const PENDING_MARKS: Record<PendingMarkKind, { label: string; icon: IconName }> = {
    pending: { label: "保存待ち", icon: "layers" },
    remove: { label: "保存で削除", icon: "trash" },
    blocked: { label: "書き込めない", icon: "alert" },
  };

  /** 保存待ちの印。差分の印・コメントの印と形で見分けられるよう、破線の枠（書き込めない編集は実線）にする */
  export function pendingEditMark({ kind, compact = false }: PendingEditMarkProps): HTMLElement {
    const { label, icon: name } = PENDING_MARKS[kind];
    return h({
      tag: "span",
      attrs: { class: `pm pm-${kind}${compact ? " pm-compact" : ""}`, title: compact ? label : null },
      children: [
        icon(name),
        compact ? h({ tag: "span", attrs: { class: "sr-only" }, children: [label] }) : label,
      ],
    });
  }

  /** 項目の保存待ちの印（無ければ null）。カードと表の行は文字つき、マップの節は印だけ */
  export function editMarkOf({
    edit,
    id,
    compact = false,
  }: {
    edit: { marks: Record<string, PendingMarkKind> } | null | undefined;
    id: string;
    compact?: boolean;
  }): HTMLElement | null {
    const kind = edit?.marks[id];
    return kind === undefined ? null : pendingEditMark({ kind, compact });
  }

  /** 一覧の上の帯に置く「項目を追加」。幅 480px 以下は印だけにし、文字を読み上げに残す */
  export function addItemButton({ kind, onAdd }: { kind: Kind; onAdd: () => void }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: "btn pe-add",
        type: "button",
        "data-kind": kind,
        "aria-label": `${KIND_LABEL[kind]}の項目を追加`,
        title: "項目を追加",
        onclick: () => onAdd(),
      },
      children: [icon("plus"), h({ tag: "span", attrs: { class: "lbl" }, children: ["項目を追加"] })],
    });
  }

  /** 追加する項目のタイトル（まだ書いていなければ「（タイトル未入力）」） */
  export function addedTitle(item: Item): string {
    return item.title === "" ? "（タイトル未入力）" : item.title;
  }

  /** 追加する項目のカード（ボード・資料のカード）。ID の場所に「ID は保存で決まる」を置く破線の枠 */
  export function addedCard({
    item,
    mark,
    open,
    doc = false,
  }: {
    item: Item;
    mark: PendingMarkKind;
    open: (id: string) => void;
    /** 資料のカードの形にするか */
    doc?: boolean;
  }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: `card${doc ? " doc-card" : ""} pe-new`,
        type: "button",
        "data-new-id": item.id,
        onclick: () => open(item.id),
      },
      children: [
        h({ tag: doc ? "span" : "div", attrs: { class: "c-ttl" }, children: [addedTitle(item)] }),
        h({
          tag: doc ? "span" : "div",
          attrs: { class: "c-meta" },
          children: [h({ tag: "span", attrs: { class: "pe-noid" }, children: ["ID は保存で決まる"] }), pendingEditMark({ kind: mark })],
        }),
      ],
    });
  }
}
