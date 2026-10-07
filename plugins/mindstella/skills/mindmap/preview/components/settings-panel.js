"use strict";
// 表示の設定の中身。表示する種類を選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す。見た目はネットワークのドロップダウンで選ぶので、ここでは選ばせない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 選べるネットワークの見た目 */
    MindmapPreview.NETWORK_LOOKS = [
        { key: "glow", label: "グロウ", note: "玉と流れる光に、やわらかい光のにじみ" },
        { key: "starlight", label: "星の光", note: "白い芯と色の光。明るい星に十字の光条" },
        { key: "constellation", label: "星図", note: "回転に合わせて回る天球の経緯線" },
        { key: "deep", label: "深宇宙", note: "星空と星雲の地に、光のにじむ星" },
        { key: "dust", label: "星屑", note: "色を抜いた細かな点と細い線" },
    ];
    /** ワークスペースの既定も個人の上書きも無いときの見た目 */
    MindmapPreview.BUILTIN_LOOK = "deep";
    /** 見た目の値 → 画面に出す名前 */
    function lookLabel(look) {
        return MindmapPreview.NETWORK_LOOKS.find((option) => option.key === look)?.label ?? look;
    }
    MindmapPreview.lookLabel = lookLabel;
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
    /** 概要・ネットワークの行（常に出す。チェックの箱を持たない） */
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
    /** 表示する種類の選び（先頭にまとめて選ぶチェック、概要とネットワークは常に出す行） */
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
                        alwaysRow({ iconName: "network", label: "ネットワーク" }),
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
    function saveBlock({ look, defaultLook, kinds, defaultKinds, on }) {
        const differs = look !== defaultLook || !sameSet(kinds, defaultKinds);
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
                        children: ["今の選びはワークスペースの既定と同じです。"],
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
    /** 表示の設定の中身を返す */
    function settingsPanel(props) {
        const { canSave, message = null, storageOk = true } = props;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-wrap" },
            children: [
                storageOk ? null : storageNote(),
                kindsField(props),
                resetBlock(props),
                canSave ? saveBlock(props) : null,
                messageLine(message),
            ],
        });
    }
    MindmapPreview.settingsPanel = settingsPanel;
})(MindmapPreview || (MindmapPreview = {}));
