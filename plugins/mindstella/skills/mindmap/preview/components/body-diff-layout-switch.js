"use strict";
// 本文の差分の並べ方の切り替え。差分の表示の間、本文の差分の頭に「インライン」「左右に並べる」のボタンの組を置く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 切り替えの読み上げの名前と、表示の設定の「この端末で変えている項目」に出す名前 */
    MindmapPreview.BODY_LAYOUT_LABEL = "本文の差分の並べ方";
    /** 並べ方 → ボタンの文言 */
    const BODY_LAYOUT_BUTTON = { inline: "インライン", side: "左右に並べる" };
    /** 本文の差分の並べ方を切り替えるボタンの組を返す（描き直しは使う側が行う） */
    function bodyDiffLayoutSwitch({ layout, on }) {
        const button = (value) => MindmapPreview.h({
            tag: "button",
            attrs: {
                type: "button",
                "data-layout": value,
                "aria-pressed": String(layout === value),
                onclick: () => {
                    // 選んでいる並べ方を押しても何もしない
                    if (layout !== value)
                        on.change(value);
                },
            },
            children: [BODY_LAYOUT_BUTTON[value]],
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "segment sbs-switch", role: "group", "aria-label": MindmapPreview.BODY_LAYOUT_LABEL },
            children: [button("inline"), button("side")],
        });
    }
    MindmapPreview.bodyDiffLayoutSwitch = bodyDiffLayoutSwitch;
})(MindmapPreview || (MindmapPreview = {}));
