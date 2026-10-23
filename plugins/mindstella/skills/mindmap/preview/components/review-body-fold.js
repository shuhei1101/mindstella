"use strict";
// レビュー中の書き込みの本文の折りたたみ。折り返した後の見た目の行で一定の行数までに本文を畳み、超えるときだけ開閉のボタンを出す。本文の要素と開閉のボタンを別々に返し、ボタンの置き場所は使う側が決める。
var MindmapPreview;
(function (MindmapPreview) {
    /** 畳んだときに出す、折り返した後の見た目の行の数 */
    MindmapPreview.REVIEW_FOLD_LINES = 5;
    /** 全文の高さが、行の高さ × 行数を超えたとみなす余裕（小数の丸め） */
    const FOLD_TOLERANCE_PX = 1;
    /** 開閉のボタンの文言・矢印・読み上げの名前を、開いているかに合わせる */
    function setToggle({ more, open, label }) {
        more.setAttribute("aria-expanded", String(open));
        more.setAttribute("aria-label", open ? `${label}の本文を折りたたむ` : `${label}の続きを読む`);
        more.replaceChildren(MindmapPreview.icon("chev"), MindmapPreview.h({ tag: "span", children: [open ? "折りたたむ" : "続きを読む"] }));
    }
    /** 全文が畳む行の数を超えるか */
    function exceedsLines({ body, lines }) {
        const lineHeight = parseFloat(getComputedStyle(body).lineHeight);
        // 畳んでいても scrollHeight は全文の高さを返す
        return body.scrollHeight > lineHeight * lines + FOLD_TOLERANCE_PX;
    }
    /** 本文を畳み、開閉のボタンを添えて返す */
    function reviewBodyFold({ id, label, body, changeSets = () => null, open = false, lines = MindmapPreview.REVIEW_FOLD_LINES, on }) {
        const bodyId = `review-body-${id}`;
        const text = MindmapPreview.postBody({
            body,
            titles: () => null,
            changeSets,
            className: "review-body",
            // 項目の ID は文字のまま出すので、押されることは無い
            on: { openId: () => undefined, changeSet: on.changeSet },
        });
        text.id = bodyId;
        text.style.setProperty("--fold-lines", String(lines));
        let opened = open;
        const more = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn ghost review-more",
                type: "button",
                // 測るまでは出さない
                hidden: true,
                "aria-controls": bodyId,
                "data-focus": `more:${id}`,
                onclick: () => {
                    opened = !opened;
                    text.classList.toggle("folded", !opened);
                    setToggle({ more, open: opened, label });
                    // 折りたたんだ行が画面から外れないように寄せる
                    if (!opened)
                        text.closest("li")?.scrollIntoView({ block: "nearest" });
                    on.toggle(id, opened);
                },
            },
        });
        setToggle({ more, open: opened, label });
        // 超えるときだけ畳んで開閉のボタンを出す
        const measure = () => {
            const exceeds = exceedsLines({ body: text, lines });
            text.classList.toggle("folded", exceeds && !opened);
            more.hidden = !exceeds;
        };
        // 描いた直後は、描画の前のフレームで測る
        requestAnimationFrame(measure);
        // 本文の幅が変わると折り返しが変わる。通知の中で本文の高さを変えると通知を送りきれないので、次のフレームで測り直す
        new ResizeObserver(() => requestAnimationFrame(measure)).observe(text);
        return { body: text, more };
    }
    MindmapPreview.reviewBodyFold = reviewBodyFold;
})(MindmapPreview || (MindmapPreview = {}));
