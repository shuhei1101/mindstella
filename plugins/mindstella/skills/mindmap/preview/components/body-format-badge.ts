// 本文の形式の札。資料のカード・ボードのカードの種類の右と、表の「形式」の列と、詳細のヘッダーの種類と ID の右に置く。形式の名前を等幅の文字で出し、HTML は地の面を敷いて一覧で拾いやすくする。

namespace MindmapPreview {
  /** 本文の形式の札の引数 */
  export type BodyFormatBadgeProps = {
    /** 本文の形式。資料の `body` の拡張子から使う側が決める（`html` のコードブロックを含む Markdown の資料は `md`） */
    format: "md" | "html";
  };

  /** 形式 → 札の文言 */
  const FORMAT_LABEL = { md: "MD", html: "HTML" } as const;

  /** 形式 → 札の `title`（略語だけにしない） */
  const FORMAT_TITLE = { md: "本文は Markdown", html: "本文は HTML" } as const;

  /** 本文の形式の札。色だけに頼らず、`MD` / `HTML` の文字で伝える */
  export function bodyFormatBadge({ format }: BodyFormatBadgeProps): HTMLElement {
    return h({
      tag: "span",
      attrs: { class: `fmt-badge fmt-${format}`, title: FORMAT_TITLE[format] },
      children: [FORMAT_LABEL[format]],
    });
  }

  /** 資料の `body` から本文の形式の札を返す（`body` を持たないか知らない拡張子なら null） */
  export function bodyFormatBadgeOf(body: string | undefined): HTMLElement | null {
    const format = bodyFormatOf(body);
    return format === null ? null : bodyFormatBadge({ format });
  }
}
