"use strict";
// 返信の入力。スレッドの下端に留める、返信をレビュー中に溜める入力欄と「レビューに追加」のボタン。
var MindmapPreview;
(function (MindmapPreview) {
    /** 入力欄の ID に付ける連番（同じ文書に複数置いても ID が重ならないように） */
    let replyFormSequence = 0;
    /** 結果の要素の中身（状態ごとの印と文言） */
    function replyResult({ status, count, detail }) {
        if (status === "saving") {
            return [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["レビューに追加しています"] })];
        }
        if (status === "saved") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`レビューに追加しました（レビュー中 ${count ?? 0} 件）。`] })];
        }
        if (status === "failed") {
            const reason = detail === null || detail === undefined
                ? "サーバーが止まっています。立ち上げ直してから追加してください。"
                : detail;
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`レビューに追加できませんでした。${reason}`] })];
        }
        return [];
    }
    /** 返信をレビュー中に溜める入力欄と「レビューに追加」のボタン、結果を返す */
    function replyForm({ thread, body = "", status = "idle", count = null, detail = null, on }) {
        replyFormSequence += 1;
        const fieldId = `reply-${replyFormSequence}`;
        const messageId = `${fieldId}-msg`;
        const saving = status === "saving";
        /** 空白だけの間と溜めている間は溜めない。それ以外は入力欄の中身そのままを渡す */
        const trySave = () => {
            if (saving || textarea.value.trim() === "")
                return;
            on.save(thread, textarea.value);
        };
        const textarea = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: fieldId,
                name: "body",
                rows: 2,
                maxlength: MindmapPreview.COMMENT_BODY_MAX_LENGTH,
                "aria-keyshortcuts": "Control+Enter",
                "aria-describedby": messageId,
                // 溜めている間は書き換えられない
                readonly: saving,
                oninput: () => {
                    on.input(textarea.value);
                    // 入力に合わせて、ボタンを押せるかを合わせる
                    submit.disabled = saving || textarea.value.trim() === "";
                },
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では溜めない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        trySave();
                    }
                    // Esc は入力から外れるだけにする（使う側の「一覧へ戻る」へ伝えない）
                    if (key.key === "Escape") {
                        key.preventDefault();
                        key.stopPropagation();
                        textarea.blur();
                    }
                },
            },
            children: [body],
        });
        const submit = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn primary",
                type: "submit",
                title: "レビューに追加（Ctrl+Enter）",
                "data-focus": "reply-send",
                disabled: saving || body.trim() === "",
            },
            children: [MindmapPreview.icon("comment"), "レビューに追加"],
        });
        return MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "send send-footer reply",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    trySave();
                },
            },
            children: [
                MindmapPreview.h({ tag: "label", attrs: { class: "send-label", for: fieldId }, children: ["返信"] }),
                textarea,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-row" },
                    children: [
                        MindmapPreview.h({ tag: "p", attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" }, children: replyResult({ status, count, detail }) }),
                        submit,
                    ],
                }),
            ],
        });
    }
    MindmapPreview.replyForm = replyForm;
})(MindmapPreview || (MindmapPreview = {}));
