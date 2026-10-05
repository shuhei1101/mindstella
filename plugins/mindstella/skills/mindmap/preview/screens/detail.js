"use strict";
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。差分の表示の間は、選んだ時点の前後の差分も出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 前の値が無いときに出す文字 */
    const NO_VALUE = "（なし）";
    /** 差分に並べるキーから外す、ツールが付けるキーと本文の名前 */
    const UNDIFFED_KEYS = new Set(["id", "created", "updated", "history", "history_dropped_seq", "body"]);
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
    /** 読み上げにだけ残す文字 */
    function srOnly(text) {
        return MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [text] });
    }
    /** 差分の記号（見えるのは記号だけで、名前は読み上げに残す） */
    function signMarks(op) {
        const { glyph, name } = SIGNS[op];
        return [MindmapPreview.h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [glyph] }), ...(name === "" ? [] : [srOnly(name)])];
    }
    /** 変わったキーの前の値と今の値を並べる。前の値は取り消し線、今の値は下線。plain は面を塗らず、線と矢印だけで示す */
    function keyDiff({ was, now, plain = false }) {
        const empty = (value) => value === null || value === undefined || value === false || value === "";
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: plain ? "df-kv df-plain" : "df-kv" },
            children: [
                MindmapPreview.h({
                    tag: "del",
                    attrs: { class: "df-was" },
                    children: [srOnly("前の値: "), empty(was) ? NO_VALUE : was],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "df-arrow", "aria-hidden": "true" }, children: ["→"] }),
                MindmapPreview.h({
                    tag: "ins",
                    attrs: { class: "df-now" },
                    children: [srOnly("今の値: "), empty(now) ? NO_VALUE : now],
                }),
            ],
        });
    }
    /** キーの値を、差分に並べる文字にする。値が無ければ null */
    function valueText(value) {
        if (value === undefined || value === null || value === "")
            return null;
        if (Array.isArray(value))
            return value.length === 0 ? null : value.join("、");
        return String(value);
    }
    /** 前の版と後の版を比べ、値が変わったキー（ツールが付けるキーと本文の名前を除く）の見せ方を返す */
    function keyDiffs(before, after) {
        const left = { ...before };
        const right = { ...after };
        const changed = new Set([...new Set([...Object.keys(left), ...Object.keys(right)])].filter((key) => !UNDIFFED_KEYS.has(key) && JSON.stringify(left[key]) !== JSON.stringify(right[key])));
        return {
            has: (key) => changed.has(key),
            show: (key, render = valueText, plain = false) => changed.has(key) ? keyDiff({ was: render(left[key]), now: render(right[key]), plain }) : render(right[key]),
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
    /** 案の採用の状態の名前 */
    function optionResult(option) {
        if (option === undefined)
            return null;
        return option.adopted === true ? "採用" : option.adopted === false ? "不採用" : "検討中";
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由を出す）。previous があれば、変わった値に前の値を並べる */
    function optionCards(options, previous) {
        const compare = previous !== null;
        const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
        return MindmapPreview.h({
            tag: "div",
            children: [
                ...options.map((option) => {
                    const before = previous?.find((entry) => entry.key === option.key);
                    const result = optionResult(option) ?? "検討中";
                    const rows = [
                        ["メリット", "pros", option.pros],
                        ["デメリット", "cons", option.cons],
                        ["備考", "note", option.note],
                        ["理由", "reason", option.reason],
                    ];
                    // 前の値と違う値は前の値と今の値を並べる。前に無かった案は全ての値を足した印にする
                    const shown = rows.filter(([, field, value]) => (value !== undefined && value !== "") || (compare && before?.[field] !== undefined));
                    const valueOf = (field, value) => compare && before?.[field] !== value ? keyDiff({ was: before?.[field] ?? null, now: value ?? null }) : value;
                    const resultChild = compare && optionResult(before) !== result ? keyDiff({ was: optionResult(before), now: result, plain: true }) : result;
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
                                    valueSpan(`options[${option.key}].content`, [
                                        compare && before?.content !== option.content ? keyDiff({ was: before?.content ?? null, now: option.content }) : option.content,
                                    ]),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "res" }, children: [resultChild] }),
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
        ];
        const rows = pairs.flatMap(([label, key, value]) => {
            const changed = diff?.has(key) === true;
            // 値が無く、変わってもいないキーは出さない
            if ((value === undefined || value === "") && !changed)
                return [];
            return [
                MindmapPreview.h({ tag: "dt", attrs: { class: changed ? "df-key" : null }, children: [label] }),
                MindmapPreview.h({ tag: "dd", attrs: { class: changed ? "df-key" : null }, children: [diff === null ? value : diff.show(key)] }),
            ];
        });
        const tagsChanged = diff?.has("tags") === true;
        if ((item.tags ?? []).length > 0 || tagsChanged) {
            rows.push(MindmapPreview.h({ tag: "dt", attrs: { class: tagsChanged ? "df-key" : null }, children: ["タグ"] }), MindmapPreview.h({ tag: "dd", attrs: { class: tagsChanged ? "df-key" : null }, children: [tagsChanged ? diff?.show("tags") : MindmapPreview.tagList(item.tags)] }));
        }
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
    /** 差分の記号を頭に置いた、足した塊・消した塊の囲み */
    function diffBlock({ op, children }) {
        return MindmapPreview.h({
            tag: op === "add" ? "ins" : "del",
            attrs: { class: "df-blk" },
            children: [...signMarks(op), ...children],
        });
    }
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
        lowerHeadings(rendered);
        plainDiagrams(rendered);
        return rendered;
    }
    /** 消した行のかたまりを、今の本文の差し込む場所の前（無ければ本文の最後）へ差し込む */
    function insertRemovedBlocks({ root, blocks }) {
        // 差し込む前の、行の印を持つ今のブロック（差し込む要素は印を持たない）
        const stamped = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
        for (const block of blocks) {
            const rendered = renderRemoved(block);
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
                    continue;
                }
                if (previous?.tagName === "TR") {
                    previous.after(...rows);
                    continue;
                }
            }
            const piece = diffBlock({ op: "del", children: [...rendered.childNodes] });
            if (target === undefined) {
                root.append(piece);
                continue;
            }
            // 足した塊の囲みの中・箇条書きや表の中ではなく、その外側の前へ差し込む
            const outer = target.parentElement?.matches("ins.df-blk") === true ? target.parentElement : target;
            (outer.closest("ul, ol, table") ?? outer).before(piece);
        }
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
    /** 前後の本文を行ごとに比べ、今の本文を描いて足した部分と消した部分に印を付ける。差分を計算しきれなかったら null */
    function renderBodyDiff({ before, after }) {
        const compared = MindmapPreview.diffLineParts(before, after);
        if (compared === null)
            return null;
        const parts = withoutDiagramEdits({ parts: compared, before });
        const rendered = MindmapPreview.renderMarkdown(after);
        lowerHeadings(rendered);
        markAddedBlocks({ root: rendered, parts, source: after });
        insertRemovedBlocks({ root: rendered, blocks: MindmapPreview.placeRemovedBlocks(parts) });
        return rendered;
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
    /** 記法の行ごとの差分を、足した行（+）・消した行（−）の印つきの行にする */
    function rawDiffLines(parts) {
        const op = { added: "add", removed: "del", same: "same" };
        return parts.flatMap((part) => part.lines.map((text) => MindmapPreview.h({
            tag: "span",
            attrs: { class: `df-line${part.kind === "same" ? "" : ` df-${op[part.kind]}`}` },
            children: [...signMarks(op[part.kind]), text],
        })));
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
    /** 変わった図に、色・凡例と消したもの・Raw の行ごとの差分を付ける。前の版の図を描けない・色を付けない種類・突き合わせを打ち切ったときは、図の枠に色を付ける */
    async function decorateDiagram({ figure, beforeSource }) {
        const holder = figure.querySelector(".mermaid");
        const afterSource = holder?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
        figure.classList.add("df-changed", "df-frame");
        // Raw: 記法の行ごとの差分（打ち切ったときは今の記法のまま）
        const raw = figure.querySelector(":scope > .dg-raw");
        const parts = MindmapPreview.diffLineParts(withTrailingNewline(beforeSource), withTrailingNewline(afterSource));
        if (raw !== null && parts !== null) {
            raw.classList.add("df-raw");
            raw.replaceChildren(...rawDiffLines(parts));
        }
        const type = diagramType(afterSource);
        const afterSvg = holder?.querySelector("svg") ?? null;
        let colored = false;
        let removed = [];
        if (afterSvg !== null && MindmapPreview.COLORED_DIAGRAM_TYPES.includes(type) && beforeSource.trim() !== "") {
            const beforeSvg = await MindmapPreview.renderDiagramSvg(beforeSource);
            if (beforeSvg !== null) {
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
                if (diagram !== null) {
                    for (const element of diagram.added)
                        paintDiagramElement({ element, mode: "add" });
                    for (const element of diagram.changed)
                        paintDiagramElement({ element, mode: "chg" });
                    removed = diagram.removed;
                    colored = true;
                }
            }
        }
        figure.classList.toggle("df-frame", !colored);
        figure.classList.toggle("df-colored", colored);
        figure.append(diagramNotes({ colored, removed }));
        // 図の拡大が、同じ凡例と Raw の差分を出せるようになる
        figure.setAttribute(BEFORE_SOURCE_ATTR, beforeSource);
    }
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
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on, reviews, view }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "detail" } });
        if (entry === undefined)
            return body;
        const { kind } = entry;
        const item = view?.shown ?? entry.item;
        const keys = view?.keys ?? null;
        const related = MindmapPreview.relatedItems({ id, index });
        /** キーの値。変わっていれば前の値と今の値を並べる */
        const textOf = (key, value) => (keys?.has(key) === true ? keys.show(key) : value);
        const labelled = (label, key, value) => {
            const changed = keys?.has(key) === true;
            if ((value === undefined || value === "") && !changed)
                return null;
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: changed ? "d-answer df-key" : "d-answer" },
                children: [MindmapPreview.h({ tag: "b", children: [label] }), valueSpan(key, [textOf(key, value)])],
            });
        };
        /** 見出しの下の 1 段落 */
        const lead = (key, value, className) => {
            if ((value === undefined || value === "") && keys?.has(key) !== true)
                return null;
            return MindmapPreview.h({ tag: "p", attrs: { class: className, [MindmapPreview.VALUE_KEY_ATTR]: key }, children: [textOf(key, value)] });
        };
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす。差分の表示の間は、本文と図の差分を重ねる */
        const bodySection = (label) => {
            const source = view?.body ?? index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            let rendered = null;
            let notice = null;
            let diagramBefore = null;
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
                    rendered = renderBodyDiff({ before: versions.beforeBody, after: source });
                    if (rendered === null)
                        notice = noteBox(NOTE_BODY_TOO_LARGE);
                }
            }
            const root = rendered ?? MindmapPreview.renderMarkdown(source);
            if (rendered === null)
                lowerHeadings(root);
            // 古いまとまりを選び、その後に本文を直した: 描いた本文は今の本文の行と合わないので、行の印を外す（選んだ箇所のコメントも示す箇所も今の行に向けない）
            if (source !== index.data.bodies[item.body ?? ""])
                withoutLineMarks(root);
            const drawn = MindmapPreview.renderDiagrams(root);
            if (diagramBefore !== null) {
                const before = diagramBefore;
                void drawn.then(() => decorateDiagrams({ root, before }));
            }
            root.addEventListener("click", (event) => {
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
            });
            const content = document.createDocumentFragment();
            content.append(...(notice === null ? [] : [notice]), root);
            return section(label, content);
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
                        keys?.has("title") === true ? keys.show("title") : item.title,
                        item.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                        view?.kind === "new" ? MindmapPreview.diffMark({ kind: "new", labeled: true }) : null,
                    ],
                }),
                metaList({ item, settings: index.data.settings, diff: keys }),
            ],
        });
        if (kind === "decisions") {
            const previous = keys?.has("options") === true ? (keys.before.options ?? []) : null;
            MindmapPreview.append({
                parent: body,
                children: [
                    lead("lead", item.lead, "d-lead"),
                    labelled("決定内容", "answer", item.answer),
                    labelled("理由", "reason", item.reason),
                    (item.options ?? []).length > 0 || previous !== null ? section("案", optionCards(item.options ?? [], previous)) : null,
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
                    lead("question", item.question, "d-lead"),
                    labelled("結論", "conclusion", item.conclusion),
                    listSection("調査の観点", "angles", item.angles),
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
                    listSection("別名", "aliases", item.aliases),
                    listSection("使わない表記", "avoid", item.avoid),
                ],
            });
        }
        else if (kind === "notes") {
            MindmapPreview.append({ parent: body, children: [lead("content", item.content, null)] });
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
                reviews === null ? null : reviewSection(reviews),
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
    /** コメントの一覧から開いたとき、そのコメントの箇所に印の色の地を付け、描いた後にその箇所までスクロールする。合わなければ示さず、項目の先頭を出す */
    function applyHighlight({ root, loc }) {
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
        for (const element of hits)
            element.classList.add("loc-hit");
        // 文書に入れた後でないとスクロールできない
        const target = hits[0];
        if (target !== undefined)
            requestAnimationFrame(() => target.scrollIntoView({ block: "center" }));
    }
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on, comment, highlight = null, diff = null } = props;
        const kind = index.byId.get(id)?.kind;
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-body" },
            children: [detailBody({ id, index, on, reviews: comment === null ? null : comment.reviews, view: resolveDiffView({ id, index, diff }) })],
        });
        const head = detailHead(props);
        // 見出しと下端の入力の間の本文だけをスクロールする
        const footer = comment === null ? null : MindmapPreview.sendForm(comment.form);
        let root;
        if (!full) {
            root = MindmapPreview.h({
                tag: "aside",
                attrs: { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" },
                children: [head, body, footer],
            });
        }
        else {
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
            root = dialog;
        }
        if (highlight !== null)
            applyHighlight({ root, loc: highlight });
        return root;
    }
    MindmapPreview.detailPanel = detailPanel;
})(MindmapPreview || (MindmapPreview = {}));
