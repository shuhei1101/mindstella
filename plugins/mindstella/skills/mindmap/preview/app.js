"use strict";
// 起動。記録を読み（配る書き出しは埋め込みから、サーバーの配信は記録の取得から）、URL のハッシュが指す画面を描き、操作を画面の移動・書き換えの知らせ・回答・意見の送信・端末の保存領域につなぐ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 埋め込みのデータの要素の ID */
    const DATA_ELEMENT_ID = "mindmap-data";
    /** 端末の保存領域のキー */
    MindmapPreview.PREFS_KEY = "mindmap-preview";
    /** 書きかけの本文を残す sessionStorage のキーの頭（`{頭}{項目の ID}`）。ポートを含むオリジンごとに分かれ、配信はワークスペースごとに別のポートなので、ワークスペースを含めなくても混ざらない */
    MindmapPreview.DRAFT_KEY_PREFIX = "mindmap-draft:";
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
    /** その項目の書きかけを sessionStorage から読む。無いか保存領域が例外を送るときは空を返す */
    function loadDraft(storage, id) {
        try {
            return storage.getItem(`${MindmapPreview.DRAFT_KEY_PREFIX}${id}`) ?? "";
        }
        catch {
            return "";
        }
    }
    MindmapPreview.loadDraft = loadDraft;
    /** その項目の書きかけを sessionStorage に残す。空なら消す。保存領域が例外を送るときは何もしない */
    function saveDraft(storage, id, body) {
        try {
            if (body === "")
                storage.removeItem(`${MindmapPreview.DRAFT_KEY_PREFIX}${id}`);
            else
                storage.setItem(`${MindmapPreview.DRAFT_KEY_PREFIX}${id}`, body);
        }
        catch {
            // 保存できない環境では、開いている間のメモリの状態だけで保つ
        }
    }
    MindmapPreview.saveDraft = saveDraft;
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
        const draftStorage = openStorage("sessionStorage");
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
                    return MindmapPreview.decisionsScreen({ index, route, on });
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
            document.body.classList.toggle("panel-open", route.id !== null && !route.full);
            MindmapPreview.markSelected(route.id);
            // 開いている項目が無い: パネルも全画面も閉じる
            if (route.id === null) {
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
                send: serverMode ? sendFormProps(route.id) : null,
            });
            if (route.full) {
                existing?.classList.remove("open");
                fullDialog?.remove();
                document.body.append(panel);
                panel.showModal();
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
        // ===== 回答・意見の送信 =====
        /** 項目ごとの送信の状態（描き直し・項目の移動・詳細パネルと全画面の行き来でも保つ） */
        const sendStates = new Map();
        /** 項目の送信の状態。無ければ、sessionStorage の書きかけから作る */
        const sendStateOf = (id) => {
            let state = sendStates.get(id);
            if (state === undefined) {
                state = { body: loadDraft(draftStorage, id), status: "idle", sentAt: null, detail: null };
                sendStates.set(id, state);
            }
            return state;
        };
        /** 開いている送信の部品の結果を消す。入力中の欄を作り直さない（変換の途中を壊さないため） */
        const clearSendResult = () => {
            const form = document.querySelector("form.send");
            const message = form?.querySelector(".send-msg");
            if (message !== null && message !== undefined) {
                message.className = "send-msg";
                message.replaceChildren();
            }
            form?.querySelector("textarea")?.removeAttribute("aria-invalid");
        };
        /** 開いている項目の送信の部品を、今の状態で差し替え、入力欄へフォーカスを戻す */
        const redrawSend = (id) => {
            const current = document.querySelector("form.send");
            // 別の項目へ移っていたら、状態だけ持っておく
            if (current === null || route.id !== id)
                return;
            const next = MindmapPreview.sendForm(sendFormProps(id));
            current.replaceWith(next);
            const field = next.querySelector("textarea");
            field?.focus();
            field?.setSelectionRange(field.value.length, field.value.length);
        };
        /** 本文を送り、結果を状態に残して部品を描き直す */
        const submit = async (id, body) => {
            const state = sendStateOf(id);
            state.body = body;
            // 空白だけ: 送らず、入力欄へフォーカスを戻す
            if (body.trim() === "") {
                Object.assign(state, { status: "empty", detail: null });
                redrawSend(id);
                return;
            }
            Object.assign(state, { status: "sending", detail: null });
            redrawSend(id);
            const result = await MindmapPreview.postSubmission(id, body);
            if (result.ok) {
                // 送れた: 書きかけを空にする
                Object.assign(state, { body: "", status: "sent", sentAt: result.sent, detail: null });
                saveDraft(draftStorage, id, "");
            }
            else {
                // 断られた・届かない: 本文を残す
                Object.assign(state, { status: "failed", detail: result.detail });
            }
            redrawSend(id);
        };
        /** 項目の送信の部品の引数 */
        const sendFormProps = (id) => {
            const state = sendStateOf(id);
            return {
                target: id,
                body: state.body,
                status: state.status,
                sentAt: state.sentAt,
                detail: state.detail,
                onInput: (body) => {
                    state.body = body;
                    saveDraft(draftStorage, id, body);
                    // 送った・本文が空の結果は、入力を始めたら消す（送れなかった結果は次に送るまで残す）
                    if (state.status === "sent" || state.status === "empty") {
                        state.status = "idle";
                        clearSendResult();
                    }
                },
                onSend: (body) => void submit(id, body),
                onCopy: (body) => void navigator.clipboard?.writeText(body),
            };
        };
        // ===== 書き換えの知らせ =====
        /** 入力中の欄の選択とスクロールの位置を保って、画面を描き直す */
        const redrawKeepingState = () => {
            const field = document.activeElement;
            const typing = field instanceof HTMLTextAreaElement && field.closest("form.send") !== null;
            const selection = typing ? { start: field.selectionStart, end: field.selectionEnd } : null;
            const panelScroll = document.querySelector(".panel-body")?.scrollTop ?? 0;
            const pageScroll = window.scrollY;
            render({ screen: true });
            const panelBody = document.querySelector(".panel-body");
            if (panelBody !== null)
                panelBody.scrollTop = panelScroll;
            window.scrollTo(0, pageScroll);
            if (selection !== null) {
                const restored = document.querySelector("form.send textarea");
                restored?.focus();
                restored?.setSelectionRange(selection.start, selection.end);
            }
        };
        /** 記録を読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
        const reload = async () => {
            const result = await MindmapPreview.fetchRecords();
            if (!result.ok)
                return;
            data = result.data;
            index = MindmapPreview.buildIndex(data);
            document.title = `${data.settings.summary} | mindstella`;
            // 開いていた項目が消えた: 詳細パネルを閉じる
            if (route.id !== null && !index.byId.has(route.id)) {
                route = { ...route, id: null, full: false, filters: {} };
                MindmapPreview.navigate({ route, push: false });
            }
            redrawKeepingState();
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
