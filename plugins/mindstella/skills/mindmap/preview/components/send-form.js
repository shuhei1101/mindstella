"use strict";
// コメントの入力。詳細パネルと詳細の全画面の下端と、コメントの一覧の下端に留める、コメントをレビュー中に溜める入力欄と「レビューに追加」のボタン。選んだ箇所を添えられ、溜めた結果を入力の近くに出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 溜めている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる処理では点滅させない */
    const SENDING_NOTICE_DELAY_MS = 1000;
    /** 項目を指さないコメントの入力欄の読み上げの名前 */
    const NO_TARGET_LABEL = "項目を指さないコメント";
    /** 入力欄の ID に付ける連番（同じ文書に複数置いても ID が重ならないように） */
    let sendFormSequence = 0;
    /** UTC のタイムゾーン付き ISO 8601 を JST の `MM/DD HH:mm` にする */
    function formatJst(iso) {
        const parts = new Intl.DateTimeFormat("ja-JP", {
            timeZone: "Asia/Tokyo",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
        }).formatToParts(new Date(iso));
        const part = (type) => parts.find((entry) => entry.type === type)?.value ?? "";
        return `${part("month")}/${part("day")} ${part("hour")}:${part("minute")}`;
    }
    MindmapPreview.formatJst = formatJst;
    /** 結果の要素の中身（状態ごとの印と文言） */
    function resultContent({ status, count, detail, onCopy, }) {
        if (status === "saved") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`レビューに追加しました（レビュー中 ${count ?? 0} 件）。`] })];
        }
        if (status === "empty") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["コメントを入れてから追加してください。"] })];
        }
        if (status === "failed") {
            // サーバーが理由を返した: 理由を出す
            if (detail !== null && detail !== undefined) {
                return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`レビューに追加できませんでした。${detail}`] })];
            }
            // サーバーに届かなかった: 立ち上げ直すと URL が変わり、書きかけは引き継がれないので、本文を写す手段を添える
            return [
                MindmapPreview.icon("alert"),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "send-msg-body" },
                    children: [
                        MindmapPreview.h({
                            tag: "span",
                            children: [
                                "レビューに追加できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから追加してください。",
                            ],
                        }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn ghost send-copy", type: "button", onclick: onCopy },
                            children: [MindmapPreview.icon("copy"), "本文を写す"],
                        }),
                    ],
                }),
            ];
        }
        return [];
    }
    /** 添えた箇所（名前・選んだ文・外す ×）の要素 */
    function locationChip({ loc, label, onUnquote }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "send-loc" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-loc-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "send-loc-name" }, children: [label] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn send-unquote", type: "button", "aria-label": "箇所を外す", title: "箇所を外す", onclick: onUnquote },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [loc.text] }),
            ],
        });
    }
    /** 項目へのコメントをレビュー中に溜める入力欄と「レビューに追加」のボタン、結果を返す */
    function sendForm({ target, loc = null, locLabel = null, body = "", status = "idle", count = null, detail = null, collapsed = false, on, }) {
        sendFormSequence += 1;
        const fieldId = `send-${sendFormSequence}`;
        const messageId = `${fieldId}-msg`;
        /** 畳むのは、項目を指さない入力だけ */
        const folded = collapsed && target === null;
        /** 溜めている間は溜めない。それ以外は入力欄の中身そのままを渡す */
        const trySave = () => {
            if (status === "saving")
                return;
            on.save(textarea.value);
        };
        const textarea = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: fieldId,
                name: "body",
                rows: folded ? 1 : 2,
                "aria-label": target === null ? NO_TARGET_LABEL : null,
                "aria-describedby": folded ? null : messageId,
                "aria-keyshortcuts": "Control+Enter",
                // 溜めている間は書き換えられない
                readonly: status === "saving",
                // 本文が空で溜めようとした: 入力の誤りとして示す
                "aria-invalid": status === "empty" ? "true" : null,
                oninput: () => on.input(textarea.value),
                onfocus: () => on.focus(),
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では溜めない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        trySave();
                    }
                },
            },
            children: [body],
        });
        const message = MindmapPreview.h({
            tag: "p",
            attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" },
            children: resultContent({ status, count, detail, onCopy: () => on.copy(textarea.value) }),
        });
        // 溜めている印と文言は、待ちの後に入れる
        if (status === "saving") {
            window.setTimeout(() => {
                message.replaceChildren(MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["レビューに追加しています"] }));
            }, SENDING_NOTICE_DELAY_MS);
        }
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: `send send-footer${folded ? " collapsed" : ""}`,
                novalidate: true,
                "data-id": target,
                onsubmit: (event) => {
                    event.preventDefault();
                    trySave();
                },
                onfocusout: (event) => {
                    // フォーカスが部品の外へ出たときだけ知らせる
                    const next = event.relatedTarget;
                    if (next === null || !form.contains(next))
                        on.blur();
                },
            },
            children: [
                target === null
                    ? null
                    : MindmapPreview.h({
                        tag: "label",
                        attrs: { class: "send-label", for: fieldId },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }), " へのコメント"],
                    }),
                target !== null && loc !== null ? locationChip({ loc, label: locLabel ?? MindmapPreview.locationLabel(loc), onUnquote: on.unquote }) : null,
                textarea,
                folded
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "send-row" },
                        children: [
                            message,
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "btn primary",
                                    type: "submit",
                                    title: "レビューに追加（Ctrl+Enter）",
                                    disabled: status === "saving",
                                },
                                children: [MindmapPreview.icon("comment"), "レビューに追加"],
                            }),
                        ],
                    }),
            ],
        });
        return form;
    }
    MindmapPreview.sendForm = sendForm;
})(MindmapPreview || (MindmapPreview = {}));
