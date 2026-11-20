"use strict";
// 表示の設定の中身。表示する種類と差分のミニマップと本文の表とセクションの見せ方と「レビューに追加」の後のフォーカスを選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 差分のミニマップの呼び名（表示の設定の切り替えと「この端末で変えている項目」に出す名前） */
    MindmapPreview.MINIMAP_LABEL = "差分のミニマップ";
    /** 「レビューに追加」の後のフォーカスの呼び名（表示の設定のラジオの凡例と「この端末で変えている項目」に出す名前） */
    MindmapPreview.FOCUS_AFTER_ADD_LABEL = "レビューに追加した後のフォーカス";
    /** 「レビューに追加」の後のフォーカスの選択肢（値・名前） */
    const FOCUS_AFTER_ADD_OPTIONS = [
        { key: "auto", label: "自動" },
        { key: "input", label: "入力欄へ戻す" },
        { key: "none", label: "戻さない" },
    ];
    /** 種類 → 種類の行に出す印 */
    const KIND_ICON = {
        decisions: "decision",
        tasks: "task",
        research: "research",
        docs: "doc",
        terms: "term",
        notes: "note",
        logs: "log",
    };
    /** 2 つの集合が同じ要素を持つか */
    function sameSet(a, b) {
        return a.size === b.size && [...a].every((value) => b.has(value));
    }
    /** 種類の並び（種類の定義の順）にそろえる */
    function orderedKinds(kinds) {
        return MindmapPreview.KIND_KEYS.filter((kind) => kinds.has(kind));
    }
    /** 端末に保存できない旨（パネルの先頭） */
    function storageNote() {
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: "st-note", role: "alert" },
            children: [
                MindmapPreview.icon("alert"),
                MindmapPreview.h({ tag: "span", children: ["この端末に保存できません。選んだ表示は、このページを開いている間だけ当たります。"] }),
            ],
        });
    }
    /** 概要の行（常に出す。チェックの箱を持たない） */
    function alwaysRow({ iconName, label }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "st-always" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "st-always-box" }, children: [MindmapPreview.icon("check")] }),
                MindmapPreview.icon(iconName),
                MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: [label] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "st-always-note" }, children: ["常に表示"] }),
            ],
        });
    }
    /** 表示する種類の選び（先頭にまとめて選ぶチェック、概要は常に出す行） */
    function kindsField({ kinds, counts, on }) {
        const shownCount = MindmapPreview.KIND_KEYS.filter((kind) => kinds.has(kind)).length;
        const allBox = MindmapPreview.h({
            tag: "input",
            attrs: {
                type: "checkbox",
                checked: shownCount === MindmapPreview.KIND_KEYS.length,
                "data-focus": "kinds-all",
                // 全て選んでいるときは全て外し、そうでなければ全て選ぶ
                onchange: () => on.kinds(shownCount === MindmapPreview.KIND_KEYS.length ? [] : [...MindmapPreview.KIND_KEYS]),
            },
        });
        // 一部だけを選んでいる途中の状態は、属性で持てないため要素に付ける
        allBox.indeterminate = shownCount > 0 && shownCount < MindmapPreview.KIND_KEYS.length;
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "st-sec" },
            children: [
                MindmapPreview.h({ tag: "legend", children: ["表示する種類"] }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "st-kinds" },
                    children: [
                        MindmapPreview.h({
                            tag: "li",
                            attrs: { class: "st-all" },
                            children: [
                                MindmapPreview.h({
                                    tag: "label",
                                    children: [
                                        allBox,
                                        MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: ["すべて"] }),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "n mono" }, children: [`${shownCount}/${MindmapPreview.KIND_KEYS.length}`] }),
                                    ],
                                }),
                            ],
                        }),
                        alwaysRow({ iconName: "home", label: "概要" }),
                        ...MindmapPreview.KIND_KEYS.map((kind) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                MindmapPreview.h({
                                    tag: "label",
                                    children: [
                                        MindmapPreview.h({
                                            tag: "input",
                                            attrs: {
                                                type: "checkbox",
                                                value: kind,
                                                checked: kinds.has(kind),
                                                "data-focus": `kind:${kind}`,
                                                // 押した種類だけを入れ替えた、変えた後の並びを知らせる
                                                onchange: () => {
                                                    const next = new Set(kinds);
                                                    if (next.has(kind))
                                                        next.delete(kind);
                                                    else
                                                        next.add(kind);
                                                    on.kinds(orderedKinds(next));
                                                },
                                            },
                                        }),
                                        MindmapPreview.icon(KIND_ICON[kind]),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: [MindmapPreview.KIND_LABEL[kind]] }),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "n mono" }, children: [counts[kind] ?? ""] }),
                                    ],
                                }),
                            ],
                        })),
                    ],
                }),
            ],
        });
    }
    /** 詳細に表示するものの 1 行（チェックと名前） */
    function detailCheck({ checked, focus, label, onChange }) {
        return MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({
                    tag: "label",
                    children: [
                        MindmapPreview.h({ tag: "input", attrs: { type: "checkbox", checked, "data-focus": focus, onchange: onChange } }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: [label] }),
                    ],
                }),
            ],
        });
    }
    /** 詳細に表示するものの選び（差分のミニマップと、本文の表とセクションの見せ方の 4 つのチェック） */
    function detailField({ minimap = true, bodyView = MindmapPreview.BODY_VIEW_DEFAULT, on }) {
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "st-sec" },
            children: [
                MindmapPreview.h({ tag: "legend", children: ["詳細に表示するもの"] }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "st-kinds" },
                    children: [
                        detailCheck({ checked: minimap, focus: "minimap", label: MindmapPreview.MINIMAP_LABEL, onChange: () => on.minimap(!minimap) }),
                        ...MindmapPreview.BODY_VIEW_KEYS.map((key) => detailCheck({
                            checked: bodyView[key],
                            focus: `body-view:${key}`,
                            label: MindmapPreview.BODY_VIEW_LABELS[key],
                            onChange: () => on.bodyView({ key, value: !bodyView[key] }),
                        })),
                    ],
                }),
            ],
        });
    }
    /** コメントの入力の選び（「レビューに追加」の後のフォーカスの 3 つのラジオ。「自動」の下にこの端末でどちらになるかを出す） */
    function commentInputField({ focusAfterAdd = "auto", pointerCoarse = false, on }) {
        const hintId = "st-focus-after-add-hint";
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "st-sec" },
            children: [
                MindmapPreview.h({ tag: "legend", children: ["コメントの入力"] }),
                MindmapPreview.h({
                    tag: "fieldset",
                    attrs: { class: "st-sub-sec", "aria-describedby": hintId },
                    children: [
                        MindmapPreview.h({ tag: "legend", children: [MindmapPreview.FOCUS_AFTER_ADD_LABEL] }),
                        MindmapPreview.h({
                            tag: "ul",
                            attrs: { class: "st-kinds" },
                            children: FOCUS_AFTER_ADD_OPTIONS.map(({ key, label }) => MindmapPreview.h({
                                tag: "li",
                                children: [
                                    MindmapPreview.h({
                                        tag: "label",
                                        children: [
                                            MindmapPreview.h({
                                                tag: "input",
                                                attrs: {
                                                    type: "radio",
                                                    name: "focus-after-add",
                                                    value: key,
                                                    checked: focusAfterAdd === key,
                                                    "data-focus": `focus-after-add:${key}`,
                                                    onchange: () => on.focusAfterAdd(key),
                                                },
                                            }),
                                            MindmapPreview.h({
                                                tag: "span",
                                                attrs: { class: "st-k-label" },
                                                children: [
                                                    label,
                                                    ...(key === "auto"
                                                        ? [MindmapPreview.h({ tag: "span", attrs: { class: "st-k-sub" }, children: [pointerCoarse ? "この端末では戻しません" : "この端末では入力欄へ戻します"] })]
                                                        : []),
                                                ],
                                            }),
                                        ],
                                    }),
                                ],
                            })),
                        }),
                        MindmapPreview.h({
                            tag: "p",
                            attrs: { class: "st-hint", id: hintId },
                            children: ["自動は、マウスで操作する端末では入力欄へ戻し、タッチで操作する端末では戻しません。"],
                        }),
                    ],
                }),
            ],
        });
    }
    /** この端末で変えている項目と「既定に戻す」。上書きが無いときはボタンを出さず、その旨を出す */
    function resetBlock({ overrides, on }) {
        if (overrides.length === 0) {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "st-reset" },
                children: [
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "st-over st-none", tabindex: "-1", "data-focus": "over" },
                        children: ["ワークスペースの既定のまま表示しています。"],
                    }),
                ],
            });
        }
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-reset" },
            children: [
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "st-over" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "st-over-h" }, children: ["この端末で変えている項目"] }),
                        MindmapPreview.h({ tag: "span", children: [overrides.join("・")] }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn", type: "button", "data-focus": "reset", onclick: () => on.reset() },
                    children: [MindmapPreview.icon("undo"), "既定に戻す"],
                }),
            ],
        });
    }
    /** 「ワークスペースの既定にする」。選びが既定と同じときはボタンの代わりにその旨を出す */
    function saveBlock({ kinds, defaultKinds, on }) {
        const differs = !sameSet(kinds, defaultKinds);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-save" },
            children: [
                differs
                    ? MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "btn",
                            type: "button",
                            "aria-haspopup": "dialog",
                            "data-focus": "save",
                            onclick: () => on.save(),
                        },
                        children: [MindmapPreview.icon("save"), "ワークスペースの既定にする"],
                    })
                    : MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "st-same", tabindex: "-1", "data-focus": "same" },
                        children: ["表示する種類は、ワークスペースの既定と同じです。"],
                    }),
            ],
        });
    }
    /** 下端に残す知らせ（`role="status"`） */
    function messageLine(message) {
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: `st-msg${message === null ? "" : ` ${message.kind}`}`, role: "status" },
            children: message === null ? [] : [MindmapPreview.icon(message.kind === "ok" ? "check" : "sliders"), MindmapPreview.h({ tag: "span", children: [message.text] })],
        });
    }
    /** ワークスペースの設定の入口（見出し・何を書き換えられるかの案内・「設定を編集する」） */
    function workspaceEntry(onWorkspace) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-ws-entry" },
            children: [
                MindmapPreview.h({ tag: "h3", children: ["ワークスペースの設定"] }),
                MindmapPreview.h({ tag: "p", attrs: { class: "pe-ws-sum" }, children: ["題名・説明・関連する場所"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn", type: "button", onclick: () => onWorkspace() },
                    children: [MindmapPreview.icon("edit"), "設定を編集する"],
                }),
            ],
        });
    }
    /** 表示の設定の中身を返す */
    function settingsPanel(props) {
        const { canSave, message = null, storageOk = true, onWorkspace = null } = props;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-wrap" },
            children: [
                storageOk ? null : storageNote(),
                kindsField(props),
                detailField(props),
                // 配る書き出し（ワークスペースの既定にできない）はコメントの入力を持たないため、区画を出さない
                ...(props.canSave ? [commentInputField(props)] : []),
                resetBlock(props),
                canSave ? saveBlock(props) : null,
                messageLine(message),
                onWorkspace === null ? null : workspaceEntry(onWorkspace),
            ],
        });
    }
    MindmapPreview.settingsPanel = settingsPanel;
})(MindmapPreview || (MindmapPreview = {}));
