"use strict";
// 描画のライブラリ（mdmark・marked・elkjs・mermaid）と差分のライブラリ（jsdiff）の読み込み・有無と呼び出し、選んだ範囲から箇所を求める処理。読めなかったときは名前を出し、代わりの読み込みはしない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 描画のライブラリの名前 → 読めたときに置かれるグローバルの名前 */
    MindmapPreview.LIBRARIES = {
        mdmark: "mdmark",
        marked: "marked",
        elkjs: "ELK",
        mermaid: "mermaid",
        jsdiff: "Diff",
    };
    /** 図の入れ物が原文を持つ属性の名前 */
    MindmapPreview.DIAGRAM_SOURCE_ATTR = "data-source";
    /** `mdmark.mount` の `config.features` に渡す、プレビューの画面と重なる機能と、コードの色付け（`syntax`。配信元から highlight.js を `integrity` なしで読む）のオフ（`code`・`html`・`diagrams` は既定のまま） */
    MindmapPreview.MDMARK_FEATURES = {
        glossary: false,
        backlinks: false,
        comments: false,
        print: false,
        anchors: false,
        sections: false,
        table: false,
        toc: false,
        views: false,
        syntax: false,
    };
    /** mdmark の操作できる部品の今の値をコピーするボタン（`.mdmark-param-copy`）に出す文言 */
    MindmapPreview.MDMARK_PARAM_COPY_LABEL = "今の値をコピー";
    /** 配る書き出しが mdmark の JavaScript を中身に持つ要素の id */
    MindmapPreview.MDMARK_EMBEDDED_ID = "mindmap-mdmark";
    /** 雛形の import map（`script[type="importmap"]`）の `integrity` のただ 1 つのキー（mdmark の JavaScript の URL）と、その `integrity` を返す。import map が無いか読めないか、キーが 1 つでないときは null */
    function mdmarkImportMapEntry() {
        const script = document.querySelector('script[type="importmap"]');
        if (script === null)
            return null;
        try {
            const entries = Object.entries(JSON.parse(script.textContent ?? "").integrity ?? {});
            const [only] = entries;
            return entries.length === 1 && only !== undefined ? { url: only[0], integrity: only[1] } : null;
        }
        catch {
            // JSON として読めない import map は、読めなかったものとして扱う
            return null;
        }
    }
    MindmapPreview.mdmarkImportMapEntry = mdmarkImportMapEntry;
    /** mdmark の JavaScript を読み、読めたらグローバルの `mdmark` に置く。配る書き出しは中身を持つ要素（`#mindmap-mdmark`）を Blob の URL にして読み、サーバーの配信は import map の URL をブラウザが `integrity` で確かめて読む。読めなくても拒否せず解決する（読めなかったことは `missingLibraries` が伝える） */
    async function loadMdmark() {
        const embedded = document.getElementById(MindmapPreview.MDMARK_EMBEDDED_ID);
        try {
            let loaded;
            if (embedded !== null) {
                const url = URL.createObjectURL(new Blob([embedded.textContent ?? ""], { type: "text/javascript" }));
                try {
                    loaded = (await import(url));
                }
                finally {
                    URL.revokeObjectURL(url);
                }
            }
            else {
                const entry = mdmarkImportMapEntry();
                // import map が無いか読めない
                if (entry === null)
                    return;
                loaded = (await import(entry.url));
            }
            Reflect.set(window, MindmapPreview.LIBRARIES.mdmark, loaded);
        }
        catch {
            // `import()` の拒否（取れない・`integrity` が合わない）は、グローバルを置かずに解決する
        }
    }
    MindmapPreview.loadMdmark = loadMdmark;
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
    /** Markdown の中の `html` のコードブロックを置き換えた、HTML の本文の枠の入れ物の class */
    MindmapPreview.HTML_BLOCK_CLASS = "html-block";
    /** 本文の表を包む、表の中だけで横に送る入れ物の class */
    MindmapPreview.TABLE_WRAP_CLASS = "md-table-wrap";
    /** HTML の本文の開きタグが持つ、中身が始まる元の HTML の行（1 始まり）の属性。サーバーが足す */
    MindmapPreview.HTML_LINE_ATTR = "data-line";
    /** 開きタグの直後の改行を、解析のときに取り除く要素 */
    const LEADING_NEWLINE_TAGS = ["PRE", "TEXTAREA", "LISTING"];
    /** 項目の値を描いた要素が持つ、項目のキーのパスの属性 */
    MindmapPreview.VALUE_KEY_ATTR = "data-key";
    /** mdmark が描いたブロックが持つ、元の Markdown のブロックの開始の行（0 始まり）の属性 */
    const SOURCE_LINE_ATTR = "data-source-line";
    /** mdmark が描いた、埋め込んだ HTML の範囲の要素の class */
    MindmapPreview.EMBEDDED_HTML_CLASS = "mdmark-html";
    /** 埋め込んだ HTML の範囲の要素が持つ、範囲の始まりの印 `<!-- html -->` の行（1 始まり）の属性 */
    MindmapPreview.HTML_OPEN_ATTR = "data-html-open";
    /** 埋め込んだ HTML の範囲の要素が持つ、範囲の終わりの印 `<!-- /html -->` の行（1 始まり）の属性 */
    MindmapPreview.HTML_CLOSE_ATTR = "data-html-close";
    /** 行全体が `<!-- html -->` の範囲の始まりの印（間の空白を許す） */
    const EMBEDDED_HTML_OPEN_LINE = /^\s*<!--\s*html\s*-->\s*$/;
    /** 行全体が `<!-- /html -->` の範囲の終わりの印（間の空白を許す） */
    const EMBEDDED_HTML_CLOSE_LINE = /^\s*<!--\s*\/html\s*-->\s*$/;
    /** 元の行の印（`data-line-start`）を付けるブロックの要素 */
    const LINE_MARK_TAGS = new Set(["H1", "H2", "H3", "H4", "H5", "H6", "P", "LI", "TR", "PRE"]);
    /** 開始の行の行頭の空白・引用の `>`・リストのマーカーを除いた先が、フェンス（```` ``` ```` か `~~~`）で始まる行 */
    const FENCE_LINE = /^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*(```|~~~)/;
    /** 改行の数を返す */
    function countNewlines(text) {
        return text.split("\n").length - 1;
    }
    /** mdmark が付けた `data-source-line`（0 始まり）を元の行の印 `data-line-start`（1 始まり。フェンスのコードは中身の最初の行）に読み替え、全ての `data-source-line` を外す。段落を持つリストの項目は中の段落が印を持つので付けない */
    function convertSourceLines({ root, source }) {
        const lines = source.split("\n");
        for (const element of root.querySelectorAll(`[${SOURCE_LINE_ATTR}]`)) {
            const start = Number(element.getAttribute(SOURCE_LINE_ATTR));
            element.removeAttribute(SOURCE_LINE_ATTR);
            if (!LINE_MARK_TAGS.has(element.tagName))
                continue;
            if (element.tagName === "LI" && element.querySelector(":scope > p") !== null)
                continue;
            const fence = element.tagName === "PRE" && FENCE_LINE.test(lines[start] ?? "") ? 1 : 0;
            element.setAttribute(MindmapPreview.LINE_ATTR, String(start + 1 + fence));
        }
    }
    /** 要素の中に、機能を止めた mdmark で Markdown を描く（描き直しは要素ごと作り直すので、返る `update`・`destroy` は使わない） */
    function mountMarkdown({ root, markdown }) {
        mdmark.mount(root, { markdown, config: { features: MindmapPreview.MDMARK_FEATURES } });
        trimBreakNewlines(root);
        relabelParamCopy(root);
    }
    /** 引用の `>` を除いた先が `[!{英字}]` だけの Alert の種類の行（後ろに `-` を許す）。mdmark はこの行の後ろが強制改行だと Alert にしない */
    const ALERT_MARKER_LINE = /^[ \t]*(?:>[ \t]*)+\[![A-Za-z]+\]-?[ \t]*$/;
    /** `br` の直後の改行の文字を取り除く（mdmark は強制改行を `<br>` と改行の文字で描くので、改行の数え方が `br` の分と二重になる） */
    function trimBreakNewlines(root) {
        for (const br of root.querySelectorAll("br")) {
            const next = br.nextSibling;
            if (next?.nodeType !== Node.TEXT_NODE || !(next.textContent ?? "").startsWith("\n"))
                continue;
            next.textContent = (next.textContent ?? "").slice(1);
            if (next.textContent === "")
                next.remove();
        }
    }
    /** フェンスと字下げのコードの外で、次の行が空行でない行の末尾に空白 2 つを足した Markdown を返す（mdmark は `breaks` を持たないため、段落の中の 1 つの改行を `br` にする。Alert の種類の行は足さない）。行の数は変えない */
    function withHardBreaks(source) {
        const lines = source.split("\n");
        // 開いているフェンスの記号と、閉じるのに要る数
        let fence = null;
        // 直前の行が空行か字下げのコードの行（字下げのコードを始められる）
        let codeMayStart = true;
        return lines
            .map((line, index) => {
            const stripped = line.replace(/^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*/, "");
            // フェンスの中と、フェンスの行（開く行・閉じる行）はそのまま残す
            if (fence !== null) {
                if (new RegExp(`^${fence.symbol}{${fence.count},}[ \\t]*$`).test(stripped))
                    fence = null;
                return line;
            }
            const opened = /^(`{3,}|~{3,})/.exec(stripped);
            if (opened !== null) {
                fence = { symbol: opened[1][0], count: opened[1].length };
                return line;
            }
            // 字下げのコードの行はそのまま残す
            const indented = codeMayStart && /^( {4}|\t)/.test(line);
            codeMayStart = line.trim() === "" || indented;
            if (indented || line.trim() === "")
                return line;
            // Alert の種類の行はそのまま残す
            if (ALERT_MARKER_LINE.test(line))
                return line;
            // 次の行があり、空白だけの行でなければ強制改行にする
            const next = lines[index + 1];
            return next !== undefined && next.trim() !== "" ? `${line}  ` : line;
        })
            .join("\n");
    }
    MindmapPreview.withHardBreaks = withHardBreaks;
    /** Markdown の本文の中の `<!-- html -->` 〜 `<!-- /html -->` の範囲を、本文の中の並びの順に印の行（1 始まり）で返す。フェンスの中の印は範囲にせず、閉じていない始まりは範囲にしない */
    function embeddedHtmlRanges(source) {
        const ranges = [];
        // 開いているフェンスの記号と、閉じるのに要る数
        let fence = null;
        // 開いている範囲の始まりの行
        let open = null;
        source.split("\n").forEach((line, index) => {
            const stripped = line.replace(/^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*/, "");
            // フェンスの中は印を探さない。閉じる行でフェンスを終える
            if (fence !== null) {
                if (new RegExp(`^${fence.symbol}{${fence.count},}[ \\t]*$`).test(stripped))
                    fence = null;
                return;
            }
            const opened = /^(`{3,}|~{3,})/.exec(stripped);
            if (opened !== null) {
                fence = { symbol: opened[1][0], count: opened[1].length };
                return;
            }
            if (open === null && EMBEDDED_HTML_OPEN_LINE.test(line))
                open = index + 1;
            else if (open !== null && EMBEDDED_HTML_CLOSE_LINE.test(line)) {
                ranges.push({ open, close: index + 1 });
                open = null;
            }
        });
        return ranges;
    }
    MindmapPreview.embeddedHtmlRanges = embeddedHtmlRanges;
    /** 見張りを付け済みの本文（同じ本文に 2 回当てても見張りを重ねない） */
    const relabeledRoots = new WeakSet();
    /** 今の値をコピーするボタンの文言を `MDMARK_PARAM_COPY_LABEL` に替える。アイコンの要素は残し、文字のノードだけを置き換える（文言が同じボタンは触らない） */
    function relabelButton(button) {
        const texts = [...button.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);
        if (texts.length === 1 && texts[0].textContent === MindmapPreview.MDMARK_PARAM_COPY_LABEL)
            return;
        for (const text of texts)
            text.remove();
        button.append(document.createTextNode(MindmapPreview.MDMARK_PARAM_COPY_LABEL));
    }
    /** mdmark が描いた部品の今の値をコピーするボタンの文言を替える。部品が描き直したボタンにも当てるため、本文の子孫の追加を見張る */
    function relabelParamCopy(root) {
        for (const button of root.querySelectorAll(".mdmark-param-copy"))
            relabelButton(button);
        if (relabeledRoots.has(root))
            return;
        relabeledRoots.add(root);
        new MutationObserver((records) => {
            for (const record of records) {
                for (const added of record.addedNodes) {
                    if (!(added instanceof Element))
                        continue;
                    if (added.matches(".mdmark-param-copy"))
                        relabelButton(added);
                    for (const button of added.querySelectorAll(".mdmark-param-copy"))
                        relabelButton(button);
                }
            }
        }).observe(root, { childList: true, subtree: true });
    }
    MindmapPreview.relabelParamCopy = relabelParamCopy;
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
    /** 選択の端から、本文の中で行の印（`data-html-open`）を持つ埋め込んだ HTML の範囲の要素を返す（範囲の中でなければ null） */
    function embeddedHtmlElement(node) {
        const element = node instanceof Element ? node : node.parentElement;
        const range = element?.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}[${MindmapPreview.HTML_OPEN_ATTR}]`) ?? null;
        return range?.closest(".md") ? range : null;
    }
    /** 選んだ範囲を、本文なら元の Markdown の行の範囲、値ならキーのパスの箇所にする。本文と値の外・空の選択は null */
    function selectionLocation(range) {
        if (range.collapsed)
            return null;
        const text = range.toString().trim();
        // 文が空白だけ
        if (text === "")
            return null;
        // 始点と終点が同じ値の中: 値の箇所
        const startKey = keyElement(range.startContainer);
        if (startKey !== null && startKey === keyElement(range.endContainer)) {
            return { kind: "value", key: startKey.getAttribute(MindmapPreview.VALUE_KEY_ATTR) ?? "", text };
        }
        const startRange = embeddedHtmlElement(range.startContainer);
        const endRange = embeddedHtmlElement(range.endContainer);
        const startBlock = startRange === null ? lineBlock(range.startContainer) : null;
        const endBlock = endRange === null ? lineBlock(range.endContainer) : null;
        // 本文の外（端が埋め込んだ HTML の範囲の中なら、範囲の印の行がある）
        if ((startRange === null && !startBlock) || (endRange === null && !endBlock))
            return null;
        // 範囲の中の始点は範囲の始まりの印の行、終点は終わりの印の行にする。それ以外は、印を持つブロックの行に端までの改行の数を足す
        const start = startRange !== null
            ? Number(startRange.getAttribute(MindmapPreview.HTML_OPEN_ATTR))
            : Number(startBlock.getAttribute(MindmapPreview.LINE_ATTR)) + linesBefore({ block: startBlock, node: range.startContainer, offset: range.startOffset });
        const end = endRange !== null
            ? Number(endRange.getAttribute(MindmapPreview.HTML_CLOSE_ATTR))
            : Number(endBlock.getAttribute(MindmapPreview.LINE_ATTR)) + linesBefore({ block: endBlock, node: range.endContainer, offset: range.endOffset });
        return { kind: "body", start, end, text };
    }
    MindmapPreview.selectionLocation = selectionLocation;
    /** 文書の順で端より前にある、行の印（`data-line`）を持つ要素のうち最も後のものを返す（無ければ null） */
    function htmlLineElement({ doc, node, offset }) {
        const probe = doc.createRange();
        probe.setStart(node, offset);
        probe.collapse(true);
        let found = null;
        for (const element of doc.querySelectorAll(`[${MindmapPreview.HTML_LINE_ATTR}]`)) {
            // 要素の先頭が端より前（端と同じ位置を含む）にあるものだけが候補
            if (probe.comparePoint(element, 0) > 0)
                break;
            found = element;
        }
        return found;
    }
    /** 行の印を持つ要素の開きタグの直後から端までにある改行（文とコメントの中の改行。`br` は数えない）の数を返す */
    function htmlLinesBefore({ element, node, offset }) {
        const range = element.ownerDocument.createRange();
        range.setStart(element, 0);
        range.setEnd(node, offset);
        const fragment = range.cloneContents();
        let count = countNewlines(fragment.textContent ?? "");
        // コメントは textContent に入らないので、中の改行を足す
        const walker = element.ownerDocument.createTreeWalker(fragment, NodeFilter.SHOW_COMMENT);
        while (walker.nextNode())
            count += countNewlines(walker.currentNode.data);
        return count;
    }
    /** `pre`・`textarea`・`listing` の開きタグの直後に改行があるとき 1（その改行は解析のときに取り除かれる）を返す */
    function leadingNewlineBefore({ element, source }) {
        if (!LEADING_NEWLINE_TAGS.includes(element.tagName))
            return 0;
        const line = source.split("\n")[Number(element.getAttribute(MindmapPreview.HTML_LINE_ATTR)) - 1] ?? "";
        return /<(?:pre|textarea|listing)\b[^>]*>\r?$/i.test(line) ? 1 : 0;
    }
    /** HTML の本文の枠の中で選んだ範囲を、元の HTML の行の範囲の箇所にする。空の選択・端より前に行の印を持つ要素が無い選択は null */
    function htmlSelectionLocation(range, source) {
        if (range.collapsed)
            return null;
        const text = range.toString().trim();
        // 文が空白だけ
        if (text === "")
            return null;
        const doc = range.startContainer.ownerDocument ?? range.startContainer;
        const startElement = htmlLineElement({ doc, node: range.startContainer, offset: range.startOffset });
        const endElement = htmlLineElement({ doc, node: range.endContainer, offset: range.endOffset });
        // 端より前に行の印を持つ要素が無い
        if (startElement === null || endElement === null)
            return null;
        const lineOfBoundary = (element, node, offset) => Number(element.getAttribute(MindmapPreview.HTML_LINE_ATTR)) +
            htmlLinesBefore({ element, node, offset }) +
            leadingNewlineBefore({ element, source });
        return {
            kind: "body",
            start: lineOfBoundary(startElement, range.startContainer, range.startOffset),
            end: lineOfBoundary(endElement, range.endContainer, range.endOffset),
            text,
        };
    }
    MindmapPreview.htmlSelectionLocation = htmlSelectionLocation;
    /** HTML の本文の枠の中のリンクのうち、新しいタブで開く URL のスキーム（`URL` の `protocol` の形） */
    MindmapPreview.HTML_LINK_OPEN_SCHEMES = ["http:", "https:", "mailto:"];
    /** HTML の本文の枠の中のリンクの `href`（書かれたままの値）から、新しいタブで開く・本文の中の場所まで送る・何もしないのどれかを決める */
    function htmlLinkAction(href) {
        const value = href.trim();
        // `#` で始まる: 本文の中の場所を指す。`#` の後ろを戻した id を送り先にする
        if (value.startsWith("#")) {
            const encoded = value.slice(1);
            let id = encoded;
            try {
                id = decodeURIComponent(encoded);
            }
            catch {
                // 戻せない（`%` の後ろが不正）ときは、書かれたままを id にする
            }
            return id === "" ? { kind: "none" } : { kind: "anchor", id };
        }
        // それだけで絶対の URL として読めない（相対の URL）
        if (!URL.canParse(value))
            return { kind: "none" };
        const url = new URL(value);
        // 開くスキーム以外（`javascript:`・`data:`・`file:` ほか）
        if (!MindmapPreview.HTML_LINK_OPEN_SCHEMES.includes(url.protocol))
            return { kind: "none" };
        return { kind: "open", url: url.href };
    }
    MindmapPreview.htmlLinkAction = htmlLinkAction;
    /** 選択の端から、値のキーのパスを持つ最も近い要素を返す（無ければ null） */
    function keyElement(node) {
        const element = node instanceof Element ? node : node.parentElement;
        return element?.closest(`[${MindmapPreview.VALUE_KEY_ATTR}]`) ?? null;
    }
    /** 項目の文字列の値の Markdown を、段落の中の改行も改行にして mdmark で描いた要素にする。mdmark が読めないときは、改行を残した文字のままの要素にする（知らせは本文の描画が出す） */
    function renderValue(source) {
        if (missingLibraries(["mdmark"]).length > 0) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "md-value-raw" }, children: [source] });
        }
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "md md-value" } });
        // mdmark は描くときに無害化する（記録は利用者のもの）。行の印は付けず、mermaid のコードブロックも図にしない
        mountMarkdown({ root, markdown: withHardBreaks(source) });
        for (const element of root.querySelectorAll(`[${SOURCE_LINE_ATTR}]`))
            element.removeAttribute(SOURCE_LINE_ATTR);
        return root;
    }
    MindmapPreview.renderValue = renderValue;
    /** 本文の Markdown を mdmark で描いた要素にする（mdmark が描くときに無害化する）。ブロックに元の行の印を付け、mermaid のコードブロックは図の入れ物に、`html` のコードブロックは HTML の本文の枠の入れ物に置き換え、表は横に送れる要素で包む */
    function renderMarkdown(source) {
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "md" } });
        const missing = missingLibraries(["mdmark"]);
        const hasDiagram = source.includes("```mermaid");
        // mdmark が読めていない: 知らせと原文を出す
        if (missing.length > 0) {
            const names = [...missing];
            if (hasDiagram && missingLibraries(["mermaid"]).length > 0)
                names.push("mermaid");
            root.append(libraryNotice({ names, what: "本文" }), MindmapPreview.h({ tag: "pre", attrs: { class: "md-raw" }, children: [source] }));
            return root;
        }
        // mdmark は描くときに無害化する（記録は利用者のもの）
        mountMarkdown({ root, markdown: source });
        convertSourceLines({ root, source });
        // 埋め込んだ HTML の範囲は `data-source-line` を持たないので、本文の中の n 番目の範囲に、n 番目の範囲の印の行を持たせる（範囲の中の要素には行の印を付けない）
        const ranges = embeddedHtmlRanges(source);
        root.querySelectorAll(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`).forEach((element, order) => {
            const range = ranges[order];
            if (range === undefined)
                return;
            element.setAttribute(MindmapPreview.HTML_OPEN_ATTR, String(range.open));
            element.setAttribute(MindmapPreview.HTML_CLOSE_ATTR, String(range.close));
        });
        // mermaid のコードブロックを、原文を持つ図の入れ物（拡大・Raw・コピーの道具つき）に置き換える（埋め込んだ HTML の範囲の外だけ）
        for (const code of root.querySelectorAll("code.language-mermaid")) {
            if (code.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`) !== null)
                continue;
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
        // html のコードブロックを、原文と元の行の印を持つ HTML の本文の枠の入れ物に置き換える（枠を描くのは詳細の画面。埋め込んだ HTML の範囲の外だけ）
        for (const code of root.querySelectorAll("code.language-html")) {
            if (code.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`) !== null)
                continue;
            const pre = code.closest("pre") ?? code;
            const block = MindmapPreview.h({
                tag: "div",
                attrs: { class: MindmapPreview.HTML_BLOCK_CLASS, [MindmapPreview.DIAGRAM_SOURCE_ATTR]: code.textContent ?? "" },
            });
            const line = pre.getAttribute(MindmapPreview.LINE_ATTR);
            if (line !== null)
                block.setAttribute(MindmapPreview.LINE_ATTR, line);
            pre.replaceWith(block);
        }
        // 表を、表の中だけで横に送れる入れ物で包む（行の印は表の行に残し、入れ物には付けない）
        for (const table of root.querySelectorAll("table")) {
            const wrap = MindmapPreview.h({
                tag: "div",
                attrs: { class: MindmapPreview.TABLE_WRAP_CLASS, tabindex: "0", role: "group", "aria-label": "本文の表" },
            });
            table.replaceWith(wrap);
            wrap.append(table);
        }
        return root;
    }
    MindmapPreview.renderMarkdown = renderMarkdown;
    /** 見出しの文言から、見出しを指す名前を作る（前後の空白を除き、間の空白の並びを `-` 1 つにする。同じ名前の 2 つ目から `-1`・`-2` を続ける）。`seen` は同じ本文でこれまでに作った名前 → 出た回数で、呼ぶたびに書き換える */
    function headingSlug({ text, seen }) {
        const base = text.trim().replace(/\s+/g, "-");
        const count = seen.get(base) ?? 0;
        seen.set(base, count + 1);
        return count === 0 ? base : `${base}-${count}`;
    }
    MindmapPreview.headingSlug = headingSlug;
    /** 今のハッシュの `id`・`h` を替えた URL のハッシュ（キーボードとリンクのコピーで使うリンク先。押したときは使う側の移動に替える） */
    function hashWith({ id, heading }) {
        const params = new URLSearchParams(location.hash.replace(/^#/, ""));
        if (id !== undefined)
            params.set("id", id);
        if (heading === null)
            params.delete("h");
        else
            params.set("h", heading);
        return `#${params.toString()}`;
    }
    MindmapPreview.hashWith = hashWith;
    /** 描いた本文の見出しに、見出しを指す名前（`data-heading`）と右の # のリンクを付け、本文の中の `#見出し` のリンクをその見出しへの移動に、`#diff=` のリンクをまとまりの知らせにする。押したときは既定の動作を止め、見出しの名前を `onHeading` に、`diff` の値を `onChangeSet` に知らせる */
    function linkHeadings({ root, onHeading, onChangeSet, }) {
        // 本文の中の `[文言](#...)` のリンク（# のリンクを足す前の分）。`diff` の引数を持つものはまとまりのリンク、持たないものは見出しのリンクで、同じ名前の見出しがあるときだけ知らせ、無ければ何もしない
        const bodyLinks = [...root.querySelectorAll("a[href^='#']")];
        const seen = new Map();
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const text = heading.textContent ?? "";
            const slug = headingSlug({ text, seen });
            heading.dataset["heading"] = slug;
            heading.append(MindmapPreview.h({
                tag: "a",
                attrs: {
                    class: "h-link",
                    href: hashWith({ heading: slug }),
                    "aria-label": `見出し「${text.trim()}」へのリンク`,
                    onclick: (event) => {
                        event.preventDefault();
                        onHeading(slug);
                    },
                },
                children: [MindmapPreview.icon("hash")],
            }));
        }
        for (const link of bodyLinks) {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                const raw = (link.getAttribute("href") ?? "").slice(1);
                // まとまりのリンク: 見出しとしては扱わない。空・`since`・`pending` は知らせない（記録にあるまとまりかは使う側が確かめる）
                const changeSet = new URLSearchParams(raw).get("diff");
                if (changeSet !== null) {
                    if (changeSet !== "" && changeSet !== "since" && changeSet !== "pending")
                        onChangeSet(changeSet);
                    return;
                }
                let decoded = raw;
                try {
                    decoded = decodeURIComponent(raw);
                }
                catch {
                    // 戻せない文字列は、そのまま見出しの名前として探す
                }
                const slug = headingSlug({ text: decoded, seen: new Map() });
                if (root.querySelector(`[data-heading="${CSS.escape(slug)}"]`) !== null)
                    onHeading(slug);
            });
        }
    }
    MindmapPreview.linkHeadings = linkHeadings;
    /** 英数字だけの語か（前後が英数字のときと、後ろが `-` と数字のとき（`API-2` の `API`）は印にしない） */
    const ALPHANUMERIC_WORD = /^[A-Za-z0-9]+$/;
    /** 本文の印に当てる項目の種類（一致した項目とツールチップの並びもこの順） */
    MindmapPreview.MARK_KINDS = ["terms", "docs", "research"];
    /** 印を当てない祖先（`pre`・図・リンク・ボタン・見出しの中） */
    const UNMARKED_ANCESTORS = "pre, figure, a, button, svg, .mermaid, h1, h2, h3, h4, h5, h6";
    /** 項目の ID（英大文字 - 数字。前後が英数字のものは当てない） */
    const ITEM_ID_PATTERN = /(?<![A-Za-z0-9-])[A-Z]+-[0-9]+(?![0-9])/g;
    /** 本文の中の、用語の印に当てられる文字のノード（祖先が `UNMARKED_ANCESTORS` でなく、本文のブロック `block` 自身の行を持つもの）を文書の順に返す */
    function markableTextNodes(block) {
        const own = block.classList.contains(MindmapPreview.EMBEDDED_HTML_CLASS);
        const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => {
                const parent = node.parentElement;
                if (parent === null || parent.closest(UNMARKED_ANCESTORS) !== null)
                    return NodeFilter.FILTER_REJECT;
                // 入れ子のブロック（リストの項目の中のリストの項目など）の文字は、そのブロックの行に任せる
                if (!own && parent.closest(`[${MindmapPreview.LINE_ATTR}]`) !== block)
                    return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            },
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        return nodes;
    }
    /** 描いた本文の文中（埋め込んだ HTML の範囲の中を含む）の、用語集の用語のタイトルと別名、資料・調査のエイリアスを印に、記録にある項目の ID をリンクにする。語の一致と一致の前の正規化は mdmark の `collectMatches` に任せる。`pre`・図・リンク・見出しの中は飛ばし、インラインコードは中身がちょうど語か ID のときだけ当てる。押したときは既定の動作を止め、ID のリンクと用語 1 件だけに一致した印はその項目の ID を `onOpen` に知らせる（用語 2 件以上か、資料・調査にも一致した印は知らせず、ツールチップを残す使う側に任せる） */
    function linkBody({ root, index, selfId, onOpen, source, }) {
        // 語 → 一致した項目の ID（用語 → 資料 → 調査の順）。項目自身・取り下げた資料と調査・空の語は当てない
        const byWord = new Map();
        for (const kind of MindmapPreview.MARK_KINDS) {
            for (const item of index.data[kind]) {
                if (item.id === selfId || (kind !== "terms" && item.withdrawn === true))
                    continue;
                const words = kind === "terms" ? [item.title, ...(item.aliases ?? [])] : (item.aliases ?? []);
                // 同じ項目の同じ語（用語のタイトルと同じ別名を含む）は 1 つにまとめる
                for (const word of new Set(words.map((value) => value.trim()).filter((value) => value !== ""))) {
                    byWord.set(word, [...(byWord.get(word) ?? []), item.id]);
                }
            }
        }
        // 項目の印と、押したときの動き。用語 2 件以上か、資料・調査にも一致した印は、ツールチップの中のリンクで移る先を選ぶ
        const termMark = ({ text, ids }) => {
            const multi = ids.length > 1 || ids.some((id) => index.byId.get(id)?.kind !== "terms");
            return MindmapPreview.h({
                tag: "a",
                attrs: {
                    class: "term",
                    href: hashWith({ id: ids[0], heading: null }),
                    "data-id": ids[0],
                    "data-ids": ids.join(" "),
                    "aria-describedby": multi ? null : MindmapPreview.TERM_TIP_ID,
                    "aria-details": multi ? MindmapPreview.TERM_TIP_ID : null,
                    onclick: (event) => {
                        event.preventDefault();
                        if (!multi)
                            onOpen(ids[0]);
                    },
                },
                children: [text],
            });
        };
        const idMark = (id) => MindmapPreview.h({
            tag: "a",
            attrs: {
                class: "idref",
                href: hashWith({ id, heading: null }),
                "data-id": id,
                onclick: (event) => {
                    event.preventDefault();
                    onOpen(id);
                },
            },
            children: [id],
        });
        // 文字のノードの中の [開始, 終了) を、印に置き換える
        const replaceRanges = ({ node, ranges }) => {
            const text = node.data;
            const parts = [];
            let last = 0;
            for (const range of ranges) {
                parts.push(text.slice(last, range.start), range.mark);
                last = range.end;
            }
            parts.push(text.slice(last));
            node.replaceWith(...parts.filter((part) => part !== ""));
        };
        // 本文の語の位置を mdmark に求める。語ごとの用語（`meaning` が空だと照合しない）と、本文と語そのものの文書を渡す
        const words = [...byWord.keys()];
        if (words.length > 0) {
            const documents = { "self.md": source };
            const docs = [{ id: "self", path: "self.md", title: "self" }];
            words.forEach((word, order) => {
                documents[`w${order}.md`] = word;
                docs.push({ id: `w${order}`, path: `w${order}.md`, title: `w${order}` });
            });
            const terms = words.map((word, order) => ({ id: `W-${order}`, term: word, meaning: word }));
            const { byDocument } = mdmark.collectMatches({ index: { docs, terms }, documents });
            // 正規化の後に同じになる語は、まとまる先の用語に項目の ID を寄せる（用語 → 資料 → 調査の順）
            const merged = new Map();
            words.forEach((word, order) => {
                const hit = byDocument[`w${order}`]?.find((match) => match.line === 1 && match.start === 0 && match.end === word.length);
                if (hit === undefined)
                    return;
                merged.set(hit.id, [...(merged.get(hit.id) ?? []), ...(byWord.get(word) ?? [])]);
            });
            for (const [id, ids] of merged) {
                const unique = [...new Set(ids)];
                const rank = (itemId) => MindmapPreview.MARK_KINDS.indexOf((index.byId.get(itemId)?.kind ?? "terms"));
                merged.set(id, unique.sort((a, b) => rank(a) - rank(b)));
            }
            // 一致が属するブロック（埋め込んだ HTML の範囲の中の行は範囲、それ以外は行を含む最も後の `data-line-start` の要素）
            const lines = source.split("\n");
            const lineBlocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
            const rangeBlocks = [...root.querySelectorAll(`.${MindmapPreview.EMBEDDED_HTML_CLASS}[${MindmapPreview.HTML_OPEN_ATTR}]`)];
            const blockOfLine = (line) => {
                const range = rangeBlocks.find((element) => Number(element.getAttribute(MindmapPreview.HTML_OPEN_ATTR)) <= line && line <= Number(element.getAttribute(MindmapPreview.HTML_CLOSE_ATTR)));
                if (range !== undefined)
                    return range;
                let found = null;
                let foundLine = 0;
                for (const element of lineBlocks) {
                    const start = Number(element.getAttribute(MindmapPreview.LINE_ATTR));
                    if (start <= line && start >= foundLine) {
                        found = element;
                        foundLine = start;
                    }
                }
                return found;
            };
            // ブロックごとの、印に当てられる文字のノードと、前の一致の後ろの位置
            const cursors = new Map();
            const planned = new Map();
            const matches = [...(byDocument["self"] ?? [])].sort((a, b) => a.line - b.line || a.start - b.start);
            for (const match of matches) {
                const ids = merged.get(match.id);
                const block = blockOfLine(match.line);
                if (ids === undefined || block === null)
                    continue;
                const original = (lines[match.line - 1] ?? "").slice(match.start, match.end);
                let cursor = cursors.get(block);
                if (cursor === undefined) {
                    cursor = { nodes: markableTextNodes(block), at: 0, offset: 0 };
                    cursors.set(block, cursor);
                }
                // 前の一致の後ろから、元の語を探す。英数字だけの語は、前後が英数字のときと、後ろが `-` と数字のときは印にせず、次の出現を探す
                const alphanumeric = ALPHANUMERIC_WORD.test(original);
                search: for (let at = cursor.at; at < cursor.nodes.length; at += 1) {
                    const node = cursor.nodes[at];
                    for (let found = node.data.indexOf(original, at === cursor.at ? cursor.offset : 0); found !== -1; found = node.data.indexOf(original, found + 1)) {
                        const before = node.data[found - 1] ?? "";
                        const after = node.data.slice(found + original.length, found + original.length + 2);
                        if (alphanumeric && (/[A-Za-z0-9]/.test(before) || /^[A-Za-z0-9]/.test(after) || /^-[0-9]/.test(after)))
                            continue;
                        cursor.at = at;
                        cursor.offset = found + original.length;
                        const ranges = planned.get(node) ?? [];
                        ranges.push({ start: found, end: found + original.length, mark: termMark({ text: original, ids }) });
                        planned.set(node, ranges);
                        break search;
                    }
                }
            }
            for (const [node, ranges] of planned)
                replaceRanges({ node, ranges });
        }
        // インラインコードは、中身が前後の空白を除いてちょうど語のときだけ当てる（パスや識別子の一部には付けない）
        for (const code of root.querySelectorAll("code")) {
            if (code.closest("pre, figure, a, button, h1, h2, h3, h4, h5, h6") !== null)
                continue;
            const only = code.childNodes.length === 1 && code.firstChild?.nodeType === Node.TEXT_NODE ? code.firstChild : null;
            const ids = only === null ? undefined : byWord.get(only.data.trim());
            if (only === null || ids === undefined)
                continue;
            only.replaceWith(termMark({ text: only.data.trim(), ids }));
        }
        // 項目の ID は、記録にあるものだけをリンクにする（コードの中は、中身がちょうど ID のときだけ）
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => node.parentElement?.closest("pre, figure, a, button, svg, .mermaid, h1, h2, h3, h4, h5, h6") !== null
                ? NodeFilter.FILTER_REJECT
                : NodeFilter.FILTER_ACCEPT,
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        for (const node of nodes) {
            const text = node.data;
            const inCode = node.parentElement?.closest("code") !== null;
            const ranges = [];
            for (const match of text.matchAll(ITEM_ID_PATTERN)) {
                const id = match[0];
                // 記録に無い ID・項目自身の ID・コードの一部は、そのままにする
                if (!index.byId.has(id) || id === selfId || (inCode && text.trim() !== id))
                    continue;
                ranges.push({ start: match.index ?? 0, end: (match.index ?? 0) + id.length, mark: idMark(id) });
            }
            if (ranges.length > 0)
                replaceRanges({ node, ranges });
        }
    }
    MindmapPreview.linkBody = linkBody;
    /** 用語のツールチップの要素の id（用語の印の `aria-describedby` が指す） */
    MindmapPreview.TERM_TIP_ID = "term-tip";
    /** mermaid を初期化したときの、地の色（変わったら初期化し直す） */
    let initializedFor = null;
    /** 図の ID を作る連番 */
    let diagramCounter = 0;
    /** 直前の `renderDiagrams` で描いた・写した図（記法 → mermaid の出力と、その SVG の ID） */
    let lastDrawn = new Map();
    /** 図の ID を新しく振る */
    function nextDiagramId() {
        return `mindmap-diagram-${(diagramCounter += 1)}`;
    }
    /** 色の値をトークンから引く */
    function token(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    /** 初めて描くとき（と、テーマが変わったとき）に、トークンの色で mermaid を初期化する */
    function initializeMermaid() {
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
            // 古いテーマの色で描いた SVG は使い回さない
            lastDrawn = new Map();
        }
    }
    /** 記法を mermaid で SVG に描いて返す（画面には出さない）。mermaid が読めていないか、描けないときは null */
    async function renderDiagramSvg(source) {
        if (missingLibraries(["mermaid"]).length > 0)
            return null;
        initializeMermaid();
        const id = nextDiagramId();
        try {
            const { svg } = await mermaid.render(id, source);
            const holder = document.createElement("template");
            holder.innerHTML = svg;
            return holder.content.firstElementChild;
        }
        catch {
            // 描けなかった図: mermaid が body に残した作業用の要素を消す
            document.getElementById(`d${id}`)?.remove();
            document.getElementById(id)?.remove();
            return null;
        }
    }
    MindmapPreview.renderDiagramSvg = renderDiagramSvg;
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
        initializeMermaid();
        // この呼び出しで描いた・写した図だけを、次の呼び出しのために覚える
        const drawn = new Map();
        for (const container of containers) {
            const source = container.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            const id = nextDiagramId();
            try {
                // 直前に描いた同じ記法の図: 描き直さず、新しい ID に置き換えて写す（同じ図が文書に 2 つあっても ID と参照が重ならない）
                const reused = lastDrawn.get(source);
                const svg = reused === undefined
                    ? (await mermaid.render(id, source)).svg
                    : reused.svg.replace(new RegExp(`${reused.id}(?![0-9])`, "g"), id);
                container.innerHTML = svg;
                drawn.set(source, { svg, id });
            }
            catch {
                // 描けなかった図: mermaid が body に残した作業用の要素を消し、描けなかったことと原文を入れる
                document.getElementById(`d${id}`)?.remove();
                document.getElementById(id)?.remove();
                container.replaceChildren(MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: ["この図は表示できませんでした。原文を表示します。"] }), MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
            }
        }
        lastDrawn = drawn;
    }
    MindmapPreview.renderDiagrams = renderDiagrams;
})(MindmapPreview || (MindmapPreview = {}));
