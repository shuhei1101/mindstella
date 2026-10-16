"use strict";
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。差分の表示の間は、選んだ時点の前後の差分も出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 前の値が無いときに出す文字（差分のミニマップが、前に無かったキーを見分けるのにも使う） */
    MindmapPreview.NO_VALUE = "（なし）";
    /** 詳細パネルのレビュー中のコメントの行の `data-focus` の接頭辞（コメントの一覧と同時に開いても、描き直した後のフォーカスの戻し先を分ける） */
    MindmapPreview.REVIEW_FOCUS = "detail-";
    /** 差分に並べるキーから外す、ツールが付けるキーと本文の名前 */
    const UNDIFFED_KEYS = new Set(["id", "created", "updated", "updated_by", "history", "history_dropped_seq", "body"]);
    /** 前後を組み立てられない旨・本文の差分を出せない旨の文言 */
    const NOTE_TRIMMED = "このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。";
    const NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。";
    const NOTE_BODY_TOO_LARGE = "本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。今の本文を出しています。";
    /** 図の前の版の記法を、図の要素に持たせる属性の名前（図の拡大が Raw の差分に読む） */
    const BEFORE_SOURCE_ATTR = "data-before-source";
    /** 前の版の図を描いて突き合わせる間、描いた SVG を置く画面の外の位置（px）と幅（px） */
    const OFFSCREEN_LEFT_PX = -10000;
    const OFFSCREEN_WIDTH_PX = 800;
    /** 差分の記号と、読み上げに残す名前 */
    const SIGNS = {
        add: { glyph: "+", name: "追加: " },
        del: { glyph: "−", name: "削除: " },
        same: { glyph: " ", name: "" },
    };
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
    /** 文字列の値を Markdown で描く（値が無ければ何も描かない。ライブラリを読めないときは文字のまま） */
    function markdownValue(value) {
        return value === undefined ? undefined : MindmapPreview.renderValue(value);
    }
    /** Markdown で描く値の入れ物。選んだ箇所のコメント・示す箇所・キーの差分が、キーのパスで値を指せるようにする */
    function valueBlock(key, children) {
        return MindmapPreview.h({ tag: "div", attrs: { class: "d-value", [MindmapPreview.VALUE_KEY_ATTR]: key }, children });
    }
    /** 読み上げにだけ残す文字 */
    function srOnly(text) {
        return MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [text] });
    }
    /** 差分の記号（見えるのは記号だけで、名前は読み上げに残す） */
    function signMarks(op) {
        const { glyph, name } = SIGNS[op];
        return [MindmapPreview.h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [glyph] }), ...(name === "" ? [] : [srOnly(name)])];
    }
    MindmapPreview.signMarks = signMarks;
    /** 変わったキーの前の値と今の値を並べる。前の値は取り消し線、今の値は下線。plain は面を塗らず、線と矢印だけで示す。pairs を渡すと、前後がどちらも空でない文字のとき、並べた対を語の面を付ける対として pairs に足す */
    function keyDiff({ was, now, plain = false, pairs, }) {
        const empty = (value) => value === null || value === undefined || value === false || value === "";
        const wasElement = MindmapPreview.h({ tag: "del", attrs: { class: "df-was" }, children: [srOnly("前の値: "), empty(was) ? MindmapPreview.NO_VALUE : was] });
        const nowElement = MindmapPreview.h({ tag: "ins", attrs: { class: "df-now" }, children: [srOnly("今の値: "), empty(now) ? MindmapPreview.NO_VALUE : now] });
        if (typeof was === "string" && typeof now === "string" && !empty(was) && !empty(now))
            pairs?.push({ was: wasElement, now: nowElement });
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: plain ? "df-kv df-plain" : "df-kv" },
            children: [wasElement, MindmapPreview.h({ tag: "span", attrs: { class: "df-arrow", "aria-hidden": "true" }, children: ["→"] }), nowElement],
        });
    }
    /** 控えたキーの値の対の文字（読み上げの文字を除く） */
    function keyWordNodes(root) {
        return wordTextNodes(root).filter((node) => node.parentElement?.closest(".sr-only") == null);
    }
    /** 控えたキーの値の対の前後の文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
    function markKeyWords({ pairs, deadline }) {
        for (const pair of pairs) {
            const wasNodes = keyWordNodes(pair.was);
            const nowNodes = keyWordNodes(pair.now);
            const inline = MindmapPreview.diffInline(wasNodes.map((node) => node.data).join(""), nowNodes.map((node) => node.data).join(""), deadline);
            if (inline === null)
                continue;
            wrapWords({ nodes: wasNodes, parts: inline.before, mark: "del" });
            wrapWords({ nodes: nowNodes, parts: inline.after, mark: "add" });
        }
    }
    /** キーの値を、差分に並べる文字にする。値が無ければ null */
    function valueText(value) {
        if (value === undefined || value === null || value === "")
            return null;
        if (Array.isArray(value))
            return value.length === 0 ? null : value.join("、");
        return String(value);
    }
    /** 案の値（文字列か文字列の配列）を、Markdown で描く 1 つの文字列にする。配列は「、」でつなぐ。空なら undefined */
    function optionText(value) {
        if (Array.isArray(value))
            return value.length === 0 ? undefined : value.join("、");
        return value;
    }
    /** 前の版と後の版を比べ、値が変わったキー（ツールが付けるキーと本文の名前を除く）の見せ方を返す */
    function keyDiffs(before, after) {
        const left = { ...before };
        const right = { ...after };
        const changed = new Set([...new Set([...Object.keys(left), ...Object.keys(right)])].filter((key) => !UNDIFFED_KEYS.has(key) && JSON.stringify(left[key]) !== JSON.stringify(right[key])));
        const pairs = [];
        return {
            has: (key) => changed.has(key),
            show: (key, render = valueText, plain = false) => changed.has(key) ? keyDiff({ was: render(left[key]), now: render(right[key]), plain }) : render(right[key]),
            showWords: (key) => changed.has(key) ? keyDiff({ was: valueText(left[key]), now: valueText(right[key]), pairs }) : valueText(right[key]),
            pairs,
            before,
        };
    }
    /** 状態の値（文字）を、印と名前の表示にする。状態を持たなければ null */
    function statusOf(value) {
        return typeof value === "string" ? MindmapPreview.statusBadge(value) : null;
    }
    /** 選んだ時点で、開いた項目が足されたか変わったときの、前後の版と画面に出す内容。そうでなければ null */
    function resolveDiffView({ id, index, diff }) {
        const entry = index.byId.get(id);
        if (diff === null || entry === undefined)
            return null;
        const { item } = entry;
        const body = index.data.bodies[item.body ?? ""];
        if (diff.added.has(id))
            return { point: diff, kind: "new", versions: null, keys: null, shown: item, body };
        if (!diff.changed.has(id))
            return null;
        const versions = MindmapPreview.buildVersions(item, body ?? "", diff);
        // 前後を組み立てられない: 今の内容を差分なしで出す
        if (versions.trimmed || versions.before === null) {
            return { point: diff, kind: "changed", versions, keys: null, shown: item, body };
        }
        return {
            point: diff,
            kind: "changed",
            versions,
            keys: keyDiffs(versions.before, versions.after),
            shown: versions.after,
            body: body === undefined ? undefined : versions.afterBody,
        };
    }
    /** 差分の表示の冒頭の帯。選んだ時点の名前と日時 */
    function diffHead(point) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "df-head" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "df-head-t" }, children: [MindmapPreview.icon("history"), point.name] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "df-when" }, children: [point.sub] }),
            ],
        });
    }
    /** 前後を組み立てられない旨・本文の差分を出せない旨の知らせ */
    function noteBox(text) {
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: "df-note", role: "note" },
            children: [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [text] })],
        });
    }
    /** 案の採用の状態の名前（採用でも不採用でもない案は null） */
    function optionResult(option) {
        if (option === undefined)
            return null;
        return option.adopted === true ? "採用" : option.adopted === false ? "不採用" : null;
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由、採用した案が無いときは推奨の印を出す）。previous があれば、変わった値に前の値を並べる */
    function optionCards({ options, previous, pairs }) {
        const compare = previous !== null;
        const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
        // 採用した案があれば採用の表示を優先し、推奨の印は出さない
        const decided = options.some((option) => option.adopted === true);
        return MindmapPreview.h({
            tag: "div",
            children: [
                ...options.map((option) => {
                    const before = previous?.find((entry) => entry.key === option.key);
                    const result = optionResult(option);
                    const recommended = option.recommended === true && !decided;
                    const rows = [
                        ["メリット", "pros", optionText(option.pros)],
                        ["デメリット", "cons", optionText(option.cons)],
                        ["備考", "note", option.note],
                        ["理由", "reason", option.reason],
                    ];
                    // 前の値と違う値は前の値と今の値を並べる。前に無かった案は全ての値を足した印にする
                    const beforeOf = (field) => optionText(before?.[field]);
                    const shown = rows.filter(([, field, value]) => (value !== undefined && value !== "") || (compare && beforeOf(field) !== undefined));
                    const valueOf = (field, value) => compare && beforeOf(field) !== value
                        ? keyDiff({ was: beforeOf(field) ?? null, now: value ?? null, pairs })
                        : markdownValue(value);
                    const resultChild = compare && optionResult(before) !== result ? keyDiff({ was: optionResult(before), now: result, plain: true }) : result;
                    return MindmapPreview.h({
                        tag: "div",
                        attrs: {
                            class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}${recommended ? " recommended" : ""}`,
                        },
                        children: [
                            MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "o-head" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                    valueBlock(`options[${option.key}].content`, [
                                        compare && before?.content !== option.content
                                            ? keyDiff({ was: before?.content ?? null, now: option.content, pairs })
                                            : markdownValue(option.content),
                                    ]),
                                    recommended ? MindmapPreview.h({ tag: "span", attrs: { class: "rec-badge" }, children: [MindmapPreview.icon("star"), "推奨"] }) : null,
                                    resultChild === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "res" }, children: [resultChild] }),
                                ],
                            }),
                            shown.length > 0
                                ? MindmapPreview.h({
                                    tag: "dl",
                                    children: [
                                        ...shown.flatMap(([label, field, value]) => [
                                            MindmapPreview.h({ tag: "dt", children: [label] }),
                                            MindmapPreview.h({ tag: "dd", attrs: { [MindmapPreview.VALUE_KEY_ATTR]: `options[${option.key}].${field}` }, children: [valueOf(field, value)] }),
                                        ]),
                                    ],
                                })
                                : null,
                        ],
                    });
                }),
                // 後の版で消えた案: 全ての値を消した印で並べる
                ...removed.map((option) => MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "opt" },
                    children: [
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "o-head" },
                            children: [
                                MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                MindmapPreview.h({ tag: "del", attrs: { class: "df-was" }, children: [srOnly("消した案: "), option.content] }),
                            ],
                        }),
                    ],
                })),
            ],
        });
    }
    /** 見出しの下の、項目のキー（対象・カテゴリー・フェーズ・影響度・種類・確度・日付・更新日・タグ）の一覧。変わったキーは前の値と今の値を並べる */
    function metaList({ item, settings, diff }) {
        const pairs = [
            [settings.target_label, "target", item.target],
            ["カテゴリー", "category", item.category],
            ["フェーズ", "phase", item.phase],
            ["影響度", "weight", item.weight],
            ["種類", "kind", item.kind],
            ["確度", "confidence", item.confidence],
            ["日付", "date", item.date],
            ["更新日", "updated", item.updated],
            // 取り下げは値をここに出さず（題の右の札が示す）、差分の表示で変わったときだけ前後を並べる
            ["取り下げ", "withdrawn", undefined],
        ];
        const rows = pairs.flatMap(([label, key, value]) => {
            const changed = diff?.has(key) === true;
            // 値が無く、変わってもいないキーは出さない
            if ((value === undefined || value === "") && !changed)
                return [];
            const shown = diff === null
                ? value
                : key === "withdrawn"
                    ? diff.show(key, (flag) => (flag === true ? MindmapPreview.withdrawnBadge() : null))
                    : diff.show(key);
            return [
                MindmapPreview.h({ tag: "dt", attrs: { class: changed ? "df-key" : null }, children: [label] }),
                MindmapPreview.h({ tag: "dd", attrs: { class: changed ? "df-key" : null }, children: [shown] }),
            ];
        });
        const tagsChanged = diff?.has("tags") === true;
        if ((item.tags ?? []).length > 0 || tagsChanged) {
            rows.push(MindmapPreview.h({ tag: "dt", attrs: { class: tagsChanged ? "df-key" : null }, children: ["タグ"] }), MindmapPreview.h({ tag: "dd", attrs: { class: tagsChanged ? "df-key" : null }, children: [tagsChanged ? diff?.show("tags") : MindmapPreview.tagList(item.tags)] }));
        }
        return MindmapPreview.h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
    }
    /** この項目へのレビュー中のコメントの節（各行の右上の「修正」「削除」で、その場で直す・消す・戻す。チェックとまとめて送るはコメントの一覧で行う） */
    function reviewSection({ items, edit }) {
        // 消した行は元の場所（溜めた順）に「元に戻す」と共に残す
        const rows = [...items.map((item) => ({ item, gone: false })), ...edit.removed.map((item) => ({ item, gone: true }))].sort((a, b) => MindmapPreview.commentNumber(a.item.id) - MindmapPreview.commentNumber(b.item.id));
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec d-review" },
            children: [
                MindmapPreview.h({
                    tag: "h3",
                    children: ["レビュー中のコメント", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })],
                }),
                rows.length === 0
                    ? MindmapPreview.emptyNote("レビュー中のコメントはありません。")
                    : MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list review-list" },
                        children: rows.map(({ item, gone }) => {
                            if (gone)
                                return MindmapPreview.removedReviewRow({ item, focus: MindmapPreview.REVIEW_FOCUS, on: { restore: edit.on.restore } });
                            const editing = edit.editing === item.id;
                            // 入力欄は修正を始めた場所だけに描く。コメントの一覧で始めた行は、ここでは本文だけにして「修正」「削除」も出さない
                            const editingHere = editing && edit.editingIn === "detail";
                            return MindmapPreview.h({
                                tag: "li",
                                attrs: { class: `review-row${editing ? " editing" : ""}`, "data-comment": item.id },
                                children: [
                                    MindmapPreview.h({
                                        tag: "div",
                                        attrs: { class: "review-main" },
                                        children: [
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
                                            editingHere
                                                ? MindmapPreview.reviewEditForm({
                                                    item,
                                                    body: edit.editBody,
                                                    error: edit.editError,
                                                    focus: MindmapPreview.REVIEW_FOCUS,
                                                    on: { saveEdit: edit.on.saveEdit, cancelEdit: edit.on.cancelEdit },
                                                })
                                                : MindmapPreview.h({ tag: "p", attrs: { class: "review-body" }, children: [item.body] }),
                                        ],
                                    }),
                                    // 書き換えている行には「修正」「削除」を出さない（入力欄の「キャンセル」「修正」と並べない）
                                    editing ? null : MindmapPreview.reviewRowActions({ item, focus: MindmapPreview.REVIEW_FOCUS, on: { edit: edit.on.edit, remove: edit.on.remove } }),
                                ],
                            });
                        }),
                    }),
            ],
        });
    }
    // ─── 本文の差分 ───
    /** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
    function linesOf(text) {
        const lines = text.split("\n");
        if (lines.at(-1) === "")
            lines.pop();
        return lines;
    }
    /** 今の本文の行（1 始まり）のうち、差分で足した行 */
    function addedLines({ parts, now }) {
        const added = new Set();
        let line = 0;
        for (const part of parts) {
            if (part.kind === "removed")
                continue;
            for (const _ of part.lines) {
                line += 1;
                // 空行だけの足しは段落の間の空きで、どの塊も足したことにしない
                if (part.kind === "added" && (now[line - 1] ?? "").trim() !== "")
                    added.add(line);
            }
        }
        return added;
    }
    /** 今の本文の各行が属するブロックの先頭の行を求める。図のコードブロックの中は null（図の差分が示す）。それ以外のコードブロックの中は、中身の最初の行を持つブロックに属する */
    function blockOwners({ now, starts }) {
        const owners = [];
        let fence = null;
        now.forEach((text, offset) => {
            const line = offset + 1;
            const opening = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
            if (fence !== null) {
                owners.push(fence.owner);
                // 閉じるフェンス（言語を持たない行）で、コードブロックを出る
                if (opening !== null && opening[2] === "")
                    fence = null;
                return;
            }
            if (opening !== null) {
                fence = { owner: opening[2] === "mermaid" ? null : line + 1 };
                owners.push(fence.owner);
                return;
            }
            // 印を持つブロックのうち、この行以前で最も後ろのもの
            owners.push(starts.filter((start) => start <= line).at(-1) ?? null);
        });
        return owners;
    }
    MindmapPreview.blockOwners = blockOwners;
    /** 差分の記号を頭に置いた、足した塊・消した塊の囲み */
    function diffBlock({ op, children }) {
        return MindmapPreview.h({
            tag: op === "add" ? "ins" : "del",
            attrs: { class: "df-blk" },
            children: [...signMarks(op), ...children],
        });
    }
    MindmapPreview.diffBlock = diffBlock;
    /** 本文の足した部分の印を、今の本文の要素に付ける（段落・見出し・コードは囲み、表の行と箇条書きの項目は行の印にする） */
    function markAddedBlocks({ root, parts, source }) {
        const now = linesOf(source);
        const added = addedLines({ parts, now });
        if (added.size === 0)
            return;
        const blocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(MindmapPreview.LINE_ATTR))) });
        const marked = new Set();
        for (const line of added) {
            const owner = owners[line - 1];
            if (owner !== null && owner !== undefined)
                marked.add(owner);
        }
        for (const block of blocks) {
            if (!marked.has(Number(block.getAttribute(MindmapPreview.LINE_ATTR))))
                continue;
            if (block.tagName === "TR") {
                block.classList.add("df-row", "df-add");
                block.firstElementChild?.prepend(...signMarks("add"));
            }
            else if (block.tagName === "LI") {
                block.classList.add("df-li-add");
            }
            else {
                // 囲みを元の位置に置いてから、ブロックを囲みの中へ移す
                const wrapper = diffBlock({ op: "add", children: [] });
                block.replaceWith(wrapper);
                wrapper.append(block);
            }
        }
    }
    /** 消した行を別に描いた要素から、行の印を外す（今の本文の行に対応づけない） */
    function withoutLineMarks(root) {
        for (const element of root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`))
            element.removeAttribute(MindmapPreview.LINE_ATTR);
        return root;
    }
    MindmapPreview.withoutLineMarks = withoutLineMarks;
    /** 消した行の図のコードブロックを、記法の原文だけにする（描かない） */
    function plainDiagrams(root) {
        for (const figure of root.querySelectorAll("figure.diagram")) {
            const source = figure.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            figure.replaceWith(MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
        }
    }
    /** 消した行のかたまりを、別に Markdown として描いた要素にする */
    function renderRemoved(block) {
        const lines = block.tableHeader === null ? block.lines : [...block.tableHeader, ...block.lines];
        const rendered = withoutLineMarks(MindmapPreview.renderMarkdown(lines.join("\n")));
        plainDiagrams(rendered);
        return rendered;
    }
    /** 描いた消した行のかたまりを、今の本文の差し込む場所の前（無ければ本文の最後）へ差し込む。かたまりごとに、差し込んだ語の面を付ける対象のブロックを返す */
    function insertRemovedBlocks({ root, blocks }) {
        // 差し込む前の、行の印を持つ今のブロック（差し込む要素は印を持たない）
        const stamped = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
        const placed = [];
        for (const { block, rendered } of blocks) {
            const target = block.beforeLine === null ? undefined : stamped.find((element) => lineOf(element) >= (block.beforeLine ?? 0));
            const previous = target === undefined ? stamped.at(-1) : stamped[stamped.indexOf(target) - 1];
            // 表の本体の行だけ: 今の表の行の間（表の最後の後も）へ、消した行の印を付けた行として差し込む
            if (block.tableHeader !== null) {
                const rows = [...rendered.querySelectorAll("tbody tr")].map((row) => {
                    row.classList.add("df-row", "df-del");
                    row.firstElementChild?.prepend(...signMarks("del"));
                    return row;
                });
                if (target?.tagName === "TR") {
                    target.before(...rows);
                    placed.push(rows);
                    continue;
                }
                if (previous?.tagName === "TR") {
                    previous.after(...rows);
                    placed.push(rows);
                    continue;
                }
            }
            // 囲みの中へ移す前に、語の面を付ける対象のブロックを引く
            placed.push(wordBlocksIn(rendered));
            const piece = diffBlock({ op: "del", children: [...rendered.childNodes] });
            if (target === undefined) {
                root.append(piece);
                continue;
            }
            // 足した塊の囲みの中・箇条書きや表の中ではなく、その外側の前へ差し込む（表は包む入れ物ごと外側にする）
            const outer = target.parentElement?.matches("ins.df-blk") === true ? target.parentElement : target;
            const container = outer.closest("ul, ol, table") ?? outer;
            (container.parentElement?.matches(`.${MindmapPreview.TABLE_WRAP_CLASS}`) === true ? container.parentElement : container).before(piece);
        }
        return placed;
    }
    /** 前の本文の図のコードブロック（開く行から閉じる行まで。1 始まり）。閉じていないコードブロックは本文の最後まで */
    function diagramFenceRanges(lines) {
        const ranges = [];
        let open = null;
        lines.forEach((text, offset) => {
            const fence = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
            if (fence === null)
                return;
            if (open === null) {
                if (fence[2] === "mermaid")
                    open = offset + 1;
            }
            else if (fence[2] === "") {
                ranges.push({ open, close: offset + 1 });
                open = null;
            }
        });
        if (open !== null)
            ranges.push({ open, close: lines.length });
        return ranges;
    }
    /** 消した行のうち、図のコードブロックの一部だけを消した分を外す（図の差分が示すので、本文には消した行として差し込まない）。図を丸ごと消した分は残す */
    function withoutDiagramEdits({ parts, before }) {
        const ranges = diagramFenceRanges(linesOf(before));
        if (ranges.length === 0)
            return parts;
        let line = 0;
        return parts.flatMap((part) => {
            if (part.kind === "added")
                return [part];
            const first = line + 1;
            line += part.lines.length;
            if (part.kind === "same")
                return [part];
            const last = line;
            // この消した部分に丸ごと入っていない図のコードブロックの行
            const partial = ranges.filter((range) => range.open < first || range.close > last);
            const kept = part.lines.filter((_, offset) => !partial.some((range) => first + offset >= range.open && first + offset <= range.close));
            return kept.length === 0 ? [] : [{ kind: part.kind, lines: kept }];
        });
    }
    /** 語の面を付ける対象になる、描いたブロック（段落・見出し・箇条書きの項目・表の本体の行）の選び方 */
    const WORD_BLOCK_SELECTOR = "p, h1, h2, h3, h4, h5, h6, li, tbody tr";
    /** 語の面を付ける対象のブロックか（ほかの対象のブロックを中に持たないもの） */
    function isWordBlock(element) {
        return element.matches(WORD_BLOCK_SELECTOR) && element.querySelector(WORD_BLOCK_SELECTOR) === null;
    }
    /** 要素の中の、語の面を付ける対象のブロック（文書の順） */
    function wordBlocksIn(root) {
        return [...root.querySelectorAll(WORD_BLOCK_SELECTOR)].filter(isWordBlock);
    }
    MindmapPreview.wordBlocksIn = wordBlocksIn;
    /** 足した部分ごとの、足した行（空行を除く）を持つ今のブロックのうち、語の面を付ける対象のもの（足した行の順） */
    function addedBlocksByPart({ root, parts, now }) {
        const blocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(MindmapPreview.LINE_ATTR))) });
        const byStart = new Map(blocks.map((block) => [Number(block.getAttribute(MindmapPreview.LINE_ATTR)), block]));
        const found = new Map();
        let line = 0;
        parts.forEach((part, position) => {
            if (part.kind === "removed")
                return;
            const here = [];
            for (const _ of part.lines) {
                line += 1;
                // 空行だけの足しは段落の間の空きで、どのブロックも足したことにしない
                if (part.kind !== "added" || (now[line - 1] ?? "").trim() === "")
                    continue;
                const owner = owners[line - 1];
                const block = owner === null || owner === undefined ? undefined : byStart.get(owner);
                if (block !== undefined && isWordBlock(block) && !here.includes(block))
                    here.push(block);
            }
            if (part.kind === "added")
                found.set(position, here);
        });
        return found;
    }
    /** 変えた行の対（`pairedParts`）ごとに、消した部分から描いたブロックと、足した部分の行を持つ今のブロックを前から順に並べ、両方の数が同じときだけ 1 つずつ対にする */
    function wordPairs({ root, parts, now, placed, }) {
        // 消した部分の並びの何番目か（`placed` は消した部分の順）
        const removedOrder = parts.flatMap((part, position) => (part.kind === "removed" ? [position] : []));
        const addedBlocks = addedBlocksByPart({ root, parts, now });
        return MindmapPreview.pairedParts(parts).flatMap(({ removed, added }) => {
            const removedList = placed[removedOrder.indexOf(removed)] ?? [];
            const addedList = addedBlocks.get(added) ?? [];
            if (removedList.length === 0 || removedList.length !== addedList.length)
                return [];
            return removedList.map((block, offset) => ({ removed: block, added: addedList[offset] }));
        });
    }
    /** 要素の中の、行の印（`signMarks` が入れる記号と読み上げの文字）と、表・リストの構造の間の整形の空白を除いた文字のノード（文書の順） */
    function wordTextNodes(root) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => {
                const parent = node.parentElement;
                const isSign = parent?.closest(".df-sign") != null || parent?.matches(".df-sign + .sr-only") === true;
                const isLayoutSpace = (node.textContent ?? "").trim() === "" && parent?.matches("table, thead, tbody, tr, ul, ol") === true;
                return isSign || isLayoutSpace ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
            },
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        return nodes;
    }
    /** 変わった語の面の要素 */
    function wordMark({ mark, text }) {
        return MindmapPreview.h({ tag: "span", attrs: { class: `df-word df-${mark}` }, children: [text] });
    }
    /** 文字のノードの並びのうち、語の差分の足した・消した部分を面の要素で囲む（ノードをまたぐ部分はノードごとに囲み、ノードの外の要素は分けない） */
    function wrapWords({ nodes, parts, mark }) {
        // 同じでない部分の、文字の頭からの範囲
        const ranges = [];
        let offset = 0;
        for (const part of parts) {
            if (part.kind !== "same")
                ranges.push({ start: offset, end: offset + part.text.length });
            offset += part.text.length;
        }
        let nodeStart = 0;
        for (const node of nodes) {
            const text = node.data;
            const nodeEnd = nodeStart + text.length;
            const pieces = [];
            // ノードの中で、ここまでを pieces に入れた位置
            let cursor = 0;
            for (const range of ranges) {
                const from = Math.max(range.start, nodeStart) - nodeStart;
                const to = Math.min(range.end, nodeEnd) - nodeStart;
                if (from >= to)
                    continue;
                if (from > cursor)
                    pieces.push(text.slice(cursor, from));
                pieces.push(wordMark({ mark, text: text.slice(from, to) }));
                cursor = to;
            }
            nodeStart = nodeEnd;
            if (pieces.length === 0)
                continue;
            if (cursor < text.length)
                pieces.push(text.slice(cursor));
            node.replaceWith(...pieces);
        }
    }
    /** 対の 2 つのブロックの、行の印を除いた文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
    function markWords({ pair, deadline }) {
        const removedNodes = wordTextNodes(pair.removed);
        const addedNodes = wordTextNodes(pair.added);
        const inline = MindmapPreview.diffInline(removedNodes.map((node) => node.data).join(""), addedNodes.map((node) => node.data).join(""), deadline);
        if (inline === null)
            return;
        wrapWords({ nodes: removedNodes, parts: inline.before, mark: "del" });
        wrapWords({ nodes: addedNodes, parts: inline.after, mark: "add" });
    }
    MindmapPreview.markWords = markWords;
    /** 前後の本文を行ごとに比べ、今の本文を描いて足した部分と消した部分に印を付ける。差分を計算しきれなかったら null */
    function renderBodyDiff({ before, after, deadline }) {
        const compared = MindmapPreview.diffLineParts(before, after);
        if (compared === null)
            return null;
        const parts = withoutDiagramEdits({ parts: compared, before });
        const rendered = MindmapPreview.renderMarkdown(after);
        const removed = MindmapPreview.placeRemovedBlocks(parts).map((block) => ({ block, rendered: renderRemoved(block) }));
        // 今の本文と消した部分の見出しを合わせた最も上の段から、段の差を 1 つ求める
        const shift = headingShift([rendered, ...removed.map((piece) => piece.rendered)]);
        lowerHeadings({ root: rendered, shift });
        for (const piece of removed)
            lowerHeadings({ root: piece.rendered, shift });
        markAddedBlocks({ root: rendered, parts, source: after });
        const placed = insertRemovedBlocks({ root: rendered, blocks: removed });
        const pairs = wordPairs({ root: rendered, parts, now: linesOf(after), placed });
        return { root: rendered, markWords: () => pairs.forEach((pair) => markWords({ pair, deadline })) };
    }
    // ─── 図の差分 ───
    /** 記法の 1 行目の語（図の種類）。先頭の設定の行（`%%`）と空行は読み飛ばす */
    function diagramType(source) {
        const first = source
            .split("\n")
            .map((line) => line.trim())
            .find((line) => line !== "" && !line.startsWith("%%"));
        return first?.split(/\s+/)[0] ?? "";
    }
    /** 行の差分を比べやすいよう、記法の末尾を改行 1 つにそろえる */
    function withTrailingNewline(source) {
        return source.endsWith("\n") ? source : `${source}\n`;
    }
    /** 記法の行ごとの差分を、足した行（+）・消した行（−）の印つきの行にする。変えた行の対は、変わった語を濃い面で囲む（`deadline` は、行の差分を呼ぶ直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
    function rawDiffLines({ parts, deadline }) {
        const op = { added: "add", removed: "del", same: "same" };
        // 対の行ごとの語の差分（`parts` の添え字 → 行ごと）。対の行ごとに 1 回だけ比べ、消した側と足した側に同じ結果を使う
        const inlines = new Map();
        for (const { removed, added } of MindmapPreview.pairedParts(parts)) {
            const removedLines = parts[removed]?.lines ?? [];
            const addedLines = parts[added]?.lines ?? [];
            const compared = removedLines.map((text, offset) => MindmapPreview.diffInline(text, addedLines[offset] ?? "", deadline));
            inlines.set(removed, compared);
            inlines.set(added, compared);
        }
        return parts.flatMap((part, position) => part.lines.map((text, offset) => {
            const inline = inlines.get(position)?.[offset] ?? null;
            const pieces = inline === null ? null : part.kind === "removed" ? inline.before : inline.after;
            return MindmapPreview.h({
                tag: "span",
                attrs: { class: `df-line${part.kind === "same" ? "" : ` df-${op[part.kind]}`}` },
                children: [
                    ...signMarks(op[part.kind]),
                    ...(pieces === null ? [text] : pieces.map((piece) => (piece.kind === "same" ? piece.text : wordMark({ mark: part.kind === "removed" ? "del" : "add", text: piece.text })))),
                ],
            });
        }));
    }
    MindmapPreview.rawDiffLines = rawDiffLines;
    /** 前後の版の図の記法の並びから、今の図ごとの前の版の記法を決める。前の版と同じ図は null、前に無い図は空文字列。同じ記法の図を先に組にし、残りを並びの順で組にする */
    function pairDiagrams({ before, after }) {
        const free = new Set(before.keys());
        const unchanged = after.map((source) => {
            const match = [...free].find((candidate) => (before[candidate] ?? "").trim() === source.trim());
            if (match === undefined)
                return false;
            free.delete(match);
            return true;
        });
        const rest = [...free];
        return after.map((_, position) => {
            if (unchanged[position] === true)
                return null;
            const next = rest.shift();
            return next === undefined ? "" : (before[next] ?? "");
        });
    }
    /** 図の下に出す、凡例と「消したもの」 */
    function diagramNotes({ colored, removed }) {
        const legend = colored
            ? MindmapPreview.h({
                tag: "div",
                attrs: { class: "df-legend" },
                children: [
                    MindmapPreview.h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } }), "足した"] }),
                    MindmapPreview.h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
                ],
            })
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "df-legend" },
                children: [
                    MindmapPreview.h({ tag: "span", attrs: { class: "df-badge df-chg" }, children: [MindmapPreview.icon("changed"), "変わった図"] }),
                    MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["図の中の変更は Raw で見られます"] }),
                ],
            });
        return MindmapPreview.h({
            tag: "figcaption",
            attrs: { class: "df-notes" },
            children: [
                legend,
                removed.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "df-removed" },
                        children: [
                            MindmapPreview.h({ tag: "span", attrs: { class: "df-removed-t" }, children: ["消したもの"] }),
                            MindmapPreview.h({
                                tag: "ul",
                                children: removed.map((name) => MindmapPreview.h({ tag: "li", children: [MindmapPreview.h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: ["−"] }), srOnly("消した: "), name] })),
                            }),
                        ],
                    }),
            ],
        });
    }
    /** 図の差分で見つけた要素に色の印を付ける（ノードは枠と面、辺は線、メッセージは文字と線） */
    function paintDiagramElement({ element, mode }) {
        if (element.matches("text")) {
            element.classList.add(`df-t-${mode}`);
            element.nextElementSibling?.classList.add(`df-e-${mode}`);
            return;
        }
        element.classList.add(element.matches("path") ? `df-e-${mode}` : `df-n-${mode}`);
    }
    /** 前の版の図を `renderDiagramSvg` で描き、今の版の図と `diffDiagram` で突き合わせる。前の版の図を描けないときと、色を付けない種類・突き合わせを打ち切ったときは null */
    async function diffByRenderedBefore({ type, beforeSource, afterSvg }) {
        const beforeSvg = await MindmapPreview.renderDiagramSvg(beforeSource);
        if (beforeSvg === null)
            return null;
        // 前の版の図は、座標を取れるよう画面の外に置いて突き合わせる
        const offscreen = MindmapPreview.h({
            tag: "div",
            attrs: {
                "aria-hidden": "true",
                style: `position:absolute;top:0;left:${OFFSCREEN_LEFT_PX}px;width:${OFFSCREEN_WIDTH_PX}px`,
            },
            children: [beforeSvg],
        });
        document.body.append(offscreen);
        const diagram = MindmapPreview.diffDiagram(type, beforeSvg, afterSvg);
        offscreen.remove();
        return diagram;
    }
    /** 変わった図に、色・凡例と消したもの・Raw の行ごとの差分を付ける。前の版の図を描けない・色を付けない種類・突き合わせを打ち切ったときは、図の枠に色を付ける */
    async function decorateDiagram({ figure, beforeSource }) {
        const holder = figure.querySelector(".mermaid");
        const afterSource = holder?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
        figure.classList.add("df-changed", "df-frame");
        // Raw: 記法の行ごとの差分（打ち切ったときは今の記法のまま）
        const raw = figure.querySelector(":scope > .dg-raw");
        const deadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
        const parts = MindmapPreview.diffLineParts(withTrailingNewline(beforeSource), withTrailingNewline(afterSource));
        if (raw !== null && parts !== null) {
            raw.classList.add("df-raw");
            raw.replaceChildren(...rawDiffLines({ parts, deadline }));
        }
        const type = diagramType(afterSource);
        const afterSvg = holder?.querySelector("svg") ?? null;
        let colored = false;
        let removed = [];
        if (afterSvg !== null && MindmapPreview.COLORED_DIAGRAM_TYPES.includes(type) && beforeSource.trim() !== "") {
            // flowchart は前後の記法の解析で突き合わせ、前の版を描かない。null（flowchart でない・解析できない）の図だけ前の版を描く
            const diagram = (await MindmapPreview.diffDiagramFromSource(type, beforeSource, afterSource, afterSvg)) ?? (await diffByRenderedBefore({ type, beforeSource, afterSvg }));
            if (diagram !== null) {
                for (const element of diagram.added)
                    paintDiagramElement({ element, mode: "add" });
                for (const element of diagram.changed)
                    paintDiagramElement({ element, mode: "chg" });
                removed = diagram.removed;
                colored = true;
            }
        }
        figure.classList.toggle("df-frame", !colored);
        figure.classList.toggle("df-colored", colored);
        figure.append(diagramNotes({ colored, removed }));
        // 図の拡大が、同じ凡例と Raw の差分を出せるようになる
        figure.setAttribute(BEFORE_SOURCE_ATTR, beforeSource);
    }
    MindmapPreview.decorateDiagram = decorateDiagram;
    /** 差分の表示の間、今の本文の図のうち前の版から変わったものを、色・凡例・Raw の差分で示す */
    function decorateDiagrams({ root, before }) {
        const afterFigures = [...root.querySelectorAll("figure.diagram")];
        if (afterFigures.length === 0)
            return;
        const sourceOf = (figure) => figure.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
        const beforeSources = [...MindmapPreview.renderMarkdown(before).querySelectorAll("figure.diagram")].map(sourceOf);
        const pairs = pairDiagrams({ before: beforeSources, after: afterFigures.map(sourceOf) });
        afterFigures.forEach((figure, position) => {
            const beforeSource = pairs[position];
            // 前の版と同じ図は印を付けない
            if (beforeSource === null || beforeSource === undefined)
                return;
            void decorateDiagram({ figure, beforeSource });
        });
    }
    /** 資料の HTML の本文の枠が持つ属性（コメントの一覧から開いたとき、示す箇所を求める枠を引く） */
    const HTML_BODY_ATTR = "data-html-body";
    /** Markdown の本文の中の `html` のコードブロックの入れ物を、枠に置き換える。差分の表示の間の足した・消した部分は、枠に描かず原文に印を付けたまま出す */
    function drawHtmlBlocks(root) {
        for (const block of root.querySelectorAll(`.${MindmapPreview.HTML_BLOCK_CLASS}`)) {
            const source = block.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            if (block.closest(".df-blk") !== null) {
                block.replaceWith(MindmapPreview.h({ tag: "pre", attrs: { class: "html-block-src" }, children: [source] }));
            }
            else {
                const frame = MindmapPreview.htmlBodyFrame({ source, selectable: false, label: "html のコードブロック" });
                frame.classList.add(MindmapPreview.HTML_BLOCK_CLASS);
                const line = block.getAttribute(MindmapPreview.LINE_ATTR);
                if (line !== null)
                    frame.setAttribute(MindmapPreview.LINE_ATTR, line);
                block.replaceWith(frame);
            }
        }
    }
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on, review, view, bodyLayout }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "detail" } });
        if (entry === undefined)
            return body;
        const { kind } = entry;
        const item = view?.shown ?? entry.item;
        const keys = view?.keys ?? null;
        const related = MindmapPreview.relatedItems({ id, index });
        /** キーの値。変わっていれば前の値と今の値を並べる */
        const textOf = (key, value) => (keys?.has(key) === true ? keys.showWords(key) : value);
        const labelled = (label, key, value) => {
            const changed = keys?.has(key) === true;
            if ((value === undefined || value === "") && !changed)
                return null;
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: changed ? "d-answer df-key" : "d-answer" },
                children: [MindmapPreview.h({ tag: "b", children: [label] }), valueBlock(key, [changed ? textOf(key, value) : markdownValue(value)])],
            });
        };
        /** 資料・調査の説明の節（値があるとき、または値が変わったときだけ）。値が変わっていれば、前の値と今の値を並べる */
        const descriptionSection = () => {
            const changed = keys?.has("description") === true;
            if ((item.description === undefined || item.description === "") && !changed)
                return null;
            const described = section("説明", valueBlock("description", [changed ? textOf("description", item.description) : markdownValue(item.description)]));
            // 見た目は結論と同じ、灰色の面に小さな名前を添えた形
            described.classList.add("d-answer");
            return described;
        };
        /** 取り下げた理由の節（検討事項・タスクの `reason` は別の節が持つ）。値が変わっていれば、前の値と今の値を並べる */
        const withdrawnReason = () => {
            if (kind === "decisions" || kind === "tasks")
                return null;
            const changed = keys?.has("reason") === true;
            if ((item.reason === undefined || item.reason === "") && !changed)
                return null;
            return section("取り下げた理由", valueBlock("reason", [changed ? textOf("reason", item.reason) : markdownValue(item.reason)]));
        };
        /** 見出しの下の 1 段落 */
        const lead = (key, value, className) => {
            if ((value === undefined || value === "") && keys?.has(key) !== true)
                return null;
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: className, [MindmapPreview.VALUE_KEY_ATTR]: key },
                children: [keys?.has(key) === true ? textOf(key, value) : markdownValue(value)],
            });
        };
        let keysMarked = false;
        /** キーの値の語の面を、1 回だけ付ける。deadline は本文の語の差分と共有する（本文の差分を描かないときは、比べる直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
        const markKeys = (deadline) => {
            if (keys === null || keysMarked)
                return;
            keysMarked = true;
            markKeyWords({ pairs: keys.pairs, deadline });
        };
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす。差分の表示の間は、本文と図の差分を重ねる */
        const bodySection = (label) => {
            const source = view?.body ?? index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            if (MindmapPreview.bodyFormatOf(item.body) === "html")
                return htmlBodySection({ label, source });
            let rendered = null;
            let markBodyWords = null;
            let bodyDeadline = null;
            let notice = null;
            let diagramBefore = null;
            // 左右に並べた本文（並べ方が「左右に並べる」のとき）と、並べ方の切り替え
            let side = null;
            let layoutBar = null;
            const versions = view?.versions ?? null;
            if (versions !== null && versions.before !== null && !versions.trimmed) {
                if (MindmapPreview.missingLibraries(["jsdiff"]).length > 0) {
                    // jsdiff を読めない: 本文・図・Raw は今の版を差分なしで描く
                    notice = MindmapPreview.libraryNotice({ names: ["jsdiff"], what: "本文と図の差分" });
                }
                else if (versions.beforeBody === null) {
                    notice = noteBox(NOTE_BODY_UNAVAILABLE);
                }
                else {
                    diagramBefore = versions.beforeBody;
                    // 語の差分は、行の差分を呼ぶ前に決めたこの時刻の内に収める（行の差分を打ち切ったときも、キーの値の語の差分と共有する）
                    bodyDeadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
                    const bodyDiff = renderBodyDiff({ before: versions.beforeBody, after: source, deadline: bodyDeadline });
                    rendered = bodyDiff?.root ?? null;
                    markBodyWords = bodyDiff?.markWords ?? null;
                    if (rendered === null) {
                        notice = noteBox(NOTE_BODY_TOO_LARGE);
                    }
                    else if (versions.beforeBody !== source) {
                        // 本文が選んだ時点から変わっていて差分を描けたときだけ、並べ方の切り替えを置く
                        side =
                            bodyLayout === "side"
                                ? MindmapPreview.sideBySideBodyDiff({ before: versions.beforeBody, after: source, lined: source === index.data.bodies[item.body ?? ""], deadline: bodyDeadline })
                                : null;
                        if (bodyLayout === "side" && side === null) {
                            notice = noteBox(NOTE_BODY_TOO_LARGE);
                        }
                        else {
                            layoutBar = MindmapPreview.h({ tag: "div", attrs: { class: "body-diff-bar" }, children: [MindmapPreview.bodyDiffLayoutSwitch({ layout: bodyLayout, on: { change: on.layout } })] });
                        }
                    }
                }
            }
            const root = rendered ?? MindmapPreview.renderMarkdown(source);
            if (rendered === null)
                lowerHeadings({ root, shift: headingShift([root]) });
            // 古いまとまりを選び、その後に本文を直した: 描いた本文は今の本文の行と合わないので、行の印を外す（選んだ箇所のコメントも示す箇所も今の行に向けない）
            if (source !== index.data.bodies[item.body ?? ""])
                withoutLineMarks(root);
            // 見出しのリンクと、本文の用語・項目の ID の印を付ける
            MindmapPreview.linkHeadings({
                root,
                onHeading: (slug) => {
                    scrollToHeading({ root, slug });
                    on.heading(slug);
                },
                onChangeSet: on.changeSet,
            });
            MindmapPreview.linkBody({ root, index, selfId: id, onOpen: on.open });
            drawHtmlBlocks(root);
            // 左右に並べた本文にも、見出しのリンクと本文の印を付ける（右の列だけが今の本文の行を持つ）
            for (const column of side?.columns ?? []) {
                MindmapPreview.linkHeadings({
                    root: column,
                    onHeading: (slug) => {
                        scrollToHeading({ root: column, slug });
                        on.heading(slug);
                    },
                    onChangeSet: on.changeSet,
                });
                MindmapPreview.linkBody({ root: column, index, selfId: id, onOpen: on.open });
                drawHtmlBlocks(column);
            }
            // 語の面は、リンクと用語の印を付けた後に付ける（印の要素は分けず、中の文字だけを囲む）。キーの値の語の面を先に付ける
            if (bodyDeadline !== null)
                markKeys(bodyDeadline);
            markBodyWords?.();
            side?.markWords();
            const drawn = MindmapPreview.renderDiagrams(root);
            if (diagramBefore !== null) {
                const before = diagramBefore;
                void drawn.then(() => decorateDiagrams({ root, before }));
            }
            // 左右に並べた本文の図を描き、右の変えた図に色・凡例・Raw の差分を付ける
            if (side !== null) {
                const sideView = side;
                void MindmapPreview.renderDiagrams(sideView.root).then(() => sideView.decorate());
            }
            const onDiagramTool = (event) => {
                const button = event.target.closest("[data-act]");
                const figure = button?.closest(".diagram");
                if (button === null || button === undefined || figure === null || figure === undefined)
                    return;
                const act = button.dataset["act"];
                const original = figure.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
                if (act === "diagram-zoom") {
                    const svgElement = figure.querySelector(".mermaid svg");
                    const beforeSource = figure.getAttribute(BEFORE_SOURCE_ATTR);
                    if (svgElement !== null)
                        on.diagram(svgElement, beforeSource === null ? null : { beforeSource });
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
            };
            root.addEventListener("click", onDiagramTool);
            const content = document.createDocumentFragment();
            // 左右に並べるときは、本文の幅が足りないときに出すインラインの本文も持つ
            if (side !== null) {
                side.root.addEventListener("click", onDiagramTool);
                root.classList.add("sbs-fallback");
            }
            content.append(...(notice === null ? [] : [notice]), ...(layoutBar === null ? [] : [layoutBar]), ...(side === null ? [] : [side.root]), root);
            return section(label, content);
        };
        /** HTML の本文の節。本文を枠に描く。差分の表示の間は、描いた結果の上の印と原文の差分で前後を見せる */
        const htmlBodySection = ({ label, source }) => {
            const current = index.data.bodies[entry.item.body ?? ""];
            const marked = index.data.marked_bodies?.[entry.item.body ?? ""];
            // 選んだ時点が今の本文のとき、行の印つきの HTML を使う（古いまとまりを選び、その後に本文を直したときは、今の行と合わない）
            const lined = source === current && marked !== undefined;
            const drawn = lined ? marked : source;
            let notice = null;
            let content = null;
            const versions = view?.versions ?? null;
            if (versions !== null && versions.before !== null && !versions.trimmed) {
                if (MindmapPreview.missingLibraries(["jsdiff"]).length > 0) {
                    notice = MindmapPreview.libraryNotice({ names: ["jsdiff"], what: "本文の差分" });
                }
                else if (versions.beforeBody === null) {
                    notice = noteBox(NOTE_BODY_UNAVAILABLE);
                }
                else if (versions.beforeBody !== source) {
                    content = MindmapPreview.htmlBodyDiff({
                        before: versions.beforeBody,
                        after: source,
                        marked: drawn,
                        beforeFormat: MindmapPreview.bodyFormatOf(versions.before.body) === "md" ? "md" : "html",
                        layout: bodyLayout,
                        layoutSwitch: MindmapPreview.bodyDiffLayoutSwitch({ layout: bodyLayout, on: { change: on.layout } }),
                    });
                    if (content === null)
                        notice = noteBox(NOTE_BODY_TOO_LARGE);
                }
            }
            const frame = content ??
                MindmapPreview.htmlBodyFrame({
                    source: drawn,
                    // 配る書き出しと、今の本文の行と合わない本文では、選んだ箇所のコメントの入口を出さない
                    selectable: review !== null && lined,
                    ...(on.frame === undefined ? {} : { on: { select: on.frame.select, clear: on.frame.clear } }),
                });
            if (frame instanceof HTMLIFrameElement)
                frame.setAttribute(HTML_BODY_ATTR, "");
            const wrapped = document.createDocumentFragment();
            wrapped.append(...(notice === null ? [] : [notice]), frame);
            return section(label, wrapped);
        };
        /** 採用した案と理由の節（決定内容・理由のどちらかがあるときだけ） */
        const adoptedSection = () => {
            const rows = [labelled("決定内容", "answer", item.answer), labelled("理由", "reason", item.reason)].filter((row) => row !== null);
            if (rows.length === 0)
                return null;
            const content = document.createDocumentFragment();
            content.append(...rows);
            return section("採用した案と理由", content);
        };
        /** 関係する項目の節（1 件以上あるときだけ） */
        const relation = (label, ids) => ids.length === 0 ? null : section(label, itemList(index, ids, on.open));
        /** タグなどの一覧の節。値が変わっていれば、前の値と今の値を並べる */
        const listSection = (label, key, values) => {
            if (keys?.has(key) === true)
                return section(label, valueSpan(key, [keys.show(key)]));
            return (values ?? []).length > 0 ? section(label, MindmapPreview.tagList(values)) : null;
        };
        MindmapPreview.append({
            parent: body,
            children: [
                view === null ? null : diffHead(view.point),
                view?.versions?.trimmed === true ? noteBox(NOTE_TRIMMED) : null,
                valueSpan("status", [keys?.has("status") === true ? keys.show("status", statusOf, true) : MindmapPreview.statusBadge(item.status)]),
                MindmapPreview.h({
                    tag: "h2",
                    attrs: { class: "d-title", [MindmapPreview.VALUE_KEY_ATTR]: "title" },
                    children: [
                        keys?.has("title") === true ? keys.showWords("title") : item.title,
                        item.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                        view?.kind === "new" ? MindmapPreview.diffMark({ kind: "new", labeled: true }) : null,
                        // 取り下げた項目は、差分の表示によらず題の右に札を置く
                        item.withdrawn === true ? MindmapPreview.withdrawnBadge({ large: true }) : null,
                    ],
                }),
                metaList({ item, settings: index.data.settings, diff: keys }),
                withdrawnReason(),
            ],
        });
        if (kind === "decisions") {
            const previous = keys?.has("options") === true ? (keys.before.options ?? []) : null;
            MindmapPreview.append({
                parent: body,
                children: [
                    lead("lead", item.lead, "d-lead"),
                    (item.options ?? []).length > 0 || previous !== null ? section("案", optionCards({ options: item.options ?? [], previous, ...(keys === null ? {} : { pairs: keys.pairs }) })) : null,
                    adoptedSection(),
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
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "research") {
            MindmapPreview.append({
                parent: body,
                children: [
                    lead("question", item.question, "d-lead"),
                    descriptionSection(),
                    labelled("結論", "conclusion", item.conclusion),
                    listSection("エイリアス", "aliases", item.aliases),
                    listSection("調査の観点", "angles", item.angles),
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "docs") {
            MindmapPreview.append({ parent: body, children: [descriptionSection(), listSection("エイリアス", "aliases", item.aliases), bodySection("本文")] });
        }
        else if (kind === "terms") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled("意味", "meaning", item.meaning),
                    listSection("別名", "aliases", item.aliases),
                    listSection("使わない表記", "avoid", item.avoid),
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "notes") {
            MindmapPreview.append({ parent: body, children: [lead("content", item.content, null), bodySection("本文")] });
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
        // 本文の差分を描かなかったとき、キーの値の語の面をここで付ける
        markKeys(performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS);
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
                        // 狭い幅でタイトルに幅を譲るとき、種類の名前だけを見た目から外せるよう包む
                        entry === undefined ? "" : MindmapPreview.h({ tag: "span", attrs: { class: "panel-kind-label" }, children: [`${MindmapPreview.KIND_LABEL[entry.kind]} `] }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                    ],
                }),
                entry?.kind === "docs" ? MindmapPreview.bodyFormatBadgeOf(entry.item.body) : null,
                // 本文の先頭のタイトルと二重に読ませないよう読み上げから外す。収まらない分は省略し、乗せると全文が読める
                entry === undefined
                    ? null
                    : MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "panel-title", "aria-hidden": "true", title: entry.item.title },
                        children: [entry.item.title],
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
                        // 全画面の間は、縮小のアイコンと元に戻す名前にする（色は変えず、押された状態は持たない）
                        "aria-label": full ? "元の大きさに戻す" : "全画面表示",
                        title: full ? "元の大きさに戻す" : "全画面表示",
                        onclick: () => on.full(!full),
                    },
                    children: [MindmapPreview.icon(full ? "shrink" : "expand")],
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
    /** 本文の先頭のタイトルが本文のスクロール領域の上へ出ている間だけ、見出しのタイトルに `is-shown` を付ける */
    function bindHeadTitle({ head, body }) {
        const headTitle = head.querySelector(".panel-title");
        const bodyTitle = body.querySelector(".d-title");
        if (headTitle === null || bodyTitle === null)
            return;
        const observer = new IntersectionObserver((entries) => {
            // 描き直されて文書から外れた見出しの見張りは外す
            if (!head.isConnected) {
                observer.disconnect();
                return;
            }
            const last = entries[entries.length - 1];
            // 領域の上へ出たときだけ出す（下にあるときは出さない）
            headTitle.classList.toggle("is-shown", !last.isIntersecting && last.boundingClientRect.top < (last.rootBounds?.top ?? 0));
        }, { root: body, threshold: 0 });
        observer.observe(bodyTitle);
    }
    /** 節の見出し「本文」（h3）の次に置く、本文の見出しのうち最も上の段 */
    const BODY_TOP_HEADING_LEVEL = 4;
    /** 見出しの要素の最も下の段（h6） */
    const LOWEST_HEADING_LEVEL = 6;
    /** 見出しの要素の段（h1〜h6 の数字） */
    function headingLevel(heading) {
        return Number(heading.tagName.slice(1));
    }
    /** 本文の見出しのうち最も上の段を h4 にするための、全ての見出しに足す段の差。見出しが無ければ 0 */
    function headingShift(roots) {
        const levels = roots.flatMap((root) => [...root.querySelectorAll("h1, h2, h3, h4, h5, h6")].map(headingLevel));
        return levels.length === 0 ? 0 : BODY_TOP_HEADING_LEVEL - Math.min(...levels);
    }
    MindmapPreview.headingShift = headingShift;
    /** 本文の見出しに段の差を足して、パネルの節の見出しより下の段（h4〜h6）に並べる。見た目は元の段のまま（`data-md-level`） */
    function lowerHeadings({ root, shift }) {
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const level = headingLevel(heading);
            const lowered = Math.min(level + shift, LOWEST_HEADING_LEVEL);
            const replacement = MindmapPreview.h({
                tag: `h${lowered}`,
                attrs: {
                    "data-md-level": level,
                    // 元の Markdown の行の印を引き継ぐ
                    [MindmapPreview.LINE_ATTR]: heading.getAttribute(MindmapPreview.LINE_ATTR),
                    // h6 を超える段は、読み上げの段で伝える
                    "aria-level": level + shift > LOWEST_HEADING_LEVEL ? level + shift : null,
                },
                children: [...heading.childNodes],
            });
            heading.replaceWith(replacement);
        }
    }
    MindmapPreview.lowerHeadings = lowerHeadings;
    /** 本文の見出しを、本文のスクロール領域の中で画面に入れる（見えている見出しが本文に無ければ false。左右に並べるときは同じ見出しが 3 か所にあるので、矩形を持つ最初のものへ送る） */
    function scrollToHeading({ root, slug }) {
        const target = [...root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)].find(MindmapPreview.isRendered);
        if (target === undefined)
            return false;
        target.scrollIntoView({ block: "start" });
        return true;
    }
    /** 本文の印のツールチップを隠すまで待つミリ秒（印からツールチップへポインターを動かす間に消さない） */
    const TIP_HIDE_DELAY_MS = 150;
    /** ツールチップを隠す待ちのタイマー */
    let tipTimer = 0;
    /** 今出している（出していた）ツールチップの印と、押して残しているか */
    let tipState = null;
    /** Esc で閉じて印へフォーカスを戻すとき、その印のフォーカスでツールチップを出し直さない */
    let refocused = null;
    /** 今のツールチップの要素（使い回す 1 つ。隠していても文書に残る） */
    function currentTip() {
        return document.getElementById(MindmapPreview.TERM_TIP_ID);
    }
    /** 押して残しているか。ツールチップがまだ文書にあって開いているときに限る（詳細パネルの描き直しで外れたものは残していないとみなす） */
    function isPinned() {
        return tipState?.pinned === true && currentTip()?.matches(":popover-open") === true;
    }
    /** ツールチップを隠す（`now` が偽のときは、少し待ってから） */
    function hideTermTip(now) {
        window.clearTimeout(tipTimer);
        const hide = () => {
            const tip = currentTip();
            if (tip?.matches(":popover-open") === true)
                tip.hidePopover();
            tipState = null;
        };
        if (now)
            hide();
        else
            tipTimer = window.setTimeout(hide, TIP_HIDE_DELAY_MS);
    }
    /** 印の上に、一致した項目のツールチップを出す。重ねる面の上にも出せるよう、印のある詳細パネル・全画面のモーダルの中に置く（モーダルの外は操作できない） */
    function showTermTip({ mark, entries, pinned, onOpen, }) {
        window.clearTimeout(tipTimer);
        const previous = currentTip();
        // 同じ印を同じ出し方で出しているときは出し直さない（中のスクロールを保つ）
        if (tipState?.mark === mark && tipState.pinned === pinned && previous?.matches(":popover-open") === true)
            return;
        if (previous !== null) {
            if (previous.matches(":popover-open"))
                previous.hidePopover();
            previous.remove();
        }
        const tip = MindmapPreview.termTip({
            entries,
            anchor: mark,
            pinned,
            on: {
                open: (id) => {
                    hideTermTip(true);
                    onOpen(id);
                },
                close: () => hideTermTip(true),
            },
        });
        // ツールチップに乗せている間は消さない。押して残した間は、外れても消さない
        tip.addEventListener("mouseenter", () => window.clearTimeout(tipTimer));
        tip.addEventListener("mouseleave", () => {
            if (!pinned)
                hideTermTip(false);
        });
        (mark.closest("dialog, aside") ?? document.body).append(tip);
        tip.showPopover();
        tipState = { mark, pinned };
    }
    /** Esc でツールチップを隠す。中にフォーカスがあれば印へ戻し、全画面の Esc（元の大きさに戻す）を起こさない */
    document.addEventListener("keydown", (event) => {
        const tip = currentTip();
        // 詳細パネルが出したツールチップだけを対象にする
        if (event.key !== "Escape" || tipState === null || tip?.matches(":popover-open") !== true)
            return;
        const back = tip.contains(document.activeElement) ? tipState.mark : null;
        event.preventDefault();
        event.stopPropagation();
        hideTermTip(true);
        refocused = back;
        back?.focus();
        refocused = null;
    }, true);
    /** 本文の印に乗せる・フォーカスするとツールチップを出し、外れると隠す（本文の要素に委ねて付ける）。用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残し、Tab で中へ移れる */
    function attachTermTips({ root, index, onOpen }) {
        /** イベントの先の印と、一致した項目（用語 → 資料 → 調査の順）。用語 2 件以上か、資料・調査を含むか */
        const markOf = (event) => {
            const mark = event.target.closest?.("a.term") ?? null;
            if (mark === null)
                return null;
            const ids = (mark.getAttribute("data-ids") ?? mark.getAttribute("data-id") ?? "").split(" ");
            const entries = ids.flatMap((id) => {
                const found = index.byId.get(id);
                return found === undefined ? [] : [{ kind: found.kind, item: found.item }];
            });
            return entries.length === 0 ? null : { mark, entries, multi: entries.length > 1 || entries.some((entry) => entry.kind !== "terms") };
        };
        root.addEventListener("mouseover", (event) => {
            const found = markOf(event);
            // 押して残している間は、ほかの印に乗せても替えない
            if (found !== null && !isPinned())
                showTermTip({ ...found, pinned: false, onOpen });
        });
        root.addEventListener("focusin", (event) => {
            const found = markOf(event);
            if (found !== null && found.mark !== refocused)
                showTermTip({ ...found, pinned: false, onOpen });
        });
        root.addEventListener("mouseout", (event) => {
            if (markOf(event) !== null && !isPinned())
                hideTermTip(false);
        });
        root.addEventListener("focusout", (event) => {
            const to = event.relatedTarget;
            // ツールチップの中へ移るときは残す。押して残している間は、フォーカスの行き先が無い（余白を押した）ときも残す
            if (markOf(event) === null || (to instanceof Node && currentTip()?.contains(to) === true))
                return;
            if (to === null && isPinned())
                return;
            hideTermTip(true);
        });
        // 用語 2 件以上か、資料・調査にも一致した印から Tab で、ツールチップの中の最初のリンクへ移る
        root.addEventListener("keydown", (event) => {
            const found = markOf(event);
            const tip = currentTip();
            if (event.key !== "Tab" || event.shiftKey || found === null || !found.multi || tip?.matches(":popover-open") !== true)
                return;
            const first = tip.querySelector("a[href]");
            if (first === null)
                return;
            event.preventDefault();
            first.focus();
        });
        root.addEventListener("click", (event) => {
            const found = markOf(event);
            if (found === null)
                return;
            // 用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残す（移る先は中のリンクで選ぶ）
            if (found.multi) {
                showTermTip({ ...found, pinned: true, onOpen });
                return;
            }
            // 用語 1 件だけに一致した印を押して項目へ移るときは、ツールチップを残さない
            hideTermTip(true);
        });
    }
    /** コメントの一覧から開いたとき、そのコメントの箇所に印の色の地を付け、描いた後にその箇所までスクロールする。合わなければ示さず、項目の先頭を出す */
    function applyHighlight({ root, loc }) {
        let hits = [];
        if (loc.kind === "value") {
            hits = [...root.querySelectorAll(`[${MindmapPreview.VALUE_KEY_ATTR}]`)].filter((element) => element.getAttribute(MindmapPreview.VALUE_KEY_ATTR) === loc.key);
        }
        else {
            const start = loc.start ?? 0;
            const end = loc.end ?? start;
            // HTML の本文: 枠の中で、始まりの行を含む最も内側の要素を示す
            const frame = root.querySelector(`iframe[${HTML_BODY_ATTR}]`);
            if (frame !== null) {
                MindmapPreview.highlightFrameLine({ frame, line: start, scroller: root.querySelector(".panel-body") });
                return;
            }
            const blocks = [...root.querySelectorAll(`.md [${MindmapPreview.LINE_ATTR}]`)];
            const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
            // 始まりの行を含む（始まりの行以前で最も後ろの）ブロックから、終わりの行までのブロック
            const first = blocks.filter((element) => lineOf(element) <= start).at(-1);
            if (first !== undefined)
                hits = blocks.filter((element) => lineOf(element) >= lineOf(first) && lineOf(element) <= end);
        }
        for (const element of hits)
            element.classList.add("loc-hit");
        // 文書に入れた後でないとスクロールできない
        const target = hits[0];
        if (target !== undefined)
            requestAnimationFrame(() => target.scrollIntoView({ block: "center" }));
    }
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on, comment, highlight = null, diff = null, heading = null, minimap = true, bodyLayout = "inline" } = props;
        const kind = index.byId.get(id)?.kind;
        // 中にフォーカスできる要素が無い項目でも、キーボードで送れるように領域ごとフォーカスできるようにする
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" },
            children: [
                detailBody({ id, index, on, review: comment === null ? null : { items: comment.reviews, edit: comment.edit }, view: resolveDiffView({ id, index, diff }), bodyLayout }),
            ],
        });
        const head = detailHead(props);
        bindHeadTitle({ head, body });
        // 見出しと下端の入力の間の本文だけをスクロールする。差分の表示の間で、表示の設定で外していなければ、本文の右にミニマップを並べる
        const footer = comment === null ? null : MindmapPreview.sendForm(comment.form);
        const scroller = MindmapPreview.diffMinimapFrame({ body, shown: diff !== null && minimap });
        let root;
        if (!full) {
            root = MindmapPreview.h({
                tag: "aside",
                attrs: { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" },
                children: [head, scroller, footer],
            });
        }
        else {
            const dialog = MindmapPreview.h({ tag: "dialog", attrs: { class: "full", "aria-label": "詳細の全画面" }, children: [head, scroller, footer] });
            // Esc は閉じずに元の大きさ（詳細パネル）に戻す。外側（後ろの幕）を押したときも同じ
            dialog.addEventListener("cancel", (event) => {
                event.preventDefault();
                on.full(false);
            });
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog)
                    on.full(false);
            });
            root = dialog;
        }
        if (highlight !== null)
            applyHighlight({ root, loc: highlight });
        attachTermTips({ root: body, index, onOpen: on.open });
        // 見出しを指して開いた: 描いた後にその見出しを本文の領域の中で画面に入れる（本文に無ければ、本文の頭で開き、ハッシュから外させる）
        if (heading !== null) {
            requestAnimationFrame(() => {
                if (!scrollToHeading({ root: body, slug: heading }))
                    on.heading(null);
            });
        }
        return root;
    }
    MindmapPreview.detailPanel = detailPanel;
})(MindmapPreview || (MindmapPreview = {}));
