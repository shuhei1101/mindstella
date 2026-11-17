"use strict";
// 重なった ID の通知。トップバーの下の帯に、同じ ID の項目が 2 件になったことと、その ID のリンク・片方の ID を変更する案内・閉じるボタンを出す。自動では閉じない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 重なった ID の通知の帯（`role="alert"`）。`ids` が空なら null */
    function duplicateIdNotice({ ids, onOpen, onClose }) {
        if (ids.length === 0)
            return null;
        const links = [];
        ids.forEach(({ id, kind }, index) => {
            if (index > 0)
                links.push("、");
            links.push(`${kind} `, MindmapPreview.h({
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
            }));
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "dup-note", role: "alert" },
            children: [
                MindmapPreview.icon("alert"),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "dup-body" },
                    children: [
                        MindmapPreview.h({ tag: "strong", children: ["同じ ID の項目が 2 件あります"] }),
                        "ほかのセッションの書き込みで、",
                        MindmapPreview.h({ tag: "span", attrs: { class: "dup-ids" }, children: links }),
                        " が重なりました。片方の ID を変更してください。",
                    ],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "dup-close", type: "button", "aria-label": "通知を閉じる", title: "通知を閉じる", onclick: () => onClose() },
                    children: [MindmapPreview.icon("x")],
                }),
            ],
        });
    }
    MindmapPreview.duplicateIdNotice = duplicateIdNotice;
})(MindmapPreview || (MindmapPreview = {}));
