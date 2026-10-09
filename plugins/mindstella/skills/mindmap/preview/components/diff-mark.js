"use strict";
// 差分の印。差分の表示の間、選んだ時点で足した項目に新規（太い +）、変えた項目に変更（塗った ●）、消した項目に消した（太い −）の印を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類 → 画面に出す名前 */
    const DIFF_LABEL = { new: "新規", changed: "変更", removed: "消した" };
    /** 種類 → 記号 */
    const DIFF_GLYPH = { new: "plus", changed: "changed", removed: "minus" };
    /** 種類 → 色の class */
    const DIFF_TONE = { new: "df-new", changed: "df-chg", removed: "df-del" };
    /** 差分の印。色だけでなく形（+ と ● と −）でも新規と変更と消したを分け、名前は読み上げに残す */
    function diffMark({ kind, labeled = false }) {
        const label = DIFF_LABEL[kind];
        const glyph = MindmapPreview.icon(DIFF_GLYPH[kind]);
        const tone = DIFF_TONE[kind];
        // 札: 記号と文言を見える形で出す
        if (labeled)
            return MindmapPreview.h({ tag: "span", attrs: { class: `df-badge ${tone}` }, children: [glyph, label] });
        // 一覧の印: 記号だけを見せ、名前を読み上げと title に持つ
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: `df-mark ${tone}`, title: label },
            children: [glyph, MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [label] })],
        });
    }
    MindmapPreview.diffMark = diffMark;
    /** 項目の ID に印があれば、一覧の印（文言なし）を返す。無ければ null */
    function markFor({ marks, id }) {
        const kind = marks?.[id];
        return kind === undefined ? null : diffMark({ kind });
    }
    MindmapPreview.markFor = markFor;
})(MindmapPreview || (MindmapPreview = {}));
