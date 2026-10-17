"use strict";
// サーバーの配信とのやり取り。記録の取得・レビュー中のコメントと書きかけ・まとめて送る・スレッド・書き換えの知らせの購読。
var MindmapPreview;
(function (MindmapPreview) {
    /** 配信のパス（画面が開いた URL からの相対パス） */
    MindmapPreview.API_PATHS = {
        records: "api/records",
        events: "api/events",
        comments: "api/comments",
        commentsSend: "api/comments/send",
        drafts: "api/drafts",
        opened: "api/opened",
        configDisplay: "api/config/display",
        threads: "api/threads",
    };
    /** 応答の本文から、日本語の理由（`detail`）を取り出す。読めなければ null */
    async function detailOf(response) {
        try {
            const problem = (await response.json());
            return typeof problem.detail === "string" ? problem.detail : null;
        }
        catch {
            return null;
        }
    }
    /** 記録を読む。届かないときと、サーバーが読めないと返したときを分ける */
    async function fetchRecords(fetchFn = window.fetch.bind(window)) {
        let response;
        try {
            response = await fetchFn(MindmapPreview.API_PATHS.records, { cache: "no-store" });
        }
        catch {
            return { ok: false, reason: "unreachable", detail: null };
        }
        // 200 でない: サーバーが読めないと返した
        if (!response.ok)
            return { ok: false, reason: "invalid", detail: await detailOf(response) };
        return { ok: true, data: (await response.json()) };
    }
    MindmapPreview.fetchRecords = fetchRecords;
    /** 値が前回開いた時点の形（文字列の `at` と 0 以上の整数の `seq`）か。日時だけの文字列（前の版の形）は偽 */
    function isOpenedPoint(value) {
        if (typeof value !== "object" || value === null)
            return false;
        const { at, seq } = value;
        return typeof at === "string" && typeof seq === "number" && Number.isInteger(seq) && seq >= 0;
    }
    MindmapPreview.isOpenedPoint = isOpenedPoint;
    /** プレビューを開いたことを知らせ、前回開いた時点と今の時点を返す。届かない・200 でない・読めないときは null */
    async function postOpened(fetchFn = window.fetch.bind(window)) {
        try {
            const response = await fetchFn(MindmapPreview.API_PATHS.opened, { method: "POST" });
            if (!response.ok)
                return null;
            const body = (await response.json());
            // 今の時点が読めない（前の版の形）: 使わない
            if (!isOpenedPoint(body.opened))
                return null;
            return { previous: isOpenedPoint(body.previous) ? body.previous : null, opened: body.opened };
        }
        catch {
            return null;
        }
    }
    MindmapPreview.postOpened = postOpened;
    /** ワークスペースの既定として、見た目と表示する種類を保存する。200 なら `data` が書いた後の `{display}` */
    async function putDisplay(display, fetchFn = window.fetch.bind(window)) {
        return callApi("PUT", MindmapPreview.API_PATHS.configDisplay, display, fetchFn);
    }
    MindmapPreview.putDisplay = putDisplay;
    /** コメント・書きかけの API を 1 回呼ぶ。届かないときと、断られたときを分ける */
    async function callApi(method, path, body = null, fetchFn = window.fetch.bind(window)) {
        let response;
        try {
            response = await fetchFn(path, body === null
                ? { method, cache: "no-store" }
                : { method, cache: "no-store", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        }
        catch {
            return { ok: false, status: null, detail: null, stale: [] };
        }
        if (response.ok) {
            // 204 は本文を持たない
            return { ok: true, data: response.status === 204 ? null : (await response.json()) };
        }
        // 断られた: 理由が読めなければ、ステータスの文言を使う
        let stale = [];
        let detail = null;
        try {
            const problem = (await response.json());
            detail = typeof problem.detail === "string" ? problem.detail : null;
            stale = Array.isArray(problem.stale) ? problem.stale : [];
        }
        catch {
            // 本文が JSON でない
        }
        return {
            ok: false,
            status: response.status,
            detail: detail ?? (response.statusText || String(response.status)),
            stale,
        };
    }
    MindmapPreview.callApi = callApi;
    /** コメント・書きかけの API の 6 つの呼び出しを束ねて返す */
    function commentApi(fetchFn = window.fetch.bind(window)) {
        return {
            read: () => callApi("GET", MindmapPreview.API_PATHS.comments, null, fetchFn),
            add: (input) => callApi("POST", MindmapPreview.API_PATHS.comments, input, fetchFn),
            update: (id, patch) => callApi("PATCH", `${MindmapPreview.API_PATHS.comments}/${encodeURIComponent(id)}`, patch, fetchFn),
            remove: (id) => callApi("DELETE", `${MindmapPreview.API_PATHS.comments}/${encodeURIComponent(id)}`, null, fetchFn),
            saveDraft: (draft) => callApi("PUT", MindmapPreview.API_PATHS.drafts, draft, fetchFn),
            send: (ids) => callApi("POST", MindmapPreview.API_PATHS.commentsSend, { ids }, fetchFn),
        };
    }
    MindmapPreview.commentApi = commentApi;
    /** スレッドの読み取り・状態の書き換え・利用者の既読を束ねて返す。理由が空白だけなら `null` を送る */
    function threadApi(fetchFn = window.fetch.bind(window)) {
        return {
            read: () => callApi("GET", MindmapPreview.API_PATHS.threads, null, fetchFn),
            setStatus: (id, status, reason) => callApi("PATCH", `${MindmapPreview.API_PATHS.threads}/${encodeURIComponent(id)}`, { status, reason: reason === null || reason.trim() === "" ? null : reason.trim() }, fetchFn),
            seen: (id) => callApi("POST", `${MindmapPreview.API_PATHS.threads}/${encodeURIComponent(id)}/seen`, null, fetchFn),
        };
    }
    MindmapPreview.threadApi = threadApi;
    /** 書き換えの知らせにつなぎ、`changed` と接続の状態の変化を知らせる。つなぎ直しは `EventSource` に任せる。返す関数でつながりを閉じる */
    function subscribeEvents({ onChanged, onConnection, EventSourceCtor = window.EventSource, }) {
        const source = new EventSourceCtor(MindmapPreview.API_PATHS.events);
        let last = null;
        /** 接続の状態が変わったときだけ知らせる */
        const report = (connected) => {
            if (last === connected)
                return;
            last = connected;
            onConnection(connected);
        };
        source.addEventListener("open", () => report(true));
        source.addEventListener("error", () => report(false));
        source.addEventListener("changed", () => onChanged());
        return () => source.close();
    }
    MindmapPreview.subscribeEvents = subscribeEvents;
})(MindmapPreview || (MindmapPreview = {}));
