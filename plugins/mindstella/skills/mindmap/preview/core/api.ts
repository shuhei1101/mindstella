// サーバーの配信とのやり取り。記録の取得・レビュー中のコメントと書きかけ・まとめて送る・スレッド・書き換えの知らせの購読。

namespace MindmapPreview {
  /** 配信のパス（画面が開いた URL からの相対パス） */
  export const API_PATHS = {
    records: "api/records",
    events: "api/events",
    comments: "api/comments",
    commentsSend: "api/comments/send",
    drafts: "api/drafts",
    opened: "api/opened",
    configDisplay: "api/config/display",
    threads: "api/threads",
    edits: "api/edits",
    editsSave: "api/edits/save",
  } as const;

  /** 記録の取得の結果。読めなかったときは、届かなかったか、サーバーが 422 を返したかを分ける */
  export type FetchResult =
    | { ok: true; data: MindmapData }
    | { ok: false; reason: "unreachable" | "invalid"; detail: string | null };

  /** コメント・書きかけの API を呼んだ結果。届かなかったとき `status`・`detail` は null */
  export type ApiResult<T> =
    | { ok: true; data: T | null }
    | {
        ok: false;
        status: number | null;
        detail: string | null;
        stale: { id: string; reason: string }[];
        /** 409 のときの書き込めない編集（まとめて保存だけが持つ。それ以外はキーを持たない） */
        blocked?: BlockedEdit[];
      };

  /** 『保存待ちの編集の読み取り』の `items[]` の 1 件 */
  export type PendingEdit = {
    /** `E-{連番}` */
    id: string;
    /** 項目の ID・追加する項目の仮の ID（`new-{連番}`）・`settings` */
    target: string;
    op: "set" | "option-add" | "option-edit" | "option-remove" | "adopt" | "item-add" | "item-remove" | "setting";
    /** 項目のキー・案の記号・種類・設定のキー */
    key: string | null;
    /** 編集した後の値 */
    value: unknown;
    /** 溜めたときの元の値 */
    before: unknown;
    /** 最初に溜めた日時 */
    created: string;
  };

  /** まとめて保存の 409 の `blocked[]` の 1 件 */
  export type BlockedEdit = {
    id: string;
    reason: "changed" | "missing" | "referenced" | "invalid";
    /** 日本語の理由 */
    detail: string;
    /** `referenced` のとき、消す項目を指している項目の ID */
    refs: string[];
  };

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

  /** 『レビュー中のコメントの読み取り』の本文。`thread` を持つ書き込みはスレッドへの返信、持たないものは新しいスレッドの最初の書き込み */
  export type ReviewState = {
    items: {
      id: string;
      target: string | null;
      target_title: string | null;
      loc: Location | null;
      thread: string | null;
      body: string;
      created: string;
    }[];
    drafts: { target: string | null; loc: Location | null; thread: string | null; body: string }[];
  };

  /** 書き手 */
  export type PostAuthor = "user" | "ai";

  /** 『スレッドの読み取り』の `threads[]` の 1 件 */
  export type Thread = {
    id: string;
    status: "open" | "closed";
    tags: string[];
    /** 要約。まだ書いていなければ null */
    summary: string | null;
    target: string | null;
    /** 向けた項目のタイトル。項目が消えていれば null */
    target_title: string | null;
    /** 最初の書き込みに添えた箇所 */
    loc: Location | null;
    /** 書き込み。`seen` は利用者の既読 */
    posts: { id: string; author: PostAuthor; body: string; created: string; seen: boolean }[];
    events: { kind: "closed" | "reopened"; author: PostAuthor; reason: string | null; created: string }[];
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

  /** 前回開いた時点。「前回開いてから」の範囲の始まり */
  export type OpenedPoint = {
    /** 開いた日時（UTC のタイムゾーン付き ISO 8601）。`{日時} より後` の表示にだけ使う */
    at: string;
    /** 開いた時点の先頭のまとまりの `until_seq`（無ければ 0）。`until_seq` がこれより大きいまとまりが範囲に入る */
    seq: number;
  };

  /** `POST /api/opened` の応答 */
  export type OpenedReply = {
    /** 前回開いた時点。無いときは null */
    previous: OpenedPoint | null;
    /** サーバーが書き込んだ今の時点 */
    opened: OpenedPoint;
  };

  /** 値が前回開いた時点の形（文字列の `at` と 0 以上の整数の `seq`）か。日時だけの文字列（前の版の形）は偽 */
  export function isOpenedPoint(value: unknown): value is OpenedPoint {
    if (typeof value !== "object" || value === null) return false;
    const { at, seq } = value as { at?: unknown; seq?: unknown };
    return typeof at === "string" && typeof seq === "number" && Number.isInteger(seq) && seq >= 0;
  }

  /** プレビューを開いたことを知らせ、前回開いた時点と今の時点を返す。届かない・200 でない・読めないときは null */
  export async function postOpened(fetchFn: FetchFn = window.fetch.bind(window)): Promise<OpenedReply | null> {
    try {
      const response = await fetchFn(API_PATHS.opened, { method: "POST" });
      if (!response.ok) return null;
      const body = (await response.json()) as { previous?: unknown; opened?: unknown };
      // 今の時点が読めない（前の版の形）: 使わない
      if (!isOpenedPoint(body.opened)) return null;
      return { previous: isOpenedPoint(body.previous) ? body.previous : null, opened: body.opened };
    } catch {
      return null;
    }
  }

  /** ワークスペースの既定として、見た目と表示する種類を保存する。200 なら `data` が書いた後の `{display}` */
  export async function putDisplay(
    display: { network_look: string; visible_kinds: string[] },
    fetchFn: FetchFn = window.fetch.bind(window),
  ): Promise<ApiResult<{ display: DisplayDefaults }>> {
    return callApi("PUT", API_PATHS.configDisplay, display, fetchFn);
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
    let blocked: BlockedEdit[] = [];
    let detail: string | null = null;
    try {
      const problem = (await response.json()) as {
        detail?: unknown;
        stale?: { id: string; reason: string }[];
        blocked?: BlockedEdit[];
      };
      detail = typeof problem.detail === "string" ? problem.detail : null;
      stale = Array.isArray(problem.stale) ? problem.stale : [];
      blocked = Array.isArray(problem.blocked) ? problem.blocked : [];
    } catch {
      // 本文が JSON でない
    }
    return {
      ok: false,
      status: response.status,
      detail: detail ?? (response.statusText || String(response.status)),
      stale,
      ...(blocked.length > 0 ? { blocked } : {}),
    };
  }

  /** コメント・書きかけの API の 6 つの呼び出しを束ねて返す */
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
        callApi<{ sent: string; items: { comment: string; thread: string; post: string }[]; entered: boolean }>(
          "POST",
          API_PATHS.commentsSend,
          { ids },
          fetchFn,
        ),
    };
  }

  /** 保存待ちの編集の読み取り・追加・取り消し・まとめて保存を束ねて返す */
  export function editApi(fetchFn: FetchFn = window.fetch.bind(window)) {
    return {
      read: () => callApi<{ items: PendingEdit[]; count: number }>("GET", API_PATHS.edits, null, fetchFn),
      add: (input: object) => callApi<{ id: string | null; target: string; count: number }>("POST", API_PATHS.edits, input, fetchFn),
      remove: (id: string) =>
        callApi<{ removed: string[]; count: number }>(
          "DELETE",
          `${API_PATHS.edits}/${encodeURIComponent(id)}`,
          null,
          fetchFn,
        ),
      save: () =>
        callApi<{
          set: string | null;
          at: string;
          added: { temp: string; id: string }[];
          changed: string[];
          removed: string[];
          settings: string[];
        }>("POST", API_PATHS.editsSave, null, fetchFn),
    };
  }

  /** スレッドの読み取り・状態の書き換え・利用者の既読を束ねて返す。理由が空白だけなら `null` を送る */
  export function threadApi(fetchFn: FetchFn = window.fetch.bind(window)) {
    return {
      read: () => callApi<{ threads: Thread[] }>("GET", API_PATHS.threads, null, fetchFn),
      setStatus: (id: string, status: "open" | "closed", reason: string | null) =>
        callApi<{ id: string; status: string; changed: boolean }>(
          "PATCH",
          `${API_PATHS.threads}/${encodeURIComponent(id)}`,
          { status, reason: reason === null || reason.trim() === "" ? null : reason.trim() },
          fetchFn,
        ),
      seen: (id: string) =>
        callApi<{ id: string; seen: string[] }>(
          "POST",
          `${API_PATHS.threads}/${encodeURIComponent(id)}/seen`,
          null,
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
