"use strict";
// 概要。未読の AI の書き込み・未決定の検討事項・要見直しの検討事項・確認中の資料のタイルを並べる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 小さなタイルに出す件数 */
    const MINI_LIMIT = 3;
    /** 種類を表示するか（`visibleKinds` を渡さないときは全ての種類を表示する） */
    function isShown(props, kind) {
        return props.visibleKinds === undefined || props.visibleKinds.has(kind);
    }
    /** 絞った表へ移る `Route`（画面の既定の表示形式で開く） */
    function tableRoute(tab, filters, view = "table") {
        return { tab, view, id: null, full: false, filters, heading: null, diff: null };
    }
    /** 「すべて表示（N 件）」のボタン */
    function showAll(count, onClick) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "t-link", type: "button", onclick: onClick },
            children: [`すべて表示（${count} 件）`],
        });
    }
    /** 見出し（アイコンと名前）と、右端の「すべて表示」 */
    function tileHead(id, iconName, title, link) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "t-head" },
            children: [MindmapPreview.h({ tag: "h2", attrs: { id }, children: [MindmapPreview.icon(iconName), title] }), link],
        });
    }
    /** 1 行が項目のボタンの一覧（押すと詳細を開く） */
    function miniList(items, emptyText, open, marks) {
        if (items.length === 0)
            return MindmapPreview.emptyNote(emptyText);
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "mini" },
            children: [
                ...items.slice(0, MINI_LIMIT).map((item) => MindmapPreview.h({
                    tag: "li",
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { type: "button", "data-id": item.id, onclick: () => open(item.id) },
                            children: [
                                MindmapPreview.statusMark(item.status),
                                MindmapPreview.h({ tag: "span", attrs: { class: "mt" }, children: [item.title] }),
                                MindmapPreview.markFor({ marks, id: item.id }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [MindmapPreview.icon("chev")] }),
                            ],
                        }),
                    ],
                })),
            ],
        });
    }
    /** 未読の AI の書き込みを持つオープンのスレッドを、最後の未読の書き込みの新しい順に返す */
    function unreadThreads(threads) {
        return (threads ?? [])
            .filter((thread) => thread.status === "open")
            .flatMap((thread) => {
            const unseen = thread.posts.filter((post) => post.author === "ai" && !post.seen);
            const last = unseen.at(-1);
            return last === undefined ? [] : [{ thread, last: last.created }];
        })
            .sort((a, b) => (a.last < b.last ? 1 : a.last > b.last ? -1 : 0));
    }
    /** 未読の AI の書き込みのタイル（押すとコメントの一覧でそのスレッドを開く） */
    function unreadTile(props) {
        const rows = unreadThreads(props.threads);
        const openThread = props.on.openThread;
        return MindmapPreview.h({
            tag: "section",
            attrs: { id: "tile-unread", class: "tile t-small", "aria-labelledby": "h-unread" },
            children: [
                tileHead("h-unread", "comment", "未読の AI の書き込み", rows.length > 0 && openThread !== undefined ? showAll(rows.length, () => openThread(null)) : null),
                MindmapPreview.h({ tag: "p", attrs: { class: "num" }, children: [rows.length] }),
                rows.length === 0
                    ? MindmapPreview.emptyNote("未読の AI の書き込みはありません。")
                    : MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "mini" },
                        children: rows.slice(0, MINI_LIMIT).map(({ thread, last }) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                MindmapPreview.h({
                                    tag: "button",
                                    attrs: {
                                        type: "button",
                                        "data-id": thread.id,
                                        disabled: openThread === undefined,
                                        onclick: () => openThread?.(thread.id),
                                    },
                                    children: [
                                        MindmapPreview.h({ tag: "span", attrs: { class: "mt" }, children: [`${thread.id} ${thread.summary ?? ""}`.trim()] }),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [MindmapPreview.icon("chev")] }),
                                    ],
                                }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "wait" }, children: [MindmapPreview.formatJst(last)] }),
                            ],
                        })),
                    }),
            ],
        });
    }
    /** 件数と名前の小さなタイル（未決定・要見直し・確認中の資料） */
    function smallTile({ tileId, id, iconName, title, items, emptyText, link, open, marks, linked, }) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { id: tileId, class: "tile t-small", "aria-labelledby": id },
            children: [
                tileHead(id, iconName, title, items.length > 0 && linked ? showAll(items.length, link) : null),
                MindmapPreview.h({ tag: "p", attrs: { class: "num" }, children: [items.length] }),
                miniList(items, emptyText, open, marks),
            ],
        });
    }
    /** 概要の画面を返す */
    function overviewScreen(props) {
        const { index, on } = props;
        const { settings } = index.data;
        const byNumber = (items) => [...items].sort((a, b) => MindmapPreview.compareIds(a.id, b.id));
        const decisions = index.data.decisions;
        const open = byNumber(decisions.filter((item) => item.status === "未決定"));
        const review = byNumber(decisions.filter((item) => item.status === "要見直し"));
        const docs = byNumber(index.data.docs.filter((item) => item.status === "確認中"));
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "overview" },
            children: [
                MindmapPreview.h({
                    tag: "header",
                    attrs: { class: "hero" },
                    children: [
                        // 話し合いの概要があるときだけ、題名の上に出す
                        settings.description !== undefined
                            ? MindmapPreview.h({
                                tag: "p",
                                attrs: { id: "overview-description", class: "hero-sub hero-desc" },
                                children: [settings.description],
                            })
                            : null,
                        MindmapPreview.h({ tag: "h1", children: [settings.summary] }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "bento" },
                    children: [
                        unreadTile(props),
                        smallTile({
                            tileId: "tile-open",
                            id: "h-open",
                            iconName: "decision",
                            title: "未決定の検討事項",
                            items: open,
                            emptyText: "未決定の検討事項はありません。",
                            link: () => on.navigate(tableRoute("decisions", { status: ["未決定"] })),
                            open: on.open,
                            marks: props.marks,
                            linked: isShown(props, "decisions"),
                        }),
                        smallTile({
                            tileId: "tile-review",
                            id: "h-review",
                            iconName: "alert",
                            title: "要見直し",
                            items: review,
                            emptyText: "要見直しの検討事項はありません。",
                            link: () => on.navigate(tableRoute("decisions", { status: ["要見直し"] })),
                            open: on.open,
                            marks: props.marks,
                            linked: isShown(props, "decisions"),
                        }),
                        smallTile({
                            tileId: "tile-docs",
                            id: "h-docs",
                            iconName: "doc",
                            title: "確認中の資料",
                            items: docs,
                            emptyText: "確認中の資料はありません。",
                            link: () => on.navigate(tableRoute("docs", { status: ["確認中"] }, "cards")),
                            open: on.open,
                            marks: props.marks,
                            linked: isShown(props, "docs"),
                        }),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.overviewScreen = overviewScreen;
})(MindmapPreview || (MindmapPreview = {}));
