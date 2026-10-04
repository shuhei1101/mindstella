"use strict";
// 描画のライブラリ（marked・DOMPurify・elkjs・mermaid）の有無と呼び出し。読めなかったときは名前を出し、代わりの読み込みはしない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 描画のライブラリの名前 → 読めたときに置かれるグローバルの名前 */
    MindmapPreview.LIBRARIES = {
        marked: "marked",
        DOMPurify: "DOMPurify",
        elkjs: "ELK",
        mermaid: "mermaid",
    };
    /** 図の入れ物が原文を持つ属性の名前 */
    MindmapPreview.DIAGRAM_SOURCE_ATTR = "data-source";
    /** 渡したライブラリのうち、グローバルが無いものの名前を返す（渡した順） */
    function missingLibraries(names) {
        return names.filter((name) => Reflect.get(window, MindmapPreview.LIBRARIES[name]) === undefined);
    }
    MindmapPreview.missingLibraries = missingLibraries;
    /** 読めなかったライブラリの名前を出す知らせの要素を返す */
    function libraryNotice({ names, what }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "lib-error", role: "alert" },
            children: [
                MindmapPreview.h({ tag: "span", children: [`${what}を表示できません。読み込めなかったライブラリ: ${names.join("・")}`] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["通信を確認して、ページを再読み込みしてください。"] }),
            ],
        });
    }
    MindmapPreview.libraryNotice = libraryNotice;
    // ─── 本文の行の印 ───
    /** 本文のブロックの要素が持つ、元の Markdown の先頭の行（1 始まり）の属性 */
    MindmapPreview.LINE_ATTR = "data-line-start";
    /** 改行の数を返す */
    function countNewlines(text) {
        return text.split("\n").length - 1;
    }
    /** token の並びに、先頭の行から raw の改行を足し進めた行を持たせる（リストの項目・引用の中も同じ） */
    function assignLines({ tokens, start }) {
        let line = start;
        for (const token of tokens) {
            token.line = line;
            if (token.type === "list" && token.items) {
                assignLines({ tokens: token.items, start: line });
            }
            else if ((token.type === "list_item" || token.type === "blockquote") && token.tokens) {
                // 項目の中の token は字下げを外した raw を持つが、改行の数は元と同じ
                assignLines({ tokens: token.tokens, start: line });
            }
            line += countNewlines(token.raw);
        }
    }
    /** token が持つ行を返す */
    function lineOf(token) {
        return token.line;
    }
    /** 描いた HTML の最初の開きタグに、行の印を足す */
    function withLine(html, line) {
        if (line === undefined)
            return html;
        return html.replace(/^<(\w+)/, `<$1 ${MindmapPreview.LINE_ATTR}="${line + 1}"`);
    }
    /** 本文の Markdown を、空行を持たないブロックごとに行の印を付けて HTML に描く */
    function renderWithLines(source) {
        const tokens = marked.lexer(source);
        assignLines({ tokens: tokens, start: 0 });
        const renderer = new marked.Renderer();
        const base = {
            heading: renderer.heading.bind(renderer),
            paragraph: renderer.paragraph.bind(renderer),
            code: renderer.code.bind(renderer),
            listitem: renderer.listitem.bind(renderer),
            table: renderer.table.bind(renderer),
        };
        renderer.heading = (token) => withLine(base.heading(token), lineOf(token));
        renderer.paragraph = (token) => withLine(base.paragraph(token), lineOf(token));
        // mermaid の図は印を付けない（図の中の選択を本文の外として扱う）
        // フェンスで囲んだコードは、中身がフェンスの次の行から始まる
        renderer.code = (token) => {
            if (token.lang === "mermaid")
                return base.code(token);
            const line = lineOf(token);
            const fence = token.codeBlockStyle === "indented" ? 0 : 1;
            return withLine(base.code(token), line === undefined ? undefined : line + fence);
        };
        // 段落を持つ項目は中の段落が印を持つので、段落を持たない項目だけ li に付ける
        renderer.listitem = (item) => (item.loose ? base.listitem(item) : withLine(base.listitem(item), lineOf(item)));
        // 表は行ごとに 1 行。見出しの行の次に区切りの行がある
        renderer.table = (token) => {
            const start = lineOf(token);
            if (start === undefined)
                return base.table(token);
            let row = 0;
            return base.table(token).replace(/<tr>/g, () => {
                const line = row === 0 ? start : start + 1 + row;
                row += 1;
                return `<tr ${MindmapPreview.LINE_ATTR}="${line + 1}">`;
            });
        };
        return marked.parser(tokens, { renderer });
    }
    MindmapPreview.renderWithLines = renderWithLines;
    /** 印を持つブロックの先頭から、選択の端までにある改行（文の \n と br）の数を返す */
    function linesBefore({ block, node, offset }) {
        // 表の行は 1 行で、セルの間の空白の改行は数えない
        if (block.tagName === "TR")
            return 0;
        const range = document.createRange();
        range.setStart(block, 0);
        range.setEnd(node, offset);
        const fragment = range.cloneContents();
        return countNewlines(fragment.textContent ?? "") + fragment.querySelectorAll("br").length;
    }
    /** 選択の端から、本文の中で印を持つ最も近いブロックを返す（本文の外なら null） */
    function lineBlock(node) {
        const element = node instanceof Element ? node : node.parentElement;
        const block = element?.closest(`[${MindmapPreview.LINE_ATTR}]`) ?? null;
        return block?.closest(".md") ? block : null;
    }
    /** 選んだ範囲を元の Markdown の行の範囲へ対応づける。本文の外か空の選択なら null */
    function selectionLines(range) {
        if (range.collapsed)
            return null;
        const startBlock = lineBlock(range.startContainer);
        const endBlock = lineBlock(range.endContainer);
        if (!startBlock || !endBlock)
            return null;
        const first = Number(startBlock.getAttribute(MindmapPreview.LINE_ATTR));
        const last = Number(endBlock.getAttribute(MindmapPreview.LINE_ATTR));
        return {
            start: first + linesBefore({ block: startBlock, node: range.startContainer, offset: range.startOffset }),
            end: last + linesBefore({ block: endBlock, node: range.endContainer, offset: range.endOffset }),
            text: range.toString(),
        };
    }
    MindmapPreview.selectionLines = selectionLines;
    /** 本文の Markdown を無害化した要素にする。mermaid のコードブロックは図の入れ物に置き換える */
    function renderMarkdown(source) {
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "md" } });
        const missing = missingLibraries(["marked", "DOMPurify"]);
        const hasDiagram = source.includes("```mermaid");
        // marked か DOMPurify が読めていない: 知らせと原文を出す
        if (missing.length > 0) {
            const names = [...missing];
            if (hasDiagram && missingLibraries(["mermaid"]).length > 0)
                names.push("mermaid");
            root.append(libraryNotice({ names, what: "本文" }), MindmapPreview.h({ tag: "pre", attrs: { class: "md-raw" }, children: [source] }));
            return root;
        }
        // 描いた HTML は無害化してから差し込む（記録は利用者のもの）
        root.innerHTML = DOMPurify.sanitize(renderWithLines(source));
        // mermaid のコードブロックを、原文を持つ図の入れ物（拡大・Raw・コピーの道具つき）に置き換える
        for (const code of root.querySelectorAll("code.language-mermaid")) {
            const original = code.textContent ?? "";
            const figure = MindmapPreview.h({
                tag: "figure",
                attrs: { class: "diagram" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "dg-tools" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "icon-btn", type: "button", "data-act": "diagram-zoom", "aria-label": "図を拡大表示", title: "拡大表示" },
                                children: [MindmapPreview.icon("expand")],
                            }),
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "btn ghost", type: "button", "data-act": "diagram-raw", "aria-pressed": "false" },
                                children: ["Raw"],
                            }),
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "icon-btn", type: "button", "data-act": "diagram-copy", "aria-label": "原文をコピー", title: "コピー" },
                                children: [MindmapPreview.icon("copy")],
                            }),
                        ],
                    }),
                    MindmapPreview.h({ tag: "div", attrs: { class: "mermaid", [MindmapPreview.DIAGRAM_SOURCE_ATTR]: original } }),
                    MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw", hidden: true }, children: [original] }),
                ],
            });
            (code.closest("pre") ?? code).replaceWith(figure);
        }
        return root;
    }
    MindmapPreview.renderMarkdown = renderMarkdown;
    /** mermaid を初期化したときの、地の色（変わったら初期化し直す） */
    let initializedFor = null;
    /** 図の ID を作る連番 */
    let diagramCounter = 0;
    /** 色の値をトークンから引く */
    function token(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    /** 要素の中の図の入れ物を mermaid で SVG に描く。描けない図は原文を残し、ほかの図は続ける */
    async function renderDiagrams(root) {
        const containers = [...root.querySelectorAll(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)];
        // mermaid が読めていない: 各入れ物に知らせと原文を入れる
        if (missingLibraries(["mermaid"]).length > 0) {
            for (const container of containers) {
                container.replaceChildren(libraryNotice({ names: ["mermaid"], what: "図" }), MindmapPreview.h({
                    tag: "pre",
                    attrs: { class: "dg-raw" },
                    children: [container.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? ""],
                }));
            }
            return;
        }
        // 初めて描くとき（と、テーマが変わったとき）に、トークンの色で初期化する
        const surface = token("--surface");
        if (initializedFor !== surface) {
            // 図の変数 → 色のトークン（トークンが無い文書では、mermaid の既定の色に任せる）
            const colorTokens = {
                background: "--surface",
                primaryColor: "--surface-2",
                primaryTextColor: "--text",
                primaryBorderColor: "--border",
                secondaryColor: "--surface-2",
                tertiaryColor: "--surface",
                lineColor: "--text-2",
                textColor: "--text",
                edgeLabelBackground: "--surface",
                clusterBkg: "--surface-2",
                clusterBorder: "--border",
            };
            const themeVariables = Object.fromEntries(Object.entries(colorTokens)
                .map(([variable, name]) => [variable, token(name)])
                .filter(([, color]) => color !== ""));
            mermaid.initialize({
                startOnLoad: false,
                securityLevel: "strict",
                theme: "base",
                fontFamily: "Noto Sans JP, sans-serif",
                themeVariables,
            });
            initializedFor = surface;
        }
        for (const container of containers) {
            const source = container.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            const id = `mindmap-diagram-${(diagramCounter += 1)}`;
            try {
                const { svg } = await mermaid.render(id, source);
                container.innerHTML = svg;
            }
            catch {
                // 描けなかった図: mermaid が body に残した作業用の要素を消し、描けなかったことと原文を入れる
                document.getElementById(`d${id}`)?.remove();
                document.getElementById(id)?.remove();
                container.replaceChildren(MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: ["この図は表示できませんでした。原文を表示します。"] }), MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
            }
        }
    }
    MindmapPreview.renderDiagrams = renderDiagrams;
})(MindmapPreview || (MindmapPreview = {}));
