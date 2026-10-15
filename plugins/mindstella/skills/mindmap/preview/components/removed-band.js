"use strict";
// 消した項目の帯。差分の表示の間、選んだ時点で消したその種類の項目を、一覧の上に消した印・ID・消したときのタイトルで並べる。消した項目は中身が残らないので、押せる要素にしない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 消した項目の帯。項目が無ければ null */
    function removedBand({ items }) {
        if (items.length === 0)
            return null;
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "rm-band", "aria-label": "この時点で消した項目" },
            children: [
                MindmapPreview.h({
                    tag: "h2",
                    attrs: { class: "rm-band-t" },
                    children: ["消した項目", MindmapPreview.h({ tag: "span", attrs: { class: "n mono" }, children: [items.length] })],
                }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "rm-list" },
                    children: items.map((item) => MindmapPreview.h({
                        tag: "li",
                        attrs: { class: "rm-item", "data-removed-id": item.id },
                        children: [
                            MindmapPreview.diffMark({ kind: "removed" }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "rm-ttl" }, children: [item.title] }),
                        ],
                    })),
                }),
            ],
        });
    }
    MindmapPreview.removedBand = removedBand;
})(MindmapPreview || (MindmapPreview = {}));
