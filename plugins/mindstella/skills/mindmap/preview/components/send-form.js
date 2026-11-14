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
            // サーバーに届かなかった: 立ち上げ直すと URL が変わり、書きかけは引き継がれないので、本文をコピーする手段を添える
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
                            attrs: { class: "icon-btn send-copy", type: "button", "aria-label": "本文をコピー", title: "本文をコピー", onclick: onCopy },
                            children: [MindmapPreview.icon("copy")],
                        }),
                    ],
                }),
            ];
        }
        return [];
    }
    /** 音声入力の結果（レビュー中に追加した・送信した・挿入した・失敗した）の中身。音声入力の結果でなければ null */
    function voiceResultContent(status, detail, entered = false) {
        if (status === "sent") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [entered ? "送信し、Claude Code へ入力しました。" : "送信しました。Claude Code へは入力していません。"] })];
        }
        if (status === "inserted") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: ["文字起こしの結果を挿入しました。"] })];
        }
        if (status === "reviewed") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: ["文字起こしの結果をレビュー中に追加しました。"] })];
        }
        if (status === "voice-failed") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [detail ?? MindmapPreview.VOICE_TEXT.failed] })];
        }
        return null;
    }
    MindmapPreview.voiceResultContent = voiceResultContent;
    /** 録音中・文字起こし中の結果の行の中身。どちらでもなければ null */
    function voiceProgressContent(voice, elapsed) {
        if (voice === "recording") {
            // 録音中: 丸と経過の時間は見た目だけにし、読み上げは「録音中」だけにする
            return [
                MindmapPreview.h({ tag: "span", attrs: { class: "rec-dot", "aria-hidden": "true" } }),
                MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["録音中"] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "rec-time", "aria-hidden": "true" }, children: [MindmapPreview.formatElapsed(elapsed)] }),
            ];
        }
        if (voice === "transcribing") {
            return [
                MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }),
                MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["文字起こししています。"] }),
            ];
        }
        return null;
    }
    MindmapPreview.voiceProgressContent = voiceProgressContent;
    /** 結果の行のクラスの状態（録音中・文字起こし中は音声の状態を優先する） */
    function messageState(voice, status) {
        if (voice === "recording")
            return "recording";
        if (voice === "transcribing")
            return "saving";
        return status;
    }
    MindmapPreview.messageState = messageState;
    /** 録音中に入力欄の場所へ出す波形。音量 1 つが縦の棒 1 本で、読み上げない。録音中でなければ null */
    function voiceWave(voice, levels) {
        if (voice !== "recording")
            return null;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "send-wave", "aria-hidden": "true" },
            children: levels.map((level) => MindmapPreview.h({ tag: "i", attrs: { style: `--lv: ${level}` } })),
        });
    }
    MindmapPreview.voiceWave = voiceWave;
    /** 音声入力のボタンを入れる連番（ツールチップの ID が重ならないように） */
    let voiceSequence = 0;
    /**
     * 入力欄の右に並べる音声入力のボタン。
     * idle・disabled はマイクのボタンと submit を、recording・transcribing は × と ✓ を返す。
     */
    function voiceButtons({ voice, voiceReason, textarea, submit, on, }) {
        if (voice === "recording" || voice === "transcribing") {
            const busy = voice === "transcribing";
            return [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-rec-actions" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn send-rec-cancel",
                                type: "button",
                                "aria-label": "キャンセル",
                                title: "キャンセル（録音を破棄）",
                                disabled: busy,
                                onclick: () => on.voiceCancel?.(),
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn send-rec-done",
                                type: "button",
                                "aria-label": busy ? "文字起こし中" : "文字起こし",
                                title: busy ? "文字起こし中" : "文字起こし",
                                disabled: busy,
                                "data-saving": busy ? "" : null,
                                onclick: () => on.voiceDone?.({ body: textarea.value, start: textarea.selectionStart, end: textarea.selectionEnd }),
                            },
                            children: [busy ? MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }) : MindmapPreview.icon("check")],
                        }),
                    ],
                }),
            ];
        }
        const blocked = voice === "disabled";
        voiceSequence += 1;
        const tipId = `voice-tip-${voiceSequence}`;
        const mic = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "icon-btn send-mic",
                type: "button",
                "aria-label": "音声で入力",
                title: blocked ? (voiceReason ?? "") : "音声で入力",
                // 押せないときもフォーカスを受けたまま、理由をツールチップで指す
                "aria-disabled": blocked ? "true" : null,
                "aria-describedby": blocked ? tipId : null,
                onclick: () => (blocked ? on.voiceBlocked?.() : on.voiceStart?.()),
            },
            children: [MindmapPreview.icon("mic")],
        });
        const micPart = blocked
            ? MindmapPreview.h({
                tag: "span",
                attrs: { class: "send-tip-wrap" },
                children: [mic, MindmapPreview.h({ tag: "span", attrs: { class: "send-tip", role: "tooltip", id: tipId }, children: [voiceReason ?? ""] })],
            })
            : mic;
        return [micPart, submit];
    }
    MindmapPreview.voiceButtons = voiceButtons;
    /** 添えた箇所（名前・選んだ文・外す ×）の要素 */
    function locationChip({ loc, id, onUnquote }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "send-loc", id },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-loc-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "send-loc-name" }, children: [MindmapPreview.locationLabel(loc)] }),
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
    function sendForm({ target, loc = null, body = "", status = "idle", count = null, detail = null, collapsed = false, label = NO_TARGET_LABEL, open = true, voice = "idle", voiceReason = null, elapsed = 0, levels = [], entered = false, on, }) {
        sendFormSequence += 1;
        const fieldId = `send-${sendFormSequence}`;
        const messageId = `${fieldId}-msg`;
        const locId = `${fieldId}-loc`;
        const bodyId = `${fieldId}-body`;
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
                rows: 1,
                "aria-label": target === null ? label : null,
                "aria-describedby": folded ? null : target !== null && loc !== null ? `${locId} ${messageId}` : messageId,
                "aria-keyshortcuts": "Control+Enter",
                // 溜めている間・録音中・文字起こし中は書き換えられない
                readonly: status === "saving" || voice === "recording" || voice === "transcribing",
                // 録音中は波形と入れ替えて隠す（中身と選んだ範囲は残す）
                hidden: voice === "recording",
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
        const shownState = messageState(voice, status);
        const message = MindmapPreview.h({
            tag: "p",
            attrs: { class: shownState === "idle" ? "send-msg" : `send-msg ${shownState}`, id: messageId, role: "status" },
            children: voiceProgressContent(voice, elapsed) ??
                voiceResultContent(status, detail, entered) ??
                resultContent({ status, count, detail, onCopy: () => on.copy(textarea.value) }),
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
            children: target === null ? [textareaLine(), folded ? null : message] : [head(), formBody()],
        });
        return form;
        /** 入力欄と、その右の「レビューに追加」（アイコンだけのボタン）の行 */
        function textareaLine() {
            if (folded)
                return textarea;
            const submit = MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "icon-btn send-submit",
                    type: "submit",
                    "aria-label": "レビューに追加",
                    title: "レビューに追加（Ctrl+Enter）",
                    disabled: status === "saving",
                    // 溜めている間は処理中のカーソルにする
                    "data-saving": status === "saving" ? "" : null,
                },
                children: [MindmapPreview.icon("comment")],
            });
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "send-line" },
                children: [textarea, voiceWave(voice, levels), ...voiceButtons({ voice, voiceReason, textarea, submit, on })],
            });
        }
        /** 見出しの行（「{ID} へのコメント」・書きかけの印・開閉のボタン） */
        function head() {
            const toggleLabel = open ? "コメントの入力を閉じる" : "コメントの入力を開く";
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "send-head" },
                children: [
                    MindmapPreview.h({
                        tag: open ? "label" : "span",
                        attrs: { class: "send-label", for: open ? fieldId : null },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target ?? ""] }), " へのコメント"],
                    }),
                    !open && body.trim() !== ""
                        ? MindmapPreview.h({ tag: "span", attrs: { class: "send-draft" }, children: [MindmapPreview.icon("edit"), "書きかけ"] })
                        : null,
                    MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "icon-btn send-toggle",
                            type: "button",
                            "aria-expanded": open ? "true" : "false",
                            "aria-controls": bodyId,
                            "aria-label": toggleLabel,
                            title: toggleLabel,
                            onclick: () => on.toggle?.(!open),
                        },
                        children: [MindmapPreview.icon("chev")],
                    }),
                ],
            });
        }
        /** 開閉する範囲（添えた箇所・入力欄の行・結果） */
        function formBody() {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "send-body", id: bodyId, hidden: !open },
                children: [loc !== null ? locationChip({ loc, id: locId, onUnquote: on.unquote }) : null, textareaLine(), message],
            });
        }
    }
    MindmapPreview.sendForm = sendForm;
})(MindmapPreview || (MindmapPreview = {}));
