"use strict";
// 保存待ちのパネル。保存待ちの編集を項目ごとに並べ、1 件ずつ取り消し、まとめて保存する。コメントの一覧と同じ左から出すパネル。
var MindmapPreview;
(function (MindmapPreview) {
    /** 設定のキーの呼び名 */
    const SETTING_LABELS = {
        summary: "題名",
        description: "説明",
        playbooks: "プレイブック",
        phases: "フェーズ",
        target_label: "最上位の軸の呼び名",
        goal: "ゴール",
        targets: "対象",
        categories: "カテゴリー",
        tags: "タグの語彙",
        links: "関連する場所",
        history_limit: "保持する回数",
    };
    /** 項目のキーの呼び名（詳細パネルの見出しと同じ言葉） */
    MindmapPreview.KEY_LABELS = {
        status: "状態",
        title: "タイトル",
        target: "機能",
        category: "カテゴリー",
        phase: "フェーズ",
        tags: "タグ",
        depends_on: "依存先",
        answer: "決定内容",
        reason: "理由",
        body: "本文",
        result: "結果",
        kind: "種類",
        question: "問い",
        conclusion: "結論",
        confidence: "確からしさ",
        related: "関連",
        withdrawn: "取り下げ",
        meaning: "意味",
        aliases: "別名",
        content: "内容",
        date: "日付",
        deliverable: "納品物",
        description: "説明",
    };
    /** 値を 1 行の文字にする（空は「（空）」、配列は「、」でつなぐ） */
    function flat(value) {
        if (value === undefined || value === null || value === "")
            return "（空）";
        if (Array.isArray(value))
            return value.length === 0 ? "（空）" : value.map((entry) => flat(entry)).join("、");
        if (value === true)
            return "はい";
        if (value === false)
            return "いいえ";
        if (typeof value === "object")
            return JSON.stringify(value);
        return String(value).replace(/\s+/g, " ");
    }
    /** 1 件の編集の「何を」と「前 → 後」。本文・削除は値を出さず、追加は前を持たない */
    function editRowText(edit) {
        const key = edit.key ?? "";
        switch (edit.op) {
            case "item-add":
                return { what: "項目を追加", before: null, after: flat(edit.value?.title) };
            case "item-remove":
                return { what: "項目を削除", before: null, after: null };
            case "setting":
                return { what: SETTING_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
            case "option-add":
                return {
                    what: `案 ${key} を追加`,
                    before: null,
                    after: flat(edit.value?.content),
                };
            case "option-remove":
                return { what: `案 ${key} を削除`, before: null, after: null };
            case "option-edit":
                return {
                    what: `案 ${key}`,
                    before: flat(edit.before?.content ?? edit.before),
                    after: flat(edit.value?.content),
                };
            case "adopt":
                return { what: "採用する案", before: flat(edit.before ?? "なし"), after: flat(edit.value) };
            default:
                if (key === "body")
                    return { what: "本文", before: null, after: null };
                return { what: MindmapPreview.KEY_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
        }
    }
    MindmapPreview.editRowText = editRowText;
    /** 編集を向け先ごとに、最初に溜めた順にまとめる */
    function groupEdits(edits) {
        const groups = [];
        for (const edit of edits) {
            const found = groups.find((group) => group.target === edit.target);
            if (found === undefined)
                groups.push({ target: edit.target, edits: [edit] });
            else
                found.edits.push(edit);
        }
        return groups;
    }
    MindmapPreview.groupEdits = groupEdits;
    /** まとまりの見出しに出す、項目の種類・ID・タイトル（設定は「設定」、追加する項目は「{種類}を追加」） */
    function describeTarget({ target, edits, index, }) {
        if (target === MindmapPreview.SETTINGS_TARGET)
            return { kind: "設定", id: null, title: index.data.settings.summary };
        const added = edits.find((edit) => edit.op === "item-add");
        if (added !== undefined) {
            const kind = MindmapPreview.KIND_LABEL[(added.key ?? "")] ?? added.key ?? "";
            return { kind: `${kind}を追加`, id: null, title: added.value.title ?? "" };
        }
        const entry = index.byId.get(target);
        if (entry === undefined)
            return { kind: "項目", id: target, title: "" };
        return { kind: MindmapPreview.KIND_LABEL[entry.kind], id: target, title: entry.item.title };
    }
    /** 読み上げ用の「前:」「後:」を添えた前 → 後の値 */
    function changeView(text) {
        if (text.after === null)
            return null;
        if (text.before === null) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "pe-change" }, children: [MindmapPreview.h({ tag: "ins", children: [text.after] })] });
        }
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "pe-change" },
            children: [
                MindmapPreview.h({ tag: "del", children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["前: "] }), text.before] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "pe-arrow", "aria-hidden": "true" }, children: ["→"] }),
                MindmapPreview.h({ tag: "ins", children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["後: "] }), text.after] }),
            ],
        });
    }
    /** 保存待ちのパネル（開閉は使う側が `open` のクラスで決める） */
    function pendingEditsPanel({ edits, blocked, index, status, rejected = null, on }) {
        const removals = edits.filter((edit) => edit.op === "item-remove").length;
        const saving = status === "saving";
        const blockedBy = new Map(blocked.map((entry) => [entry.id, entry]));
        const blockedEdits = edits.filter((edit) => blockedBy.has(edit.id));
        /** 書き込めない編集の行の名前（「{ID か種類} の{何を}」） */
        const nameOf = (edit) => {
            const who = describeTarget({
                target: edit.target,
                edits: edits.filter((other) => other.target === edit.target),
                index,
            });
            return `${who.id ?? who.kind} の${editRowText(edit).what}`;
        };
        const list = MindmapPreview.h({ tag: "div", attrs: { class: "comments-body pe-list" } });
        if (blockedEdits.length > 0) {
            list.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
                children: [
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-title" },
                        children: [MindmapPreview.icon("alert"), `${blockedEdits.length} 件の編集を書き込めないため、何も保存していません。`],
                    }),
                    MindmapPreview.h({
                        tag: "ul",
                        children: blockedEdits.map((edit) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                MindmapPreview.h({
                                    tag: "a",
                                    attrs: {
                                        href: `#pe-row-${edit.id}`,
                                        onclick: (event) => {
                                            event.preventDefault();
                                            document.getElementById(`pe-row-${edit.id}`)?.querySelector("button")?.focus();
                                        },
                                    },
                                    children: [nameOf(edit)],
                                }),
                            ],
                        })),
                    }),
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-next" },
                        children: ["書き込めない編集を取り消してから、もう一度保存してください。"],
                    }),
                ],
            }));
        }
        if (rejected !== null) {
            list.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
                children: [
                    MindmapPreview.h({ tag: "p", attrs: { class: "pe-alert-title" }, children: [MindmapPreview.icon("alert"), `保存できませんでした。${rejected}`] }),
                ],
            }));
        }
        if (status === "offline") {
            list.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
                children: [
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-title" },
                        children: [MindmapPreview.icon("alert"), "サーバーにつながらないため、保存できませんでした。"],
                    }),
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-next" },
                        children: ["保存待ちの編集は残っています。サーバーを立ち上げ直してから、もう一度保存してください。"],
                    }),
                ],
            }));
        }
        if (edits.length === 0)
            list.append(MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("layers"), "保存待ちの編集はありません。"] }));
        for (const group of groupEdits(edits)) {
            const who = describeTarget({ target: group.target, edits: group.edits, index });
            const isBlocked = group.edits.some((edit) => blockedBy.has(edit.id));
            list.append(MindmapPreview.h({
                tag: "section",
                attrs: { class: `pe-group${isBlocked ? " is-blocked" : ""}` },
                children: [
                    MindmapPreview.h({
                        tag: "h3",
                        attrs: { class: "pe-group-head" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "pe-open",
                                    type: "button",
                                    "aria-label": `${who.id ?? who.kind}「${who.title}」を開く`,
                                    onclick: () => on.open(group.target),
                                },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "pe-kind" }, children: [who.kind] }),
                                    who.id === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [who.id] }),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "pe-title" }, children: [who.title] }),
                                ],
                            }),
                        ],
                    }),
                    MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "pe-rows" },
                        children: group.edits.map((edit) => editRow({ edit, who, blockedEdit: blockedBy.get(edit.id), index, on })),
                    }),
                ],
            }));
        }
        const label = saving ? "保存しています…" : removals > 0 ? `まとめて保存する（${removals} 件を削除）` : "まとめて保存する";
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "pending-panel", "aria-label": "保存待ちの編集", id: "pending-panel" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-head" },
                    children: [
                        MindmapPreview.h({
                            tag: "h2",
                            attrs: { tabindex: "-1" },
                            children: ["保存待ち", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [`${edits.length} 件`] })],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn",
                                type: "button",
                                "aria-label": "保存待ちの編集を閉じる",
                                "data-focus": "close",
                                onclick: () => on.close(),
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                list,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-free pe-foot" },
                    children: [
                        edits.length === 0
                            ? null
                            : MindmapPreview.h({
                                tag: "p",
                                attrs: { class: "pe-foot-sum" },
                                children: [`${edits.length} 件${removals > 0 ? `（うち削除 ${removals} 件）` : ""}をワークスペースに書きます`],
                            }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary pe-save",
                                type: "button",
                                disabled: saving || edits.length === 0,
                                "aria-busy": saving ? "true" : null,
                                onclick: () => on.save(),
                            },
                            children: [saving ? MindmapPreview.h({ tag: "span", attrs: { class: "pe-spin" }, children: [MindmapPreview.icon("spin")] }) : MindmapPreview.icon("save"), label],
                        }),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.pendingEditsPanel = pendingEditsPanel;
    /** 編集の行（何を・前 → 後・書き込めない理由と、取り消すボタン） */
    function editRow({ edit, who, blockedEdit, index, on, }) {
        const text = editRowText(edit);
        const name = `${who.id ?? who.kind} の${text.what}`;
        return MindmapPreview.h({
            tag: "li",
            attrs: {
                class: `pe-row${blockedEdit === undefined ? "" : " is-blocked"}${edit.op === "item-remove" ? " is-remove" : ""}`,
                id: `pe-row-${edit.id}`,
            },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "pe-row-main" },
                    children: [
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "pe-what" },
                            children: [edit.op === "item-remove" ? MindmapPreview.icon("trash") : null, text.what],
                        }),
                        changeView(text),
                        blockedEdit === undefined
                            ? null
                            : MindmapPreview.blockedNote({
                                blocked: blockedEdit,
                                updated: index.byId.get(edit.target)?.item.updated ?? null,
                                onOpen: on.open,
                            }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "btn ghost pe-undo",
                        type: "button",
                        "data-focus": `undo:${edit.id}`,
                        "aria-label": `${name}の編集を取り消す`,
                        onclick: () => on.undo(edit.id),
                    },
                    children: [MindmapPreview.icon("undo"), MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["取り消す"] })],
                }),
            ],
        });
    }
    /** まとめて保存できたときに画面の下に出す知らせ（`role="status"`）。消すのは使う側 */
    function savedNotice({ count }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-toast", role: "status" },
            children: [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`${count} 件を保存しました。`] })],
        });
    }
    MindmapPreview.savedNotice = savedNotice;
})(MindmapPreview || (MindmapPreview = {}));
