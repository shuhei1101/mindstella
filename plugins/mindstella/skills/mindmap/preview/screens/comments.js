"use strict";
// コメントの一覧。見ている画面に重ねて左から出すパネルに、レビュー中のコメントを並べ、チェックしたものだけをまとめて送る。
var MindmapPreview;
(function (MindmapPreview) {
    /** コメントの本文の長さの上限（サーバーが受け付ける文字数と同じ） */
    MindmapPreview.COMMENT_BODY_MAX_LENGTH = 10000;
    /** コメントの ID の連番 */
    function commentNumber(id) {
        return Number(id.replace(/^\D+-/, ""));
    }
    MindmapPreview.commentNumber = commentNumber;
    /** 送った結果の文言（印と文）。結果が無いときは null */
    function outcomeContent({ result, checkedCount }) {
        if (result === null) {
            // チェックが 0 件
            return checkedCount === 0 ? [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["送るコメントにチェックを付けてください。"] })] : null;
        }
        if (result.kind === "sending") {
            return [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["送っています"] })];
        }
        if (result.kind === "sent") {
            const time = result.at === undefined ? "" : MindmapPreview.formatJst(result.at).slice(-5);
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`${result.count ?? 0} 件を送りました（${time}）。`] })];
        }
        if (result.kind === "stale") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`送れませんでした。箇所が合わないコメントが ${result.count ?? 0} 件あります。`] })];
        }
        const detail = result.detail ?? null;
        return [
            MindmapPreview.icon("alert"),
            MindmapPreview.h({
                tag: "span",
                children: [
                    detail === null
                        ? "送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。"
                        : `送れませんでした。${detail}`,
                ],
            }),
        ];
    }
    /** 行の向けた項目（押すとその項目を開く。項目を指さない・消えた項目は押せない） */
    function targetCell(item, props) {
        // 項目を指さない
        if (item.target === null)
            return MindmapPreview.h({ tag: "span", attrs: { class: "row-target none" }, children: ["項目を指さない"] });
        const title = props.titleOf(item.target);
        // 項目が消えた: 押せない ID だけを出す
        if (title === null) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.target] })] });
        }
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "row-target idlink", type: "button", "data-focus": `open:${item.id}`, onclick: () => props.on.open(item) },
            children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.target] }), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [title] })],
        });
    }
    /** 本文をその場で書き換える入力欄と「キャンセル」「修正」（コメントの一覧と詳細パネルが使う） */
    function reviewEditForm({ item, body, error, focus, on, }) {
        const field = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                name: "body",
                rows: 2,
                maxlength: MindmapPreview.COMMENT_BODY_MAX_LENGTH,
                "aria-label": `${item.id} へのコメントの本文`,
                "data-focus": `${focus}edit:${item.id}`,
                onkeydown: (event) => {
                    if (event.key === "Escape") {
                        // 詳細の全画面の `dialog` の `cancel` を起こさない
                        event.preventDefault();
                        event.stopPropagation();
                        on.cancelEdit();
                    }
                },
            },
            children: [body ?? item.body],
        });
        const message = MindmapPreview.h({ tag: "p", attrs: { class: "send-msg failed", role: "alert" }, children: error ? [MindmapPreview.icon("alert"), error] : [] });
        return MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "row-edit",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    // 空白だけは送らない
                    if (field.value.trim() === "") {
                        field.setAttribute("aria-invalid", "true");
                        message.replaceChildren(MindmapPreview.icon("alert"), "コメントを入れてから直してください。");
                        field.focus();
                        return;
                    }
                    on.saveEdit(item.id, field.value);
                },
            },
            children: [
                field,
                message,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-edit-actions" },
                    children: [
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn ghost", type: "button", onclick: on.cancelEdit }, children: ["キャンセル"] }),
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn primary", type: "submit" }, children: ["修正"] }),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.reviewEditForm = reviewEditForm;
    /** 行の右上に置く、鉛筆の印の「修正」とごみ箱の印の「削除」（コメントの一覧と詳細パネルが使う） */
    function reviewRowActions({ item, focus, on, }) {
        const label = item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "row-actions" },
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": `${label}を修正`,
                        title: "修正",
                        "data-focus": `${focus}edit-open:${item.id}`,
                        onclick: () => on.edit(item.id),
                    },
                    children: [MindmapPreview.icon("edit")],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": `${label}を削除`,
                        title: "削除",
                        "data-focus": `${focus}remove:${item.id}`,
                        onclick: () => on.remove(item.id),
                    },
                    children: [MindmapPreview.icon("trash")],
                }),
            ],
        });
    }
    MindmapPreview.reviewRowActions = reviewRowActions;
    /** 消した行（元の場所に「コメントを削除しました。」と「元に戻す」を出す。コメントの一覧と詳細パネルが使う） */
    function removedReviewRow({ item, focus, on, }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "row removed", "data-comment": item.id },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "removed-msg", role: "status" }, children: ["コメントを削除しました。"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn ghost", type: "button", "data-focus": `${focus}restore:${item.id}`, onclick: () => on.restore(item.id) },
                    children: [MindmapPreview.icon("undo"), "元に戻す"],
                }),
            ],
        });
    }
    MindmapPreview.removedReviewRow = removedReviewRow;
    /** コメントの行 */
    function commentRow(item, props) {
        const reason = props.stale.get(item.id);
        const label = item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
        return MindmapPreview.h({
            tag: "li",
            attrs: {
                class: `row${item.id === props.selected ? " selected" : ""}${reason === undefined ? "" : " stale"}`,
                "data-comment": item.id,
            },
            children: [
                MindmapPreview.h({
                    tag: "input",
                    attrs: {
                        type: "checkbox",
                        class: "row-check",
                        checked: props.checked.has(item.id),
                        "aria-label": `${label}を送る`,
                        "data-focus": `check:${item.id}`,
                        onchange: (event) => props.on.check(item.id, event.target.checked),
                    },
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-main" },
                    children: [
                        targetCell(item, props),
                        item.loc === null
                            ? null
                            : MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "review-loc" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "review-loc-name" }, children: [MindmapPreview.locationLabel(item.loc)] }),
                                    MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [item.loc.text] }),
                                ],
                            }),
                        props.editing === item.id
                            ? reviewEditForm({
                                item,
                                body: props.editBody ?? null,
                                error: props.editError ?? null,
                                focus: "",
                                on: { saveEdit: props.on.saveEdit, cancelEdit: props.on.cancelEdit },
                            })
                            : MindmapPreview.h({ tag: "p", attrs: { class: "review-body" }, children: [item.body] }),
                        reason === undefined
                            ? null
                            : MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-stale", role: "alert" },
                                children: [
                                    MindmapPreview.icon("alert"),
                                    MindmapPreview.h({ tag: "span", children: [reason] }),
                                    // 項目が記録にあるときだけ、箇所を外して項目へのコメントにできる
                                    item.loc !== null && item.target !== null && props.titleOf(item.target) !== null
                                        ? MindmapPreview.h({
                                            tag: "button",
                                            attrs: { class: "btn ghost", type: "button", "data-focus": `unloc:${item.id}`, onclick: () => props.on.unloc(item.id) },
                                            children: ["箇所を外す"],
                                        })
                                        : null,
                                ],
                            }),
                    ],
                }),
                reviewRowActions({ item, focus: "", on: { edit: props.on.edit, remove: props.on.remove } }),
            ],
        });
    }
    /** 送る帯の先頭に置く、文字を添えない三状態のチェックの箱。押すと、全てチェックしていれば全て外し、それ以外は全てチェックする */
    function selectAllBox({ ids, checked, onChange, }) {
        const count = ids.filter((id) => checked.has(id)).length;
        const checkbox = MindmapPreview.h({
            tag: "input",
            attrs: {
                type: "checkbox",
                checked: count === ids.length,
                "aria-label": "すべて選ぶ",
                onchange: () => onChange(count < ids.length),
            },
        });
        // 一部だけチェックしているときの横棒は、属性でなくプロパティで付ける
        checkbox.indeterminate = count > 0 && count < ids.length;
        return MindmapPreview.h({ tag: "label", attrs: { class: "legend-all-check", title: "すべて選ぶ" }, children: [checkbox] });
    }
    /** コメントの一覧を返す */
    function commentsPanel(props) {
        const { items, removed, checked, result, on } = props;
        const checkedCount = items.filter((item) => checked.has(item.id)).length;
        const isEmpty = items.length === 0 && removed.length === 0;
        // 送る帯は一覧の上端に留める。送っている間とチェックが 0 件のときは押せない
        const sending = result?.kind === "sending";
        const message = outcomeContent({ result, checkedCount });
        // 送った直後は、送るものが無くなっても結果を出す
        const band = isEmpty && result === null
            ? null
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "send-band" },
                children: [
                    items.length === 0
                        ? null
                        : selectAllBox({
                            ids: items.map((item) => item.id),
                            checked,
                            onChange: on.checkAll,
                        }),
                    items.length === 0
                        ? null
                        : MindmapPreview.h({ tag: "span", attrs: { class: "send-count" }, children: [`${checkedCount} / ${items.length} 件`] }),
                    isEmpty
                        ? null
                        : MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary",
                                type: "button",
                                "data-focus": "send",
                                disabled: checkedCount === 0 || sending,
                                onclick: () => on.send(),
                            },
                            children: [MindmapPreview.icon("send"), `まとめて送る（${checkedCount} 件）`],
                        }),
                    MindmapPreview.h({ tag: "p", attrs: { class: `send-msg${result === null ? "" : ` ${result.kind}`}`, role: "status" }, children: message ?? [] }),
                ],
            });
        // 消したコメントは元の場所（ID の連番の順）に出す
        const rows = [...items.map((item) => ({ item, gone: false })), ...removed.map((item) => ({ item, gone: true }))].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "comments-panel", "aria-label": "コメントの一覧" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-head" },
                    children: [
                        MindmapPreview.h({ tag: "h2", children: ["レビュー中のコメント", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "コメントの一覧を閉じる", "data-focus": "close", onclick: on.close },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                band,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-body" },
                    children: [
                        isEmpty
                            ? MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("comment"), "レビュー中のコメントはありません。"] })
                            : MindmapPreview.h({
                                tag: "ul",
                                attrs: { class: "comments-list" },
                                children: rows.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : commentRow(item, props))),
                            }),
                    ],
                }),
                MindmapPreview.h({ tag: "div", attrs: { class: "comments-free" }, children: [MindmapPreview.sendForm(props.free)] }),
            ],
        });
    }
    MindmapPreview.commentsPanel = commentsPanel;
})(MindmapPreview || (MindmapPreview = {}));
