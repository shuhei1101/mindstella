"use strict";
// コメントの印。コメントを書いた項目に、吹き出しの線と件数の小さなピルを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 画面に実数で出す件数の上限（これを超えると「99+」） */
    const COMMENT_MARK_SHOWN_MAX = 99;
    /** 印を置く場所を表す属性（値は項目の ID） */
    const COMMENT_TARGET_ATTR = "data-comment-target";
    /** コメントの印。数字は画面にだけ見せ、読み上げは実数の「コメント {件数} 件」を `sr-only` と `title` に持つ */
    function commentMark({ count }) {
        const spoken = `コメント ${count} 件`;
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "cmk", title: spoken },
            children: [
                MindmapPreview.icon("bubble"),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "cmk-n", "aria-hidden": "true" },
                    children: [count > COMMENT_MARK_SHOWN_MAX ? `${COMMENT_MARK_SHOWN_MAX}+` : String(count)],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [spoken] }),
            ],
        });
    }
    MindmapPreview.commentMark = commentMark;
    /** 本文の画面の中の印を置く場所ごとに、`counts` の件数で印を入れ替える。画面は描き直さない */
    function refreshCommentMarks({ root, counts, }) {
        for (const place of root.querySelectorAll(`[${COMMENT_TARGET_ATTR}]`)) {
            const count = counts[place.getAttribute(COMMENT_TARGET_ATTR) ?? ""] ?? 0;
            // 件数が無い場所は空にする
            if (count === 0)
                place.replaceChildren();
            else
                place.replaceChildren(commentMark({ count }));
        }
    }
    MindmapPreview.refreshCommentMarks = refreshCommentMarks;
    /** 項目の印を置く場所（`refreshCommentMarks` が差し替える）。件数があればその印を入れて返す */
    function commentPlace({ id, count }) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "cmk-place", [COMMENT_TARGET_ATTR]: id },
            children: [count === undefined || count === 0 ? null : commentMark({ count })],
        });
    }
    MindmapPreview.commentPlace = commentPlace;
})(MindmapPreview || (MindmapPreview = {}));
