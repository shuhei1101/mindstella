// 重なった ID の通知。トップバーの下の帯に、同じ ID の項目が 2 件になったことと、その ID のリンク・片方の ID を変更する案内・閉じるボタンを出す。自動では閉じない。

namespace MindmapPreview {
  /** 重なった ID の通知の引数 */
  export type DuplicateIdNoticeProps = {
    /** 重なった ID と、その項目の種類の名前。空なら何も描かない */
    ids: { id: string; kind: string }[];
    /** ID のリンクを押したとき */
    onOpen: (id: string) => void;
    /** 閉じるボタンを押したとき */
    onClose: () => void;
  };

  /** 重なった ID の通知の帯（`role="alert"`）。`ids` が空なら null */
  export function duplicateIdNotice({ ids, onOpen, onClose }: DuplicateIdNoticeProps): HTMLElement | null {
    if (ids.length === 0) return null;
    const links: Child[] = [];
    ids.forEach(({ id, kind }, index) => {
      if (index > 0) links.push("、");
      links.push(
        `${kind} `,
        h({
          tag: "a",
          attrs: {
            href: `#id=${encodeURIComponent(id)}`,
            class: "mono",
            onclick: (event) => {
              event.preventDefault();
              onOpen(id);
            },
          },
          children: [id],
        }),
      );
    });
    return h({
      tag: "div",
      attrs: { class: "dup-note", role: "alert" },
      children: [
        icon("alert"),
        h({
          tag: "div",
          attrs: { class: "dup-body" },
          children: [
            h({ tag: "strong", children: ["同じ ID の項目が 2 件あります"] }),
            "ほかのセッションの書き込みで、",
            h({ tag: "span", attrs: { class: "dup-ids" }, children: links }),
            " が重なりました。片方の ID を変更してください。",
          ],
        }),
        h({
          tag: "button",
          attrs: { class: "dup-close", type: "button", "aria-label": "通知を閉じる", title: "通知を閉じる", onclick: () => onClose() },
          children: [icon("x")],
        }),
      ],
    });
  }
}
