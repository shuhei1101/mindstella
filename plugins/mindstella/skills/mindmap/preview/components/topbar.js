"use strict";
// トップバー。話し合いの題名・全体の検索の入口・変更履歴・ライト / ダークの切り替え・絞り込みとコメントのボタンと、画面を移るタブの帯（右端につながりの入口）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 件数の表示を揺らさない上限 */
    const COMMENT_COUNT_CAP = 99;
    /** ブランドのマーク（木の形の線画） */
    function brandMark() {
        const holder = document.createElement("template");
        holder.innerHTML =
            '<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="16" r="4"/><path d="M12 16h5M17 16V7h5M17 16v9h5"/><circle cx="25" cy="7" r="2.6"/><circle cx="25" cy="25" r="2.6"/></svg>';
        return holder.content.firstElementChild;
    }
    /** 画面を移るリンク（ハッシュのリンクにして、押したときは使う側が移る） */
    function tabLink({ key, label, icon: iconName, count, marked = false }, current, onNavigate, extraClass = "") {
        return MindmapPreview.h({
            tag: "a",
            attrs: {
                class: `tab ${extraClass}`.trim(),
                href: `#${key === "overview" ? "" : `tab=${key}`}`,
                "data-tab": key,
                "aria-current": key === current ? "page" : null,
                onclick: (event) => {
                    event.preventDefault();
                    onNavigate(key);
                },
            },
            children: [
                MindmapPreview.icon(iconName),
                label,
                count === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [count] }),
                // 差分の表示の間、印の付いた項目を持つ種類に、件数を残したまま点を重ねる
                marked
                    ? MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "df-dot" },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["新規・変更の項目があります"] })],
                    })
                    : null,
            ],
        });
    }
    /** 「変更履歴」のボタン（印と文言）。押すと変更履歴のモーダルを開く */
    function historyButton(onClick) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "hist-btn",
                type: "button",
                "data-act": "hist",
                "aria-haspopup": "dialog",
                "aria-label": "変更履歴",
                onclick: onClick,
            },
            children: [MindmapPreview.icon("history"), MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["変更履歴"] })],
        });
    }
    /** 選んだ時点の札と、差分の表示をやめる × */
    function diffChip({ point, onOff }) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "df-chip" },
            children: [
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "df-chip-t", title: `${point.name}（${point.sub}）` },
                    children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["差分の時点: "] }), point.name],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        type: "button",
                        "data-act": "diffoff",
                        "aria-label": "差分の表示をやめる",
                        title: "差分の表示をやめる",
                        onclick: () => onOff?.(),
                    },
                    children: [MindmapPreview.icon("x")],
                }),
            ],
        });
    }
    /** サーバーにつながらないときの表示。広い幅は読んだ日時つきの文言、狭い幅は短い文言で、日時は `title` に持つ */
    function connectionNotice(readAt) {
        const readAtText = readAt === null ? null : MindmapPreview.formatJst(readAt);
        return MindmapPreview.h({
            tag: "span",
            attrs: {
                class: "conn",
                role: "status",
                title: readAtText === null ? "サーバーにつながりません" : `${readAtText} に読んだ記録を出しています`,
            },
            children: [
                MindmapPreview.icon("offline"),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "conn-long" },
                    children: [
                        readAtText === null
                            ? "サーバーにつながりません"
                            : `サーバーにつながりません（${readAtText} に読んだ記録）`,
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "conn-short" }, children: ["つながりません"] }),
            ],
        });
    }
    /** コメントのボタン（印と「コメント」と件数）。押すとコメントの一覧を開く・閉じる */
    function commentsButton({ count, open, onClick }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `comments-btn${open ? " open" : ""}`,
                type: "button",
                "data-act": "comments",
                "aria-label": `コメント（レビュー中 ${count} 件）`,
                "aria-expanded": String(open),
                onclick: () => onClick?.(),
            },
            children: [
                MindmapPreview.icon("comment"),
                MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["コメント"] }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: `count${count === 0 ? " zero" : ""}` },
                    children: [count > COMMENT_COUNT_CAP ? `${COMMENT_COUNT_CAP}+` : count],
                }),
            ],
        });
    }
    /** 絞り込みのボタン（印と「絞り込み」と、値を選んでいる条件の数のバッジ）。押すと絞り込みのドロワーを開く・閉じる */
    function filterButton({ count, open, onClick }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `filter-btn${open ? " open" : ""}`,
                type: "button",
                "data-act": "filter",
                "aria-label": count === 0 ? "絞り込み" : `絞り込み（${count} つの条件で絞り込み中）`,
                "aria-expanded": String(open),
                "aria-controls": "drawer",
                onclick: () => onClick?.(),
            },
            children: [
                MindmapPreview.icon("filter"),
                MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["絞り込み"] }),
                count === 0 ? null : MindmapPreview.h({ tag: "span", attrs: { class: "fbadge", "aria-hidden": "true" }, children: [count] }),
            ],
        });
    }
    /** トップバーとタブの帯を返す */
    function topbar({ title, tabs, current, theme, onNavigate, onSearch, onTheme, connection = "online", readAt = null, comments = false, commentCount = 0, commentsOpen = false, onComments, diffPoint = null, onHistory, onDiffOff, filter = false, filterCount = 0, filterOpen = false, onFilter, }) {
        const nextTheme = theme === "dark" ? "light" : "dark";
        const bar = MindmapPreview.h({
            tag: "header",
            attrs: { class: comments ? "topbar has-comments" : "topbar" },
            children: [
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "brand" },
                    children: [
                        brandMark(),
                        MindmapPreview.h({ tag: "span", attrs: { class: "brand-name" }, children: ["mindstella"] }),
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "brand-sub", title }, children: [title] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                connection === "offline" ? connectionNotice(readAt) : null,
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "search-trigger",
                        type: "button",
                        "data-act": "search",
                        "aria-label": "すべての項目を検索",
                        onclick: () => onSearch(),
                    },
                    children: [
                        MindmapPreview.icon("search"),
                        MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["すべての項目を検索"] }),
                        MindmapPreview.h({ tag: "kbd", children: ["/"] }),
                    ],
                }),
                onHistory === undefined ? null : historyButton(onHistory),
                // 差分の表示の間は、選んだ時点の札と外すボタンを「変更履歴」の右に出す
                diffPoint === null ? null : diffChip({ point: diffPoint, onOff: onDiffOff }),
                // コメントのボタンを右端に置くとき、検索の入口を中央へ寄せる
                comments ? MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }) : null,
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "top-btn",
                        type: "button",
                        "data-theme": nextTheme,
                        "aria-label": theme === "dark" ? "ライトに切り替え" : "ダークに切り替え",
                        onclick: () => onTheme(nextTheme),
                    },
                    children: [MindmapPreview.icon(theme === "dark" ? "sun" : "moon")],
                }),
                filter ? filterButton({ count: filterCount, open: filterOpen, onClick: onFilter }) : null,
                comments ? commentsButton({ count: commentCount, open: commentsOpen, onClick: onComments }) : null,
            ],
        });
        const tabbar = MindmapPreview.h({
            tag: "nav",
            attrs: { class: "tabbar", "aria-label": "項目の種類" },
            children: [
                ...tabs.map((tab) => tabLink(tab, current, onNavigate)),
                MindmapPreview.h({ tag: "span", attrs: { class: "tab-gap" } }),
                tabLink({ key: "graph", label: "つながり", icon: "orbit" }, current, onNavigate, "tab-special"),
            ],
        });
        return MindmapPreview.h({ tag: "div", attrs: { class: "top" }, children: [bar, tabbar] });
    }
    MindmapPreview.topbar = topbar;
})(MindmapPreview || (MindmapPreview = {}));
