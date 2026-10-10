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
    /** 画面の下に「ワークスペースの既定が変わりました。」を出しておくミリ秒 */
    MindmapPreview.NOTICE_MS = 6000;
    /** そのタブの「前回開いてから」の始まりの日時を残す sessionStorage のキー。あれば `POST /api/opened` を呼ばない（同じタブで読み込み直しても範囲を変えない） */
    MindmapPreview.SINCE_KEY = "mindmap-since";
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
    /** 画面の名前（ネットワークは種類のタブに無いので、ここで持つ） */
    function screenName(tab) {
        return tab === "graph" ? "ネットワーク" : tabLabel(tab);
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
        return { theme: null, columns: {}, look: null, kinds: null, diffSel: null };
    }
    /** 端末の保存領域から設定を読む。読めないときは既定を返す */
    function loadPrefs(storage) {
        try {
            const saved = storage.getItem(MindmapPreview.PREFS_KEY);
            if (saved === null)
                return defaultPrefs();
            const parsed = { ...defaultPrefs(), ...JSON.parse(saved) };
            // 選べない値の見た目・種類は、その項目だけワークスペースの既定に従う
            const looks = MindmapPreview.NETWORK_LOOKS.map((option) => option.key);
            if (!looks.includes(parsed.look))
                parsed.look = null;
            const kinds = MindmapPreview.KIND_KEYS;
            if (!Array.isArray(parsed.kinds) || !parsed.kinds.every((kind) => kinds.includes(kind)))
                parsed.kinds = null;
            return parsed;
        }
        catch {
            return defaultPrefs();
        }
    }
    MindmapPreview.loadPrefs = loadPrefs;
    /** 設定を端末の保存領域に残し、書けたかを返す。保存領域が例外を送るときは偽を返す（開いている間だけ設定を保つ） */
    function savePrefs({ storage, prefs }) {
        try {
            storage.setItem(MindmapPreview.PREFS_KEY, JSON.stringify(prefs));
            return true;
        }
        catch {
            return false;
        }
    }
    MindmapPreview.savePrefs = savePrefs;
    /** 項目ごとに、個人の上書きがあればそれを、無ければワークスペースの既定を、それも無ければ組み込みの既定を使う */
    function resolveDisplay(prefs, display) {
        const defaultLook = display?.network_look ?? MindmapPreview.BUILTIN_LOOK;
        const defaultKinds = new Set(display?.visible_kinds ?? MindmapPreview.KIND_KEYS);
        // 上書きを持つ項目の名前を、見た目・種類・ライト / ダーク・表の列の順に並べる
        const overrides = [
            ...(prefs.look === null ? [] : ["ネットワークの見た目"]),
            ...(prefs.kinds === null ? [] : ["表示する種類"]),
            ...(prefs.theme === null ? [] : ["ライト / ダーク"]),
            ...MindmapPreview.KIND_KEYS.filter((kind) => prefs.columns[kind] !== undefined).map((kind) => `表の列（${MindmapPreview.KIND_LABEL[kind]}）`),
        ];
        return {
            look: prefs.look ?? defaultLook,
            kinds: prefs.kinds === null ? defaultKinds : new Set(prefs.kinds),
            defaultLook,
            defaultKinds,
            overrides,
        };
    }
    MindmapPreview.resolveDisplay = resolveDisplay;
    /** 「既定に戻す」で、見た目・表示する種類・ライト / ダーク・表の列を外した設定を返す（`diffSel` は残し、渡した設定は変えない） */
    function clearOverrides(prefs) {
        return { ...prefs, theme: null, look: null, kinds: null, columns: {} };
    }
    MindmapPreview.clearOverrides = clearOverrides;
    /** 表示の既定が同じか（無いキーは同じ無しとして比べる） */
    function sameDisplay(a, b) {
        const key = (display) => JSON.stringify([display?.network_look ?? null, display?.visible_kinds ?? null]);
        return key(a) === key(b);
    }
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
                // 残せない旨を呼び手に伝える（`savePrefs` が偽を返す）
                setItem: () => {
                    throw new Error("保存領域が使えません");
                },
            };
        }
    }
    /** そのタブの「前回開いてから」の始まりを決める。同じタブで読み込み直したときは、残した日時をそのまま使う */
    async function resolveSince({ serverMode, prefs, persist, }) {
        const session = openStorage("sessionStorage");
        let kept;
        try {
            kept = session.getItem(MindmapPreview.SINCE_KEY);
        }
        catch {
            kept = null;
        }
        if (kept !== null)
            return kept;
        const now = new Date().toISOString();
        let previous;
        if (serverMode) {
            previous = await MindmapPreview.postOpened();
        }
        else {
            // 配る書き出しは、前回開いた日時を端末の設定に持ち、今の日時に書き換える
            previous = prefs.opened ?? null;
            prefs.opened = now;
            persist();
        }
        // 前回開いた日時が無い・呼べなかったときは、タブを開いた日時にする
        const since = previous ?? now;
        try {
            session.setItem(MindmapPreview.SINCE_KEY, since);
        }
        catch {
            // 残せない環境では、読み込み直すたびに決め直す
        }
        return since;
    }
    /** 変更履歴のモーダルに、差分を出さない行と、まだまとめていない変更・前回開いてから・まとまりの行を新しい順に並べる */
    function historyPoints({ changes, since }) {
        /** その時点で足した・変えた・消した項目の数（合わせた範囲で足して消した項目は、消した項目として 1 件に数える） */
        const countOf = (sel) => {
            const point = MindmapPreview.resolveDiffPoint(changes, sel, since);
            return point === null ? 0 : point.added.size + point.changed.size + point.removed.size;
        };
        const hasPending = changes.pending.added.length + changes.pending.changed.length + (changes.pending.removed ?? []).length > 0;
        return [
            { sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" },
            ...(hasPending
                ? [{ sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: countOf("pending") }]
                : []),
            { sel: "since", name: "前回開いてから", sub: `${MindmapPreview.formatJst(since)} より後`, count: countOf("since") },
            ...changes.sets.map((set) => ({ sel: set.id, name: set.summary, sub: MindmapPreview.formatJst(set.at), count: countOf(set.id) })),
        ];
    }
    /** 選んだ時点の、項目の ID → 差分の印 */
    function marksOf(point) {
        if (point === null)
            return undefined;
        return Object.fromEntries([
            ...[...point.added].map((id) => [id, "new"]),
            ...[...point.changed].map((id) => [id, "changed"]),
        ]);
    }
    /** レビュー中のコメントを `target` ごとに数え、項目の ID → 件数を返す（箇所を指すコメントもその項目に数え、項目を指さないコメントと件数 0 の項目は含めない） */
    function commentCounts(items) {
        const counts = {};
        for (const item of items) {
            if (item.target === null)
                continue;
            counts[item.target] = (counts[item.target] ?? 0) + 1;
        }
        return counts;
    }
    MindmapPreview.commentCounts = commentCounts;
    /** 2 つの件数の対応が同じか */
    function sameCounts(a, b) {
        const keys = Object.keys(a);
        return keys.length === Object.keys(b).length && keys.every((key) => a[key] === b[key]);
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
            display.storageOk = persist();
            // 表の列の上書きは、パネルの「この端末で変えている項目」に合わせる
            resolved = resolveDisplay(prefs, data.settings.display);
            if (display.open)
                renderSettings();
        });
        // ===== テーマ =====
        /** 端末のライト / ダーク（個人の上書きが無いときに従う） */
        const systemTheme = () => (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        let theme = prefs.theme ?? systemTheme();
        document.documentElement.dataset["theme"] = theme;
        // ===== 記録 =====
        let data = embedded ?? (await waitForRecords(theme));
        let index = MindmapPreview.buildIndex(data);
        document.title = `${data.settings.summary} | mindstella`;
        let connection = "online";
        // 表示の設定: 項目ごとに、個人の上書き → ワークスペースの既定 → 組み込みの既定の順で読み分けた値
        let resolved = resolveDisplay(prefs, data.settings.display);
        const display = { open: false, confirm: null, message: null, savedDisplay: null, storageOk: true };
        /** 表示しない種類のタブを指す route は、概要へ置き換える（`id` は残し、詳細パネルは開く） */
        const visibleRoute = (next) => next.tab === "overview" || next.tab === "graph" || resolved.kinds.has(next.tab)
            ? next
            : { ...next, tab: "overview", view: MindmapPreview.defaultView("overview"), filters: {} };
        // 差分の表示: そのタブの「前回開いてから」の始まりと、選んだ時点（持たない・記録に無いときは差分を出さない）
        const since = await resolveSince({ serverMode, prefs, persist });
        let point = MindmapPreview.resolveDiffPoint(data.changes, prefs.diffSel ?? null, since);
        // ===== 画面の土台 =====
        const top = MindmapPreview.h({ tag: "div", attrs: { id: "top" } });
        const main = MindmapPreview.h({ tag: "main", attrs: { class: "content", id: "main" } });
        document.body.prepend(top, main);
        let route = visibleRoute(MindmapPreview.parseHash({ hash: location.hash, index }));
        let fullViewer = null;
        /** 詳細パネルがもう画面に入れた見出し（同じ項目・同じ見出しでは、描き直しのたびに本文のスクロールを戻さない） */
        let shownHeading = null;
        const filterState = { byTab: {}, drawerOpen: false };
        const lockState = { graph: null, map: null };
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
            const next = { ...route, id, filters: {}, heading: null };
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
            route = { ...route, id: null, full: false, filters: {}, heading: null };
            MindmapPreview.navigate({ route, push: false });
            render({ screen: route.tab === "decisions" && route.view === "map" });
        };
        /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
        const openFromSearch = (id) => {
            const kind = index.byId.get(id)?.kind;
            if (kind === undefined)
                return;
            // 表示しない種類の項目は、概要の上の詳細パネルで開く
            const tab = resolved.kinds.has(kind) ? kind : "overview";
            go({ tab, view: MindmapPreview.defaultView(tab), id, full: false, filters: {}, heading: null }, tab !== route.tab);
        };
        // ===== ロック =====
        /** 効いているロック。画面ごとの `LockState` の項目が、その画面の絞り込みの条件を通る（描いている）ときだけその ID、通らないときは null（`LockState` は残し、条件を戻して描かれたらまたロック中に戻る） */
        const effectiveLock = (key) => {
            const id = lockState[key];
            if (id === null)
                return null;
            const shown = key === "graph"
                ? MindmapPreview.shownGraphIds({ index, filters: filterState.byTab["graph"] ?? {} })
                : MindmapPreview.shownDecisionIds({ index, filters: filterState.byTab["decisions"] ?? {} });
            return shown.has(id) ? id : null;
        };
        /** 玉か節（余白なら null）を押した、または `L` キーを押した。`lockTap` で判定し、`lock`・`unlock` のときだけ `LockState` を変えて画面に反映する。`open` は詳細を切り替え、`blank` は詳細を閉じて全体の表示へ戻し、`shake` は何も変えない（画面が鍵を震わせる） */
        const lockPress = ({ key, pressed }) => {
            const result = MindmapPreview.lockTap({ locked: effectiveLock(key), pressed, open: route.id });
            if (result.action === "lock" || result.action === "unlock") {
                lockState[key] = result.locked;
                // ネットワークは視点を保ったまま中心と強調を寄せ、マップは詳細パネルをそのままに描き直す
                if (key === "graph")
                    MindmapPreview.setGraphLock(effectiveLock("graph"));
                else
                    redrawKeepingState();
            }
            else if (result.action === "open" && pressed !== null) {
                openItem(pressed, false);
            }
            else if (result.action === "blank" && route.id !== null) {
                closeDetail();
            }
            return result.action;
        };
        /** ネットワークの見た目のドロップダウンで選んだ値を個人の上書きに残す（ネットワークは作り直さず、次のコマから当てる） */
        const changeLook = (value) => {
            prefs.look = value;
            changePrefs({ redrawMain: false });
            MindmapPreview.setGraphLook(resolved.look);
        };
        // ===== 描く =====
        /** トップバーとタブの帯 */
        const renderTop = () => {
            const marks = marksOf(point);
            top.replaceChildren(MindmapPreview.topbar({
                title: data.settings.summary,
                tabs: MindmapPreview.TAB_KEYS.filter((key) => key === "overview" || resolved.kinds.has(key)).map((key) => ({
                    key,
                    label: tabLabel(key),
                    icon: TAB_ICON[key],
                    count: key === "overview" ? undefined : data[key].length,
                    // 差分の表示の間、新規・変更・消した項目を持つ種類のタブに点を重ねる
                    marked: key !== "overview" &&
                        ((marks !== undefined && data[key].some((item) => marks[item.id] !== undefined)) ||
                            MindmapPreview.removedOf({ point, kind: key }).length > 0),
                })),
                current: route.tab,
                theme,
                connection,
                readAt: serverMode ? data.built_at : null,
                comments: serverMode,
                commentCount: comment.review.items.length,
                commentsOpen: comment.listOpen,
                onComments: () => (comment.listOpen ? closeList() : openList()),
                settingsOpen: display.open,
                onSettings: () => (display.open ? closeSettings() : openSettings()),
                // 概要以外の画面に絞り込みのボタンを置き、値を選んでいる条件の数をバッジに出す
                filter: route.tab !== "overview",
                filterCount: MindmapPreview.activeConditionCount(filterState.byTab[route.tab] ?? {}),
                filterOpen: filterState.drawerOpen,
                onFilter: toggleDrawer,
                diffPoint: point === null ? null : { name: point.name, sub: point.sub },
                onHistory: openHistory,
                onDiffOff: () => selectPoint(null),
                onNavigate: (tab) => go({ ...route, tab, view: MindmapPreview.defaultView(tab), filters: {} }, true),
                onSearch: openSearch,
                onTheme: (next) => {
                    theme = next;
                    prefs.theme = next;
                    changePrefs({ redrawMain: false });
                    document.documentElement.dataset["theme"] = next;
                },
            }));
        };
        /** 今の画面 */
        const screenElement = () => {
            const on = {
                open: (id) => openItem(id, false),
                view: (view) => go({ ...route, view, filters: {} }, false),
                filter: changeFilters,
                closeDrawer,
            };
            const marks = marksOf(point);
            // サーバーにつながって開いたときだけ、項目ごとのコメントの件数を渡す（配る書き出しは印を出さない）
            const comments = serverMode ? commentsNow : undefined;
            const filters = filterState.byTab[route.tab] ?? {};
            const { drawerOpen } = filterState;
            // 選んだ時点で消した、この画面の種類の項目
            const removed = MindmapPreview.removedOf({ point, kind: route.tab });
            switch (route.tab) {
                case "overview":
                    return MindmapPreview.overviewScreen({
                        index,
                        on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) },
                        marks,
                        visibleKinds: resolved.kinds,
                    });
                case "decisions":
                    return MindmapPreview.decisionsScreen({
                        index,
                        route,
                        on: { ...on, clear: closeDetail, lock: (id) => lockPress({ key: "map", pressed: id }) },
                        lockedId: effectiveLock("map"),
                        filters,
                        drawerOpen,
                        marks,
                        comments,
                        removed,
                    });
                case "tasks":
                    return MindmapPreview.tasksScreen({ index, route, on, filters, drawerOpen, marks, comments, removed });
                case "docs":
                    return MindmapPreview.docsScreen({ index, route, on, filters, drawerOpen, marks, comments, removed });
                case "graph":
                    return MindmapPreview.graphScreen({
                        index,
                        on: {
                            open: on.open,
                            filter: changeFilters,
                            closeDrawer,
                            lock: (id) => lockPress({ key: "graph", pressed: id }),
                            look: changeLook,
                        },
                        filters,
                        drawerOpen,
                        selectedId: route.id,
                        lockedId: effectiveLock("graph"),
                        look: resolved.look,
                        defaultLook: resolved.defaultLook,
                        comments,
                    });
                default:
                    return MindmapPreview.recordsScreen({
                        index,
                        route,
                        on: { open: on.open, filter: changeFilters, closeDrawer },
                        filters,
                        drawerOpen,
                        marks,
                        comments,
                        removed,
                    });
            }
        };
        /** 本文の領域を描く。画面（タブ・表示形式）が変わったときだけ描き直す */
        const renderMain = () => {
            main.classList.toggle("map-view", route.tab === "decisions" && route.view === "map");
            // 概要は題名が h1。それ以外の画面は、画面の名前を見えない h1 にする（見出しで画面を探せるように）
            main.replaceChildren(...(route.tab === "overview"
                ? []
                : [MindmapPreview.h({ tag: "h1", attrs: { class: "sr-only" }, children: [screenName(route.tab)] })]), screenElement());
            if (route.tab === "graph")
                MindmapPreview.selectGraphItem(route.id);
        };
        /** 今の画面の絞り込みを用意する。ハッシュの `f.{列}` があればそれだけを（開き直したときも）、無く初めて開く画面なら既定を入れ、ハッシュの分は一度だけ使う。概要には絞り込みのドロワーを置かないので閉じる（タブを押したときも、戻る・進むで移ったときも通る） */
        const prepareFilters = () => {
            if (route.tab === "overview")
                filterState.drawerOpen = false;
            if (Object.keys(route.filters).length > 0 || filterState.byTab[route.tab] === undefined) {
                filterState.byTab[route.tab] = MindmapPreview.initialFilters(route.tab, route.filters);
            }
            route = { ...route, filters: {} };
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
                    // 本文の見出しへ移った: ハッシュの `h` を、履歴に積まずに置き換える
                    heading: (heading) => {
                        route = { ...route, heading };
                        shownHeading = heading === null || route.id === null ? null : { id: route.id, heading };
                        MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
                    },
                },
                comment: serverMode
                    ? { form: formProps(route.id), reviews: comment.review.items.filter((item) => item.target === route.id) }
                    : null,
                highlight: openedLocation(),
                diff: point,
                // 開いたときにだけ見出しを画面に入れる
                heading: shownHeading?.id === route.id && shownHeading.heading === route.heading ? null : route.heading,
            });
            shownHeading = route.heading === null ? null : { id: route.id, heading: route.heading };
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
        /** コメントの一覧の行から開いたとき、そのコメントの箇所。別の項目へ移っていれば示すのをやめる */
        const openedLocation = () => {
            const opened = comment.review.items.find((item) => item.id === comment.opened);
            if (opened === undefined || opened.target !== route.id) {
                comment.opened = null;
                return null;
            }
            return opened.loc;
        };
        /** 描く（`screen` が真のとき本文の領域も描き直す） */
        const render = ({ screen }) => {
            prepareFilters();
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
            // 作り直した本文にも、開いているパネルの下の部品を止める
            scheduleInert();
        };
        // ===== 絞り込み =====
        /** 開いているパネルが覆った本文の部品を止める関数が返した、止めた分を外す関数 */
        let releaseInert = null;
        /** 前に止めた分を外してから、開いているパネル（絞り込みのドロワー・コメントの一覧・表示の設定のパネル）が覆った本文の部品を止める */
        const applyInert = () => {
            releaseInert?.();
            releaseInert = null;
            const panel = filterState.drawerOpen
                ? document.querySelector("dialog.drawer")
                : comment.listOpen
                    ? document.querySelector(".comments-panel")
                    : display.open
                        ? document.querySelector(".settings-drawer")
                        : null;
            if (panel !== null)
                releaseInert = MindmapPreview.inertBehind(panel);
        };
        /** パネルが開いた後（ドロワーは文書に入った後の次のマイクロタスクで開く）に、本文の部品を止める */
        const scheduleInert = () => queueMicrotask(applyInert);
        /** 画面の条件を変えて描き直す（ドロワーは開いたまま） */
        const changeFilters = (next) => {
            filterState.byTab[route.tab] = next;
            redrawKeepingState();
        };
        /** 絞り込みのドロワーを閉じ、絞り込みのボタンへフォーカスを戻す */
        const closeDrawer = () => {
            filterState.drawerOpen = false;
            redrawKeepingState();
            document.querySelector("[data-act='filter']")?.focus();
        };
        /** 絞り込みのドロワーを開く・閉じる（開くときはコメントの一覧と表示の設定のパネルを閉じる） */
        const toggleDrawer = () => {
            if (filterState.drawerOpen) {
                closeDrawer();
                return;
            }
            if (comment.listOpen)
                closeList();
            if (display.open) {
                display.open = false;
                renderSettings();
            }
            filterState.drawerOpen = true;
            redrawKeepingState();
        };
        // ===== 図の拡大 =====
        /** 図を拡大して見る。詳細パネルからはモーダル、全画面からは全画面の中身を切り替える */
        const showDiagram = (svg, diff) => {
            if (route.full) {
                const dialog = document.querySelector("dialog.full");
                const body = dialog?.querySelector(".panel-body");
                if (dialog === null || dialog === undefined || body === null || body === undefined)
                    return;
                body.hidden = true;
                const viewer = MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "full-viewer" },
                    children: [MindmapPreview.diagramViewer({ svg, on: { close: closeFullViewer }, diff })],
                });
                body.after(viewer);
                fullViewer = viewer;
                return;
            }
            const modal = MindmapPreview.h({ tag: "dialog", attrs: { class: "viewer", "aria-label": "図の拡大" } });
            modal.append(MindmapPreview.diagramViewer({ svg, on: { close: () => modal.close() }, diff }));
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
        /** 各画面へ渡す項目の ID → コメントの件数。画面は描き直すたびにこれを読むので、件数が変わったときは同じ物の中身を入れ替える */
        const commentsNow = {};
        /** レビュー中のコメントの件数が変わっていれば、画面を描き直さずに印だけを差し替える（つながりは次のコマから） */
        const syncCommentMarks = () => {
            const next = commentCounts(comment.review.items);
            if (sameCounts(commentsNow, next))
                return;
            for (const key of Object.keys(commentsNow))
                delete commentsNow[key];
            Object.assign(commentsNow, next);
            MindmapPreview.refreshCommentMarks({ root: main, counts: commentsNow });
            MindmapPreview.setGraphComments(commentsNow);
        };
        /** 書きかけを保つ待ちのタイマー（入力欄のキー → タイマー） */
        const draftTimers = new Map();
        /** 幅 720px 以下か（項目を指さない入力を畳む幅） */
        const isCompact = () => matchMedia("(max-width: 720px)").matches;
        /** 読んだレビュー中を状態に入れる。初めて読んだコメントはチェックした状態で入れ、最初の読み込みだけ書きかけの箇所を入力に添える */
        const applyReview = (review, first) => {
            comment.review = review;
            syncCommentMarks();
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
                scheduleInert();
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
            scheduleInert();
        };
        /** トップバーの件数・詳細パネルのレビュー中のコメント・一覧を、入力中の欄とスクロールの位置を保って描き直す */
        const refreshComments = () => {
            preserving(() => {
                renderTop();
                renderDetail();
            });
            renderComments();
        };
        /** コメントの一覧を開く（絞り込みのドロワーは閉じる） */
        const openList = () => {
            // 絞り込みのドロワー・表示の設定のパネルとは 1 つだけを開く
            if (filterState.drawerOpen) {
                filterState.drawerOpen = false;
                redrawKeepingState();
            }
            display.open = false;
            renderSettings();
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
            // 全画面のときは詳細パネルも文書に残るので、今の画面の本文を引く
            const bodySelector = route.full ? "dialog.full .panel-body" : "aside.panel .panel-body";
            const panelScroll = document.querySelector(bodySelector)?.scrollTop ?? 0;
            const pageScroll = window.scrollY;
            draw();
            const panelBody = document.querySelector(bodySelector);
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
        // ===== 表示の設定 =====
        /** 端末の上書きを変えた後に、残して読み分け直し、描き直す。開いている画面の種類を外したときは概要へ移る（履歴に積まない） */
        const changePrefs = ({ redrawMain }) => {
            display.storageOk = persist();
            resolved = resolveDisplay(prefs, data.settings.display);
            const visible = visibleRoute(route);
            const moved = visible !== route;
            if (moved) {
                route = visible;
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
            }
            if (redrawMain || moved)
                redrawKeepingState();
            else
                renderTop();
            renderSettings();
        };
        /** 表示の設定の中身の引数 */
        const settingsProps = () => ({
            look: resolved.look,
            defaultLook: resolved.defaultLook,
            kinds: resolved.kinds,
            defaultKinds: resolved.defaultKinds,
            counts: Object.fromEntries(MindmapPreview.KIND_KEYS.map((kind) => [kind, data[kind].length])),
            overrides: resolved.overrides,
            canSave: serverMode,
            message: display.message,
            storageOk: display.storageOk,
            on: {
                kinds: (kinds) => {
                    prefs.kinds = kinds;
                    changePrefs({ redrawMain: true });
                },
                reset: () => {
                    // 見た目・表示する種類・ライト / ダーク・表の列を全て外し、ワークスペースの既定の表示に戻す
                    Object.assign(prefs, clearOverrides(prefs));
                    MindmapPreview.clearTablePrefs();
                    theme = systemTheme();
                    document.documentElement.dataset["theme"] = theme;
                    changePrefs({ redrawMain: true });
                    document.querySelector('.settings-drawer [data-focus="over"]')?.focus();
                },
                save: openConfirm,
                close: closeSettings,
            },
        });
        /** 表示の設定のパネルを作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
        const renderSettings = () => {
            const current = document.querySelector(".settings-drawer");
            if (!display.open) {
                current?.remove();
                return;
            }
            const active = document.activeElement;
            const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
            const scroll = current?.querySelector(".st-wrap")?.scrollTop ?? 0;
            const next = MindmapPreview.settingsDrawer({ panel: settingsProps() });
            if (current === null) {
                document.body.append(next);
                requestAnimationFrame(() => next.classList.add("open"));
            }
            else {
                current.className = `${next.className} open`;
                current.replaceChildren(...next.children);
            }
            const panel = document.querySelector(".settings-drawer");
            const wrap = panel?.querySelector(".st-wrap");
            if (wrap !== null && wrap !== undefined)
                wrap.scrollTop = scroll;
            if (focusKey !== null)
                panel?.querySelector(`[data-focus="${focusKey}"]`)?.focus();
        };
        /** 表示の設定のパネルを開く。コメントの一覧と絞り込みのドロワーは閉じ、右の詳細パネルは開いたままにする（履歴に積まない） */
        const openSettings = () => {
            if (comment.listOpen) {
                flushDrafts();
                comment.listOpen = false;
                comment.opened = null;
                comment.removed = [];
                renderComments();
            }
            display.open = true;
            if (filterState.drawerOpen) {
                filterState.drawerOpen = false;
                redrawKeepingState();
            }
            else {
                renderTop();
            }
            renderSettings();
            scheduleInert();
        };
        /** 表示の設定のパネルを閉じ、トップバーのボタンへフォーカスを戻す */
        const closeSettings = () => {
            display.open = false;
            renderTop();
            renderSettings();
            scheduleInert();
            document.querySelector("[data-act='settings']")?.focus();
        };
        // ===== ワークスペースの既定の保存 =====
        /** 既定の保存の確かめを今の状態で描く（開き直して、最初のフォーカスを取り消すに置く） */
        const renderConfirm = () => {
            const old = document.querySelector("dialog.sconfirm");
            old?.close();
            old?.remove();
            if (display.confirm === null)
                return;
            const dialog = MindmapPreview.settingsConfirm({
                from: { look: resolved.defaultLook, kinds: resolved.defaultKinds },
                to: { look: resolved.look, kinds: resolved.kinds },
                busy: display.confirm.busy,
                error: display.confirm.error,
                on: { save: () => void saveDefault(), cancel: closeConfirm },
            });
            document.body.append(dialog);
            dialog.showModal();
        };
        /** 確かめを開く */
        const openConfirm = () => {
            display.confirm = { busy: false, error: null };
            renderConfirm();
        };
        /** 何も書かずに確かめを閉じ、「ワークスペースの既定にする」へフォーカスを戻す */
        const closeConfirm = () => {
            display.confirm = null;
            renderConfirm();
            document.querySelector('.settings-drawer [data-focus="save"]')?.focus();
        };
        /** 今当てている見た目と表示する種類を、ワークスペースの既定として保存する */
        const saveDefault = async () => {
            if (display.confirm === null)
                return;
            display.confirm = { busy: true, error: null };
            renderConfirm();
            const result = await MindmapPreview.putDisplay({
                network_look: resolved.look,
                visible_kinds: MindmapPreview.KIND_KEYS.filter((kind) => resolved.kinds.has(kind)),
            });
            if (!result.ok) {
                // 断られた・届かない: 確かめの中に理由を出し、config.yaml と画面の表示は保存の前のまま
                display.confirm = {
                    busy: false,
                    error: result.detail === null
                        ? "保存できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから保存してください。"
                        : `保存できませんでした。${result.detail}`,
                };
                renderConfirm();
                return;
            }
            // 書けた: 返った既定を記録に入れ、個人の上書きはそのまま残す
            const saved = result.data?.display ?? { network_look: resolved.look, visible_kinds: MindmapPreview.KIND_KEYS.filter((kind) => resolved.kinds.has(kind)) };
            data = { ...data, settings: { ...data.settings, display: saved } };
            index = MindmapPreview.buildIndex(data);
            display.savedDisplay = saved;
            display.message = { kind: "ok", text: `ワークスペースの既定にしました（${MindmapPreview.formatJst(new Date().toISOString())}）。` };
            display.confirm = null;
            renderConfirm();
            resolved = resolveDisplay(prefs, data.settings.display);
            redrawKeepingState();
            renderSettings();
            document.querySelector('.settings-drawer [data-focus="same"]')?.focus();
        };
        // ===== 変更履歴と差分の表示 =====
        /** 選んだ時点を変えて残し、どの画面もその時点の差分の表示で描き直す（記録は読み直さず、履歴に積まない）。null は差分の表示をやめる */
        const selectPoint = (sel) => {
            prefs.diffSel = sel;
            persist();
            point = MindmapPreview.resolveDiffPoint(data.changes, sel, since);
            redrawKeepingState();
        };
        /** 変更履歴のモーダルを開く（開いているときは何もしない） */
        const openHistory = () => {
            if (document.querySelector("dialog.hist") !== null)
                return;
            const dialog = MindmapPreview.historyDialog({
                points: historyPoints({ changes: data.changes, since }),
                current: point?.sel ?? "",
                onPick: (sel) => selectPoint(sel === "" ? null : sel),
                // 選ばずに閉じたときも、選んだときも、「変更履歴」のボタンへフォーカスを戻す
                onClose: () => document.querySelector("[data-act='hist']")?.focus(),
            });
            document.body.append(dialog);
            dialog.showModal();
        };
        /** 記録を読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
        const reload = async () => {
            const result = await MindmapPreview.fetchRecords();
            if (!result.ok)
                return;
            await loadReview();
            const previousDisplay = data.settings.display;
            data = result.data;
            index = MindmapPreview.buildIndex(data);
            // ロックした項目が無くなっていれば、ロックを外す
            if (lockState.graph !== null && !index.byId.has(lockState.graph))
                lockState.graph = null;
            if (lockState.map !== null && index.byId.get(lockState.map)?.kind !== "decisions")
                lockState.map = null;
            // 表示の既定が変わった: 上書きを持たない項目に新しい既定を当て、知らせる（自分が既定にした直後の知らせは出さない）
            if (display.savedDisplay !== null && sameDisplay(display.savedDisplay, data.settings.display)) {
                display.savedDisplay = null;
            }
            else if (!sameDisplay(previousDisplay, data.settings.display)) {
                display.savedDisplay = null;
                MindmapPreview.settingsNotice({ durationMs: MindmapPreview.NOTICE_MS });
                display.message = { kind: "info", text: `ワークスペースの既定が変わりました（${MindmapPreview.formatJst(new Date().toISOString())}）。` };
            }
            resolved = resolveDisplay(prefs, data.settings.display);
            // 開いていた画面の種類が表示しない種類になった: 概要へ移る
            const visible = visibleRoute(route);
            if (visible !== route) {
                route = visible;
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
            }
            // 選んだ時点と「前回開いてから」の始まりは保ち、新しい記録で印を引き直す
            point = MindmapPreview.resolveDiffPoint(data.changes, prefs.diffSel ?? null, since);
            document.title = `${data.settings.summary} | mindstella`;
            // 開いていた項目が消えた: 詳細パネルを閉じる
            if (route.id !== null && !index.byId.has(route.id)) {
                route = { ...route, id: null, full: false, filters: {}, heading: null };
                MindmapPreview.navigate({ route, push: false });
            }
            redrawKeepingState();
            renderComments();
            renderSettings();
        };
        // ===== 操作と履歴 =====
        document.addEventListener("keydown", (event) => {
            // L: ネットワークで、詳細を開いている項目をもう一度押したのと同じ規則でロックを付け外しする。修飾キーがあるとき・変換中・入力欄にフォーカスがあるとき・重ねる面を開いているときは受けない
            if (event.key.toLowerCase() === "l" &&
                !event.ctrlKey &&
                !event.altKey &&
                !event.metaKey &&
                !event.isComposing &&
                !MindmapPreview.isTyping(document.activeElement) &&
                document.querySelector("dialog[open]") === null &&
                document.querySelector(":popover-open") === null &&
                matchMedia(MindmapPreview.LOCK_QUERY).matches &&
                route.tab === "graph" &&
                route.id !== null) {
                if (lockPress({ key: "graph", pressed: route.id }) === "shake")
                    MindmapPreview.shakeGraphKey();
            }
            // Ctrl+K（macOS は Cmd+K）で全体の検索を開く。入力欄に入力中でも開き、開いているときは検索の言葉を選び直す
            if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
                event.preventDefault();
                const opened = document.querySelector("dialog.search input");
                if (opened !== null)
                    opened.select();
                else
                    openSearch();
            }
            // Esc: 重ねる面が無いときは、詳細パネルを閉じる
            if (event.key === "Escape" &&
                route.id !== null &&
                !route.full &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                closeDetail();
            }
            else if (event.key === "Escape" &&
                route.id === null &&
                comment.listOpen &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                closeList();
            }
            else if (event.key === "Escape" &&
                route.id === null &&
                display.open &&
                document.querySelector("dialog[open]") === null &&
                document.querySelector(":popover-open") === null) {
                closeSettings();
            }
        });
        /** ハッシュが変わったとき（戻る・進む・手で書き換えた）、その画面を描く */
        const onLocationChange = () => {
            const parsed = MindmapPreview.parseHash({ hash: location.hash, index });
            const next = visibleRoute(parsed);
            // 表示しない種類のタブを指していた: ハッシュを概要に置き換える
            if (next !== parsed)
                MindmapPreview.navigate({ route: { ...next, filters: {} }, push: false });
            // 画面・表示形式・項目が同じで絞り込み（`f.{列}`）も無いときは、描き直さない。絞り込みだけを足したハッシュは、開き直しとして使う
            if (MindmapPreview.toHash(next) === MindmapPreview.toHash(route) && Object.keys(next.filters).length === 0)
                return;
            const screen = next.tab !== route.tab ||
                next.view !== route.view ||
                Object.keys(next.filters).length > 0 ||
                (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
            route = next;
            render({ screen });
            // 絞り込みは画面に渡した後、ハッシュから消す（残すと、次のハッシュの変化で使い回される）
            if (Object.keys(next.filters).length > 0)
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
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
