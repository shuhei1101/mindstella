// サーバーの代わり。見本の記録（data.js が埋め込み先へ入れたもの）を `api/records` で返し、
// レビュー中のコメントの読み取り・追加・書き換え・削除を、開いている間だけ持つコピーで応える。
// 埋め込み先を空にして、プレビューをサーバーにつながった状態（コメントの入力・レビュー中のコメントを出す）で開く
(() => {
  const element = document.getElementById("mindmap-data");
  const records = JSON.parse(element.textContent);
  element.textContent = "";

  /** レビュー中のコメントの見本（D-1 へ溜めた順に 3 件（3 件目は箇所あり）、D-13 へ 1 件。D-27 は 0 件） */
  let items = [
    { id: "C-1", target: "D-1", loc: null, body: "案 A にする", created: "2026-11-02T01:00:00+00:00" },
    { id: "C-2", target: "D-1", loc: null, body: "案 B も見たい", created: "2026-11-02T01:05:00+00:00" },
    {
      id: "C-3",
      target: "D-1",
      loc: { kind: "value", key: "answer", text: "作ったワークスペースを壊さずに今の形へ整えられるようにする" },
      body: "案 C は外す",
      created: "2026-11-02T01:12:00+00:00",
    },
    { id: "C-4", target: "D-13", loc: null, body: "今の migrate との関係は、次の話し合いで決めたいです。", created: "2026-11-02T01:20:00+00:00" },
  ];
  let seq = items.length;

  /** JSON の応答を作る */
  const json = (status, body) =>
    new Response(body === null ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });

  /** 項目のタイトル（記録から引く） */
  const titleOf = (id) => {
    for (const key of ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]) {
      const found = (records[key] ?? []).find((item) => item.id === id);
      if (found !== undefined) return found.title ?? null;
    }
    return null;
  };

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const path = typeof input === "string" ? input : input.url;
    const method = (init.method ?? "GET").toUpperCase();
    const body = typeof init.body === "string" ? JSON.parse(init.body) : null;
    if (!path.startsWith("api/")) return realFetch(input, init);
    if (path === "api/records") return json(200, records);
    if (path === "api/opened") return json(200, { previous: null });
    if (path === "api/drafts") return json(204, null);
    if (path === "api/threads") return json(200, { threads: [] });
    if (path === "api/edits" && method === "GET") return json(200, { items: [], count: 0 });
    if (path === "api/comments" && method === "GET") {
      return json(200, { items: items.map((item) => ({ ...item, target_title: item.target === null ? null : titleOf(item.target) })), drafts: [] });
    }
    if (path === "api/comments" && method === "POST") {
      const id = body.id ?? `C-${++seq}`;
      const created = body.created ?? new Date().toISOString();
      items = [...items, { id, target: body.target ?? null, loc: body.loc ?? null, body: body.body, created }];
      return json(201, { id, created, count: items.length });
    }
    const match = path.match(/^api\/comments\/(.+)$/);
    if (match !== null) {
      const id = decodeURIComponent(match[1]);
      const found = items.find((item) => item.id === id);
      if (found === undefined) return json(404, { detail: "そのコメントは見つかりません。一覧を開き直してください。" });
      if (method === "PATCH") {
        const next = { ...found, ...(body.body === undefined ? {} : { body: body.body }), ...(body.loc === null ? { loc: null } : {}) };
        items = items.map((item) => (item.id === id ? next : item));
        return json(200, { id, body: next.body, loc: next.loc });
      }
      if (method === "DELETE") {
        items = items.filter((item) => item.id !== id);
        return json(200, { ...found, count: items.length });
      }
    }
    return json(404, { detail: "見本のサーバーは、この要求に応えません。" });
  };

  /** 書き換えの知らせ: つながった知らせだけを出し、書き換えは知らせない */
  window.EventSource = class {
    constructor() {
      this.listeners = {};
      setTimeout(() => (this.listeners.open ?? []).forEach((listener) => listener()), 0);
    }
    addEventListener(name, listener) {
      (this.listeners[name] ??= []).push(listener);
    }
    close() {}
  };
})();
