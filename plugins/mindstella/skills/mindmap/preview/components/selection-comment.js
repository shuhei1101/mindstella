"use strict";
// 選んだ箇所のコメントの入口。本文の文章か項目の値を選び終えたときに、選んだ範囲の近くに出す印だけの丸いボタン。
var MindmapPreview;
(function (MindmapPreview) {
    /** 入口の大きさ（位置を決めるため固定する）。押せる的は高さ 32px 以上 */
    const BUTTON_SIZE = 32;
    /** 選んだ範囲との間の空きと、画面の端から内側に収める幅 */
    const BUTTON_GAP = 6;
    const SCREEN_EDGE = 8;
    /** 入口の名前（読み上げとツールチップ） */
    const BUTTON_NAME = "選んだ箇所にコメント";
    /** 入口を返す。選んだ範囲の始まりの上に出し、上に収まらなければ終わりの下に出す。左右は画面の端から内側に収める */
    function selectionComment({ anchor, area, on }) {
        const above = anchor.first.top - BUTTON_GAP - BUTTON_SIZE;
        // 画面の端とスクロール領域の上端の内側に収まるか
        const fitsAbove = above >= Math.max(SCREEN_EDGE, area.scroller.top);
        const side = fitsAbove ? "above" : "below";
        const top = fitsAbove ? above : anchor.last.bottom + BUTTON_GAP;
        const edge = fitsAbove ? anchor.first.left : anchor.last.left;
        const left = Math.max(SCREEN_EDGE, Math.min(edge, area.viewport.width - SCREEN_EDGE - BUTTON_SIZE));
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "selection-comment",
                type: "button",
                "aria-label": BUTTON_NAME,
                "data-side": side,
                // 画面の右半分に出した入口は、ツールチップを入口の右端に揃える
                "data-tip": left + BUTTON_SIZE / 2 > area.viewport.width / 2 ? "end" : "start",
                style: `position:fixed;left:${left}px;top:${top}px;width:${BUTTON_SIZE}px;height:${BUTTON_SIZE}px`,
                // 押したときに選択が外れないよう、ポインターを押した既定の動き（選択の解除）を止める
                onpointerdown: (event) => event.preventDefault(),
                onclick: () => on.press(),
                onkeydown: (event) => {
                    if (event.key === "Escape") {
                        // 入口だけを閉じる。詳細パネルを閉じる Esc・モーダルを閉じる動きとして受けさせない
                        event.stopPropagation();
                        event.preventDefault();
                        on.close();
                    }
                },
            },
            children: [
                MindmapPreview.icon("comment"),
                // 名前のツールチップ。読み上げの名前は入口のボタンが持つので、二度読まれないよう読み上げから外す
                MindmapPreview.h({ tag: "span", attrs: { class: "sc-tip", "aria-hidden": "true" }, children: [BUTTON_NAME] }),
            ],
        });
    }
    MindmapPreview.selectionComment = selectionComment;
})(MindmapPreview || (MindmapPreview = {}));
