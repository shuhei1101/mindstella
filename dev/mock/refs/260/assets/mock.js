// モックの操作。見本の記録（data.js が埋め込み先へ入れたもの）を、サーバーの配信の代わりに返す。
// app.js の起動の前に、埋め込み先を空にしてサーバーの配信として起動させ、記録・レビュー中の書き込み・スレッドの受け口と書き換えの知らせを置き換える。
// 見本の状態はクエリで切り替える。
//   open: そのスレッドを開く / view=review: レビュー中を確かめる画面を開く / theme: light・dark で見た目を決めて開く
//   mark: 撮影用に、その CSS セレクタの要素へ赤枠を付ける
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 見た目（クエリの theme）と、差分を出さない状態を端末の設定へ入れる
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
  if (params.has("theme")) prefs.theme = params.get("theme");
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  // ===== 見本の記録 =====
  // data.js が入れた記録を取り出し、埋め込み先を空にする（空の埋め込み先はサーバーの配信として起動する）
  const holder = document.getElementById("mindmap-data");
  const records = JSON.parse(holder.textContent);
  holder.textContent = "";

  /** 見本の日時（UTC。画面は JST で出す） */
  const at = (hhmm) => `2026-10-12T${hhmm}:00+00:00`;

  /** 見本のスレッド（書き込みは書いた順）。V-2・V-5・V-6 は記録にあるまとまり、V-99 は記録に無いまとまり */
  const threads = [
    // 1 つの書き込みに、まとまりのリンク（文言に項目の ID を含む）・項目の ID のボタン・まとまりのリンクにならない書き方が並ぶ
    {
      id: "TH-1", status: "open", tags: ["資料"], target: "A-14", target_title: "プレビューの差分の読み方（手引き）", loc: null, events: [],
      summary: "A-14 の手引きの書き直しの相談。直したまとまりを示した",
      posts: [
        { id: "TH-1-1", author: "user", body: "A-14 の手引きの表が古い。消した行と足した行が分かるように直してほしい", created: at("01:20") },
        { id: "TH-1-2", author: "ai", body: "A-14 の手引きを書き直しました。直したところは [A-14 の手引きの書き直し](#diff=V-6) で見られます。\n表の行の消し方は D-12 で決めたとおりにしています。\n前に相談した版は [古い手引き](#diff=V-99) にありましたが、保持する回数を超えて消えています。", created: at("01:24") },
        { id: "TH-1-3", author: "user", body: "[A-14 の手引きの書き直し](#diff=V-6) を見た。図の凡例は R-1 の結果に合わせたい。\n[since から](#diff=since) と [ハッシュの例](#tab=docs) は押せなくてよい", created: at("01:31") },
      ],
    },
    // 文言が長いまとまりのリンクと、ほかの引数を持つ `#` のリンク
    {
      id: "TH-2", status: "open", tags: ["画面"], target: "A-11", target_title: "設定のパネルの画面の流れ（モック）", loc: null, events: [],
      summary: "A-11 の画面の流れのモックの直しの確認。返事待ち",
      posts: [
        { id: "TH-2-1", author: "ai", body: "A-11 の段落を [設定のパネルの画面の流れのうち、既定として保存するまでの段落と確かめのダイアログの説明](#tab=docs&id=A-11&diff=V-5) のとおりに直しました。\nR-1 の調べの直しは [重複と不要な調査の片付け](#diff=V-2) です。この直し方でよいですか。", created: at("04:02") },
      ],
    },
  ];

  /** 見本のレビュー中の書き込み（thread を持つものはそのスレッドへの返信、持たないものは新しいスレッドの最初の書き込み） */
  const review = [
    { id: "C-41", target: null, target_title: null, loc: null, thread: "TH-1", body: "[A-14 の手引きの書き直し](#diff=V-6) で消した表の行は戻してほしい。T-14 にも関わる。\n[古い手引き](#diff=V-99) は要らない", created: at("05:10") },
    { id: "C-42", target: "A-11", target_title: null, loc: null, thread: null, body: "[A-11 の段落の直し](#diff=V-5) の 2 段落目が長い", created: at("05:12") },
  ];
  /** レビュー中の書き込みの ID の連番 */
  let reviewSeq = 42;
  /** スレッドの ID の連番 */
  let threadSeq = threads.length;

  // ===== サーバーの配信の代わり =====
  /** JSON の応答 */
  const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  /** 今の日時（UTC） */
  const now = () => new Date().toISOString().replace(/\.\d+Z$/, "+00:00");
  /** 書き換えの知らせの受け手 */
  const listeners = [];
  /** 開いている画面へ書き換えを知らせる */
  const notifyChanged = () => {
    for (const listener of listeners) listener(new Event("changed"));
  };

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = new URL(String(input), location.href);
    // 配信の受け口でないものは、そのまま取りに行く
    if (!url.pathname.includes("/api/")) return realFetch(input, init);
    const path = url.pathname.replace(/^.*\/api\//, "api/");
    const method = init.method ?? "GET";
    const payload = init.body ? JSON.parse(init.body) : null;
    if (path === "api/records") return json(records);
    if (path === "api/opened") return json({ previous: null });
    if (path === "api/drafts") return new Response(null, { status: 204 });
    if (path === "api/comments" && method === "GET") return json({ items: review, drafts: [] });
    // レビュー中の書き込みを足す（id を持つ要求は、消した書き込みを同じ ID で戻す）
    if (path === "api/comments" && method === "POST") {
      const item = { id: payload.id ?? `C-${(reviewSeq += 1)}`, target: payload.target ?? null, target_title: null, loc: payload.loc ?? null, thread: payload.thread ?? null, body: payload.body, created: payload.created ?? now() };
      review.push(item);
      return json({ id: item.id, created: item.created, count: review.length });
    }
    // レビュー中の書き込みを書き換える・消す
    const commentMatch = path.match(/^api\/comments\/([^/]+)$/);
    if (commentMatch !== null && commentMatch[1] !== "send") {
      const position = review.findIndex((item) => item.id === decodeURIComponent(commentMatch[1]));
      if (method === "PATCH") {
        Object.assign(review[position], payload);
        return json({ id: review[position].id, body: review[position].body, loc: review[position].loc });
      }
      const [removed] = review.splice(position, 1);
      return json({ ...removed, count: review.length });
    }
    // まとめて送る: 返信は向けたスレッドの末尾に足し、新しいスレッドは 1 件ごとにオープンのスレッドにする
    if (path === "api/comments/send") {
      const sent = now();
      for (const id of payload.ids) {
        const [item] = review.splice(review.findIndex((entry) => entry.id === id), 1);
        if (item.thread !== null) {
          const thread = threads.find((entry) => entry.id === item.thread);
          thread.posts.push({ id: `${thread.id}-${thread.posts.length + 1}`, author: "user", body: item.body, created: sent });
          continue;
        }
        threadSeq += 1;
        threads.push({ id: `TH-${threadSeq}`, status: "open", tags: [], target: item.target, target_title: null, loc: null, summary: null, events: [], posts: [{ id: `TH-${threadSeq}-1`, author: "user", body: item.body, created: sent }] });
      }
      return json({ sent, items: [], entered: true });
    }
    if (path === "api/threads") return json({ threads });
    // スレッドの状態の書き換え（クローズ・オープンへの戻し）
    const threadMatch = path.match(/^api\/threads\/([^/]+)$/);
    if (threadMatch !== null && method === "PATCH") {
      const thread = threads.find((entry) => entry.id === decodeURIComponent(threadMatch[1]));
      thread.status = payload.status;
      thread.events.push({ kind: payload.status === "closed" ? "closed" : "reopened", author: "user", reason: payload.reason ?? null, created: now() });
      return json({ id: thread.id, status: thread.status });
    }
    return json({ detail: `モックに無い受け口です（${method} ${path}）` }, 404);
  };

  // 書き換えの知らせ: つないだらすぐつながった扱いにし、モックの操作で changed を送る
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

  /** 操作列の見本のリンクの行き先と、開いている見本の印を今のクエリから決める。案のリンク（data-keep）は今の見本のまま移る */
  const refreshLinks = () => {
    for (const link of document.querySelectorAll(".mockbar a[data-keep]")) {
      link.href = `${link.getAttribute("href").split("?")[0]}${location.search}`;
    }
    for (const link of document.querySelectorAll(".mockbar a[data-set]")) {
      const next = new URLSearchParams(link.dataset.set);
      // 開いている見本を選択中にする
      if (next.toString() === params.toString()) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = `?${next.toString()}`;
    }
  };
  refreshLinks();

  /** 条件の要素が描かれるまで待つ */
  const waitFor = (selector, callback) => {
    const timer = setInterval(() => {
      const found = document.querySelector(selector);
      if (found === null) return;
      clearInterval(timer);
      callback(found);
    }, 50);
  };

  // モックの操作: AI がスレッドを立て、最初の書き込みに直したまとまりのリンクを書く
  const actions = {
    "ai-thread": () => {
      threadSeq += 1;
      threads.push({
        id: `TH-${threadSeq}`, status: "open", tags: ["資料"], target: "A-16", target_title: "差分の表示の文言の点検（変わった箇所が多い資料）", loc: null, events: [],
        summary: "A-16 の文言の点検の結果の確認。返事待ち",
        posts: [{ id: `TH-${threadSeq}-1`, author: "ai", body: "A-16 の文言を点検し、[A-16 の 30 か所の直し](#diff=V-6) のとおりに直しました。T-6 の点検と同じ基準です。", created: now() }],
      });
      notifyChanged();
    },
  };
  for (const button of document.querySelectorAll(".mockbar [data-mock-act]")) {
    button.addEventListener("click", () => actions[button.dataset.mockAct]());
  }

  // 見本: コメントの一覧を開いた状態で始め、クエリの順（スレッド → レビュー中を確かめる画面）に操作する
  const steps = ["open", "view"].filter((key) => params.has(key));
  const panel = (key) => `.comments-panel [data-focus="${key}"]`;
  const selectors = {
    open: () => panel(`thread:${params.get("open")}`),
    view: () => panel("review"),
  };
  /** 残りの操作を、描かれるのを待ちながら順に押す */
  const run = (rest) => {
    if (rest.length === 0) return;
    waitFor(selectors[rest[0]](), (target) => {
      target.click();
      run(rest.slice(1));
    });
  };
  waitFor(".comments-btn", (button) => {
    button.click();
    run(steps);
  });

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
