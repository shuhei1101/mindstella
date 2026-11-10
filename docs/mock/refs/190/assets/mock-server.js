// サーバーの代わり。#127 の見本の記録（data.js が埋め込み先へ入れたもの）を `api/records` で返し、
// レビュー中のコメントの読み取り・追加・書き換え・削除を、開いている間だけ持つ写しで応える。
// 埋め込み先を空にして、プレビューをサーバーにつながった状態（コメントのボタン・入力・レビュー中のコメントを出す）で開く。
// クエリの `fail=edit` で、書き換えを届かない状態にする
(() => {
  const element = document.getElementById("mindmap-data");
  const records = JSON.parse(element.textContent);
  element.textContent = "";

  const failEdit = new URLSearchParams(location.search).get("fail") === "edit";

  /** レビュー中のコメントの見本（D-48 へ箇所あり 1 件・箇所なし 2 件、ほかの項目へ 1 件、項目を指さない 1 件） */
  let items = [
    {
      id: "C-1",
      target: "D-48",
      target_title: "最上位の軸の呼び名を AI が直す",
      loc: { kind: "value", key: "lead", text: "呼び名は帯・表の列・詳細パネルに出る" },
      body: "ネットワークの星のラベルにも出るので、並びに足してください。",
      created: "2026-10-09T01:00:00+00:00",
    },
    {
      id: "C-2",
      target: "D-48",
      target_title: "最上位の軸の呼び名を AI が直す",
      loc: null,
      body: "推奨は B でよいと思います。セットアップで聞く 1 問の文言も見せてほしいです。",
      created: "2026-10-09T01:05:00+00:00",
    },
    {
      id: "C-3",
      target: "D-48",
      target_title: "最上位の軸の呼び名を AI が直す",
      loc: null,
      body: "C の「固定の『対象』にする」は、分野ごとの言葉で読めないので外してよいです。\nただし、呼び名を提案するときに、利用者が断れる（今のまま「対象」で進める）道は残してください。断った後でも設定から直せることを、セットアップの最後に 1 行で伝えると迷わないと思います。",
      created: "2026-10-09T01:12:00+00:00",
    },
    {
      id: "C-4",
      target: "D-10",
      target_title: null,
      loc: null,
      body: "決めた理由に、比べた案の名前も残してください。",
      created: "2026-10-09T01:20:00+00:00",
    },
    {
      id: "C-5",
      target: null,
      target_title: null,
      loc: null,
      body: "全体に、未決定の数が多いので次の話し合いで絞りたいです。",
      created: "2026-10-09T01:30:00+00:00",
    },
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
    if (path === "api/comments" && method === "GET") {
      return json(200, { items: items.map((item) => ({ ...item, target_title: item.target === null ? null : titleOf(item.target) })), drafts: [] });
    }
    if (path === "api/comments" && method === "POST") {
      const id = body.id ?? `C-${++seq}`;
      const created = body.created ?? new Date().toISOString();
      items = [...items, { id, target: body.target ?? null, target_title: null, loc: body.loc ?? null, body: body.body, created }].sort((a, b) =>
        a.created.localeCompare(b.created),
      );
      return json(201, { id, created, count: items.length });
    }
    const match = path.match(/^api\/comments\/(.+)$/);
    if (match !== null) {
      const id = decodeURIComponent(match[1]);
      const found = items.find((item) => item.id === id);
      if (found === undefined) return json(404, { detail: "そのコメントは見つかりません。一覧を開き直してください。" });
      if (method === "PATCH") {
        // 届かない見本: 要求が通らない
        if (failEdit) throw new TypeError("Failed to fetch");
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
