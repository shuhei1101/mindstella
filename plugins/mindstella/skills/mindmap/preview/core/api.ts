// サーバーの配信とのやり取り。記録の取得・回答・意見の送信・書き換えの知らせの購読。

namespace MindmapPreview {
  /** 配信のパス（画面が開いた URL からの相対パス） */
  export const API_PATHS = {
    records: "api/records",
    events: "api/events",
    submissions: "api/submissions",
  } as const;

  /** 記録の取得の結果。読めなかったときは、届かなかったか、サーバーが 422 を返したかを分ける */
  export type FetchResult =
    | { ok: true; data: MindmapData }
    | { ok: false; reason: "unreachable" | "invalid"; detail: string | null };

  /** 送信の結果。届かなかったときの `detail` は null */
  export type SendResult = { ok: true; id: string; sent: string } | { ok: false; detail: string | null };

  /** 要求を送る関数（テストでは偽の関数を渡す） */
  export type FetchFn = typeof fetch;

  /** 書き換えの知らせにつなぐ関数の型（テストでは偽のものを渡す） */
  export type EventSourceCtor = typeof EventSource;

  /** 応答の本文から、日本語の理由（`detail`）を取り出す。読めなければ null */
  async function detailOf(response: Response): Promise<string | null> {
    try {
      const problem = (await response.json()) as { detail?: unknown };
      return typeof problem.detail === "string" ? problem.detail : null;
    } catch {
      return null;
    }
  }

  /** 記録を読む。届かないときと、サーバーが読めないと返したときを分ける */
  export async function fetchRecords(fetchFn: FetchFn = window.fetch.bind(window)): Promise<FetchResult> {
    let response: Response;
    try {
      response = await fetchFn(API_PATHS.records, { cache: "no-store" });
    } catch {
      return { ok: false, reason: "unreachable", detail: null };
    }
    // 200 でない: サーバーが読めないと返した
    if (!response.ok) return { ok: false, reason: "invalid", detail: await detailOf(response) };
    return { ok: true, data: (await response.json()) as MindmapData };
  }

  /** 項目の ID と本文を送る。届かないときと、断られたときを分ける */
  export async function postSubmission(
    target: string,
    body: string,
    fetchFn: FetchFn = window.fetch.bind(window),
  ): Promise<SendResult> {
    let response: Response;
    try {
      response = await fetchFn(API_PATHS.submissions, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, body }),
      });
    } catch {
      return { ok: false, detail: null };
    }
    if (response.status === 201) {
      const accepted = (await response.json()) as { id: string; sent: string };
      return { ok: true, id: accepted.id, sent: accepted.sent };
    }
    // 断られた: 理由が読めなければ、ステータスの文言を使う
    return { ok: false, detail: (await detailOf(response)) ?? (response.statusText || String(response.status)) };
  }

  /** 書き換えの知らせにつなぎ、`changed` と接続の状態の変化を知らせる。つなぎ直しは `EventSource` に任せる。返す関数でつながりを閉じる */
  export function subscribeEvents({
    onChanged,
    onConnection,
    EventSourceCtor = window.EventSource,
  }: {
    onChanged: () => void;
    onConnection: (connected: boolean) => void;
    EventSourceCtor?: EventSourceCtor;
  }): () => void {
    const source = new EventSourceCtor(API_PATHS.events);
    let last: boolean | null = null;
    /** 接続の状態が変わったときだけ知らせる */
    const report = (connected: boolean): void => {
      if (last === connected) return;
      last = connected;
      onConnection(connected);
    };
    source.addEventListener("open", () => report(true));
    source.addEventListener("error", () => report(false));
    source.addEventListener("changed", () => onChanged());
    return () => source.close();
  }
}
