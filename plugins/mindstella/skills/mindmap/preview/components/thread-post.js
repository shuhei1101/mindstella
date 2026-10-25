"use strict";
// スレッドの書き込み。スレッドの中に書いた順で並べる 1 件で、利用者と AI の書き込み・クローズとオープンへの戻しの記録・レビュー中の書き込みのどれか 1 つを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 本文の中の項目の ID（例 D-1・T-12・A-3） */
    const ITEM_ID_PATTERN = /\b[A-Z]{1,2}-\d+\b/g;
    /** 項目の ID をボタンにしない文字の置き場所（コード・リンク・ボタン・図・HTML の本文の枠の中） */
    const ITEM_ID_SKIPPED = `pre, code, a, button, figure.diagram, .${MindmapPreview.HTML_BLOCK_CLASS}`;
    /** 描いた本文の中の `#` で始まるリンクのうち、記録にあるまとまりを指すもの（`diff` の値を `changeSets` で引けたもの）をまとまりのリンクにし、それ以外は中の文字に置き換える。押したときは既定の動作を止め、まとまりの ID を `onChangeSet` に知らせる。`#` で始まらないリンクは触らない */
    function linkChangeSets({ root, changeSets, onChangeSet, }) {
        for (const link of root.querySelectorAll("a")) {
            const href = link.getAttribute("href") ?? "";
            if (!href.startsWith("#"))
                continue;
            // `diff` だけを読む（他の引数は無視する）
            const set = new URLSearchParams(href.slice(1)).get("diff");
            const summary = set === null ? null : changeSets(set);
            // 記録にあるまとまりを指さないリンクは、リンクにせず文言だけを出す
            if (set === null || summary === null) {
                link.replaceWith(...link.childNodes);
                continue;
            }
            link.className = "setlink";
            link.setAttribute("href", `#${new URLSearchParams({ diff: set }).toString()}`);
            link.title = summary;
            link.setAttribute("data-focus", `post-set:${set}`);
            link.addEventListener("click", (event) => {
                // ハッシュの書き換えは使う側に任せる
                event.preventDefault();
                onChangeSet(set);
            });
        }
    }
    /** 描いた本文の文字のうち、記録にある項目の ID を、その項目を開くボタンにする（コード・リンク・ボタン・図・HTML の本文の枠の中は飛ばす。記録に無い ID とスレッドの ID は文字のまま） */
    function buttonizeItemIds({ root, titles, onOpen, }) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => (node.parentElement?.closest(ITEM_ID_SKIPPED) !== null ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        for (const node of nodes) {
            const text = node.textContent ?? "";
            const parts = [];
            let last = 0;
            for (const match of text.matchAll(ITEM_ID_PATTERN)) {
                const title = titles(match[0]);
                // 記録に無い ID（スレッドの ID を含む）は文字のまま残す
                if (title === null)
                    continue;
                parts.push(text.slice(last, match.index), MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "idlink", type: "button", title, "data-focus": `post-id:${match[0]}`, onclick: () => onOpen(match[0]) },
                    children: [match[0]],
                }));
                last = match.index + match[0].length;
            }
            if (parts.length === 0)
                continue;
            parts.push(text.slice(last));
            node.replaceWith(...parts.filter((part) => part !== ""));
        }
    }
    /** 本文を、段落の中の改行を強制改行にして Markdown として描いた要素（項目の ID はその項目を開くボタン、記録にあるまとまりを指すリンクはまとまりのリンク）。mdmark が読めないときは、本文を文字のまま改行を保って持つ要素 */
    function postBody({ body, titles, changeSets, className, on, }) {
        // 読めない: 知らせは出さず、項目の ID とまとまりのリンクも作らない
        if (MindmapPreview.missingLibraries(["mdmark"]).length > 0)
            return MindmapPreview.h({ tag: "p", attrs: { class: className }, children: [body] });
        const root = MindmapPreview.withoutLineMarks(MindmapPreview.renderMarkdown(MindmapPreview.withHardBreaks(body)));
        root.classList.add(className);
        // 図は描き終えるのを待たずに返す
        void MindmapPreview.renderDiagrams(root);
        for (const block of root.querySelectorAll(`.${MindmapPreview.HTML_BLOCK_CLASS}`)) {
            const frame = MindmapPreview.htmlBodyFrame({ source: block.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "", selectable: false, label: "html のコードブロック" });
            frame.classList.add(MindmapPreview.HTML_BLOCK_CLASS);
            block.replaceWith(frame);
        }
        MindmapPreview.decorateMarkdown({ root, fold: false, tables: false });
        linkChangeSets({ root, changeSets, onChangeSet: on.changeSet });
        buttonizeItemIds({ root, titles, onOpen: on.openId });
        return root;
    }
    MindmapPreview.postBody = postBody;
    /** 状態の記録（枠の無い 1 行に、書き手・したこと・日時と、あれば理由） */
    function eventItem(event) {
        const closed = event.kind === "closed";
        const who = event.author === "ai" ? "AI が" : "あなたが";
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: `th-event ${event.author}`, "data-event": event.kind },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "th-event-line" },
                    children: [
                        MindmapPreview.icon(closed ? "check" : "undo"),
                        MindmapPreview.h({ tag: "span", children: [`${who}${closed ? "クローズにしました" : "オープンに戻しました"}`] }),
                        MindmapPreview.h({ tag: "time", attrs: { datetime: event.created }, children: [MindmapPreview.formatJst(event.created)] }),
                    ],
                }),
                event.reason === null ? null : MindmapPreview.h({ tag: "p", attrs: { class: "th-event-reason" }, children: [event.reason] }),
            ],
        });
    }
    /** レビュー中の書き込み（破線の枠と「レビュー中」の印を付け、右上に「修正」「削除」を置く） */
    function pendingItem({ item, titles, changeSets, editing, editBody, editError, on, }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "post user pending", "data-comment": item.id },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "post-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "post-author" }, children: [MindmapPreview.AUTHOR_LABELS.user] }),
                        MindmapPreview.pendingMark(),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        editing ? null : MindmapPreview.reviewRowActions({ item, focus: "", on: { edit: on.edit, remove: on.remove } }),
                    ],
                }),
                editing
                    ? MindmapPreview.reviewEditForm({ item, body: editBody, error: editError, focus: "", on: { saveEdit: on.saveEdit, cancelEdit: on.cancelEdit } })
                    : postBody({ body: item.body, titles, changeSets, className: "post-body", on: { openId: on.openId, changeSet: on.changeSet } }),
            ],
        });
    }
    /** スレッドの書き込み・状態の記録・レビュー中の書き込みのどれか 1 つの `li` を返す */
    function threadPost({ post = null, event = null, pending = null, titles = () => null, changeSets = () => null, editing = false, editBody = null, editError = null, on, }) {
        // 状態の記録
        if (event !== null)
            return eventItem(event);
        // レビュー中の書き込み
        if (pending !== null)
            return pendingItem({ item: pending, titles, changeSets, editing, editBody, editError, on });
        // 書き込みが無い（渡し方の誤り）
        if (post === null)
            throw new Error("threadPost には post・event・pending のどれか 1 つを渡す");
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: `post ${post.author}` },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "post-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "post-author" }, children: [MindmapPreview.AUTHOR_LABELS[post.author]] }),
                        MindmapPreview.h({ tag: "time", attrs: { datetime: post.created }, children: [MindmapPreview.formatJst(post.created)] }),
                    ],
                }),
                postBody({ body: post.body, titles, changeSets, className: "post-body", on: { openId: on.openId, changeSet: on.changeSet } }),
            ],
        });
    }
    MindmapPreview.threadPost = threadPost;
})(MindmapPreview || (MindmapPreview = {}));
