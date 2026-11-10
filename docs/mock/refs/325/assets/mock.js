// サーバーの代わりとモックの操作。app.js の起動の前に、見本の記録（data.js が埋め込み先へ入れたもの）を取り出して埋め込み先を空にし、
// サーバーにつながった状態で起動させる。記録・レビュー中のコメント・スレッドの受け口と書き換えの知らせを置き換える。
// 見本の状態はクエリで切り替える（edit.js が読む見本のキーは edit.js の冒頭に書く）。
//   diff: 選ぶ時点（無し: 差分を出さない / V-6 など: その時点を選んだ差分の表示で開く）
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 選んだ時点を端末の設定へ入れる（クエリに無いときは差分を出さない）
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = params.get("diff");
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));
  // 「前回開いてから」の始まりを、見本の書き換えのまとまりの間に固定する
  sessionStorage.setItem("mindmap-since", "2026-10-07T00:00:00+00:00");

  // ===== 見本の記録 =====
  // data.js が入れた記録を取り出し、埋め込み先を空にする（空の埋め込み先はサーバーの配信として起動する）
  const holder = document.getElementById("mindmap-data");
  const records = JSON.parse(holder.textContent);
  holder.textContent = "";
  /** 画面へ返す記録（edit.js が保存待ちの編集を当てた写しへ差し替える） */
  let served = records;
  /** 書き換えの知らせの受け手 */
  const listeners = [];
  // edit.js が元の記録を読み、保存待ちの編集を当てた記録を返させ、書き換えを知らせる口
  window.mockServer = {
    records,
    serve: (next) => {
      served = next;
    },
    notify: () => {
      for (const listener of listeners) listener(new Event("changed"));
    },
  };

  // ===== サーバーの配信の代わり =====
  /** JSON の応答 */
  const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  /** レビュー中のコメント（開いている間だけ持つ） */
  let review = [];
  let reviewSeq = 0;

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = new URL(String(input), location.href);
    // 配信の受け口でないものは、そのまま取りに行く
    if (!url.pathname.includes("/api/")) return realFetch(input, init);
    const path = url.pathname.replace(/^.*\/api\//, "api/");
    const method = init.method ?? "GET";
    const payload = init.body ? JSON.parse(init.body) : null;
    if (path === "api/records") return json(served);
    if (path === "api/opened") return json({ previous: null });
    if (path === "api/drafts") return new Response(null, { status: 204 });
    if (path === "api/threads") return json({ threads: [] });
    if (path === "api/comments" && method === "GET") return json({ items: review, drafts: [] });
    if (path === "api/comments" && method === "POST") {
      const item = { id: payload.id ?? `C-${(reviewSeq += 1)}`, target: payload.target ?? null, target_title: null, loc: payload.loc ?? null, thread: payload.thread ?? null, body: payload.body, created: new Date().toISOString() };
      review = [...review, item];
      return json({ id: item.id, created: item.created, count: review.length });
    }
    const commentMatch = path.match(/^api\/comments\/([^/]+)$/);
    if (commentMatch !== null) {
      const id = decodeURIComponent(commentMatch[1]);
      const found = review.find((item) => item.id === id);
      if (method === "PATCH") {
        Object.assign(found, payload);
        return json({ id, body: found.body, loc: found.loc });
      }
      review = review.filter((item) => item.id !== id);
      return json({ ...found, count: review.length });
    }
    return json({ detail: `モックに無い受け口です（${method} ${path}）` }, 404);
  };

  // 書き換えの知らせ: つないだらすぐつながった扱いにし、edit.js が記録を差し替えたら changed を送る
  window.EventSource = function MockEventSource() {
    const source = new EventTarget();
    source.close = () => {};
    const add = source.addEventListener.bind(source);
    source.addEventListener = (type, listener) => {
      add(type, listener);
      if (type === "changed") listeners.push(listener);
    };
    setTimeout(() => source.dispatchEvent(new Event("open")), 0);
    return source;
  };

  // ===== モックの操作列 =====
  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** 操作列のリンクの行き先と、開いている見本・案の印を今のクエリとハッシュから決める */
  const refreshLinks = () => {
    const hashNow = location.hash.replace(/^#/, "");
    for (const link of document.querySelectorAll(".mockbar a")) {
      // 案・画面のリンク（data-keep）は、今の見本（クエリ）のまま移る
      if (link.dataset.set === undefined) {
        if (link.dataset.keep === undefined) continue;
        link.dataset.base ??= link.getAttribute("href");
        link.href = `${link.dataset.base}${location.search}`;
        continue;
      }
      // 見本・論点の案のリンク（data-set）は、今のクエリに組み替えを重ね、ハッシュ（data-hash があればその画面）で開き直す
      const pairs = link.dataset.set.split("&").filter(Boolean).map((pair) => pair.split("="));
      const next = new URLSearchParams(location.search);
      for (const [key, value] of pairs) {
        if (value === "") next.delete(key);
        else next.set(key, value);
      }
      // 開いている見本・案を選択中にする（クエリに無いキーは画面の既定の data-* と比べる）
      const same = pairs.every(([key, value]) => (params.get(key) ?? body.dataset[key] ?? "") === value) && (link.dataset.hash ?? hashNow) === hashNow;
      if (same) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = `?${next.toString()}#${link.dataset.hash ?? hashNow}`;
    }
  };
  refreshLinks();
  addEventListener("hashchange", refreshLinks);
})();
