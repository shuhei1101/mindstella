// サーバーの代わり。見本の記録（data.js が埋め込み先へ入れたもの）を `api/records` で返し、保存待ちの編集の読み取り・追加・取り消し・まとめて保存に応える。
// 保存待ちの編集はタブの保存領域に持ち、読み込み直しても残る（モック専用の操作列の「見本に戻す」で消す）。保存は見本の記録へ当てて、編集を 0 件にする。
// レビュー中のコメントとスレッドは 0 件。埋め込み先を空にして、プレビューをサーバーにつながった状態で開く
(() => {
  const element = document.getElementById("mindmap-data");
  const records = JSON.parse(element.textContent);
  element.textContent = "";

  /** タブの保存領域のキー（保存待ちの編集と、保存した項目のキー） */
  const EDITS_KEY = "mock-385-edits";
  const SAVED_KEY = "mock-385-saved";
  const KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"];

  /** 保存待ちの編集（`{seq, items}`） */
  let store = JSON.parse(sessionStorage.getItem(EDITS_KEY) ?? '{"seq":0,"items":[]}');
  /** 保存した項目のキー（`{id: {key: value}}`）。読み込み直しても見本の記録へ当て直す */
  const saved = JSON.parse(sessionStorage.getItem(SAVED_KEY) ?? "{}");
  const persist = () => {
    sessionStorage.setItem(EDITS_KEY, JSON.stringify(store));
    sessionStorage.setItem(SAVED_KEY, JSON.stringify(saved));
  };

  /** 項目を ID で引く */
  const itemOf = (id) => {
    for (const kind of KINDS) {
      const found = (records[kind] ?? []).find((item) => item.id === id);
      if (found !== undefined) return found;
    }
    return null;
  };
  for (const [id, keys] of Object.entries(saved)) Object.assign(itemOf(id) ?? {}, keys);

  /** JSON の応答を作る */
  const json = (status, body) =>
    new Response(body === null ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  const same = (left, right) => JSON.stringify(left ?? null) === JSON.stringify(right ?? null);

  /** 編集を 1 件溜める（同じ項目・キーは値だけを書き換え、今の値に戻した編集は外す） */
  const addEdit = (body) => {
    const item = itemOf(body.target);
    const current = item === null ? null : item[body.key];
    const existing = store.items.find((edit) => edit.target === body.target && edit.op === body.op && edit.key === body.key);
    if (body.op === "set" && same(body.value, current)) {
      store.items = store.items.filter((edit) => edit !== existing);
      persist();
      return { id: null, target: body.target, count: store.items.length };
    }
    if (existing !== undefined) {
      existing.value = body.value;
      persist();
      return { id: existing.id, target: body.target, count: store.items.length };
    }
    const edit = { id: `E-${++store.seq}`, target: body.target, op: body.op, key: body.key ?? null, value: body.value, before: current ?? null, created: new Date().toISOString() };
    store.items.push(edit);
    persist();
    return { id: edit.id, target: body.target, count: store.items.length };
  };

  /** 溜めた編集を見本の記録へ当てて、0 件にする（見本はキーの書き換えだけを当てる） */
  const saveEdits = () => {
    const changed = [];
    for (const edit of store.items) {
      const item = itemOf(edit.target);
      if (item === null || edit.op !== "set") continue;
      item[edit.key] = edit.value;
      item.edited_by = "user";
      saved[edit.target] = { ...(saved[edit.target] ?? {}), [edit.key]: edit.value, edited_by: "user" };
      if (!changed.includes(edit.target)) changed.push(edit.target);
    }
    store = { seq: store.seq, items: [] };
    persist();
    return { set: null, at: new Date().toISOString(), added: [], changed, removed: [], settings: [] };
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
    if (path === "api/comments" && method === "GET") return json(200, { items: [], drafts: [] });
    if (path === "api/edits" && method === "GET") return json(200, { items: store.items, count: store.items.length });
    if (path === "api/edits" && method === "POST") return json(200, addEdit(body));
    if (path === "api/edits/save" && method === "POST") return json(200, saveEdits());
    const match = path.match(/^api\/edits\/(.+)$/);
    if (match !== null && method === "DELETE") {
      const id = decodeURIComponent(match[1]);
      store.items = store.items.filter((edit) => edit.id !== id);
      persist();
      return json(200, { removed: [id], count: store.items.length });
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
