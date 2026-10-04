"use strict";
// 選んだ箇所のコメントの入口。本文の文章か項目の値を選び終えたときに、選んだ範囲の近くに出すピルの形のボタン。
var MindmapPreview;
(function (MindmapPreview) {
    /** 入口の大きさ（位置を決めるため固定する）。押せる的は高さ 32px 以上 */
    const PILL_WIDTH = 104;
    const PILL_HEIGHT = 32;
    /** 選んだ範囲との間の空きと、画面の端から内側に収める幅 */
    const PILL_GAP = 6;
    const SCREEN_EDGE = 8;
    /** 入口を返す。選んだ範囲の終わりの下に出し、下に収まらなければ始まりの上に出す。左右は画面の端から内側に収める */
    function selectionComment({ anchor, placement, on }) {
        // 画面の大きさは、いま開いている画面から引く
        const viewport = { width: window.innerWidth, height: window.innerHeight };
        const below = anchor.last.bottom + PILL_GAP;
        // 向きを渡されなければ下に出し、下に収まらないときは選んだ範囲の始まりの上に出す
        const above = placement === undefined ? below + PILL_HEIGHT > viewport.height - SCREEN_EDGE : placement === "above";
        const top = above ? anchor.first.top - PILL_GAP - PILL_HEIGHT : below;
        const left = Math.max(SCREEN_EDGE, Math.min(anchor.last.left, viewport.width - SCREEN_EDGE - PILL_WIDTH));
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "selection-comment",
                type: "button",
                "aria-label": "選んだ箇所にコメント",
                style: `position:fixed;left:${left}px;top:${top}px;width:${PILL_WIDTH}px;height:${PILL_HEIGHT}px`,
                // 押したときに選択が外れないよう、ポインターを押した既定の動き（選択の解除）を止める
                onpointerdown: (event) => event.preventDefault(),
                onclick: () => on.press(),
                onkeydown: (event) => {
                    if (event.key === "Escape")
                        on.close();
                },
            },
            children: [MindmapPreview.icon("comment"), MindmapPreview.h({ tag: "span", children: ["コメント"] })],
        });
    }
    MindmapPreview.selectionComment = selectionComment;
})(MindmapPreview || (MindmapPreview = {}));
