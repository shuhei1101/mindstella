"use strict";
// Markdown の本文の見せ方。描いた本文に、表の列の幅と折り返し・右端のフェード・コードブロックの言語の札とコピー・GitHub の Alert の囲みを常に当て、表示の設定で切り替える表の列の固定・表の見出しの固定・表のしま模様・セクションの折りたたみを当てる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 本文の見せ方の項目（表示の設定に並べる順） */
    MindmapPreview.BODY_VIEW_KEYS = ["pin", "head", "stripes", "fold"];
    /** 表示の設定のチェックボックスと「この端末で変えている項目」に出す名前 */
    MindmapPreview.BODY_VIEW_LABELS = {
        pin: "表の列の固定",
        head: "表の見出しの固定",
        stripes: "表のしま模様",
        fold: "セクションの折りたたみ",
    };
    /** 個人の上書きが無いときの本文の見せ方（列の固定・見出しの固定・折りたたみはオン、しま模様はオフ） */
    MindmapPreview.BODY_VIEW_DEFAULT = { pin: true, head: true, stripes: false, fold: true };
    /** 全角を 1、半角を 0.5 と数えたセルの最大の文字数が `shortMax` 以下の列は短い列、`longMin` 以上の列は長文の列 */
    const COLUMN_BOUNDS = { shortMax: 8, longMin: 25 };
    /** 中くらいの列の最小の幅（em）の上限 */
    const MEDIUM_MIN_EM_MAX = 14;
    /** 中くらいの列の最小の幅を文字数の半分にこの値（em）を足した幅にする（文節の区切りでだけ折り返す分の余り） */
    const MEDIUM_MIN_EM_SLACK = 2;
    /** 長文の列を折り返す幅（em） */
    const LONG_COLUMN_EM = 24;
    /** 本文で使っている見出しの階層のうち、上からこの数の階層にだけ開閉を置く */
    const FOLD_LEVELS = 2;
    /** コードブロックのコピーのボタンを押した後、チェックのマーカーを出しておくミリ秒（図のコピーと同じ） */
    const CODE_COPIED_MS = 1400;
    /** mdmark が描いた Alert の囲みの種類（クラス `markdown-alert-{種類}`）→ 見出しの頭に置くアイコン */
    const CALLOUT_KINDS = {
        note: "note",
        tip: "star",
        important: "flag",
        warning: "alert",
        caution: "alert",
    };
    /** 半角として数える文字の符号位置の上限 */
    const HALF_WIDTH_MAX = 0xff;
    /** 表を送らない枠の class（右端のフェードの基準） */
    const TABLE_FRAME_CLASS = "md-table-frame";
    /** 節の中身の入れ物の class（畳むと `hidden="until-found"` にする） */
    const SECTION_BODY_CLASS = "md-section-body";
    /** 節の中身の入れ物に振る id の通し番号 */
    let sectionSeq = 0;
    /** 前後の空白を除いた文字列の幅を、符号位置が U+00FF 以下の文字を 0.5、それ以外を 1 として数える */
    function textWidth(text) {
        let width = 0;
        for (const char of text.trim())
            width += (char.codePointAt(0) ?? 0) <= HALF_WIDTH_MAX ? 0.5 : 1;
        return width;
    }
    MindmapPreview.textWidth = textWidth;
    /** 列のセルの最大の文字の幅から、列の種類と最小の幅（em。中くらいの列だけ持つ）を決める */
    function columnSize(maxWidth) {
        if (maxWidth <= COLUMN_BOUNDS.shortMax)
            return { kind: "short", minEm: null };
        if (maxWidth >= COLUMN_BOUNDS.longMin)
            return { kind: "long", minEm: null };
        return { kind: "medium", minEm: Math.min(Math.ceil(maxWidth / 2) + MEDIUM_MIN_EM_SLACK, MEDIUM_MIN_EM_MAX) };
    }
    MindmapPreview.columnSize = columnSize;
    /** 表の列ごとにセルの最大の文字の幅を数え、列のセルに種類（`data-col-size`）と中くらいの列の最小の幅（`--md-col-min`）を付ける */
    function sizeColumns(table) {
        const widths = [];
        for (const row of table.rows) {
            [...row.cells].forEach((cell, column) => {
                widths[column] = Math.max(widths[column] ?? 0, textWidth(cell.textContent ?? ""));
            });
        }
        for (const row of table.rows) {
            [...row.cells].forEach((cell, column) => {
                const size = columnSize(widths[column] ?? 0);
                cell.dataset["colSize"] = size.kind;
                if (size.minEm !== null)
                    cell.style.setProperty("--md-col-min", `${size.minEm}em`);
            });
        }
        table.style.setProperty("--md-col-long", `${LONG_COLUMN_EM}em`);
    }
    /** 表の入れ物を送らない枠で包み、右へまだ送れる間だけ枠に `data-fade` を付ける */
    function frameTable(wrap) {
        if (wrap.parentElement?.classList.contains(TABLE_FRAME_CLASS) === true)
            return;
        const frame = MindmapPreview.h({ tag: "div", attrs: { class: TABLE_FRAME_CLASS } });
        wrap.replaceWith(frame);
        frame.append(wrap);
        const update = () => {
            frame.toggleAttribute("data-fade", wrap.scrollLeft + wrap.clientWidth < wrap.scrollWidth - 1);
        };
        wrap.addEventListener("scroll", update, { passive: true });
        const observer = new ResizeObserver(update);
        observer.observe(wrap);
        const table = wrap.querySelector("table");
        if (table !== null)
            observer.observe(table);
        update();
    }
    /** 見出しのセルの文言（固定のボタンを除く） */
    function headText(cell) {
        return [...cell.childNodes]
            .filter((node) => !(node instanceof HTMLElement && node.classList.contains("md-pin")))
            .map((node) => node.textContent ?? "")
            .join("")
            .trim();
    }
    /** 表の固定した列（左から `pinTo` 列目まで）に、左の位置と右端の影のマーカーを付ける。`pinTo` が -1 なら固定しない */
    function applyPins(table) {
        const pinTo = Number(table.dataset["pinTo"] ?? "-1");
        const head = table.tHead?.rows[0];
        if (head === undefined)
            return;
        // 列ごとの左の位置（見出しのセルの幅を積む）
        const lefts = [];
        let left = 0;
        for (const cell of head.cells) {
            lefts.push(left);
            left += cell.getBoundingClientRect().width;
        }
        for (const row of table.rows) {
            [...row.cells].forEach((cell, column) => {
                const pinned = column <= pinTo;
                cell.classList.toggle("md-pinned", pinned);
                cell.classList.toggle("md-pin-edge", column === pinTo);
                cell.style.left = pinned ? `${lefts[column] ?? 0}px` : "";
            });
        }
        head.querySelectorAll(".md-pin").forEach((button, column) => {
            button.setAttribute("aria-pressed", String(column === pinTo));
        });
    }
    /** 表の見出し（最後の列を除く）に固定のボタンを置く。押した列より左を固定し、もう一度押すと外す。押すまで固定しない */
    function addPinButtons(table) {
        const head = table.tHead?.rows[0];
        if (head === undefined || head.cells.length < 2 || head.querySelector(".md-pin") !== null)
            return;
        table.classList.add("md-has-pin");
        [...head.cells].slice(0, -1).forEach((cell, column) => {
            const label = headText(cell);
            cell.append(MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "th-tool md-pin",
                    type: "button",
                    "aria-pressed": "false",
                    "aria-label": `${label === "" ? `${column + 1} 列目` : label}まで固定`,
                    title: "この列まで固定",
                    onclick: () => {
                        table.dataset["pinTo"] = String(Number(table.dataset["pinTo"] ?? "-1") === column ? -1 : column);
                        applyPins(table);
                    },
                },
                children: [MindmapPreview.icon("pin")],
            }));
        });
        // 文字の読み込み・幅の変化で列の幅が変わったら、固定した列の位置を直す
        new ResizeObserver(() => applyPins(table)).observe(table);
    }
    /** 見出しの階層（元の Markdown の階層。無ければ要素の階層） */
    function headingLevel(element) {
        return Number(element.dataset["mdLevel"] ?? element.tagName.slice(1));
    }
    /** 見出しの要素か */
    function isHeading(element) {
        return /^H[1-6]$/.test(element.tagName);
    }
    /** 見出しの節の中身（次の同じか上の階層の見出しまで）を入れ物で包んで返す。中身が無ければ null */
    function wrapSection(heading) {
        const level = headingLevel(heading);
        const items = [];
        for (let node = heading.nextElementSibling; node !== null && !(isHeading(node) && headingLevel(node) <= level); node = node.nextElementSibling) {
            items.push(node);
        }
        if (items.length === 0)
            return null;
        const body = MindmapPreview.h({ tag: "div", attrs: { class: SECTION_BODY_CLASS, id: `md-section-${(sectionSeq += 1)}` } });
        heading.after(body);
        body.append(...items);
        return body;
    }
    /** 見出しを開く・畳む。畳んだ中身は `hidden="until-found"` にし、ページ内の検索の対象に残す */
    function setFolded({ heading, folded }) {
        const body = heading.nextElementSibling;
        if (body === null || !body.classList.contains(SECTION_BODY_CLASS))
            return;
        heading.dataset["folded"] = String(folded);
        heading.querySelector(".md-fold")?.setAttribute("aria-expanded", String(!folded));
        if (folded)
            body.setAttribute("hidden", "until-found");
        else
            body.removeAttribute("hidden");
        // 本文の高さが変わったので、表の見出しの固定の位置を直す
        heading.closest(".panel-body")?.dispatchEvent(new Event("scroll"));
    }
    /** 本文の見出しの文言（# のリンクと開閉のボタンを除く） */
    function headingLabel(heading) {
        return [...heading.childNodes]
            .filter((node) => !(node instanceof HTMLElement && node.matches(".h-link, .md-fold")))
            .map((node) => node.textContent ?? "")
            .join("")
            .trim();
    }
    /** 本文の見出しに開閉の矢印のボタンを置く（上位の `FOLD_LEVELS` 階層だけ）。節の中身を入れ物で包み、開いた状態で描く */
    function addFoldButtons(root) {
        if (root.querySelector(".md-fold") !== null)
            return;
        const levels = [...new Set([...root.children].filter(isHeading).map(headingLevel))]
            .sort((a, b) => a - b)
            .slice(0, FOLD_LEVELS);
        // 上の階層から包む（下の階層の見出しは、上の階層の入れ物の中で包む）
        for (const level of levels) {
            for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
                // その階層の見出しのうち、本文の直下か上の階層の入れ物の直下にあるものだけ
                const parent = heading.parentElement;
                if (headingLevel(heading) !== level || (parent !== root && parent?.classList.contains(SECTION_BODY_CLASS) !== true))
                    continue;
                const body = wrapSection(heading);
                if (body === null)
                    continue;
                heading.dataset["folded"] = "false";
                heading.prepend(MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "md-fold",
                        type: "button",
                        "aria-expanded": "true",
                        "aria-controls": body.id,
                        "aria-label": `${headingLabel(heading)}を開閉`,
                        onclick: () => setFolded({ heading, folded: heading.dataset["folded"] !== "true" }),
                    },
                    children: [MindmapPreview.icon("chev")],
                }));
                // ページ内の検索・リンクで畳んだ中身に当たった: ブラウザが開く前に、見出しの開閉の状態を開いたにそろえる
                body.addEventListener("beforematch", () => setFolded({ heading, folded: false }));
            }
        }
    }
    /** 本文の中の見出しへ移る前に、その見出しを包む畳んだ入れ物を全て開く（開閉の矢印の `aria-expanded` も合わせる） */
    function revealHeading({ root, slug }) {
        for (const target of root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)) {
            for (let body = target.closest(`.${SECTION_BODY_CLASS}`); body !== null; body = body.parentElement?.closest(`.${SECTION_BODY_CLASS}`) ?? null) {
                const heading = body.previousElementSibling;
                if (heading instanceof HTMLElement && heading.dataset["folded"] === "true")
                    setFolded({ heading, folded: false });
            }
        }
    }
    MindmapPreview.revealHeading = revealHeading;
    /** コードブロックを入れ物で包み、右上にコピーのボタン、言語を書いたものは左上に言語の札を置く（札とボタンはコードの文字に入れない） */
    function decorateCodeBlocks(root) {
        for (const code of root.querySelectorAll("pre > code")) {
            const pre = code.parentElement;
            if (pre.parentElement?.classList.contains("md-code") === true)
                continue;
            const lang = [...code.classList].find((name) => name.startsWith("language-"))?.slice("language-".length) ?? null;
            const status = MindmapPreview.h({ tag: "span", attrs: { class: "sr-only", role: "status" } });
            const copy = MindmapPreview.h({
                tag: "button",
                attrs: { class: "icon-btn code-copy", type: "button", "aria-label": "コードをコピー", title: "コピー" },
                children: [MindmapPreview.icon("copy")],
            });
            copy.addEventListener("click", () => {
                void navigator.clipboard?.writeText(code.textContent ?? "").then(() => {
                    copy.replaceChildren(MindmapPreview.icon("check"));
                    status.textContent = "コピーしました";
                    window.setTimeout(() => {
                        copy.replaceChildren(MindmapPreview.icon("copy"));
                        status.textContent = "";
                    }, CODE_COPIED_MS);
                });
            });
            const box = MindmapPreview.h({ tag: "div", attrs: { class: lang === null ? "md-code" : "md-code has-lang" } });
            pre.replaceWith(box);
            box.append(...(lang === null ? [] : [MindmapPreview.h({ tag: "span", attrs: { class: "code-lang" }, children: [lang] })]), pre, copy, status);
        }
    }
    /** mdmark が描いた Alert の囲み（`div.markdown-alert`）の見出し（`p.markdown-alert-title`）の頭に、種類のアイコンを置く（置いてあれば重ねない） */
    function decorateCallouts(root) {
        for (const callout of root.querySelectorAll("div.markdown-alert")) {
            const title = callout.querySelector(":scope > p.markdown-alert-title");
            const kind = [...callout.classList].find((name) => name.startsWith("markdown-alert-") && name !== "markdown-alert-title")?.slice("markdown-alert-".length);
            const name = kind === undefined ? undefined : CALLOUT_KINDS[kind];
            if (title === null || name === undefined || title.firstElementChild?.matches("svg.icon") === true)
                continue;
            title.prepend(MindmapPreview.icon(name));
        }
    }
    /** 描いた本文に見せ方を当てる。`display` は表示の設定の値、`fold` は開閉を置ける本文か（本文の差分では偽にする）、`tables` は表の見せ方を当てるか（スレッドの書き込みでは偽にし、表は mdmark の共通のスタイルのまま描く） */
    function decorateMarkdown({ root, display = MindmapPreview.BODY_VIEW_DEFAULT, fold = true, tables = true, }) {
        for (const table of tables ? root.querySelectorAll("table") : []) {
            sizeColumns(table);
            const wrap = table.closest(`.${MindmapPreview.TABLE_WRAP_CLASS}`);
            if (wrap !== null)
                frameTable(wrap);
            if (display.pin)
                addPinButtons(table);
            table.classList.toggle("md-head-stick", display.head && table.tHead !== null);
            table.classList.toggle("md-stripes", display.stripes);
        }
        if (fold && display.fold)
            addFoldButtons(root);
        decorateCodeBlocks(root);
        decorateCallouts(root);
    }
    MindmapPreview.decorateMarkdown = decorateMarkdown;
    /** 本文のスクロール領域を縦に送っても、見出しを固定した表の見出しの行を領域の上端に残す。受け取りを外す関数を返す（表の入れ物が横に送るため CSS の sticky では残せず、領域の送り量を見出しのセルへ縦のずらしとして入れる） */
    function bindTableHeads(scroller) {
        let frame = 0;
        const update = () => {
            frame = 0;
            const top = scroller.getBoundingClientRect().top;
            for (const table of scroller.querySelectorAll("table.md-head-stick")) {
                const head = table.tHead;
                if (head === null)
                    continue;
                const rect = table.getBoundingClientRect();
                // 表の上端が領域の上端より上にある分だけ下げる（見出しの行が表の下端を越えない）
                const max = Math.max(rect.height - head.offsetHeight, 0);
                const offset = Math.min(Math.max(top - rect.top, 0), max);
                for (const cell of head.rows[0]?.cells ?? [])
                    cell.style.setProperty("--head-offset", `${offset}px`);
                table.classList.toggle("md-head-stuck", offset > 0);
            }
        };
        const onScroll = () => {
            if (frame === 0)
                frame = requestAnimationFrame(update);
        };
        scroller.addEventListener("scroll", onScroll, { passive: true });
        update();
        return () => {
            scroller.removeEventListener("scroll", onScroll);
            if (frame !== 0)
                cancelAnimationFrame(frame);
        };
    }
    MindmapPreview.bindTableHeads = bindTableHeads;
})(MindmapPreview || (MindmapPreview = {}));
