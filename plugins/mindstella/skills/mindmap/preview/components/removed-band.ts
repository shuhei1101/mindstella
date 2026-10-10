// 消した項目の帯。差分の表示の間、選んだ時点で消したその種類の項目を、一覧の上に消した印・ID・消したときのタイトルで並べる。消した項目は中身が残らないので、押せる要素にしない。

namespace MindmapPreview {
  /** 消した項目の帯の引数 */
  export type RemovedBandProps = {
    /** 消した項目。渡した並びで出す */
    items: Pick<RemovedItem, "id" | "title">[];
  };

  /** 消した項目の帯。項目が無ければ null */
  export function removedBand({ items }: RemovedBandProps): HTMLElement | null {
    if (items.length === 0) return null;
    return h({
      tag: "section",
      attrs: { class: "rm-band", "aria-label": "この時点で消した項目" },
      children: [
        h({
          tag: "h2",
          attrs: { class: "rm-band-t" },
          children: ["消した項目", h({ tag: "span", attrs: { class: "n mono" }, children: [items.length] })],
        }),
        h({
          tag: "ul",
          attrs: { class: "rm-list" },
          children: items.map((item) =>
            h({
              tag: "li",
              attrs: { class: "rm-item", "data-removed-id": item.id },
              children: [
                diffMark({ kind: "removed" }),
                h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
                h({ tag: "span", attrs: { class: "rm-ttl" }, children: [item.title] }),
              ],
            }),
          ),
        }),
      ],
    });
  }
}
