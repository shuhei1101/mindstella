"use strict";
// コメントの一覧。見ている画面に重ねて左から出すパネルで、スレッドの一覧・スレッド 1 件・レビュー中の書き込みの 3 つの画面を切り替える。
var MindmapPreview;
(function (MindmapPreview) {
    /** コメントの本文の長さの上限（サーバーが受け付ける文字数と同じ） */
    MindmapPreview.COMMENT_BODY_MAX_LENGTH = 10000;
    /** 状態を変える理由の長さの上限（サーバーが受け付ける文字数と同じ） */
    const REASON_MAX_LENGTH = 400;
    /** コメントの ID の連番 */
    function commentNumber(id) {
        return Number(id.replace(/^\D+-/, ""));
    }
    MindmapPreview.commentNumber = commentNumber;
    /** スレッドの ID の連番 */
    function threadNumber(id) {
        return Number(id.replace(/^\D+-/, ""));
    }
    /** 日時の前後（ISO 8601 を時刻として比べる） */
    function byTime(a, b) {
        return Date.parse(a) - Date.parse(b);
    }
    /** スレッドの最後の書き込みの日時 */
    function lastCreated(thread) {
        return thread.posts[thread.posts.length - 1].created;
    }
    /** スレッドを状態とタグで絞り、最後の書き込みの新しい順に並べる（渡した配列は変えない） */
    function visibleThreads(threads, filter, tag) {
        return threads
            .filter((thread) => filter === "all" || thread.status === filter)
            .filter((thread) => tag === null || thread.tags.includes(tag))
            .sort((a, b) => byTime(lastCreated(b), lastCreated(a)) || threadNumber(b.id) - threadNumber(a.id));
    }
    MindmapPreview.visibleThreads = visibleThreads;
    /** タグで絞ったスレッドの、状態の絞り込みに出す件数 */
    function threadCounts(threads, tag) {
        const tagged = tag === null ? threads : threads.filter((thread) => thread.tags.includes(tag));
        const open = tagged.filter((thread) => thread.status === "open").length;
        return { open, closed: tagged.length - open, all: tagged.length };
    }
    MindmapPreview.threadCounts = threadCounts;
    /** レビュー中の書き込みのうち、一覧の先頭に出す新しいスレッドの最初の書き込み（クローズの絞り込みとタグの絞り込みでは出さない） */
    function pendingThreads(items, filter, tag) {
        if (filter === "closed" || tag !== null)
            return [];
        return items.filter((item) => item.thread === null);
    }
    MindmapPreview.pendingThreads = pendingThreads;
    /** レビュー中の書き込みが、クローズのスレッドへの返信か（スレッドが見つからなければ偽。サーバーが 409 で返す） */
    function isBlockedReply(item, threads) {
        if (item.thread === null)
            return false;
        return threads.find((thread) => thread.id === item.thread)?.status === "closed";
    }
    MindmapPreview.isBlockedReply = isBlockedReply;
    /** スレッドの書き込みと状態の記録を、日時の順の 1 本の並びにする（同じ日時は書き込みを先にし、それぞれの中の並びを保つ） */
    function threadTimeline(thread) {
        const entries = [
            ...thread.posts.map((post) => ({ post, at: post.created, rank: 0 })),
            ...thread.events.map((event) => ({ event, at: event.created, rank: 1 })),
        ];
        return entries.sort((a, b) => byTime(a.at, b.at) || a.rank - b.rank);
    }
    MindmapPreview.threadTimeline = threadTimeline;
    /** 送った結果の文言（印と文）。結果が無いときは null */
    function outcomeContent({ result, checkedCount }) {
        if (result === null) {
            // チェックが 0 件
            return checkedCount === 0 ? [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["送る書き込みにチェックを付けてください。"] })] : null;
        }
        if (result.kind === "sending") {
            return [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["送っています"] })];
        }
        if (result.kind === "sent") {
            const time = result.at === undefined ? "" : MindmapPreview.formatJst(result.at).slice(-5);
            const count = result.count ?? 0;
            // Claude Code に入力できなかった: 送った内容は残り、次の話し合いの取り込みに任せる
            if (result.entered !== true) {
                return [
                    MindmapPreview.icon("alert"),
                    MindmapPreview.h({
                        tag: "span",
                        children: [
                            `${count} 件を送りましたが、Claude Code には入力できませんでした（${time}）。送った内容は保存されていて、次に話し合いを始めたときに取り込まれます。`,
                        ],
                    }),
                ];
            }
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`${count} 件を送り、Claude Code に入力しました（${time}）。`] })];
        }
        if (result.kind === "stale") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`送れませんでした。送れない書き込みが ${result.count ?? 0} 件あります。`] })];
        }
        const detail = result.detail ?? null;
        return [
            MindmapPreview.icon("alert"),
            MindmapPreview.h({
                tag: "span",
                children: [
                    detail === null
                        ? "送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。"
                        : `送れませんでした。${detail}`,
                ],
            }),
        ];
    }
    /** レビュー中の書き込みの読み上げの名前の頭（返信は「{スレッドの ID} への返信」、新しいスレッドは「{向けた項目の ID} へのコメント」） */
    function reviewLabel(item) {
        // 詳細パネルへ渡す行には `thread` を持たないものもある
        if (item.thread !== null && item.thread !== undefined)
            return `${item.thread} への返信`;
        return item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
    }
    /** 行の向けた項目（押すとその項目を開く。項目を指さない・消えた項目は押せない） */
    function targetCell(item, props) {
        // 項目を指さない
        if (item.target === null)
            return MindmapPreview.h({ tag: "span", attrs: { class: "row-target none" }, children: ["項目を指さない"] });
        const title = props.titleOf(item.target);
        // 項目が消えた: 押せない ID だけを出す
        if (title === null) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.target] })] });
        }
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "row-target idlink", type: "button", "data-focus": `open:${item.id}`, onclick: () => props.on.open(item) },
            children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.target] }), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [title] })],
        });
    }
    /** 本文をその場で書き換える入力欄と「キャンセル」「修正」（コメントの一覧と詳細パネルが使う） */
    function reviewEditForm({ item, body, error, focus, on, }) {
        const field = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                name: "body",
                rows: 2,
                maxlength: MindmapPreview.COMMENT_BODY_MAX_LENGTH,
                "aria-label": `${item.id} へのコメントの本文`,
                "data-focus": `${focus}edit:${item.id}`,
                onkeydown: (event) => {
                    if (event.key === "Escape") {
                        // 詳細の全画面の `dialog` の `cancel` を起こさない
                        event.preventDefault();
                        event.stopPropagation();
                        on.cancelEdit();
                    }
                },
            },
            children: [body ?? item.body],
        });
        // 理由があるときだけ `role="alert"` を持たせる（空のまま警告として読み上げさせない）
        const message = MindmapPreview.h({ tag: "p", attrs: { class: "send-msg failed", role: error ? "alert" : null }, children: error ? [MindmapPreview.icon("alert"), error] : [] });
        return MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "row-edit",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    // 空白だけは送らない
                    if (field.value.trim() === "") {
                        field.setAttribute("aria-invalid", "true");
                        message.setAttribute("role", "alert");
                        message.replaceChildren(MindmapPreview.icon("alert"), "コメントを入れてから直してください。");
                        field.focus();
                        return;
                    }
                    on.saveEdit(item.id, field.value);
                },
            },
            children: [
                field,
                message,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-edit-actions" },
                    children: [
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn ghost", type: "button", onclick: on.cancelEdit }, children: ["キャンセル"] }),
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn primary", type: "submit" }, children: ["修正"] }),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.reviewEditForm = reviewEditForm;
    /** 行の右上に置く、鉛筆の印の「修正」とごみ箱の印の「削除」（コメントの一覧と詳細パネルが使う） */
    function reviewRowActions({ item, focus, on, }) {
        const label = reviewLabel(item);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "row-actions" },
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": `${label}を修正`,
                        title: "修正",
                        "data-focus": `${focus}edit-open:${item.id}`,
                        onclick: () => on.edit(item.id),
                    },
                    children: [MindmapPreview.icon("edit")],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": `${label}を削除`,
                        title: "削除",
                        "data-focus": `${focus}remove:${item.id}`,
                        onclick: () => on.remove(item.id),
                    },
                    children: [MindmapPreview.icon("trash")],
                }),
            ],
        });
    }
    MindmapPreview.reviewRowActions = reviewRowActions;
    /** 消した行（元の場所に「コメントを削除しました。」と「元に戻す」を出す。コメントの一覧と詳細パネルが使う） */
    function removedReviewRow({ item, focus, on, }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "row removed", "data-comment": item.id },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "removed-msg", role: "status" }, children: ["コメントを削除しました。"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn ghost", type: "button", "data-focus": `${focus}restore:${item.id}`, onclick: () => on.restore(item.id) },
                    children: [MindmapPreview.icon("undo"), "元に戻す"],
                }),
            ],
        });
    }
    MindmapPreview.removedReviewRow = removedReviewRow;
    /** 行の頭（返信は返信先のスレッドの状態の札と題、新しいスレッドは向けた項目） */
    function rowHead(item, props) {
        const thread = item.thread === null ? undefined : props.threads.find((entry) => entry.id === item.thread);
        // 新しいスレッド: 向けた項目
        if (item.thread === null) {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "row-head" },
                children: [MindmapPreview.h({ tag: "span", attrs: { class: "row-kind" }, children: ["新しいスレッド"] }), targetCell(item, props)],
            });
        }
        // 返信: 返信先のスレッド（読めていなければ ID だけ）
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "row-head" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "row-kind" }, children: ["返信"] }),
                thread === undefined
                    ? MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.thread] })] })
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "row-target idlink-like",
                            type: "button",
                            "data-focus": `open:${item.id}`,
                            onclick: () => props.on.openThread(thread.id, false),
                        },
                        children: [MindmapPreview.threadState(thread.status), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [MindmapPreview.threadTitle(thread)] })],
                    }),
            ],
        });
    }
    /** 「スレッドを開く」の入口（新しいスレッドの行は、まだ送っていないそのスレッドを開く。クローズのスレッドへの返信の行は、そのスレッドを開く） */
    function openThreadButton({ item, id, pending, className }, props) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: className, type: "button", "data-focus": `thread-open:${item.id}`, onclick: () => props.on.openThread(id, pending) },
            children: ["スレッドを開く"],
        });
    }
    /** レビュー中の書き込みの行 */
    function reviewRow(item, props) {
        const reason = props.stale.get(item.id);
        const label = reviewLabel(item);
        const blocked = isBlockedReply(item, props.threads);
        // 詳細パネルで書き換えている行は、入力欄を出さず、「修正」「削除」も出さない
        const editingInDetail = props.editing === item.id && props.editingIn === "detail";
        const editingInList = props.editing === item.id && !editingInDetail;
        const focused = item.id === props.selected || (props.reviewFocus !== null && item.thread === props.reviewFocus);
        return MindmapPreview.h({
            tag: "li",
            attrs: {
                class: `row${focused ? " selected" : ""}${reason === undefined ? "" : " stale"}${blocked ? " blocked" : ""}`,
                "data-comment": item.id,
            },
            children: [
                MindmapPreview.h({
                    tag: "input",
                    attrs: {
                        type: "checkbox",
                        class: "row-check",
                        checked: !blocked && props.checked.has(item.id),
                        disabled: blocked,
                        "aria-label": `${label}を送る`,
                        "data-focus": `check:${item.id}`,
                        onchange: (event) => props.on.check(item.id, event.target.checked),
                    },
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-main" },
                    children: [
                        rowHead(item, props),
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
                        editingInList
                            ? reviewEditForm({
                                item,
                                body: props.editBody ?? null,
                                error: props.editError ?? null,
                                focus: "",
                                on: { saveEdit: props.on.saveEdit, cancelEdit: props.on.cancelEdit },
                            })
                            : MindmapPreview.postBody({
                                body: item.body,
                                titles: () => null,
                                changeSets: props.changeSetOf,
                                className: "review-body",
                                on: { openId: (id) => props.on.openId(id), changeSet: props.on.changeSet },
                            }),
                        // クローズのスレッドへの返信: 送れない理由と、そのスレッドを開く入口
                        blocked && item.thread !== null
                            ? MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-stale row-blocked" },
                                children: [
                                    MindmapPreview.icon("alert"),
                                    MindmapPreview.h({ tag: "span", children: ["クローズのスレッドへの返信は送れません。オープンに戻すと送れます。"] }),
                                    openThreadButton({ item, id: item.thread, pending: false, className: "btn ghost" }, props),
                                ],
                            })
                            : null,
                        // 新しいスレッド: まだ送っていないそのスレッドを開く入口
                        item.thread === null
                            ? MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-thread-open" },
                                children: [openThreadButton({ item, id: item.id, pending: true, className: "btn ghost" }, props)],
                            })
                            : null,
                        reason === undefined
                            ? null
                            : MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-stale", role: "alert" },
                                children: [
                                    MindmapPreview.icon("alert"),
                                    MindmapPreview.h({ tag: "span", children: [reason] }),
                                    // 項目が記録にあるときだけ、箇所を外して項目へのコメントにできる
                                    item.loc !== null && item.target !== null && props.titleOf(item.target) !== null
                                        ? MindmapPreview.h({
                                            tag: "button",
                                            attrs: { class: "btn ghost", type: "button", "data-focus": `unloc:${item.id}`, onclick: () => props.on.unloc(item.id) },
                                            children: ["箇所を外す"],
                                        })
                                        : null,
                                ],
                            }),
                    ],
                }),
                editingInDetail ? null : reviewRowActions({ item, focus: "", on: { edit: props.on.edit, remove: props.on.remove } }),
            ],
        });
    }
    /** 送る帯の先頭に置く、文字を添えない三状態のチェックの箱。押すと、全てチェックしていれば全て外し、それ以外は全てチェックする */
    function selectAllBox({ ids, checked, onChange, }) {
        const count = ids.filter((id) => checked.has(id)).length;
        const checkbox = MindmapPreview.h({
            tag: "input",
            attrs: {
                type: "checkbox",
                checked: count === ids.length,
                "aria-label": "すべて選ぶ",
                onchange: () => onChange(count < ids.length),
            },
        });
        // 一部だけチェックしているときの横棒は、属性でなくプロパティで付ける
        checkbox.indeterminate = count > 0 && count < ids.length;
        return MindmapPreview.h({ tag: "label", attrs: { class: "legend-all-check", title: "すべて選ぶ" }, children: [checkbox] });
    }
    /** 見出しの帯（見出し・レビュー中の入口・閉じる） */
    function panelHead(props) {
        const count = props.items.length;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "comments-head" },
            children: [
                MindmapPreview.h({ tag: "h2", children: ["コメント"] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                // レビュー中の書き込みの画面では、入口を出さない（押しても何も変わらない）
                props.view === "review"
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: `btn review-entry${count === 0 ? " zero" : ""}`,
                            type: "button",
                            "aria-label": `レビュー中の書き込みを確かめる（${count} 件）`,
                            "data-focus": "review",
                            onclick: () => props.on.review(),
                        },
                        children: ["レビュー中", MindmapPreview.h({ tag: "span", attrs: { class: "count", "aria-hidden": "true" }, children: [count] })],
                    }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "icon-btn", type: "button", "aria-label": "コメントの一覧を閉じる", "data-focus": "close", onclick: props.on.close },
                    children: [MindmapPreview.icon("x")],
                }),
            ],
        });
    }
    /** 状態の絞り込みの選択肢 */
    const THREAD_FILTERS = [
        { value: "open", label: "オープン" },
        { value: "closed", label: "クローズ" },
        { value: "all", label: "すべて" },
    ];
    /** 0 件のときの文言 */
    function emptyThreadsText({ filter, tag }) {
        const state = { open: "オープンの", closed: "クローズの", all: "" }[filter];
        return tag === null ? `${state}スレッドはありません。` : `タグ「${tag}」の${state}スレッドはありません。`;
    }
    /** スレッドを読めなかった理由の文言 */
    function threadsErrorText(error) {
        return `スレッドを読めませんでした。${error.detail ?? "サーバーが止まっています。立ち上げ直してから開いてください。"}`;
    }
    /** 一覧の下端の、新しいスレッドを立てる入口と入力 */
    function newThreadBox(props) {
        if (!props.composing) {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-free talk-new" },
                children: [
                    MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "btn", type: "button", "data-focus": "compose", onclick: () => props.on.compose(true) },
                        children: [MindmapPreview.icon("plus"), "新しいスレッド"],
                    }),
                ],
            });
        }
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "comments-free talk-new open" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "talk-new-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "send-label" }, children: ["新しいスレッド"] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "新しいスレッドの入力を閉じる", "data-focus": "compose-close", onclick: () => props.on.compose(false) },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.sendForm({ ...props.free, collapsed: false }),
            ],
        });
    }
    /** スレッドの一覧（絞り込みの帯・行・下端の新しいスレッド）を返す */
    function threadListView(props) {
        const { threads, items, filter, tag, on } = props;
        const counts = threadCounts(threads, tag);
        const rows = visibleThreads(threads, filter, tag);
        const pending = pendingThreads(items, filter, tag);
        const total = threads.filter((thread) => filter === "all" || thread.status === filter).length;
        const empty = rows.length + pending.length === 0;
        return [
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "talk-band" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "segment talk-filter", role: "group", "aria-label": "スレッドの状態で絞る" },
                        children: THREAD_FILTERS.map((entry) => MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                type: "button",
                                "aria-pressed": String(entry.value === filter),
                                "data-focus": `filter:${entry.value}`,
                                onclick: () => on.filter(entry.value),
                            },
                            children: [entry.label, MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [counts[entry.value]] })],
                        })),
                    }),
                    tag === null
                        ? null
                        : MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "chips talk-chips" },
                            children: [
                                MindmapPreview.h({
                                    tag: "span",
                                    attrs: { class: "chip" },
                                    children: [
                                        MindmapPreview.icon("hash"),
                                        tag,
                                        MindmapPreview.h({
                                            tag: "button",
                                            attrs: { type: "button", "aria-label": `タグ「${tag}」の絞り込みを外す`, "data-focus": "clear-tag", onclick: () => on.clearTag() },
                                            children: [MindmapPreview.icon("x")],
                                        }),
                                    ],
                                }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "hint" }, children: [`${rows.length} / ${total} 件`] }),
                            ],
                        }),
                ],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body" },
                children: [
                    // 読めなかった理由は、並べる行の上に出す（まだ送っていない新しいスレッドは並べる）
                    props.threadsError === null
                        ? null
                        : MindmapPreview.h({ tag: "p", attrs: { class: "send-msg failed", role: "alert" }, children: [MindmapPreview.icon("alert"), threadsErrorText(props.threadsError)] }),
                    empty
                        ? props.threadsError === null
                            ? MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("comment"), emptyThreadsText({ filter, tag })] })
                            : null
                        : MindmapPreview.h({
                            tag: "ul",
                            attrs: { class: "th-list" },
                            children: [
                                ...pending.map((item) => MindmapPreview.threadRow({ pending: item, on: { open: on.openThread, tag: on.tag } })),
                                ...rows.map((thread) => MindmapPreview.threadRow({
                                    thread,
                                    hasPendingReply: items.some((item) => item.thread === thread.id),
                                    activeTag: tag,
                                    on: { open: on.openThread, tag: on.tag },
                                })),
                            ],
                        }),
                ],
            }),
            newThreadBox(props),
        ];
    }
    MindmapPreview.threadListView = threadListView;
    /** スレッドの見出し（戻る・状態を変える・理由の入力と失敗の理由・題・向けた項目とタグ） */
    function threadHead({ status, title, target, loc, tags, statusButton, extra, props, }) {
        const targetTitle = target === null ? null : props.titleOf(target);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "th-head" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "th-head-bar" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn ghost th-back", type: "button", "data-focus": "back", onclick: () => props.on.back() },
                            children: [MindmapPreview.icon("back"), "一覧へ戻る"],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        statusButton,
                    ],
                }),
                ...extra,
                MindmapPreview.h({ tag: "h3", attrs: { class: "th-heading" }, children: [MindmapPreview.threadState(status), MindmapPreview.h({ tag: "span", children: [title] })] }),
                target === null && tags.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "th-meta" },
                        children: [
                            target === null
                                ? null
                                : targetTitle === null
                                    ? MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] })] })
                                    : MindmapPreview.h({
                                        tag: "button",
                                        attrs: {
                                            class: "row-target",
                                            type: "button",
                                            "data-focus": "target",
                                            onclick: () => (loc === null ? props.on.openId(target) : props.on.openId(target, loc)),
                                        },
                                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [targetTitle] })],
                                    }),
                            ...tags.map((entry) => MindmapPreview.h({ tag: "span", attrs: { class: "th-tag static" }, children: [MindmapPreview.icon("hash"), MindmapPreview.h({ tag: "span", children: [entry] })] })),
                        ],
                    }),
            ],
        });
    }
    /** 理由の入力（任意）。状態を変える前に出し、確定で変えた後の状態と理由を 1 回で送る */
    function reasonForm({ closing, props }) {
        const { reason, on } = props;
        const saving = reason.status === "saving";
        const verb = closing ? "クローズにする" : "オープンに戻す";
        const field = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: "reason-body",
                name: "reason",
                rows: 2,
                maxlength: REASON_MAX_LENGTH,
                "aria-keyshortcuts": "Control+Enter",
                "data-focus": "reason",
                readonly: saving,
                // 打つたびには知らせず、確定のときに中身を渡す（描き直すときは、入口が入力欄から読む）
                onchange: () => on.reasonInput(field.value),
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では確定しない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        form.requestSubmit();
                    }
                    // Esc は理由の入力をやめる（一覧へは戻らない）
                    if (key.key === "Escape") {
                        key.preventDefault();
                        key.stopPropagation();
                        on.reasonOpen(false);
                    }
                },
            },
            children: [reason.body],
        });
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "th-reason",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    if (saving)
                        return;
                    on.setStatus(closing ? "closed" : "open", field.value);
                },
            },
            children: [
                MindmapPreview.h({ tag: "label", attrs: { class: "send-label", for: "reason-body" }, children: ["理由（任意）"] }),
                field,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-edit-actions" },
                    children: [
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn ghost", type: "button", "data-focus": "reason-cancel", onclick: () => on.reasonOpen(false) }, children: ["キャンセル"] }),
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn primary", type: "submit", "data-focus": "reason-ok", disabled: saving }, children: [verb] }),
                    ],
                }),
            ],
        });
        return form;
    }
    /** 状態を変えられなかった理由 */
    function statusFailure({ closing, detail }) {
        const head = closing ? "クローズにできませんでした。" : "オープンに戻せませんでした。";
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: "send-msg failed th-action-msg", role: "alert" },
            children: [MindmapPreview.icon("alert"), `${head}${detail ?? "サーバーが止まっています。立ち上げ直してから押してください。"}`],
        });
    }
    /** レビュー中の書き込みの `li`（スレッドの中のレビュー中の書き込み） */
    function pendingPostItem(item, props) {
        return MindmapPreview.threadPost({
            pending: item,
            titles: props.titleOf,
            changeSets: props.changeSetOf,
            editing: props.editing === item.id && props.editingIn !== "detail",
            editBody: props.editBody ?? null,
            editError: props.editError ?? null,
            on: {
                openId: (id) => props.on.openId(id),
                changeSet: props.on.changeSet,
                edit: props.on.edit,
                saveEdit: props.on.saveEdit,
                cancelEdit: props.on.cancelEdit,
                remove: props.on.remove,
            },
        });
    }
    /** まだ送っていない新しいスレッド（最初の書き込みをレビュー中の形で出し、状態を変えると返信の入力を出さない） */
    function pendingThreadView(commentId, props) {
        const item = props.items.find((entry) => entry.id === commentId);
        const gone = props.removed.find((entry) => entry.id === commentId);
        const shown = item ?? gone;
        return [
            threadHead({
                status: "pending",
                title: shown === undefined ? "" : shown.body.split("\n")[0],
                target: shown?.target ?? null,
                loc: shown?.loc ?? null,
                tags: [],
                statusButton: null,
                extra: [],
                props,
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body th-body" },
                children: [
                    MindmapPreview.h({
                        tag: "ol",
                        attrs: { class: "posts", "aria-label": "書き込み" },
                        children: [
                            item !== undefined
                                ? pendingPostItem(item, props)
                                : gone === undefined
                                    ? null
                                    : removedReviewRow({ item: gone, focus: "", on: { restore: props.on.restore } }),
                        ],
                    }),
                ],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-free" },
                children: [MindmapPreview.h({ tag: "p", attrs: { class: "th-closed-note" }, children: [MindmapPreview.icon("edit"), "まだ送っていないスレッドです。"] })],
            }),
        ];
    }
    /** スレッド 1 件（見出し・書き込みの並び・下端）を返す。まだ送っていない新しいスレッドも開く */
    function threadView(props) {
        const { opened } = props;
        if (opened !== null && opened.pending)
            return pendingThreadView(opened.id, props);
        const thread = props.threads.find((entry) => entry.id === opened?.id);
        // 開いているスレッドが無い（呼ぶ側が一覧へ戻す）
        if (thread === undefined)
            return [];
        const { reason, on } = props;
        const open = thread.status === "open";
        const saving = reason.status === "saving";
        // 理由の入力を出している間は、状態を変えるボタンを出さない
        const statusButton = reason.open
            ? null
            : MindmapPreview.h({
                tag: "button",
                attrs: { class: "btn", type: "button", "data-focus": "status", disabled: saving, onclick: () => on.reasonOpen(true) },
                children: open ? [MindmapPreview.icon("check"), "クローズにする"] : [MindmapPreview.icon("undo"), "オープンに戻す"],
            });
        // レビュー中の返信と、消した返信（元の場所に「元に戻す」を出す）を溜めた順に並べる
        const replies = [
            ...props.items.filter((item) => item.thread === thread.id).map((item) => ({ item, gone: false })),
            ...props.removed.filter((item) => item.thread === thread.id).map((item) => ({ item, gone: true })),
        ].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
        return [
            threadHead({
                status: thread.status,
                title: MindmapPreview.threadTitle(thread),
                target: thread.target,
                loc: thread.loc,
                tags: thread.tags,
                statusButton,
                extra: [
                    reason.open ? reasonForm({ closing: open, props }) : null,
                    reason.status === "failed" ? statusFailure({ closing: open, detail: reason.detail }) : null,
                ],
                props,
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body th-body" },
                children: [
                    MindmapPreview.h({
                        tag: "ol",
                        attrs: { class: "posts", "aria-label": "書き込み" },
                        children: [
                            ...threadTimeline(thread).map((entry) => "post" in entry
                                ? MindmapPreview.threadPost({ post: entry.post, titles: props.titleOf, changeSets: props.changeSetOf, on: { openId: (id) => on.openId(id), changeSet: on.changeSet, edit: on.edit, saveEdit: on.saveEdit, cancelEdit: on.cancelEdit, remove: on.remove } })
                                : MindmapPreview.threadPost({ event: entry.event, on: { openId: (id) => on.openId(id), changeSet: on.changeSet, edit: on.edit, saveEdit: on.saveEdit, cancelEdit: on.cancelEdit, remove: on.remove } })),
                            ...replies.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : pendingPostItem(item, props))),
                        ],
                    }),
                ],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-free" },
                children: [
                    open
                        ? MindmapPreview.replyForm({ thread: thread.id, ...props.reply, on: { input: on.replyInput, save: on.reply } })
                        : MindmapPreview.h({ tag: "p", attrs: { class: "th-closed-note" }, children: [MindmapPreview.icon("check"), "クローズにしたスレッドです。"] }),
                ],
            }),
        ];
    }
    MindmapPreview.threadView = threadView;
    /** レビュー中の書き込み（見出し・送る帯・行・空の状態）を返す */
    function reviewView(props) {
        const { items, removed, checked, result, on } = props;
        // 送れる書き込み（クローズのスレッドへの返信を除く）
        const sendable = items.filter((item) => !isBlockedReply(item, props.threads));
        const checkedCount = sendable.filter((item) => checked.has(item.id)).length;
        const isEmpty = items.length === 0 && removed.length === 0;
        // 送る帯は一覧の上端に留める。送っている間とチェックが 0 件のときは押せない
        const sending = result?.kind === "sending";
        const message = outcomeContent({ result, checkedCount });
        // 送った直後は、送るものが無くなっても結果を出す
        const band = isEmpty && result === null
            ? null
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "send-band" },
                children: [
                    sendable.length === 0
                        ? null
                        : selectAllBox({ ids: sendable.map((item) => item.id), checked, onChange: on.checkAll }),
                    sendable.length === 0
                        ? null
                        : MindmapPreview.h({ tag: "span", attrs: { class: "send-count" }, children: [`${checkedCount} / ${sendable.length} 件`] }),
                    isEmpty
                        ? null
                        : MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary",
                                type: "button",
                                "data-focus": "send",
                                disabled: checkedCount === 0 || sending,
                                onclick: () => on.send(),
                            },
                            children: [MindmapPreview.icon("send"), `まとめて送る（${checkedCount} 件）`],
                        }),
                    MindmapPreview.h({ tag: "p", attrs: { class: `send-msg${result === null ? "" : ` ${result.kind}`}`, role: "status" }, children: message ?? [] }),
                ],
            });
        // 消した書き込みは元の場所（ID の連番の順）に出す
        const rows = [...items.map((item) => ({ item, gone: false })), ...removed.map((item) => ({ item, gone: true }))].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
        const nodes = [
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "th-head review-head" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "th-head-bar" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "btn ghost th-back", type: "button", "data-focus": "back", onclick: () => on.back() },
                                children: [MindmapPreview.icon("back"), "戻る"],
                            }),
                            MindmapPreview.h({ tag: "h3", attrs: { class: "review-title" }, children: ["レビュー中の書き込み", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })] }),
                        ],
                    }),
                ],
            }),
            band,
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body" },
                children: [
                    isEmpty
                        ? MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("comment"), "レビュー中の書き込みはありません。"] })
                        : MindmapPreview.h({
                            tag: "ul",
                            attrs: { class: "comments-list" },
                            children: rows.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : reviewRow(item, props))),
                        }),
                ],
            }),
        ];
        return nodes.filter((node) => node !== null);
    }
    MindmapPreview.reviewView = reviewView;
    /** コメントの一覧を返す */
    function commentsPanel(props) {
        // 開いているスレッドが無いときは、スレッドの一覧を出す
        const threadScreen = props.view === "thread" ? threadView(props) : [];
        const screen = props.view === "review" ? reviewView(props) : threadScreen.length > 0 ? threadScreen : threadListView(props);
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "comments-panel", "aria-label": "コメントの一覧" },
            children: [panelHead(props), ...screen],
        });
    }
    MindmapPreview.commentsPanel = commentsPanel;
})(MindmapPreview || (MindmapPreview = {}));
