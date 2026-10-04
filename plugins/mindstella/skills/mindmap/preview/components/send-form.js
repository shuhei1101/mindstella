"use strict";
// 回答・意見の送信。詳細パネルと詳細の全画面の下端に留める、開いている項目へ回答・意見を送る入力欄と送るボタン。送った結果を入力の近くに出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 送っている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる送信では点滅させない */
    const SENDING_NOTICE_DELAY_MS = 1000;
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
    /** 結果の要素の中身（状態ごとの印と文言）。送っている間は、待ちの後に印と文言を入れる */
    function resultContent({ status, sentAt, detail, onCopy }) {
        if (status === "sent") {
            return [
                MindmapPreview.icon("check"),
                MindmapPreview.h({
                    tag: "span",
                    children: [`送りました（${sentAt === null || sentAt === undefined ? "" : formatJst(sentAt)}）。次の話し合いの最初に取り込みます。`],
                }),
            ];
        }
        if (status === "empty") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["回答・意見を入れてから送ってください。"] })];
        }
        if (status === "failed") {
            // サーバーが理由を返した: 理由を出す
            if (detail !== null && detail !== undefined) {
                return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`送れませんでした。${detail}`] })];
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
                                "送れませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから送ってください。",
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
    /** 項目へ回答・意見を送る入力欄と送るボタン、結果を返す */
    function sendForm({ target, body = "", status = "idle", sentAt = null, detail = null, onInput, onSend, onCopy, }) {
        sendFormSequence += 1;
        const fieldId = `send-${sendFormSequence}`;
        const messageId = `${fieldId}-msg`;
        /** 送っている間は送らない。それ以外は入力欄の中身そのままを渡す */
        const trySend = () => {
            if (status === "sending")
                return;
            onSend(textarea.value);
        };
        const textarea = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: fieldId,
                name: "body",
                rows: 2,
                "aria-describedby": messageId,
                "aria-keyshortcuts": "Control+Enter",
                // 送っている間は書き換えられない
                readonly: status === "sending",
                // 本文が空で送ろうとした: 入力の誤りとして示す
                "aria-invalid": status === "empty" ? "true" : null,
                oninput: () => onInput(textarea.value),
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では送らない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        trySend();
                    }
                },
            },
            children: [body],
        });
        const message = MindmapPreview.h({
            tag: "p",
            attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" },
            children: resultContent({ status, sentAt, detail, onCopy: () => onCopy(textarea.value) }),
        });
        // 送っている印と文言は、待ちの後に入れる
        if (status === "sending") {
            window.setTimeout(() => {
                message.replaceChildren(MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["送っています"] }));
            }, SENDING_NOTICE_DELAY_MS);
        }
        return MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "send send-footer",
                novalidate: true,
                "data-id": target,
                onsubmit: (event) => {
                    event.preventDefault();
                    trySend();
                },
            },
            children: [
                MindmapPreview.h({
                    tag: "label",
                    attrs: { class: "send-label", for: fieldId },
                    children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }), " への回答・意見"],
                }),
                textarea,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-row" },
                    children: [
                        message,
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary",
                                type: "submit",
                                title: "送る（Ctrl+Enter）",
                                disabled: status === "sending",
                            },
                            children: [MindmapPreview.icon("send"), "送る"],
                        }),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.sendForm = sendForm;
})(MindmapPreview || (MindmapPreview = {}));
