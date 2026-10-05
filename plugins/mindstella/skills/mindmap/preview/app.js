"use strict";
// 起動。記録を読み（配る書き出しは埋め込みから、サーバーの配信は記録の取得から）、URL のハッシュが指す画面を描き、操作を画面の移動・書き換えの知らせ・コメントの読み書き・端末の保存領域につなぐ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 埋め込みのデータの要素の ID */
    const DATA_ELEMENT_ID = "mindmap-data";
    /** 端末の保存領域のキー */
    MindmapPreview.PREFS_KEY = "mindmap-preview";
    /** 入力が止まってから書きかけを保つまでの待ち（ミリ秒）。打つたびに書かず、打ち終えた直後に閉じても失うのがこの待ちの分だけで済む長さ */
    MindmapPreview.DRAFT_SAVE_DELAY_MS = 500;
    /** 入力欄のキー。向けた先（`target` と `loc` の組）を 1 つの文字列にする */
    function formKey(target, loc) {
        return JSON.stringify([target, loc?.kind ?? null, loc?.start ?? null, loc?.end ?? null, loc?.key ?? null, loc?.text ?? null]);
    }
    MindmapPreview.formKey = formKey;
    /** 狭い幅（詳細パネルを別画面として積む幅） */
    const NARROW_QUERY = "(max-width: 900px)";
    /** タブのアイコン */
    const TAB_ICON = {
        overview: "home",
        decisions: "decision",
        tasks: "task",
        research: "research",
        docs: "doc",
        terms: "term",
        notes: "note",
        logs: "log",
    };
    /** タブの名前（種類の名前は読み込み順によらないよう、呼ばれたときに引く） */
    function tabLabel(key) {
        return key === "overview" ? "概要" : MindmapPreview.KIND_LABEL[key];
    }
    /** 画面の名前（つながりは種類のタブに無いので、ここで持つ） */
    function screenName(tab) {
        return tab === "graph" ? "つながり" : tabLabel(tab);
    }
    /** `mindmap-data` の要素の中身を `JSON.parse` して返す。中身が空なら（サーバーの配信）null */
    function readEmbeddedData(doc) {
        const text = doc.getElementById(DATA_ELEMENT_ID)?.textContent;
        // 要素が無い（同梱の雛形か書き出しの誤り）
        if (text === undefined || text === null)
            throw new Error("記録を読み込めませんでした。");
        // 中身が空: サーバーの配信なので、記録は取得で読む
        if (text.trim() === "")
            return null;
        try {
            return JSON.parse(text);
        }
        catch {
            throw new Error("記録を読み込めませんでした。");
        }
    }
    MindmapPreview.readEmbeddedData = readEmbeddedData;
    /** 既定の設定 */
    function defaultPrefs() {
        return { theme: null, columns: {} };
    }
    /** 端末の保存領域から設定を読む。読めないときは既定を返す */
    function loadPrefs(storage) {
        try {
            const saved = storage.getItem(MindmapPreview.PREFS_KEY);
            if (saved === null)
                return defaultPrefs();
            const parsed = JSON.parse(saved);
            return { ...defaultPrefs(), ...parsed };
        }
        catch {
            return defaultPrefs();
        }
    }
    MindmapPreview.loadPrefs = loadPrefs;
    /** 設定を端末の保存領域に残す。保存領域が例外を送るときは何もしない */
    function savePrefs({ storage, prefs }) {
        try {
            storage.setItem(MindmapPreview.PREFS_KEY, JSON.stringify(prefs));
        }
        catch {
            // 保存できない環境では、開いている間だけ設定を保つ
        }
    }
    MindmapPreview.savePrefs = savePrefs;
    /** 端末の保存領域（開けない環境では、何も返さない保存領域） */
    function openStorage(kind) {
        try {
            return window[kind];
        }
        catch {
            return {
                length: 0,
                clear: () => undefined,
                getItem: () => null,
                key: () => null,
                removeItem: () => undefined,
                setItem: () => undefined,
            };
        }
    }
    /** 記録を読み、ハッシュが指す画面を描き、操作と履歴をつなぐ */
    function start() {
        let embedded;
        try {
            embedded = readEmbeddedData(document);
        }
        catch (error) {
            document.body.prepend(MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: [error.message] }));
            return;
        }
        void run(embedded);
    }
    MindmapPreview.start = start;
    /** サーバーが記録を読めるまで待つ。読めない間は、接続の状態と理由だけを出し、書き換えの知らせか接続が戻ったときに読み直す */
    function waitForRecords(theme) {
        const holder = MindmapPreview.h({ tag: "div", attrs: { id: "unavailable" } });
        document.body.prepend(holder);
        return new Promise((resolve) => {
            const attempt = async () => {
                const result = await MindmapPreview.fetchRecords();
                if (result.ok) {
                    stop();
                    holder.remove();
                    resolve(result.data);
                    return;
                }
                const message = result.reason === "invalid" && result.detail !== null
                    ? result.detail
                    : "サーバーにつながりません。起動スクリプトで立ち上げ直し、示された新しい URL で開いてください。";
                holder.replaceChildren(MindmapPreview.topbar({
                    title: "mindstella",
                    tabs: [],
                    current: "overview",
                    theme,
                    onNavigate: () => undefined,
                    onSearch: () => undefined,
                    onTheme: () => undefined,
                    connection: "offline",
                }), MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: [message] }));
            };
            const stop = MindmapPreview.subscribeEvents({
                onChanged: () => void attempt(),
                onConnection: (connected) => {
                    if (connected)
                        void attempt();
                },
            });
            void attempt();
        });
    }
    /** 記録を用意し（サーバーの配信では取得して）、画面を描いて操作とつなぐ */
    async function run(embedded) {
        /** サーバーの配信か（配る書き出しは記録を埋め込みから読み、送信も書き換えの知らせも持たない） */
        const serverMode = embedded === null;
        const storage = openStorage("localStorage");
        const prefs = loadPrefs(storage);
        const persist = () => savePrefs({ storage, prefs });
        MindmapPreview.restoreTablePrefs(prefs.columns, (kind, tablePrefs) => {
            if (tablePrefs === null)
                delete prefs.columns[kind];
            else
                prefs.columns[kind] = tablePrefs;
            persist();
        });
        // ===== テーマ =====
        let theme = prefs.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        document.documentElement.dataset["theme"] = theme;
        // ===== 記録 =====
        let data = embedded ?? (await waitForRecords(theme));
        let index = MindmapPreview.buildIndex(data);
        document.title = `${data.settings.summary} | mindstella`;
        let connection = "online";
        // ===== 画面の土台 =====
        const top = MindmapPreview.h({ tag: "div", attrs: { id: "top" } });
        const main = MindmapPreview.h({ tag: "main", attrs: { class: "content", id: "main" } });
        document.body.prepend(top, main);
        let route = MindmapPreview.parseHash({ hash: location.hash, index });
        let fullViewer = null;
        // ===== 移動 =====
        /** 詳細パネルを別画面として積む幅か */
        const isNarrow = () => matchMedia(NARROW_QUERY).matches;
        /** 画面の既定の URL（絞り込みは書かない）に route を書き、画面を描く */
        const go = (next, push) => {
            const screenChanged = next.tab !== route.tab || next.view !== route.view || Object.keys(next.filters).length > 0;
            const idChanged = next.id !== route.id;
            route = next;
            MindmapPreview.navigate({ route: { ...route, filters: {} }, push });
            render({ screen: screenChanged || (route.tab === "decisions" && route.view === "map" && idChanged) });
        };
        /** 項目を開く。パネル・全画面の中の移動は履歴に積み、見てきた項目を行き来できるようにする */
        const openItem = (id, inPanel) => {
            flushDrafts();
            const next = { ...route, id, filters: {} };
            const trail = history.state;
            if (inPanel && route.id !== null) {
                // 今いる履歴にも先の項目を持たせ、戻った後に「→」で進めるようにする
                const items = [...(trail?.items ?? [route.id]).slice(0, (trail?.position ?? 0) + 1), id];
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false, trail: { items, position: trail?.position ?? 0 } });
                route = next;
                MindmapPreview.navigate({ route: next, push: true, trail: { items, position: items.length - 1 } });
                render({ screen: route.tab === "decisions" && route.view === "map" });
                return;
            }
            route = next;
            // 狭い幅では詳細を別画面として積み、戻る操作で一覧へ戻す
            MindmapPreview.navigate({ route: next, push: isNarrow(), trail: { items: [id], position: 0 } });
            render({ screen: route.tab === "decisions" && route.view === "map" });
        };
        /** 詳細パネルを閉じる */
        const closeDetail = () => {
            flushDrafts();
            if (isNarrow() && history.state !== null && history.state.items !== undefined && history.length > 1) {
                history.back();
                return;
            }
            route = { ...route, id: null, full: false, filters: {} };
            MindmapPreview.navigate({ route, push: false });
            render({ screen: route.tab === "decisions" && route.view === "map" });
        };
        /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
        const openFromSearch = (id) => {
            const kind = index.byId.get(id)?.kind;
            if (kind === undefined)
                return;
            const tab = kind;
            go({ tab, view: MindmapPreview.defaultView(tab), id, full: false, filters: {} }, tab !== route.tab);
        };
        // ===== 描く =====
        /** トップバーとタブの帯 */
        const renderTop = () => {
            top.replaceChildren(MindmapPreview.topbar({
                title: data.settings.summary,
                tabs: MindmapPreview.TAB_KEYS.map((key) => ({
                    key,
                    label: tabLabel(key),
                    icon: TAB_ICON[key],
                    count: key === "overview" ? undefined : data[key].length,
                })),
                current: route.tab,
                theme,
                connection,
                readAt: serverMode ? data.built_at : null,
                comments: serverMode,
                commentCount: comment.review.items.length,
                commentsOpen: comment.listOpen,
                onComments: () => (comment.listOpen ? closeList() : openList()),
                onNavigate: (tab) => go({ ...route, tab, view: MindmapPreview.defaultView(tab), filters: {} }, true),
                onSearch: openSearch,
                onTheme: (next) => {
                    theme = next;
                    prefs.theme = next;
                    persist();
                    document.documentElement.dataset["theme"] = next;
                    renderTop();
                },
            }));
        };
        /** 今の画面 */
        const screenElement = () => {
            const on = { open: (id) => openItem(id, false), view: (view) => go({ ...route, view, filters: {} }, false) };
            switch (route.tab) {
                case "overview":
                    return MindmapPreview.overviewScreen({ index, on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) } });
                case "decisions":
                    return MindmapPreview.decisionsScreen({ index, route, on: { ...on, clear: closeDetail } });
                case "tasks":
                    return MindmapPreview.tasksScreen({ index, route, on });
                case "docs":
                    return MindmapPreview.docsScreen({ index, route, on });
                case "graph":
                    return MindmapPreview.graphScreen({ index, on: { open: on.open }, selected: route.id });
                default:
                    return MindmapPreview.recordsScreen({ index, route, on: { open: on.open } });
            }
        };
        /** 本文の領域を描く。画面（タブ・表示形式）が変わったときだけ描き直す */
        const renderMain = () => {
            main.classList.toggle("map-view", route.tab === "decisions" && route.view === "map");
            // 概要は題名が h1。それ以外の画面は、画面の名前を見えない h1 にする（見出しで画面を探せるように）
            main.replaceChildren(...(route.tab === "overview"
                ? []
                : [MindmapPreview.h({ tag: "h1", attrs: { class: "sr-only" }, children: [screenName(route.tab)] })]), screenElement());
            // 開いたときの絞り込みは一度だけ使い、描き直しで使い回さない
            route = { ...route, filters: {} };
            if (route.tab === "graph")
                MindmapPreview.selectGraphItem(route.id);
        };
        /** 詳細パネルと全画面 */
        const renderDetail = () => {
            const existing = document.querySelector("aside.panel");
            const fullDialog = document.querySelector("dialog.full");
            fullViewer = null;
            closePill();
            document.body.classList.toggle("panel-open", route.id !== null && !route.full);
            MindmapPreview.markSelected(route.id);
            // 開いている項目が無い: パネルも全画面も閉じる
            if (route.id === null) {
                flushDrafts();
                comment.opened = null;
                existing?.classList.remove("open");
                fullDialog?.close();
                fullDialog?.remove();
                return;
            }
            const panel = MindmapPreview.detailPanel({
                id: route.id,
                index,
                full: route.full,
                on: {
                    open: (id) => openItem(id, true),
                    close: closeDetail,
                    full: (full) => {
                        // 全画面の中で図を拡大しているときは、本文へ戻る
                        if (!full && fullViewer !== null)
                            return closeFullViewer();
                        go({ ...route, full }, false);
                    },
                    back: () => history.back(),
                    forward: () => history.forward(),
                    diagram: showDiagram,
                },
                send: serverMode ? formProps(route.id) : null,
                review: serverMode ? comment.review.items.filter((item) => item.target === route.id) : null,
            });
            if (route.full) {
                existing?.classList.remove("open");
                fullDialog?.remove();
                document.body.append(panel);
                panel.showModal();
                showOpenedLocation();
                return;
            }
            fullDialog?.close();
            fullDialog?.remove();
            if (existing === null) {
                // 初めて開く: すべり込ませるため、置いてから次のコマで開いた状態にする
                document.body.append(panel);
                requestAnimationFrame(() => panel.classList.add("open"));
            }
            else {
                // 開いたまま項目を移った: すべり込ませずに中身だけを入れ替える
                existing.className = `${panel.className} open`;
                existing.replaceChildren(...panel.children);
            }
            showOpenedLocation();
        };
        /** コメントの一覧の行から開いたとき、そのコメントの箇所を示す。別の項目へ移っていれば示すのをやめる */
        const showOpenedLocation = () => {
            const opened = comment.review.items.find((item) => item.id === comment.opened);
            if (opened === undefined || opened.target !== route.id) {
                comment.opened = null;
                return;
            }
            const root = document.querySelector(route.full ? "dialog.full" : "aside.panel");
            if (opened.loc !== null && root !== null)
                MindmapPreview.highlightLocation({ root, loc: opened.loc });
        };
        /** 描く（`screen` が真のとき本文の領域も描き直す） */
        const render = ({ screen }) => {
            renderTop();
            if (screen) {
                const wide = document.querySelector(".table-wrap, .map-wrap, .board");
                const keep = wide === null ? 0 : wide.scrollTop;
                renderMain();
                void keep;
            }
            renderDetail();
            if (route.tab === "graph")
                MindmapPreview.selectGraphItem(route.id);
        };
        // ===== 図の拡大 =====
        /** 図を拡大して見る。詳細パネルからはモーダル、全画面からは全画面の中身を切り替える */
        const showDiagram = (svg) => {
            if (route.full) {
                const dialog = document.querySelector("dialog.full");
                const body = dialog?.querySelector(".panel-body");
                if (dialog === null || dialog === undefined || body === null || body === undefined)
                    return;
                body.hidden = true;
                const viewer = MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "full-viewer" },
                    children: [MindmapPreview.diagramViewer({ svg, on: { close: closeFullViewer } })],
                });
                body.after(viewer);
                fullViewer = viewer;
                return;
            }
            const modal = MindmapPreview.h({ tag: "dialog", attrs: { class: "viewer", "aria-label": "図の拡大" } });
            modal.append(MindmapPreview.diagramViewer({ svg, on: { close: () => modal.close() } }));
            modal.addEventListener("close", () => modal.remove());
            document.body.append(modal);
            modal.showModal();
        };
        /** 全画面の中の図の拡大を閉じて、本文に戻す */
        const closeFullViewer = () => {
            fullViewer?.remove();
            fullViewer = null;
            const body = document.querySelector("dialog.full .panel-body");
            if (body !== null)
                body.hidden = false;
        };
        // ===== 全体の検索 =====
        /** 検索を開く（開いているときは何もしない） */
        const openSearch = () => {
            if (document.querySelector("dialog.search") !== null)
                return;
            const dialog = MindmapPreview.searchDialog({
                index,
                on: {
                    open: (id) => {
                        dialog.close();
                        openFromSearch(id);
                    },
                    close: () => dialog.remove(),
                },
            });
            document.body.append(dialog);
            dialog.showModal();
        };
        // ===== コメント =====
        const api = MindmapPreview.commentApi();
        const comment = {
            review: { items: [], drafts: [] },
            forms: new Map(),
            pendingLoc: new Map(),
            checked: new Set(),
            removed: [],
            stale: new Map(),
            listOpen: false,
            opened: null,
        };
        /** まとめて送った結果・本文を直している行・直せなかった理由・項目を指さない入力にフォーカスがあるか */
        let outcome = null;
        let editing = null;
        let editError = null;
        let editBody = null;
        let freeFocused = false;
        /** 入力欄を差し替えている間か（外した入力欄の blur を受けないため） */
        let formRedrawing = false;
        /** チェックした状態で入れるのは、初めて読んだコメントだけ */
        const knownIds = new Set();
        /** 書きかけを保つ待ちのタイマー（入力欄のキー → タイマー） */
        const draftTimers = new Map();
        /** 幅 720px 以下か（項目を指さない入力を畳む幅） */
        const isCompact = () => matchMedia("(max-width: 720px)").matches;
        /** 読んだレビュー中を状態に入れる。初めて読んだコメントはチェックした状態で入れ、最初の読み込みだけ書きかけの箇所を入力に添える */
        const applyReview = (review, first) => {
            comment.review = review;
            for (const item of review.items) {
                if (knownIds.has(item.id))
                    continue;
                knownIds.add(item.id);
                comment.checked.add(item.id);
            }
            if (!first)
                return;
            for (const draft of review.drafts) {
                if (draft.target !== null && draft.loc !== null && !comment.pendingLoc.has(draft.target)) {
                    comment.pendingLoc.set(draft.target, draft.loc);
                }
            }
        };
        /** レビュー中のコメントと書きかけを読み直す。届かないときは前の写しのまま */
        const loadReview = async (first = false) => {
            const result = await api.read();
            if (result.ok && result.data !== null)
                applyReview(result.data, first);
        };
        /** 向けた先の入力欄の状態。無ければ、同じ向けた先の書きかけの本文で作る */
        const formStateOf = (target, loc) => {
            const key = formKey(target, loc);
            let state = comment.forms.get(key);
            if (state === undefined) {
                const draft = comment.review.drafts.find((entry) => formKey(entry.target, entry.loc) === key);
                state = { target, loc, body: draft?.body ?? "", status: "idle", count: null, detail: null };
                comment.forms.set(key, state);
            }
            return state;
        };
        /** 書きかけをすぐ保つ（空なら消える）。届かないときは何も出さない */
        const saveDraftNow = (state) => {
            const key = formKey(state.target, state.loc);
            window.clearTimeout(draftTimers.get(key));
            draftTimers.delete(key);
            void api.saveDraft({
                ...(state.target === null ? {} : { target: state.target }),
                ...(state.loc === null ? {} : { loc: state.loc }),
                body: state.body,
            });
        };
        /** 入力が止まってから書きかけを保つ */
        const scheduleDraft = (state) => {
            const key = formKey(state.target, state.loc);
            window.clearTimeout(draftTimers.get(key));
            draftTimers.set(key, window.setTimeout(() => saveDraftNow(state), MindmapPreview.DRAFT_SAVE_DELAY_MS));
        };
        /** 待っている書きかけを全て、待たずに保つ（パネル・一覧を閉じるときと項目を移るとき） */
        const flushDrafts = () => {
            for (const key of [...draftTimers.keys()]) {
                const state = comment.forms.get(key);
                if (state !== undefined)
                    saveDraftNow(state);
            }
        };
        /** 開いている入力の結果を消す。入力中の欄を作り直さない（変換の途中を壊さないため） */
        const clearSendResult = () => {
            const form = document.activeElement?.closest("form.send");
            const message = form?.querySelector(".send-msg");
            if (message !== null && message !== undefined) {
                message.className = "send-msg";
                message.replaceChildren();
            }
            form?.querySelector("textarea")?.removeAttribute("aria-invalid");
        };
        /** 入力欄を、今の状態で差し替える（`focus` なら入力欄へフォーカスを戻す）。別の項目へ移っていたら状態だけ持っておく */
        const redrawForm = ({ target, focus }) => {
            const current = target === null
                ? document.querySelector(".comments-panel form.send")
                : document.querySelector("aside.panel form.send, dialog.full form.send");
            if (current === null || (target !== null && route.id !== target))
                return;
            const next = MindmapPreview.sendForm(formProps(target));
            // 外した入力欄の blur は、利用者が外へ出たのではないので受けない
            formRedrawing = true;
            current.replaceWith(next);
            formRedrawing = false;
            if (!focus)
                return;
            const field = next.querySelector("textarea");
            field?.focus();
            field?.setSelectionRange(field.value.length, field.value.length);
        };
        /** 箇所を外す。書きかけは箇所を持たない向けた先へ移す */
        const unquote = (state) => {
            const { target } = state;
            if (target === null || state.loc === null)
                return;
            const plain = formStateOf(target, null);
            // 箇所を持つ書きかけを消し、本文を箇所を持たない向けた先へ移す
            const moved = state.body;
            saveDraftNow({ ...state, body: "" });
            comment.forms.delete(formKey(target, state.loc));
            comment.pendingLoc.delete(target);
            if (moved !== "") {
                plain.body = plain.body === "" ? moved : `${plain.body}\n${moved}`;
                saveDraftNow(plain);
            }
            redrawForm({ target, focus: true });
        };
        /** 入力欄の引数。`target` が null なら、コメントの一覧の下端の項目を指さない入力 */
        const formProps = (target) => {
            const loc = target === null ? null : (comment.pendingLoc.get(target) ?? null);
            const state = formStateOf(target, loc);
            return {
                target,
                loc,
                body: state.body,
                status: state.status,
                count: state.count,
                detail: state.detail,
                collapsed: target === null && isCompact() && !freeFocused && state.body === "",
                on: {
                    input: (body) => {
                        state.body = body;
                        scheduleDraft(state);
                        // 溜めた・本文が空の結果は、入力を始めたら消す（溜められなかった結果は次に溜めるまで残す）
                        if (state.status === "saved" || state.status === "empty") {
                            state.status = "idle";
                            clearSendResult();
                        }
                    },
                    save: (body) => void saveComment(state, body),
                    unquote: () => unquote(state),
                    copy: (body) => void navigator.clipboard?.writeText(body),
                    focus: () => {
                        if (target !== null || freeFocused)
                            return;
                        freeFocused = true;
                        // 畳んでいた入力だけを広げる（広げない入力は作り直さず、入力中の欄を壊さない）
                        if (isCompact() && state.body === "")
                            redrawForm({ target: null, focus: true });
                    },
                    blur: () => {
                        if (formRedrawing || target !== null || !freeFocused)
                            return;
                        freeFocused = false;
                        // 本文が空のまま外へ出たら畳む
                        if (isCompact() && state.body === "")
                            redrawForm({ target: null, focus: false });
                    },
                },
            };
        };
        /** 本文を溜め、結果を状態に残して部品を描き直す */
        const saveComment = async (state, body) => {
            state.body = body;
            // 空白だけ: 溜めず、入力欄へフォーカスを戻す
            if (body.trim() === "") {
                Object.assign(state, { status: "empty", detail: null });
                redrawForm({ target: state.target, focus: true });
                return;
            }
            // 溜める前に、この向けた先の書きかけを保つ待ちを止める（応答を待つ間にタイマーが切れて、消えた書きかけを書き戻さないため）
            window.clearTimeout(draftTimers.get(formKey(state.target, state.loc)));
            draftTimers.delete(formKey(state.target, state.loc));
            Object.assign(state, { status: "saving", detail: null });
            redrawForm({ target: state.target, focus: true });
            const result = await api.add({
                ...(state.target === null ? {} : { target: state.target }),
                ...(state.loc === null ? {} : { loc: state.loc }),
                body,
            });
            if (!result.ok || result.data === null) {
                // 断られた・届かない: 本文を残す
                Object.assign(state, { status: "failed", detail: result.ok ? null : result.detail });
                // 止めた待ちを戻す（本文を残したまま閉じても、書きかけは保つ）
                scheduleDraft(state);
                redrawForm({ target: state.target, focus: true });
                return;
            }
            // 溜めた: 入力欄と添えた箇所を空にし、結果は箇所を持たない入力に出す
            const added = result.data;
            if (state.loc !== null && state.target !== null) {
                comment.forms.delete(formKey(state.target, state.loc));
                comment.pendingLoc.delete(state.target);
            }
            const shown = formStateOf(state.target, null);
            Object.assign(shown, { status: "saved", count: added.count, detail: null });
            // 箇所を持たない入力を溜めたときだけ本文を空にする（箇所を持つ入力を溜めたときは、別の向けた先の書きかけを残す）
            if (state.loc === null)
                shown.body = "";
            knownIds.add(added.id);
            comment.checked.add(added.id);
            await loadReview();
            refreshComments();
            redrawForm({ target: state.target, focus: true });
        };
        // ===== コメントの一覧 =====
        /** 一覧を作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
        const renderComments = () => {
            const current = document.querySelector(".comments-panel");
            if (!comment.listOpen) {
                current?.remove();
                return;
            }
            const active = document.activeElement;
            const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
            const typing = active instanceof HTMLTextAreaElement && active.closest(".comments-panel form.send") !== null ? active : null;
            const selection = typing === null ? null : { start: typing.selectionStart, end: typing.selectionEnd };
            const scroll = current?.querySelector(".comments-body")?.scrollTop ?? 0;
            const next = MindmapPreview.commentsPanel({
                items: comment.review.items,
                removed: comment.removed,
                checked: comment.checked,
                editing,
                editError,
                editBody,
                stale: comment.stale,
                result: outcome,
                selected: comment.opened,
                titleOf: (id) => index.byId.get(id)?.item.title ?? null,
                free: formProps(null),
                on: {
                    close: closeList,
                    check: (id, checked) => {
                        if (checked)
                            comment.checked.add(id);
                        else
                            comment.checked.delete(id);
                        renderComments();
                    },
                    checkAll: (checked) => {
                        comment.checked = checked ? new Set(comment.review.items.map((item) => item.id)) : new Set();
                        renderComments();
                    },
                    send: () => void sendChecked(),
                    open: openRow,
                    edit: (id) => {
                        editing = id;
                        editError = null;
                        editBody = null;
                        renderComments();
                    },
                    saveEdit: (id, body) => void saveEdit(id, body),
                    cancelEdit: () => {
                        editing = null;
                        editError = null;
                        editBody = null;
                        renderComments();
                    },
                    remove: (id) => void removeComment(id),
                    restore: (id) => void restoreComment(id),
                    unloc: (id) => void detachLocation(id),
                },
            });
            if (current === null) {
                document.body.append(next);
                requestAnimationFrame(() => next.classList.add("open"));
            }
            else {
                current.className = `${next.className} open`;
                current.replaceChildren(...next.children);
            }
            const panel = document.querySelector(".comments-panel");
            const body = panel?.querySelector(".comments-body");
            if (body !== null && body !== undefined)
                body.scrollTop = scroll;
            if (typing !== null && selection !== null) {
                const restored = panel?.querySelector("form.send textarea");
                restored?.focus();
                restored?.setSelectionRange(selection.start, selection.end);
            }
            else if (focusKey !== null) {
                panel?.querySelector(`[data-focus="${focusKey}"]`)?.focus();
            }
        };
        /** トップバーの件数・詳細パネルのレビュー中のコメント・一覧を、入力中の欄とスクロールの位置を保って描き直す */
        const refreshComments = () => {
            preserving(() => {
                renderTop();
                renderDetail();
            });
            renderComments();
        };
        /** コメントの一覧を開く */
        const openList = () => {
            comment.listOpen = true;
            renderTop();
            renderComments();
        };
        /** コメントの一覧を閉じる */
        const closeList = () => {
            flushDrafts();
            comment.listOpen = false;
            comment.opened = null;
            comment.removed = [];
            renderTop();
            renderComments();
            renderDetail();
        };
        /** 行の向けた項目を、一覧を開いたまま詳細パネルに開く（箇所があればその箇所を示す） */
        const openRow = (item) => {
            if (item.target === null)
                return;
            comment.opened = item.id;
            if (route.id === item.target) {
                renderDetail();
                renderComments();
                return;
            }
            openItem(item.target, false);
            renderComments();
        };
        /** 読み直して一覧まで描き直す */
        const reloadAndRefresh = async () => {
            await loadReview();
            refreshComments();
        };
        /** 行の本文を直す */
        const saveEdit = async (id, body) => {
            const result = await api.update(id, { body });
            if (!result.ok) {
                // 断られた・届かない: 入力を残して理由を出す
                editError = result.detail ?? "サーバーが止まっています。立ち上げ直してから直してください。";
                editBody = body;
                renderComments();
                return;
            }
            editing = null;
            editError = null;
            editBody = null;
            await reloadAndRefresh();
        };
        /** 行を消す（確認は挟まず、元の場所に「元に戻す」を出す） */
        const removeComment = async (id) => {
            const result = await api.remove(id);
            if (result.ok && result.data !== null) {
                const { count: _count, ...item } = result.data;
                comment.removed = [...comment.removed, item];
                comment.stale.delete(id);
            }
            await reloadAndRefresh();
        };
        /** 消した行を、同じ ID と日時で元の場所に戻す */
        const restoreComment = async (id) => {
            const item = comment.removed.find((entry) => entry.id === id);
            if (item === undefined)
                return;
            const result = await api.add({
                id: item.id,
                created: item.created,
                ...(item.target === null ? {} : { target: item.target }),
                ...(item.loc === null ? {} : { loc: item.loc }),
                body: item.body,
            });
            if (result.ok)
                comment.removed = comment.removed.filter((entry) => entry.id !== id);
            await reloadAndRefresh();
        };
        /** 箇所が合わないコメントから箇所を外し、項目へのコメントにする */
        const detachLocation = async (id) => {
            const result = await api.update(id, { loc: null });
            if (result.ok)
                comment.stale.delete(id);
            await reloadAndRefresh();
        };
        /** チェックしたコメントを溜めた順にまとめて送る */
        const sendChecked = async () => {
            const ids = comment.review.items.filter((item) => comment.checked.has(item.id)).map((item) => item.id);
            // 送るものが無い
            if (ids.length === 0)
                return;
            outcome = { kind: "sending" };
            renderComments();
            const result = await api.send(ids);
            if (result.ok && result.data !== null) {
                comment.removed = [];
                comment.stale = new Map();
                outcome = { kind: "sent", count: ids.length, at: result.data.sent };
            }
            else if (!result.ok && result.status === 409) {
                comment.stale = new Map(result.stale.map((entry) => [entry.id, entry.reason]));
                outcome = { kind: "stale", count: result.stale.length };
            }
            else {
                outcome = { kind: "failed", detail: result.ok ? null : result.detail };
            }
            await reloadAndRefresh();
        };
        // ===== 選んだ箇所のコメントの入口 =====
        /** 出している入口 */
        let pill = null;
        /** ポインターを押している間は入口を出さない（選び終えてから出す） */
        let pointerHeld = false;
        /** 入口を閉じる */
        const closePill = () => {
            pill?.remove();
            pill = null;
        };
        /** 選んだ範囲から箇所を求め、あれば入口を出し、無ければ閉じる */
        const updatePill = () => {
            closePill();
            const selection = getSelection();
            const host = document.querySelector("dialog.full[open], aside.panel");
            // 図の拡大を開いている間・選んだ範囲が無い・詳細パネルの外
            if (!serverMode || route.id === null || document.querySelector("dialog.viewer") !== null || fullViewer !== null)
                return;
            if (selection === null || selection.rangeCount === 0 || selection.isCollapsed || host === null)
                return;
            const range = selection.getRangeAt(0);
            if (!host.contains(range.commonAncestorContainer))
                return;
            const loc = MindmapPreview.selectionLocation(range);
            const rects = range.getClientRects();
            const first = rects[0];
            const last = rects[rects.length - 1];
            if (loc === null || first === undefined || last === undefined)
                return;
            const id = route.id;
            pill = MindmapPreview.selectionComment({
                anchor: { first, last },
                viewport: { width: innerWidth, height: innerHeight },
                on: {
                    press: () => {
                        closePill();
                        comment.pendingLoc.set(id, loc);
                        redrawForm({ target: id, focus: true });
                    },
                    close: () => {
                        closePill();
                        host.querySelector(".md")?.focus();
                    },
                },
            });
            // 全画面はモーダルなので、入口もその中に置く（外に置くと押せない）
            (host.matches("dialog") ? host : document.body).append(pill);
        };
        document.addEventListener("pointerdown", () => {
            pointerHeld = true;
        });
        document.addEventListener("pointerup", () => {
            pointerHeld = false;
            window.setTimeout(updatePill, 0);
        });
        document.addEventListener("selectionchange", () => {
            if (!pointerHeld)
                updatePill();
        });
        // ===== 書き換えの知らせ =====
        /** 入力中の欄の選択とスクロールの位置を保って、渡した描き方で描き直す */
        const preserving = (draw) => {
            const field = document.activeElement;
            const form = field instanceof HTMLTextAreaElement ? field.closest("form.send") : null;
            const inList = form !== null && form.closest(".comments-panel") !== null;
            const selection = field instanceof HTMLTextAreaElement && form !== null ? { start: field.selectionStart, end: field.selectionEnd } : null;
            const bodyFocused = field instanceof HTMLElement && field.matches(".panel-body");
            const panelScroll = document.querySelector(".panel-body")?.scrollTop ?? 0;
            const pageScroll = window.scrollY;
            draw();
            const panelBody = document.querySelector(".panel-body");
            if (panelBody !== null)
                panelBody.scrollTop = panelScroll;
            if (bodyFocused)
                panelBody?.focus({ preventScroll: true });
            window.scrollTo(0, pageScroll);
            if (selection !== null) {
                const restored = document.querySelector(inList ? ".comments-panel form.send textarea" : "aside.panel form.send textarea, dialog.full form.send textarea");
                restored?.focus();
                restored?.setSelectionRange(selection.start, selection.end);
            }
        };
        /** 入力中の欄の選択とスクロールの位置を保って、画面を描き直す */
        const redrawKeepingState = () => preserving(() => render({ screen: true }));
        /** 記録を読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
        const reload = async () => {
            const result = await MindmapPreview.fetchRecords();
            if (!result.ok)
                return;
            await loadReview();
            data = result.data;
            index = MindmapPreview.buildIndex(data);
            document.title = `${data.settings.summary} | mindstella`;
            // 開いていた項目が消えた: 詳細パネルを閉じる
            if (route.id !== null && !index.byId.has(route.id)) {
                route = { ...route, id: null, full: false, filters: {} };
                MindmapPreview.navigate({ route, push: false });
            }
            redrawKeepingState();
            renderComments();
        };
        // ===== 操作と履歴 =====
        document.addEventListener("keydown", (event) => {
            const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName ?? "");
            if (event.key === "/" && !typing && document.querySelector("dialog[open]") === null) {
                event.preventDefault();
                openSearch();
            }
            // Esc: 重ねる面が無いときは、詳細パネルを閉じる
            if (event.key === "Escape" &&
                route.id !== null &&
                !route.full &&
                document.querySelector("dialog[open]") === null &&
                document.querySelector(":popover-open") === null) {
                closeDetail();
            }
            else if (event.key === "Escape" &&
                route.id === null &&
                comment.listOpen &&
                document.querySelector("dialog[open]") === null &&
                document.querySelector(":popover-open") === null) {
                closeList();
            }
        });
        /** ハッシュが変わったとき（戻る・進む・手で書き換えた）、その画面を描く */
        const onLocationChange = () => {
            const next = MindmapPreview.parseHash({ hash: location.hash, index });
            if (MindmapPreview.toHash(next) === MindmapPreview.toHash(route))
                return;
            const screen = next.tab !== route.tab || next.view !== route.view || (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
            route = next;
            render({ screen });
        };
        addEventListener("popstate", onLocationChange);
        addEventListener("hashchange", onLocationChange);
        // ===== 最初の描き =====
        // サーバーの配信では、レビュー中のコメントと書きかけを読んでおく（コメントのボタンの件数と入力に使う）
        if (serverMode)
            await loadReview(true);
        // 記録に無い項目を指すハッシュは、項目の無いハッシュに置き換える
        const requested = new URLSearchParams(location.hash.replace(/^#/, "")).get("id");
        if (requested !== null && route.id === null)
            MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
        render({ screen: true });
        // 絞り込みは画面に渡した後、ハッシュから消す
        MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
        // ===== 書き換えの知らせにつなぐ（サーバーの配信だけ） =====
        if (serverMode) {
            MindmapPreview.subscribeEvents({
                onChanged: () => void reload(),
                onConnection: (connected) => {
                    // 切れた: 接続の状態を出し、最後に読めた記録で描き続ける
                    if (!connected) {
                        connection = "offline";
                        renderTop();
                        return;
                    }
                    // つながり直した: 切れていた間の書き換えを読み直す（最初の接続は切れていないので何もしない）
                    if (connection === "offline") {
                        connection = "online";
                        renderTop();
                        void reload();
                    }
                },
            });
        }
    }
    // 文書が読み込まれたら起動する（記録の要素が無い文書では、読んだだけでは何もしない）
    if (document.getElementById(DATA_ELEMENT_ID) !== null) {
        if (document.readyState === "loading")
            document.addEventListener("DOMContentLoaded", start);
        else
            start();
    }
})(MindmapPreview || (MindmapPreview = {}));
