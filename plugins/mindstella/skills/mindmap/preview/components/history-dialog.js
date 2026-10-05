"use strict";
// 変更履歴のモーダル。差分の表示で比べる時点を、日時・説明・変わった項目の数つきで新しい順に並べ、1 つ選ばせる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 時点の行（押すと選ぶ。選んでいる行にチェックと `aria-current` を付ける） */
    function pointRow({ point, selected, onPick, }) {
        return MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "hist-item",
                        type: "button",
                        "data-sel": point.sel,
                        "aria-current": selected ? "true" : null,
                        // 開いたときのフォーカスは、選んでいる行に置く
                        autofocus: selected,
                        onclick: () => onPick(point.sel),
                    },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "hist-check", "aria-hidden": "true" }, children: [selected ? MindmapPreview.icon("check") : null] }),
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "hist-main" },
                            children: [
                                MindmapPreview.h({ tag: "span", attrs: { class: "hist-name" }, children: [point.name] }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "hist-sub" }, children: [point.sub] }),
                            ],
                        }),
                        point.count === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "hist-n mono" }, children: [`${point.count} 件`] }),
                    ],
                }),
            ],
        });
    }
    /** 変更履歴のモーダルを返す。文書に入れた後、呼ぶ側が `showModal()` で開く。外側の押下と Esc で閉じる */
    function historyDialog({ points, current, onPick, onClose }) {
        const dialog = MindmapPreview.h({
            tag: "dialog",
            attrs: { class: "hist", "aria-labelledby": "hist-title", closedby: "any" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "hist-head" },
                    children: [
                        MindmapPreview.h({ tag: "h2", attrs: { id: "hist-title" }, children: ["変更履歴"] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn",
                                type: "button",
                                "data-act": "hist-close",
                                "aria-label": "変更履歴を閉じる",
                                onclick: () => dialog.close(),
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "hist-list" },
                    children: points.map((point) => pointRow({
                        point,
                        selected: point.sel === current,
                        onPick: (sel) => {
                            // 選んだら閉じてから知らせる（使う側が描き直しても、モーダルが残らない）
                            dialog.close();
                            onPick(sel);
                        },
                    })),
                }),
            ],
        });
        // 外側（後ろの幕）を押したときも閉じる（`closedby` が効かない環境のため）
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog)
                dialog.close();
        });
        dialog.addEventListener("close", () => {
            dialog.remove();
            onClose();
        });
        return dialog;
    }
    MindmapPreview.historyDialog = historyDialog;
})(MindmapPreview || (MindmapPreview = {}));
