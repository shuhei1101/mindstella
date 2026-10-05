// 差分の印。差分の表示の間、選んだ時点で足した項目に新規（太い +）、変えた項目に変更（塗った ●）の印を出す。

namespace MindmapPreview {
  /** 差分の印の種類（新規・変更） */
  export type DiffKind = "new" | "changed";

  /** 項目の ID → 差分の印。差分の表示の間だけ画面に渡す */
  export type DiffMarks = Record<string, DiffKind>;

  /** 差分の印の引数 */
  export type DiffMarkProps = {
    kind: DiffKind;
    /** 真のとき記号に文言（「新規」「変更」）を付けた札にする。詳細パネルの題の横だけが使う */
    labeled?: boolean;
  };

  /** 種類 → 画面に出す名前 */
  const DIFF_LABEL: Record<DiffKind, string> = { new: "新規", changed: "変更" };

  /** 差分の印。色だけでなく形（+ と ●）でも新規と変更を分け、名前は読み上げに残す */
  export function diffMark({ kind, labeled = false }: DiffMarkProps): HTMLElement {
    const label = DIFF_LABEL[kind];
    const glyph = icon(kind === "new" ? "plus" : "changed");
    const tone = kind === "new" ? "df-new" : "df-chg";
    // 札: 記号と文言を見える形で出す
    if (labeled) return h({ tag: "span", attrs: { class: `df-badge ${tone}` }, children: [glyph, label] });
    // 一覧の印: 記号だけを見せ、名前を読み上げと title に持つ
    return h({
      tag: "span",
      attrs: { class: `df-mark ${tone}`, title: label },
      children: [glyph, h({ tag: "span", attrs: { class: "sr-only" }, children: [label] })],
    });
  }

  /** 項目の ID に印があれば、一覧の印（文言なし）を返す。無ければ null */
  export function markFor({ marks, id }: { marks: DiffMarks | undefined; id: string }): HTMLElement | null {
    const kind = marks?.[id];
    return kind === undefined ? null : diffMark({ kind });
  }
}
