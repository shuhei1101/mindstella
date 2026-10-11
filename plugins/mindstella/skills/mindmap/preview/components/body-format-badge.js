"use strict";
// 本文の形式の札。資料のカード・ボードのカードの種類の右と、表の「形式」の列と、詳細のヘッダーの種類と ID の右に置く。形式の名前を等幅の文字で出し、HTML は地の面を敷いて一覧で拾いやすくする。
var MindmapPreview;
(function (MindmapPreview) {
    /** 形式 → 札の文言 */
    const FORMAT_LABEL = { md: "MD", html: "HTML" };
    /** 形式 → 札の `title`（略語だけにしない） */
    const FORMAT_TITLE = { md: "本文は Markdown", html: "本文は HTML" };
    /** 本文の形式の札。色だけに頼らず、`MD` / `HTML` の文字で伝える */
    function bodyFormatBadge({ format }) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: `fmt-badge fmt-${format}`, title: FORMAT_TITLE[format] },
            children: [FORMAT_LABEL[format]],
        });
    }
    MindmapPreview.bodyFormatBadge = bodyFormatBadge;
    /** 資料の `body` から本文の形式の札を返す（`body` を持たないか知らない拡張子なら null） */
    function bodyFormatBadgeOf(body) {
        const format = MindmapPreview.bodyFormatOf(body);
        return format === null ? null : bodyFormatBadge({ format });
    }
    MindmapPreview.bodyFormatBadgeOf = bodyFormatBadgeOf;
})(MindmapPreview || (MindmapPreview = {}));
