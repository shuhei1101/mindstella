// モックの操作。見本の記録（data.js が埋め込み先へ入れたもの）を、サーバーの配信の代わりに返す。
// app.js の起動の前に、埋め込み先を空にしてサーバーの配信として起動させ、記録・レビュー中の書き込み・スレッドの受け口と書き換えの知らせを置き換える。
// 見本の状態はクエリで切り替える。
//   more: その書き込みの「続きを読む」を押す / edit: その書き込みの「修正」を押す / theme: light・dark で見た目を決めて開く
//   mark: 撮影用に、その CSS セレクタの要素へ赤枠を付ける
// body の data-open が thread のときはコメントの一覧から TH-1 を開き、detail のときは data-initial の詳細パネルで操作する
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
  const at = (hhmm) => `2026-11-04T${hhmm}:00+00:00`;

  /** 頭の 1 行と番号付きの 7 行を改行でつないだ 8 行の本文（各行は画面の幅で折り返さない短さ） */
  const eightLines = (head) =>
    `${head}\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい`;

  /** 見本のスレッド（AI の返信も 8 行。送った書き込みは畳まない） */
  const threads = [
    {
      id: "TH-1", status: "open", tags: ["画面"], target: "D-1", target_title: null, loc: null, events: [],
      summary: "プレビューの見直しの相談",
      posts: [
        { id: "TH-1-1", author: "user", body: "プレビューを一通り見直したい。気になった点を挙げてほしい", created: at("01:20"), seen: true },
        { id: "TH-1-2", author: "ai", body: eightLines("見直して気になった点を挙げます。"), created: at("01:24"), seen: true },
      ],
    },
  ];

  /** 見本のレビュー中の書き込み（thread を持つものはそのスレッドへの返信、持たないものは項目へのコメント） */
  const review = [
    // TH-1 への返信・改行で 8 行
    { id: "C-61", target: null, target_title: null, loc: null, thread: "TH-1", created: at("05:10"), body: eightLines("挙げてもらった点に、優先する順を付けました。") },
    // TH-1 への返信・2 行（5 行以下なので何も足さない）
    { id: "C-62", target: null, target_title: null, loc: null, thread: "TH-1", created: at("05:14"), body: "1 と 2 は今週中に直したい。\n残りは次のスプリントでよい" },
    // D-1 へのコメント・改行で 8 行
    { id: "C-63", target: "D-1", target_title: null, loc: null, thread: null, created: at("05:20"), body: eightLines("D-1 の画面で気になった点をまとめます。") },
    // D-1 へのコメント・改行の無い長文（パネルの幅で折り返して 5 行を超える）
    {
      id: "C-64", target: "D-1", target_title: null, loc: null, thread: null, created: at("05:24"),
      body: "案 A を採るなら、作ったワークスペースを壊さずに今の形へ整える手順を先に決めておきたいです。移し替えの途中で失敗したときに、どこまで戻せば元の状態になるのか、写しをどの時点で取るのか、失敗した後に利用者へ何を見せるのかが決まっていないと、案 A の良さである既存のワークスペースを残せる点が活きません。案 B と比べるときも、この手順の重さを含めて比べてください。また、移し替えの手順を書く場所も決めておきたいです。今は資料と検討事項の両方に少しずつ書かれていて、どちらが正しいのかが読み手には分かりません。手順は資料に 1 か所だけ書き、検討事項からはその資料を指すようにしてください。手順の中で使う言葉も、ワークスペースの書式のページの呼び名に揃えてほしいです。",
    },
    // D-1 へのコメント・1 行（5 行以下なので何も足さない）
    { id: "C-65", target: "D-1", target_title: null, loc: null, thread: null, created: at("05:30"), body: "案 B も見たい" },
  ];
  /** レビュー中の書き込みの ID の連番 */
  let reviewSeq = 65;

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
    if (path === "api/threads") return json({ threads });
    if (/^api\/threads\/[^/]+\/seen$/.test(path)) return json({ seen: 0 });
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

  // 見本: クエリの順（続きを読む → 修正）に押す。詳細パネルの「修正」は接頭辞 detail- を付けた data-focus を持つ
  const thread = body.dataset.open === "thread";
  const scope = thread ? ".comments-panel" : ".panel";
  const selectors = {
    more: () => `${scope} [data-focus="more:${params.get("more")}"]`,
    edit: () => `${scope} [data-focus="${thread ? "" : "detail-"}edit-open:${params.get("edit")}"]`,
  };
  const steps = ["more", "edit"].filter((key) => params.has(key));
  /** 見本の欄（スレッドは最初のレビュー中の返信、詳細パネルはレビュー中のコメントの節）を見える位置へ送る */
  const reveal = () => waitFor(thread ? '.comments-panel [data-comment="C-61"]' : ".panel .d-review", (target) => target.scrollIntoView({ block: "start" }));
  /** 残りの操作を、描かれるのを待ちながら順に押し、押し終えたら見本の欄を見える位置へ送る */
  const run = (rest) => {
    if (rest.length === 0) {
      reveal();
      return;
    }
    waitFor(selectors[rest[0]](), (target) => {
      target.click();
      run(rest.slice(1));
    });
  };
  if (thread) {
    // コメントの一覧を開き、TH-1 のスレッドを開いてから操作する
    waitFor(".comments-btn", (button) => {
      button.click();
      waitFor('.comments-panel [data-focus="thread:TH-1"]', (row) => {
        row.click();
        run(steps);
      });
    });
  } else {
    waitFor(".panel .d-review", () => run(steps));
  }

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
