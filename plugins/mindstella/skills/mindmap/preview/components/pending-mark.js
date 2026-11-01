"use strict";
// 保存待ちの印。保存待ちの編集がある項目・キー・案に、破線の枠と印と文字の札を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類 → 札の文字とアイコン */
    const PENDING_MARKS = {
        pending: { label: "保存待ち", icon: "layers" },
        remove: { label: "保存で削除", icon: "trash" },
        blocked: { label: "書き込めない", icon: "alert" },
    };
    /** 保存待ちの印。差分の印・コメントの印と形で見分けられるよう、破線の枠（書き込めない編集は実線）にする */
    function pendingEditMark({ kind, compact = false }) {
        const { label, icon: name } = PENDING_MARKS[kind];
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: `pm pm-${kind}${compact ? " pm-compact" : ""}`, title: compact ? label : null },
            children: [
                MindmapPreview.icon(name),
                compact ? MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [label] }) : label,
            ],
        });
    }
    MindmapPreview.pendingEditMark = pendingEditMark;
    /** 項目の保存待ちの印（無ければ null）。カードと表の行は文字つき、マップの節は印だけ */
    function editMarkOf({ edit, id, compact = false, }) {
        const kind = edit?.marks[id];
        return kind === undefined ? null : pendingEditMark({ kind, compact });
    }
    MindmapPreview.editMarkOf = editMarkOf;
    /** 一覧の上の帯に置く「項目を追加」。幅 480px 以下は印だけにし、文字を読み上げに残す */
    function addItemButton({ kind, onAdd }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn pe-add",
                type: "button",
                "data-kind": kind,
                "aria-label": `${MindmapPreview.KIND_LABEL[kind]}の項目を追加`,
                title: "項目を追加",
                onclick: () => onAdd(),
            },
            children: [MindmapPreview.icon("plus"), MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["項目を追加"] })],
        });
    }
    MindmapPreview.addItemButton = addItemButton;
    /** 追加する項目のタイトル（まだ書いていなければ「（タイトル未入力）」） */
    function addedTitle(item) {
        return item.title === "" ? "（タイトル未入力）" : item.title;
    }
    MindmapPreview.addedTitle = addedTitle;
    /** 追加する項目のカード（ボード・資料のカード）。ID の場所に「ID は保存で決まる」を置く破線の枠 */
    function addedCard({ item, mark, open, doc = false, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `card${doc ? " doc-card" : ""} pe-new`,
                type: "button",
                "data-new-id": item.id,
                onclick: () => open(item.id),
            },
            children: [
                MindmapPreview.h({ tag: doc ? "span" : "div", attrs: { class: "c-ttl" }, children: [addedTitle(item)] }),
                MindmapPreview.h({
                    tag: doc ? "span" : "div",
                    attrs: { class: "c-meta" },
                    children: [MindmapPreview.h({ tag: "span", attrs: { class: "pe-noid" }, children: ["ID は保存で決まる"] }), pendingEditMark({ kind: mark })],
                }),
            ],
        });
    }
    MindmapPreview.addedCard = addedCard;
})(MindmapPreview || (MindmapPreview = {}));
