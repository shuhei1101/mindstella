"use strict";
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目の ID を、押すと開くボタンにする */
    function idButton(id, open) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "idlink", type: "button", onclick: () => open(id) },
            children: [id],
        });
    }
    /** 項目の ID の並びを、ID・題・状態の一覧にする */
    function itemList(index, ids, open) {
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "d-list" },
            children: [
                ...ids.map((id) => MindmapPreview.h({
                    tag: "li",
                    children: [
                        idButton(id, open),
                        MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [MindmapPreview.titleOf(index, id)] }),
                        MindmapPreview.statusBadge(index.byId.get(id)?.item.status),
                    ],
                })),
            ],
        });
    }
    /** 見出しの付いた節 */
    function section(label, content) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec" },
            children: [MindmapPreview.h({ tag: "h3", children: [label] }), content],
        });
    }
    /** 値を描いた要素。選んだ箇所のコメントが、描いた要素のキーのパスで値を指せるようにする */
    function valueSpan(key, children) {
        return MindmapPreview.h({ tag: "span", attrs: { [MindmapPreview.VALUE_KEY_ATTR]: key }, children });
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由を出す） */
    function optionCards(options) {
        return MindmapPreview.h({
            tag: "div",
            children: [
                ...options.map((option) => {
                    const result = option.adopted === true ? "採用" : option.adopted === false ? "不採用" : "検討中";
                    const rows = [
                        ["メリット", "pros", option.pros],
                        ["デメリット", "cons", option.cons],
                        ["備考", "note", option.note],
                        ["理由", "reason", option.reason],
                    ];
                    const shown = rows.filter((row) => row[2] !== undefined && row[2] !== "");
                    return MindmapPreview.h({
                        tag: "div",
                        attrs: {
                            class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}`,
                        },
                        children: [
                            MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "o-head" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                    valueSpan(`options[${option.key}].content`, [option.content]),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "res" }, children: [result] }),
                                ],
                            }),
                            shown.length > 0
                                ? MindmapPreview.h({
                                    tag: "dl",
                                    children: [
                                        ...shown.flatMap(([label, field, value]) => [
                                            MindmapPreview.h({ tag: "dt", children: [label] }),
                                            MindmapPreview.h({ tag: "dd", attrs: { [MindmapPreview.VALUE_KEY_ATTR]: `options[${option.key}].${field}` }, children: [value] }),
                                        ]),
                                    ],
                                })
                                : null,
                        ],
                    });
                }),
            ],
        });
    }
    /** 見出しの下の、項目のキー（対象・カテゴリー・フェーズ・影響度・種類・確度・日付・更新日・タグ）の一覧 */
    function metaList(item, settings) {
        const pairs = [
            [settings.target_label, item.target],
            ["カテゴリー", item.category],
            ["フェーズ", item.phase],
            ["影響度", item.weight],
            ["種類", item.kind],
            ["確度", item.confidence],
            ["日付", item.date],
            ["更新日", item.updated],
        ];
        const rows = pairs.flatMap(([label, value]) => value === undefined || value === "" ? [] : [MindmapPreview.h({ tag: "dt", children: [label] }), MindmapPreview.h({ tag: "dd", children: [value] })]);
        if ((item.tags ?? []).length > 0)
            rows.push(MindmapPreview.h({ tag: "dt", children: ["タグ"] }), MindmapPreview.h({ tag: "dd", children: [MindmapPreview.tagList(item.tags)] }));
        return MindmapPreview.h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
    }
    /** この項目へのレビュー中のコメントの節（読むだけ。直す・消す・チェックはコメントの一覧で行う） */
    function reviewSection(items) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec d-review" },
            children: [
                MindmapPreview.h({
                    tag: "h3",
                    children: ["レビュー中のコメント", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })],
                }),
                items.length === 0
                    ? MindmapPreview.emptyNote("レビュー中のコメントはありません。")
                    : MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list review-list" },
                        children: items.map((comment) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                comment.loc === null
                                    ? null
                                    : MindmapPreview.h({
                                        tag: "div",
                                        attrs: { class: "review-loc" },
                                        children: [
                                            MindmapPreview.h({ tag: "span", attrs: { class: "review-loc-name" }, children: [MindmapPreview.locationLabel(comment.loc)] }),
                                            MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [comment.loc.text] }),
                                        ],
                                    }),
                                MindmapPreview.h({ tag: "p", attrs: { class: "review-body" }, children: [comment.body] }),
                            ],
                        })),
                    }),
            ],
        });
    }
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on, review }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "detail" } });
        if (entry === undefined)
            return body;
        const { kind, item } = entry;
        const related = MindmapPreview.relatedItems({ id, index });
        const labelled = (label, key, value) => value === undefined || value === ""
            ? null
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "d-answer" },
                children: [MindmapPreview.h({ tag: "b", children: [label] }), valueSpan(key, [value])],
            });
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす */
        const bodySection = (label) => {
            const source = index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            const rendered = MindmapPreview.renderMarkdown(source);
            lowerHeadings(rendered);
            void MindmapPreview.renderDiagrams(rendered);
            rendered.addEventListener("click", (event) => {
                const button = event.target.closest("[data-act]");
                const figure = button?.closest(".diagram");
                if (button === null || button === undefined || figure === null || figure === undefined)
                    return;
                const act = button.dataset["act"];
                const original = figure.querySelector(".dg-raw")?.textContent ?? "";
                if (act === "diagram-zoom") {
                    const svgElement = figure.querySelector(".mermaid svg");
                    if (svgElement !== null)
                        on.diagram(svgElement);
                }
                else if (act === "diagram-raw") {
                    // 図と mermaid の原文を切り替える
                    const pressed = button.getAttribute("aria-pressed") !== "true";
                    button.setAttribute("aria-pressed", String(pressed));
                    figure.querySelector(".mermaid").hidden = pressed;
                    figure.querySelector(".dg-raw").hidden = !pressed;
                }
                else if (act === "diagram-copy") {
                    void navigator.clipboard?.writeText(original).then(() => {
                        button.replaceChildren(MindmapPreview.icon("check"));
                        window.setTimeout(() => button.replaceChildren(MindmapPreview.icon("copy")), 1400);
                    });
                }
            });
            return section(label, rendered);
        };
        /** 関係する項目の節（1 件以上あるときだけ） */
        const relation = (label, ids) => ids.length === 0 ? null : section(label, itemList(index, ids, on.open));
        MindmapPreview.append({
            parent: body,
            children: [
                valueSpan("status", [MindmapPreview.statusBadge(item.status)]),
                MindmapPreview.h({
                    tag: "h2",
                    attrs: { class: "d-title", [MindmapPreview.VALUE_KEY_ATTR]: "title" },
                    children: [item.title, item.deliverable === true ? MindmapPreview.deliverableBadge() : null],
                }),
                metaList(item, index.data.settings),
            ],
        });
        if (kind === "decisions") {
            MindmapPreview.append({
                parent: body,
                children: [
                    item.lead === undefined ? null : MindmapPreview.h({ tag: "p", attrs: { class: "d-lead", [MindmapPreview.VALUE_KEY_ATTR]: "lead" }, children: [item.lead] }),
                    labelled("決定内容", "answer", item.answer),
                    labelled("理由", "reason", item.reason),
                    (item.options ?? []).length > 0 ? section("案", optionCards(item.options ?? [])) : null,
                    bodySection("本文"),
                    relation("前提", related.prerequisites),
                    relation("後続の項目", related.successors),
                    relation("関連タスク", related.tasks),
                    relation("経緯（会話ログ）", related.logs),
                ],
            });
        }
        else if (kind === "tasks") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled("理由", "reason", item.reason),
                    relation("進める検討事項", item.for ?? []),
                    relation("前提", related.prerequisites),
                    relation("結果", item.result === undefined ? [] : [item.result]),
                ],
            });
        }
        else if (kind === "research") {
            MindmapPreview.append({
                parent: body,
                children: [
                    item.question === undefined ? null : MindmapPreview.h({ tag: "p", attrs: { class: "d-lead", [MindmapPreview.VALUE_KEY_ATTR]: "question" }, children: [item.question] }),
                    labelled("結論", "conclusion", item.conclusion),
                    (item.angles ?? []).length > 0 ? section("調査の観点", MindmapPreview.tagList(item.angles)) : null,
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "docs") {
            MindmapPreview.append({ parent: body, children: [bodySection("本文")] });
        }
        else if (kind === "terms") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled("意味", "meaning", item.meaning),
                    (item.aliases ?? []).length > 0 ? section("別名", MindmapPreview.tagList(item.aliases)) : null,
                    (item.avoid ?? []).length > 0 ? section("使わない表記", MindmapPreview.tagList(item.avoid)) : null,
                ],
            });
        }
        else if (kind === "notes") {
            MindmapPreview.append({
                parent: body,
                children: [
                    item.content === undefined ? null : MindmapPreview.h({ tag: "p", attrs: { [MindmapPreview.VALUE_KEY_ATTR]: "content" }, children: [item.content] }),
                ],
            });
        }
        else {
            MindmapPreview.append({ parent: body, children: [bodySection("要約")] });
        }
        if ((item.links ?? []).length > 0) {
            MindmapPreview.append({
                parent: body,
                children: [
                    section("リンク", MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list" },
                        children: [
                            ...(item.links ?? []).map((link) => MindmapPreview.h({
                                tag: "li",
                                children: [
                                    MindmapPreview.icon("link"),
                                    MindmapPreview.h({
                                        tag: "a",
                                        attrs: { href: link.url, target: "_blank", rel: "noopener" },
                                        children: [link.title],
                                    }),
                                ],
                            })),
                        ],
                    })),
                ],
            });
        }
        MindmapPreview.append({
            parent: body,
            children: [
                relation(kind === "logs" ? "更新した項目" : "関連", related.related),
                relation("参照元", related.referencedBy),
                review === null ? null : reviewSection(review),
            ],
        });
        return body;
    }
    /** 見出し（前へ・次へ・全画面・閉じる）を作る */
    function detailHead({ id, index, full, on }) {
        const entry = index.byId.get(id);
        const trail = history.state;
        const position = trail?.position ?? 0;
        const length = trail?.items.length ?? 1;
        const arrow = (label, glyph, disabled, handler) => MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "icon-btn",
                type: "button",
                "data-act": glyph === "←" ? "back" : "forward",
                "aria-label": label,
                title: label,
                disabled,
                onclick: handler,
            },
            children: [glyph],
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-head" },
            children: [
                full
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: on.close },
                        children: [MindmapPreview.icon("back")],
                    }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "panel-kind" },
                    children: [
                        entry === undefined ? "" : `${MindmapPreview.KIND_LABEL[entry.kind]} `,
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                arrow("前の項目へ戻る", "←", position <= 0, on.back),
                arrow("次の項目へ進む", "→", position >= length - 1, on.forward),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn panel-full",
                        type: "button",
                        "data-act": "full",
                        "aria-label": "全画面表示",
                        title: "全画面表示",
                        "aria-pressed": String(full),
                        onclick: () => on.full(!full),
                    },
                    children: [MindmapPreview.icon("expand")],
                }),
                full
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "icon-btn panel-close-x",
                            type: "button",
                            "data-act": "close",
                            "aria-label": "詳細を閉じる",
                            onclick: on.close,
                        },
                        children: [MindmapPreview.icon("x")],
                    }),
            ],
        });
    }
    /** 詳細パネルの節の見出し（h3）の下に、本文の見出し（h1〜h6）を並べるための段の差 */
    const BODY_HEADING_OFFSET = 3;
    /** 見出しの要素の最も下の段（h6） */
    const LOWEST_HEADING_LEVEL = 6;
    /** 本文の見出しを、パネルの節の見出しより下の段（h4〜h6）に下げる。見た目は元の段のまま（`data-md-level`） */
    function lowerHeadings(root) {
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const level = Number(heading.tagName.slice(1));
            const lowered = Math.min(level + BODY_HEADING_OFFSET, LOWEST_HEADING_LEVEL);
            const replacement = MindmapPreview.h({
                tag: `h${lowered}`,
                attrs: {
                    "data-md-level": level,
                    // 元の Markdown の行の印を引き継ぐ
                    [MindmapPreview.LINE_ATTR]: heading.getAttribute(MindmapPreview.LINE_ATTR),
                    // h6 を超える段は、読み上げの段で伝える
                    "aria-level": level + BODY_HEADING_OFFSET > LOWEST_HEADING_LEVEL ? level + BODY_HEADING_OFFSET : null,
                },
                children: [...heading.childNodes],
            });
            heading.replaceWith(replacement);
        }
    }
    /** コメントの一覧から開いたとき、そのコメントの箇所までスクロールして示す。合わなければ示さず、項目の先頭を出す */
    function highlightLocation({ root, loc }) {
        const scroller = root.querySelector(".panel-body");
        let hits = [];
        if (loc.kind === "value") {
            hits = [...root.querySelectorAll(`[${MindmapPreview.VALUE_KEY_ATTR}]`)].filter((element) => element.getAttribute(MindmapPreview.VALUE_KEY_ATTR) === loc.key);
        }
        else {
            const start = loc.start ?? 0;
            const end = loc.end ?? start;
            const blocks = [...root.querySelectorAll(`.md [${MindmapPreview.LINE_ATTR}]`)];
            const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
            // 始まりの行を含む（始まりの行以前で最も後ろの）ブロックから、終わりの行までのブロック
            const first = blocks.filter((element) => lineOf(element) <= start).at(-1);
            if (first !== undefined)
                hits = blocks.filter((element) => lineOf(element) >= lineOf(first) && lineOf(element) <= end);
        }
        // 箇所が今の本文に合わない: 示さず、項目の先頭を出す
        if (hits.length === 0) {
            scroller?.scrollTo({ top: 0 });
            return;
        }
        for (const element of hits)
            element.classList.add("loc-hit");
        hits[0]?.scrollIntoView({ block: "center" });
    }
    MindmapPreview.highlightLocation = highlightLocation;
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on, send } = props;
        const kind = index.byId.get(id)?.kind;
        // 中にフォーカスできる要素が無い項目でも、キーボードで送れるように領域ごとフォーカスできるようにする
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" },
            children: [detailBody(props)],
        });
        const head = detailHead(props);
        // 見出しと下端の入力の間の本文だけをスクロールする
        const footer = send === null ? null : MindmapPreview.sendForm(send);
        if (!full) {
            return MindmapPreview.h({
                tag: "aside",
                attrs: { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" },
                children: [head, body, footer],
            });
        }
        const dialog = MindmapPreview.h({ tag: "dialog", attrs: { class: "full", "aria-label": "詳細の全画面" }, children: [head, body, footer] });
        // Esc は閉じずに元の大きさ（詳細パネル）に戻す。外側（後ろの幕）を押したときも同じ
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            on.full(false);
        });
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog)
                on.full(false);
        });
        return dialog;
    }
    MindmapPreview.detailPanel = detailPanel;
})(MindmapPreview || (MindmapPreview = {}));
