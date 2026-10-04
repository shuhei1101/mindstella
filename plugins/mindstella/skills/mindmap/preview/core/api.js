"use strict";
// サーバーの配信とのやり取り。記録の取得・回答・意見の送信・書き換えの知らせの購読。
var MindmapPreview;
(function (MindmapPreview) {
    /** 配信のパス（画面が開いた URL からの相対パス） */
    MindmapPreview.API_PATHS = {
        records: "api/records",
        events: "api/events",
        submissions: "api/submissions",
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
    /** 項目の ID と本文を送る。届かないときと、断られたときを分ける */
    async function postSubmission(target, body, fetchFn = window.fetch.bind(window)) {
        let response;
        try {
            response = await fetchFn(MindmapPreview.API_PATHS.submissions, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target, body }),
            });
        }
        catch {
            return { ok: false, detail: null };
        }
        if (response.status === 201) {
            const accepted = (await response.json());
            return { ok: true, id: accepted.id, sent: accepted.sent };
        }
        // 断られた: 理由が読めなければ、ステータスの文言を使う
        return { ok: false, detail: (await detailOf(response)) ?? (response.statusText || String(response.status)) };
    }
    MindmapPreview.postSubmission = postSubmission;
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
