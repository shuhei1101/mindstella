"use strict";
// 既定の保存の確かめ。ワークスペースの既定として保存する前に、今の既定と保存する値を並べるモーダル。
var MindmapPreview;
(function (MindmapPreview) {
    /** 表示する種類を、外した種類の名前で書く（全て出すときは「すべて表示」） */
    function kindsText(kinds) {
        const hidden = MindmapPreview.KIND_KEYS.filter((kind) => !kinds.has(kind)).map((kind) => MindmapPreview.KIND_LABEL[kind]);
        return hidden.length > 0 ? `${hidden.join("・")}を表示しない` : "すべて表示";
    }
    MindmapPreview.kindsText = kindsText;
    /** 確かめの 1 行。変える項目は今の既定と保存する値を、変えない項目は今の値と「変えない」を出す */
    function confirmRow({ label, from, to }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "sc-row" },
            children: [
                MindmapPreview.h({ tag: "dt", children: [label] }),
                MindmapPreview.h({
                    tag: "dd",
                    children: from === to
                        ? [
                            MindmapPreview.h({ tag: "span", attrs: { class: "sc-to" }, children: [to] }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "sc-same" }, children: ["変えない"] }),
                        ]
                        : [
                            MindmapPreview.h({
                                tag: "span",
                                attrs: { class: "sc-from" },
                                children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["今の既定 "] }), from],
                            }),
                            MindmapPreview.icon("arrow"),
                            MindmapPreview.h({
                                tag: "span",
                                attrs: { class: "sc-to" },
                                children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["保存する値 "] }), to],
                            }),
                        ],
                }),
            ],
        });
    }
    /** 既定の保存の確かめを返す。文書に入れた後、呼ぶ側が `showModal()` で開く。最初のフォーカスは「取り消す」 */
    function settingsConfirm({ from, to, busy = false, error = null, on }) {
        const dialog = MindmapPreview.h({
            tag: "dialog",
            attrs: { class: "confirm sconfirm", "aria-labelledby": "sc-h" },
            children: [
                MindmapPreview.h({ tag: "h2", attrs: { id: "sc-h" }, children: ["ワークスペースの既定を書き換えますか"] }),
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "sc-lead" },
                    children: ["このワークスペースを開く全員の既定が変わります。表示の設定を自分で変えている人には、変えた項目は当たりません。"],
                }),
                MindmapPreview.h({
                    tag: "dl",
                    attrs: { class: "sc-list" },
                    children: [
                        confirmRow({ label: "つながりの見た目", from: MindmapPreview.lookLabel(from.look), to: MindmapPreview.lookLabel(to.look) }),
                        confirmRow({ label: "表示する種類", from: kindsText(from.kinds), to: kindsText(to.kinds) }),
                    ],
                }),
                error === null
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "sc-error", role: "alert" },
                        children: [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [error] })],
                    }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "cf-row" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn ghost",
                                type: "button",
                                autofocus: true,
                                disabled: busy,
                                "data-focus": "cancel",
                                onclick: () => on.cancel(),
                            },
                            children: ["取り消す"],
                        }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary",
                                type: "button",
                                disabled: busy,
                                "data-focus": "confirm",
                                onclick: () => on.save(),
                            },
                            children: busy ? [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), "保存しています"] : ["保存する"],
                        }),
                    ],
                }),
            ],
        });
        // Esc: 保存している間は閉じず、それ以外は取り消す（ブラウザの既定の閉じ方を止めて、使う側が閉じる）
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            if (!busy)
                on.cancel();
        });
        return dialog;
    }
    MindmapPreview.settingsConfirm = settingsConfirm;
})(MindmapPreview || (MindmapPreview = {}));
