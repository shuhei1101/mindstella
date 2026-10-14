"use strict";
// スレッドの行。スレッドの一覧に並べる 1 件で、状態の札・題・向けた項目・最後の書き手と日時・レビュー中の印・タグを出し、押すとそのスレッドを開く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 書き手の呼び名 */
    MindmapPreview.AUTHOR_LABELS = { user: "あなた", ai: "AI" };
    /** 状態の札の印と文言 */
    const STATE_LABELS = {
        open: { icon: "changed", label: "オープン" },
        closed: { icon: "check", label: "クローズ" },
        pending: { icon: "edit", label: "レビュー中" },
    };
    /** 本文の 1 行目 */
    function firstLine(body) {
        return body.split("\n")[0];
    }
    /** 行と見出しに出す題（要約。まだ無ければ最初の書き込みの 1 行目） */
    function threadTitle(thread) {
        return thread.summary ?? firstLine(thread.posts[0].body);
    }
    MindmapPreview.threadTitle = threadTitle;
    /** 状態の札（色に加えて印と文字で区別する） */
    function threadState(status) {
        const { icon: name, label } = STATE_LABELS[status];
        return MindmapPreview.h({ tag: "span", attrs: { class: `th-state ${status}` }, children: [MindmapPreview.icon(name), label] });
    }
    MindmapPreview.threadState = threadState;
    /** レビュー中の印（レビュー中の返信を持つスレッドの行と、スレッドの中のレビュー中の書き込みに出す） */
    function pendingMark() {
        return MindmapPreview.h({ tag: "span", attrs: { class: "th-pending" }, children: [MindmapPreview.icon("edit"), "レビュー中"] });
    }
    MindmapPreview.pendingMark = pendingMark;
    /** 利用者の未読の書き込み（`seen` が偽）を持つか。`seen` を持たない書き込みは未読にしない */
    function hasUnseen(thread) {
        return thread.posts.some((post) => post.seen === false);
    }
    MindmapPreview.hasUnseen = hasUnseen;
    /** トップバーの未読の点に渡す値（オープンのスレッドに利用者の未読があるか。クローズの未読は数えない） */
    function anyOpenUnseen(threads) {
        return threads.some((thread) => thread.status === "open" && hasUnseen(thread));
    }
    MindmapPreview.anyOpenUnseen = anyOpenUnseen;
    /** 未読の札（塗りつぶしの形・点の印・「未読」の文字で示す。状態の札の線の枠、レビュー中の印の破線の枠と形で見分ける） */
    function unseenMark() {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "th-unread" },
            children: [MindmapPreview.h({ tag: "span", attrs: { class: "dot", "aria-hidden": "true" } }), "未読"],
        });
    }
    /** タグの札（行を開くボタンとは別のボタン。押すとそのタグで絞る） */
    function tagButton({ thread, tag, active, onTag }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `th-tag${active ? " on" : ""}`,
                type: "button",
                "aria-pressed": String(active),
                "aria-label": `タグ「${tag}」で絞る`,
                "data-focus": `tag:${thread.id}:${tag}`,
                onclick: () => onTag(tag),
            },
            children: [MindmapPreview.icon("hash"), tag],
        });
    }
    /** スレッドの行（`li`）を返す。送ったスレッドと、まだ送っていない新しいスレッドのどちらも同じ形で描く */
    function threadRow({ thread = null, pending = null, hasPendingReply = false, activeTag = null, on }) {
        const last = thread === null ? null : thread.posts[thread.posts.length - 1];
        const sent = thread !== null && last !== null;
        const id = sent ? thread.id : (pending?.id ?? "");
        const target = sent ? thread.target : (pending?.target ?? null);
        const author = sent ? last.author : "user";
        const created = sent ? last.created : (pending?.created ?? "");
        const title = sent ? threadTitle(thread) : firstLine(pending?.body ?? "");
        const summarized = sent && thread.summary !== null;
        const status = sent ? thread.status : "pending";
        const unseen = sent && hasUnseen(thread);
        // 未読の行は、読み上げの名前が状態の次に「未読」を読む
        const openLabel = unseen
            ? [STATE_LABELS[status].label, "未読", title, target, MindmapPreview.AUTHOR_LABELS[author], MindmapPreview.formatJst(created), hasPendingReply ? "レビュー中の返信あり" : null]
                .filter((part) => part !== null)
                .join("、")
            : null;
        return MindmapPreview.h({
            tag: "li",
            attrs: sent ? { class: `th-row${unseen ? " unread" : ""}`, "data-thread": id } : { class: "th-row pending", "data-pending": id },
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "th-open",
                        type: "button",
                        "aria-label": openLabel,
                        "data-focus": sent ? `thread:${id}` : `thread:new:${id}`,
                        onclick: () => on.open(id, !sent),
                    },
                    children: [
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "th-line1" },
                            children: [threadState(status), MindmapPreview.h({ tag: "span", attrs: { class: `th-title${summarized ? "" : " head"}` }, children: [title] })],
                        }),
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "th-line2" },
                            children: [
                                unseen ? unseenMark() : null,
                                target === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "th-author" }, children: [MindmapPreview.AUTHOR_LABELS[author]] }),
                                MindmapPreview.h({ tag: "time", attrs: { datetime: created }, children: [MindmapPreview.formatJst(created)] }),
                                hasPendingReply ? pendingMark() : null,
                            ],
                        }),
                    ],
                }),
                !sent || thread.tags.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "th-tags" },
                        children: thread.tags.map((tag) => tagButton({ thread, tag, active: tag === activeTag, onTag: on.tag })),
                    }),
            ],
        });
    }
    MindmapPreview.threadRow = threadRow;
})(MindmapPreview || (MindmapPreview = {}));
