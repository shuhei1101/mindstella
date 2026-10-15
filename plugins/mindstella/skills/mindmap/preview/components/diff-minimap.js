"use strict";
// 差分のミニマップ。差分の表示の間、詳細の本文のスクロール領域を包み、スクロールバーの外側に変わった箇所の印を並べた縦の帯を置く。印・印の無い所を押す・帯を押したまま上下に動かすと、履歴とハッシュを変えずに本文を送る。
var MindmapPreview;
(function (MindmapPreview) {
    /** 印の帯の向きの最小の長さ（px）。押せる的を保つ */
    const MINIMAP_MARK_MIN_PX = 12;
    /** 印が帯に収まらないほど多いときに縮める、最小の長さの下限（px） */
    const MINIMAP_MARK_FLOOR_PX = 4;
    /** 重なる印をずらすときに空ける間（px） */
    const MINIMAP_MARK_GAP_PX = 2;
    /** 印を押したとき、その箇所の上端を置く本文のスクロール領域の高さに対する割合 */
    const MINIMAP_JUMP_RATIO = 0.25;
    /** 飛んだ箇所に枠を付けておくミリ秒 */
    const MINIMAP_HIT_MS = 1600;
    /** 印の種類 → 読み上げの名前と `title` の頭 */
    const MINIMAP_KIND_NAME = {
        add: "足した箇所",
        del: "消した箇所",
        chg: "変わった箇所",
    };
    /** 印にする要素（キーの差分の行・本文の足した / 消した塊・箇条書きの足した項目・表の行・図の差分の枠・Raw の行） */
    const MINIMAP_TARGET_SELECTOR = [
        ".df-kv",
        ".md ins.df-blk",
        ".md del.df-blk",
        ".md li.df-li-add",
        ".md tr.df-add",
        ".md tr.df-del",
        ".diagram.df-changed",
        ".diagram.df-frame",
        ".df-raw .df-line.df-add",
        ".df-raw .df-line.df-del",
    ].join(", ");
    /** 要素が見えているか（畳んだ Raw などは矩形を持たない） */
    function isRendered(element) {
        return element.getClientRects().length > 0;
    }
    MindmapPreview.isRendered = isRendered;
    /** 前に無かったキーの差分の行か（前の値が「（なし）」） */
    function isNewKey(row) {
        const was = row.querySelector("del.df-was");
        if (was === null)
            return false;
        // 読み上げだけに残した「前の値: 」は除く
        const text = [...was.childNodes]
            .filter((node) => !(node instanceof Element && node.classList.contains("sr-only")))
            .map((node) => node.textContent ?? "")
            .join("")
            .trim();
        return text === MindmapPreview.NO_VALUE;
    }
    /** 印にする要素の種類 */
    function minimapKindOf(element) {
        if (element.matches(".diagram"))
            return "chg";
        if (element.matches(".df-kv"))
            return isNewKey(element) ? "add" : "chg";
        return element.matches("del, .df-del") ? "del" : "add";
    }
    /** 本文のスクロール領域の中の差分の印を、文書の順にミニマップの印にまとめて返す */
    function minimapTargets(body) {
        const found = [];
        for (const element of body.querySelectorAll(MINIMAP_TARGET_SELECTOR)) {
            // 見えていない印と、Raw を出している図の枠（Raw の行を並べる）は飛ばす。Raw を畳んだ図は枠を印にする
            if (!isRendered(element))
                continue;
            if (element.matches(".diagram") && [...element.querySelectorAll(".df-raw")].some(isRendered))
                continue;
            const kind = minimapKindOf(element);
            const previous = found.at(-1);
            const follows = previous !== undefined && previous.frame === null && previous.last.nextElementSibling === element;
            if (previous !== undefined && follows && previous.kind === "del" && kind === "add" && element.matches(".df-blk") && previous.last.matches(".df-blk")) {
                // 消した塊のすぐ後ろの足した塊: 書き換えた箇所
                previous.kind = "chg";
                previous.last = element;
            }
            else if (previous !== undefined && follows && previous.kind === kind) {
                // 続く同じ種類の塊・行
                previous.last = element;
            }
            else {
                found.push({ kind, first: element, last: element, frame: null });
            }
        }
        // 左右に並べた本文の印は列ごとに文書の順に並ぶので、高さの順に並べ直し、向かい合う消した塊と足した塊を「変わった」1 つにする
        if (body.querySelector(".sbs") !== null) {
            const topOf = (target) => target.first.getBoundingClientRect().top;
            found.sort((a, b) => topOf(a) - topOf(b));
            for (let position = found.length - 1; position > 0; position -= 1) {
                const upper = found[position - 1];
                const lower = found[position];
                if (upper === undefined || lower === undefined)
                    continue;
                const kinds = [upper.kind, lower.kind].sort().join();
                // 上の印の下端より上で始まる、もう片側の印
                if (kinds === "add,del" && topOf(lower) < upper.last.getBoundingClientRect().bottom) {
                    upper.kind = "chg";
                    found.splice(position, 1);
                }
            }
        }
        // HTML の本文の枠の中の印
        for (const frame of body.querySelectorAll("iframe.html-frame")) {
            if (!isRendered(frame))
                continue;
            for (const element of frame.contentDocument?.querySelectorAll("[data-df]") ?? []) {
                found.push({ kind: element.getAttribute("data-df") === "add" ? "add" : "chg", first: element, last: element, frame });
            }
        }
        return found;
    }
    MindmapPreview.minimapTargets = minimapTargets;
    /** 印が指す箇所の、本文の中身の上端からの位置と高さ */
    function minimapExtent({ body, target }) {
        const base = body.getBoundingClientRect().top - body.scrollTop;
        // 枠の中の要素の位置は枠の上端から測るため、枠の上端を足す
        const shift = target.frame === null ? 0 : target.frame.getBoundingClientRect().top;
        const top = target.first.getBoundingClientRect().top + shift - base;
        const bottom = target.last.getBoundingClientRect().bottom + shift - base;
        return { top, size: bottom - top };
    }
    /** 印の本文の中の位置と高さから、帯の中の印の始まりと長さを決める。位置と長さは本文の全体の高さに対する割合で置き、最小の長さと重なりを直す */
    function minimapLayout({ extents, total, length }) {
        // 印が多いときは最小の長さを詰める
        const min = Math.max(MINIMAP_MARK_FLOOR_PX, Math.min(MINIMAP_MARK_MIN_PX, Math.floor(length / Math.max(extents.length, 1)) - MINIMAP_MARK_GAP_PX));
        const placed = [];
        let end = 0;
        for (const extent of extents) {
            const size = Math.max(min, (extent.size / total) * length);
            const start = Math.max((extent.top / total) * length, end);
            placed.push({ start, size });
            end = start + size + MINIMAP_MARK_GAP_PX;
        }
        // 帯の終わりを出た印は、後ろから前へ詰める
        let limit = length;
        for (const mark of [...placed].reverse()) {
            mark.start = Math.max(0, Math.min(mark.start, limit - mark.size));
            limit = mark.start - MINIMAP_MARK_GAP_PX;
        }
        return placed;
    }
    MindmapPreview.minimapLayout = minimapLayout;
    /** 印の箇所まで本文を送り、その箇所を少しの間だけ枠で示す（履歴にもハッシュにも触れない） */
    function jumpToTarget({ body, target }) {
        const { top } = minimapExtent({ body, target });
        const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
        body.scrollTo({ top: Math.max(0, top - body.clientHeight * MINIMAP_JUMP_RATIO), behavior: reduce ? "auto" : "smooth" });
        // 枠の中の要素には枠の外のスタイルが当たらないため、示すのは枠の外の箇所だけ
        if (target.frame !== null)
            return;
        const hits = [];
        for (let element = target.first; element !== null; element = element.nextElementSibling) {
            hits.push(element);
            if (element === target.last)
                break;
        }
        for (const element of hits)
            element.classList.add("df-map-hit");
        window.setTimeout(() => hits.forEach((element) => element.classList.remove("df-map-hit")), MINIMAP_HIT_MS);
    }
    /** 帯のマウスの操作。押したまま上下に動かすと本文をスクロールバーと同じように送り、印の無い所を押すとその位置まで本文をすぐ送る */
    function bindMinimapPointer({ map, view, body }) {
        let drag = null;
        let dragged = false;
        /** ドラッグの間の指の位置に、見えている範囲の面が来るまで本文を送る */
        const dragTo = (clientY) => {
            if (drag === null)
                return;
            const rect = map.getBoundingClientRect();
            body.scrollTop = ((clientY - rect.top - drag.grab) / rect.height) * body.scrollHeight;
        };
        /** ドラッグを終える（離した・取り消された・押していない動きを受けた） */
        const endDrag = (event) => {
            if (drag === null || event.pointerId !== drag.id)
                return;
            drag = null;
            map.classList.remove("is-dragging");
            document.body.classList.remove("df-map-dragging");
            // 離した直後の click まで印を押した扱いにしないよう、次のコマで戻す
            requestAnimationFrame(() => {
                dragged = false;
            });
        };
        map.addEventListener("pointerdown", (event) => {
            // マウスの左ボタンだけ（タッチの端末ではドラッグしない）。本文が送れないときは何もしない
            if (event.pointerType !== "mouse" || event.button !== 0 || view.hidden)
                return;
            const face = view.getBoundingClientRect();
            const inside = event.clientY >= face.top && event.clientY <= face.bottom;
            // 面の中を押したときはつかんだ位置を保ち、外を押したときは面の中央を押した所に合わせる
            drag = { id: event.pointerId, startY: event.clientY, grab: inside ? event.clientY - face.top : face.height / 2 };
            dragged = false;
        });
        map.addEventListener("pointermove", (event) => {
            if (drag === null || event.pointerId !== drag.id)
                return;
            // ボタンを押していない動き（帯の外で離して pointerup が届かなかった）は、ドラッグを終えて送らない
            if ((event.buttons & 1) === 0) {
                endDrag(event);
                return;
            }
            // 押した位置から少し動くまでは、印を押しただけとして扱う
            if (!dragged && Math.abs(event.clientY - drag.startY) <= MindmapPreview.PRESS_SLOP_PX)
                return;
            if (!dragged) {
                dragged = true;
                map.setPointerCapture(event.pointerId);
                map.classList.add("is-dragging");
                document.body.classList.add("df-map-dragging");
            }
            dragTo(event.clientY);
        });
        map.addEventListener("pointerup", endDrag);
        map.addEventListener("pointercancel", endDrag);
        // ドラッグの間に帯が文書から外れたときも、ドラッグの見た目を戻す
        map.addEventListener("lostpointercapture", endDrag);
        // 印の無い所を動かさずに押して離すと、押した位置に見えている範囲の面の中央を合わせるまで本文をすぐ送る（タッチの端末も同じ）
        map.addEventListener("click", (event) => {
            if (dragged || view.hidden || event.target.closest(".df-map-m") !== null)
                return;
            const rect = map.getBoundingClientRect();
            body.scrollTop = ((event.clientY - rect.top) / rect.height) * body.scrollHeight - body.clientHeight / 2;
        });
        return { justDragged: () => dragged };
    }
    /** 本文のスクロール領域を `div.panel-scroll` で包んで返す。`shown` が真なら本文の右に帯を並べ、印があるときだけ出す */
    function diffMinimapFrame({ body, shown }) {
        const frame = MindmapPreview.h({ tag: "div", attrs: { class: "panel-scroll" }, children: [body] });
        if (!shown)
            return frame;
        // 見えている範囲の面
        const view = MindmapPreview.h({ tag: "span", attrs: { class: "df-map-view", "aria-hidden": "true" } });
        const map = MindmapPreview.h({
            tag: "div",
            attrs: { class: "df-map", role: "toolbar", "aria-orientation": "vertical", "aria-label": "変わった箇所", hidden: true },
            children: [view],
        });
        const pointer = bindMinimapPointer({ map, view, body });
        let targets = [];
        // タブの止まりにする印（最後に選んだ印）
        let current = 0;
        /** 見えている範囲の面を、本文の送りに合わせて置く */
        const placeView = () => {
            const scrollable = body.scrollHeight > body.clientHeight;
            view.hidden = !scrollable;
            if (!scrollable)
                return;
            view.style.top = `${(body.scrollTop / body.scrollHeight) * 100}%`;
            view.style.height = `${(body.clientHeight / body.scrollHeight) * 100}%`;
        };
        /** 印を集め直して並べ直す。印が無ければ帯ごと出さない */
        const rebuild = () => {
            const focused = map.contains(document.activeElement);
            // 後から足された子の高さの変化も見張る（同じ要素を重ねて見張っても 1 回だけ数える）
            for (const child of body.children)
                resized.observe(child);
            targets = minimapTargets(body);
            map.hidden = targets.length === 0;
            frame.classList.toggle("has-map", targets.length > 0);
            if (targets.length === 0) {
                map.replaceChildren(view);
                return;
            }
            current = Math.min(current, targets.length - 1);
            const placed = minimapLayout({
                extents: targets.map((target) => minimapExtent({ body, target })),
                total: body.scrollHeight,
                length: map.clientHeight,
            });
            const marks = targets.map((target, at) => {
                const name = `${MINIMAP_KIND_NAME[target.kind]}（${at + 1} / ${targets.length}）`;
                const { start, size } = placed[at];
                return MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: `df-map-m df-${target.kind}`,
                        type: "button",
                        "aria-label": name,
                        title: name,
                        tabindex: at === current ? "0" : "-1",
                        style: `top:${start}px;height:${size}px`,
                        onclick: () => {
                            // ドラッグで送った後に離した印は、飛ばない
                            if (pointer.justDragged())
                                return;
                            current = at;
                            jumpToTarget({ body, target });
                            rebuild();
                            map.querySelectorAll(".df-map-m")[at]?.focus();
                        },
                    },
                    children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } })],
                });
            });
            map.replaceChildren(view, ...marks);
            placeView();
            if (focused)
                marks[current]?.focus();
        };
        // 上下の矢印と Home / End で印の間を移る
        map.addEventListener("keydown", (event) => {
            const moves = { ArrowUp: current - 1, ArrowDown: current + 1, Home: 0, End: targets.length - 1 };
            const next = moves[event.key];
            if (next === undefined || next < 0 || next >= targets.length)
                return;
            event.preventDefault();
            current = next;
            const marks = [...map.querySelectorAll(".df-map-m")];
            marks.forEach((mark, at) => mark.setAttribute("tabindex", at === current ? "0" : "-1"));
            marks[current]?.focus();
        });
        frame.append(map);
        // 本文の高さが変わったとき（図の描き終わり・HTML の本文の枠の高さ・Raw の切り替え・パネルの幅）だけ置き直す
        let queued = false;
        const schedule = () => {
            if (queued)
                return;
            queued = true;
            requestAnimationFrame(() => {
                queued = false;
                rebuild();
            });
        };
        const resized = new ResizeObserver(schedule);
        resized.observe(body);
        new MutationObserver(schedule).observe(body, { childList: true, subtree: true });
        body.addEventListener("load", schedule, true);
        // 送るたびに動かすのは、見えている範囲の面だけ
        body.addEventListener("scroll", placeView, { passive: true });
        schedule();
        return frame;
    }
    MindmapPreview.diffMinimapFrame = diffMinimapFrame;
})(MindmapPreview || (MindmapPreview = {}));
