// コメントの印。コメントを書いた項目に、吹き出しの線と件数の小さなピルを出す。

namespace MindmapPreview {
  /** コメントの印の引数 */
  export type CommentMarkProps = {
    /** その項目へのレビュー中のコメントの件数（1 以上） */
    count: number;
  };

  /** 画面に実数で出す件数の上限（これを超えると「99+」） */
  const COMMENT_MARK_SHOWN_MAX = 99;

  /** 印を置く場所を表す属性（値は項目の ID） */
  const COMMENT_TARGET_ATTR = "data-comment-target";

  /** コメントの印。数字は画面にだけ見せ、読み上げは実数の「コメント {件数} 件」を `sr-only` と `title` に持つ */
  export function commentMark({ count }: CommentMarkProps): HTMLElement {
    const spoken = `コメント ${count} 件`;
    return h({
      tag: "span",
      attrs: { class: "cmk", title: spoken },
      children: [
        icon("bubble"),
        h({
          tag: "span",
          attrs: { class: "cmk-n", "aria-hidden": "true" },
          children: [count > COMMENT_MARK_SHOWN_MAX ? `${COMMENT_MARK_SHOWN_MAX}+` : String(count)],
        }),
        h({ tag: "span", attrs: { class: "sr-only" }, children: [spoken] }),
      ],
    });
  }

  /** 本文の画面の中の印を置く場所ごとに、`counts` の件数で印を入れ替える。画面は描き直さない */
  export function refreshCommentMarks({
    root,
    counts,
  }: {
    /** 本文の画面の要素 */
    root: ParentNode;
    /** 項目の ID → 件数（`commentCounts`） */
    counts: Record<string, number>;
  }): void {
    for (const place of root.querySelectorAll<HTMLElement>(`[${COMMENT_TARGET_ATTR}]`)) {
      const count = counts[place.getAttribute(COMMENT_TARGET_ATTR) ?? ""] ?? 0;
      // 件数が無い場所は空にする
      if (count === 0) place.replaceChildren();
      else place.replaceChildren(commentMark({ count }));
    }
  }

  /** 項目の印を置く場所（`refreshCommentMarks` が差し替える）。件数があればその印を入れて返す */
  export function commentPlace({ id, count }: { id: string; count: number | undefined }): HTMLElement {
    return h({
      tag: "span",
      attrs: { class: "cmk-place", [COMMENT_TARGET_ATTR]: id },
      children: [count === undefined || count === 0 ? null : commentMark({ count })],
    });
  }
}
