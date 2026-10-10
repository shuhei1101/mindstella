"use strict";
// 取り下げの札。取り下げた調査・資料・用語集・メモ・会話ログのタイトルの右に、差分の表示によらず置く。検討事項の状態「取り下げ」と同じ × の印と文言に枠を付け、状態の札（枠なし）と見分ける。
var MindmapPreview;
(function (MindmapPreview) {
    /** 取り下げの札。× の印は読み上げに出さず、「取り下げ」の文字で伝える */
    function withdrawnBadge({ large = false } = {}) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: large ? "wd-badge wd-large" : "wd-badge" },
            children: [MindmapPreview.statusMark("取り下げ"), "取り下げ"],
        });
    }
    MindmapPreview.withdrawnBadge = withdrawnBadge;
})(MindmapPreview || (MindmapPreview = {}));
