// モックの操作。見本の記録（data.js が埋め込み先へ入れたもの）を、サーバーの配信の代わりに返す。
// app.js の起動の前に、埋め込み先を空にしてサーバーの配信として起動させ、記録・レビュー中の書き込み・スレッドの受け口と書き換えの知らせを置き換える。
// 見本の状態はクエリで切り替える。
//   view=review: レビュー中を確かめる画面を開く / more: その書き込みの「続きを読む」を押す / edit: その書き込みの「修正」を押す
//   theme: light・dark で見た目を決めて開く / mark: 撮影用に、その CSS セレクタの要素へ赤枠を付ける
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 見た目（クエリの theme。既定はライト）と、差分を出さない状態を端末の設定へ入れる
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
  prefs.theme = params.get("theme") ?? "light";
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  // ===== 見本の記録 =====
  // data.js が入れた記録を取り出し、埋め込み先を空にする（空の埋め込み先はサーバーの配信として起動する）
  const holder = document.getElementById("mindmap-data");
  const records = JSON.parse(holder.textContent);
  holder.textContent = "";

  /** 見本の日時（UTC。画面は JST で出す） */
  const at = (hhmm) => `2026-10-12T${hhmm}:00+00:00`;

  /** 見本のスレッド（返信の向け先） */
  const threads = [
    {
      id: "TH-1", status: "open", tags: ["資料"], target: "A-14", target_title: "プレビューの差分の読み方（手引き）", loc: null, events: [],
      summary: "A-14 の手引きの書き直しの相談",
      posts: [
        { id: "TH-1-1", author: "user", body: "A-14 の手引きの表が古い。消した行と足した行が分かるように直してほしい", created: at("01:20") },
        { id: "TH-1-2", author: "ai", body: "A-14 の手引きを書き直しました。表の行の消し方は D-12 で決めたとおりにしています。", created: at("01:24") },
      ],
    },
  ];

  /** 見本のレビュー中の書き込み（thread を持つものはそのスレッドへの返信、持たないものは新しいスレッドの最初の書き込み） */
  const review = [
    // 項目を指さない・改行で 8 行（単一 UC『コメントを選んで送る』の長い書き込み）
    {
      id: "C-51", target: null, target_title: null, loc: null, thread: null, created: at("05:10"),
      body: "全体を読み返して気になった点をまとめます。\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい",
    },
    // 項目へ向けた・改行の無い長文（画面の幅で折り返して 5 行を超える）
    {
      id: "C-52", target: "A-14", target_title: null, loc: null, thread: null, created: at("05:14"),
      body: "A-14 の手引きは、差分の表示を初めて使う人が最初に読む資料なので、冒頭で「何と何を比べているのか」を一文で言い切ってから、選んだ時点の決め方、足した・変えた・消した項目の印の読み方、本文の差分の並べ方の切り替え、図の差分の見方の順に並べ直したほうが読みやすいと思います。今は印の読み方が最後にあり、表の行の消し方の説明より後に出てくるため、表を読んでいる途中で印の意味が分からずに上へ戻ることになります。D-12 で決めた表の行の消し方の説明はそのまま残してよいですが、例の表は 3 行ほどに縮めてほしいです。",
    },
    // 返信・2 行（5 行以下なので何も足さない）
    {
      id: "C-53", target: null, target_title: null, loc: null, thread: "TH-1", created: at("05:20"),
      body: "書き直しを読みました。表はこれで分かります。\n図の凡例だけ R-1 の結果に合わせてください。",
    },
    // 項目を指さない・1 行（5 行以下なので何も足さない）
    {
      id: "C-54", target: null, target_title: null, loc: null, thread: null, created: at("05:24"),
      body: "次に開くときは T-14 から読みたい",
    },
  ];
  /** レビュー中の書き込みの ID の連番 */
  let reviewSeq = 54;
  /** スレッドの ID の連番 */
  let threadSeq = threads.length;

  // ===== サーバーの配信の代わり =====
  /** JSON の応答 */
  const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  /** 今の日時（UTC） */
  const now = () => new Date().toISOString().replace(/\.\d+Z$/, "+00:00");

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
    return json({ detail: `モックに無い受け口です（${method} ${path}）` }, 404);
  };

  // 書き換えの知らせ: つないだらすぐつながった扱いにする
  window.EventSource = function MockEventSource() {
    const source = new EventTarget();
    source.close = () => {};
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

  /** 条件の要素が描かれ、出ている（hidden でない）状態になるまで待つ */
  const waitFor = (selector, callback) => {
    const timer = setInterval(() => {
      const found = document.querySelector(selector);
      if (found === null || found.hidden) return;
      clearInterval(timer);
      callback(found);
    }, 50);
  };

  // 見本: コメントの一覧を開いた状態で始め、クエリの順（レビュー中を確かめる画面 → 続きを読む → 修正）に操作する
  const steps = ["view", "more", "edit"].filter((key) => params.has(key));
  const panel = (key) => `.comments-panel [data-focus="${key}"]`;
  const selectors = {
    view: () => panel("review"),
    more: () => panel(`more:${params.get("more")}`),
    edit: () => panel(`edit-open:${params.get("edit")}`),
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
