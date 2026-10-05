// サーバーの配信とのやり取り。記録の取得・レビュー中のコメントと書きかけ・まとめて送る・書き換えの知らせの購読。

namespace MindmapPreview {
  /** 配信のパス（画面が開いた URL からの相対パス） */
  export const API_PATHS = {
    records: "api/records",
    events: "api/events",
    comments: "api/comments",
    commentsSend: "api/comments/send",
    drafts: "api/drafts",
    opened: "api/opened",
  } as const;

  /** 記録の取得の結果。読めなかったときは、届かなかったか、サーバーが 422 を返したかを分ける */
  export type FetchResult =
    | { ok: true; data: MindmapData }
    | { ok: false; reason: "unreachable" | "invalid"; detail: string | null };

  /** コメント・書きかけの API を呼んだ結果。届かなかったとき `status`・`detail` は null */
  export type ApiResult<T> =
    | { ok: true; data: T | null }
    | { ok: false; status: number | null; detail: string | null; stale: { id: string; reason: string }[] };

  /** コメント・書きかけが持つ箇所（本文の行の範囲か、項目の値のキーと、選んだ文） */
  export type Location = {
    kind: "body" | "value";
    /** `body` のときの始めの行（1 始まり） */
    start?: number;
    /** `body` のときの終わりの行 */
    end?: number;
    /** `value` のときの項目のキーのパス */
    key?: string;
    /** 選んだ文 */
    text: string;
  };

  /** 『レビュー中のコメントの読み取り』の本文 */
  export type ReviewState = {
    items: {
      id: string;
      target: string | null;
      target_title: string | null;
      loc: Location | null;
      body: string;
      created: string;
    }[];
    drafts: { target: string | null; loc: Location | null; body: string }[];
  };

  /** HTTP のメソッド */
  type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

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

  /** プレビューを開いたことを知らせ、前回開いた日時を返す。届かない・200 でない・読めないときは null */
  export async function postOpened(fetchFn: FetchFn = window.fetch.bind(window)): Promise<string | null> {
    try {
      const response = await fetchFn(API_PATHS.opened, { method: "POST" });
      if (!response.ok) return null;
      const body = (await response.json()) as { previous?: unknown };
      return typeof body.previous === "string" ? body.previous : null;
    } catch {
      return null;
    }
  }

  /** コメント・書きかけの API を 1 回呼ぶ。届かないときと、断られたときを分ける */
  export async function callApi<T = unknown>(
    method: Method,
    path: string,
    body: object | null = null,
    fetchFn: FetchFn = window.fetch.bind(window),
  ): Promise<ApiResult<T>> {
    let response: Response;
    try {
      response = await fetchFn(
        path,
        body === null
          ? { method, cache: "no-store" }
          : { method, cache: "no-store", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
      );
    } catch {
      return { ok: false, status: null, detail: null, stale: [] };
    }
    if (response.ok) {
      // 204 は本文を持たない
      return { ok: true, data: response.status === 204 ? null : ((await response.json()) as T) };
    }
    // 断られた: 理由が読めなければ、ステータスの文言を使う
    let stale: { id: string; reason: string }[] = [];
    let detail: string | null = null;
    try {
      const problem = (await response.json()) as { detail?: unknown; stale?: { id: string; reason: string }[] };
      detail = typeof problem.detail === "string" ? problem.detail : null;
      stale = Array.isArray(problem.stale) ? problem.stale : [];
    } catch {
      // 本文が JSON でない
    }
    return {
      ok: false,
      status: response.status,
      detail: detail ?? (response.statusText || String(response.status)),
      stale,
    };
  }

  /** コメント・書きかけの 6 つの呼び出しを束ねて返す */
  export function commentApi(fetchFn: FetchFn = window.fetch.bind(window)) {
    return {
      read: () => callApi<ReviewState>("GET", API_PATHS.comments, null, fetchFn),
      add: (input: object) => callApi<{ id: string; created: string; count: number }>("POST", API_PATHS.comments, input, fetchFn),
      update: (id: string, patch: object) =>
        callApi<{ id: string; body: string; loc: Location | null }>(
          "PATCH",
          `${API_PATHS.comments}/${encodeURIComponent(id)}`,
          patch,
          fetchFn,
        ),
      remove: (id: string) =>
        callApi<ReviewState["items"][number] & { count: number }>(
          "DELETE",
          `${API_PATHS.comments}/${encodeURIComponent(id)}`,
          null,
          fetchFn,
        ),
      saveDraft: (draft: object) => callApi<null>("PUT", API_PATHS.drafts, draft, fetchFn),
      send: (ids: string[]) =>
        callApi<{ sent: string; items: { comment: string; submission: string }[] }>(
          "POST",
          API_PATHS.commentsSend,
          { ids },
          fetchFn,
        ),
    };
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
