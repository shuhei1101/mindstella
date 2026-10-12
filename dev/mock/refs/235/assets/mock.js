// モックの操作。見本の記録（data.js が埋め込み先へ入れたもの）を、サーバーの配信の代わりに返す。
// app.js の起動の前に、埋め込み先を空にしてサーバーの配信として起動させ、記録・レビュー中のコメント・スレッドの受け口と書き換えの知らせを置き換える。
// 見本の状態はクエリで切り替える（review=0: レビュー中のコメント 0 件 / threads=0: スレッド 0 件 / offline=1: 送る・書き換える要求が届かない / entered=0: Claude Code へ入力できない / tag: 会話のタブをそのタグで絞る / open: そのスレッドを開いた状態で始める / drawer=1: コメントの一覧を開いた状態で始める）
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // ===== 見本の記録 =====
  // data.js が入れた記録を取り出し、埋め込み先を空にする（空の埋め込み先はサーバーの配信として起動する）
  const holder = document.getElementById("mindmap-data");
  const records = JSON.parse(holder.textContent);
  holder.textContent = "";

  /** 見本の日時（UTC。画面は JST で出す） */
  const at = (hhmm) => `2026-10-12T${hhmm}:00+00:00`;

  /** 見本のレビュー中のコメント */
  const review = params.get("review") === "0"
    ? []
    : [
      { id: "C-41", target: "D-5", target_title: null, loc: null, body: "写しは git のコミットで取るほうが戻しやすいと思う", created: at("05:10") },
      { id: "C-42", target: null, target_title: null, loc: null, body: "移し替えの手順の名前は版の番号だけでよい？", created: at("05:12") },
    ];

  /** 見本のスレッド（書き込みは書いた順） */
  const threads = params.get("threads") === "0"
    ? []
    : [
      {
        id: "TH-1", status: "open", tags: ["画面"], target: "D-12",
        summary: "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった",
        posts: [
          { id: "TH-1-1", author: "user", body: "D-12 は案 B にしたい。失敗したら写しから戻せるなら十分", created: at("01:20") },
          { id: "TH-1-2", author: "ai", body: "D-12 を案 B（写しから戻す）で決定にしました。戻す手順を書くタスクを T-14 に足しています。", created: at("01:24") },
        ],
      },
      {
        id: "TH-2", status: "open", tags: ["起票"], target: "D-16",
        summary: "D-16 の比べた結果を Issue に起票してよいかの確認。返事待ち",
        posts: [
          { id: "TH-2-1", author: "ai", body: "D-16 の比べた結果を Issue に起票してよいですか。\n起票先は shuhei1101/mindstella、題は「版の範囲を渡して、当てる手順を返すコマンド」です。", created: at("04:02") },
        ],
      },
      {
        id: "TH-3", status: "open", tags: ["資料"], target: "A-1",
        summary: null,
        posts: [
          { id: "TH-3-1", author: "user", body: "A-1 の背景の節が長いので、3 行にまとめてほしい。経緯は会話ログへのリンクで足りる", created: at("05:01") },
        ],
      },
      {
        id: "TH-4", status: "open", tags: ["調査", "画面"], target: null,
        summary: "移し替えの手順を画面で見られるかの質問。今は見られず、T-6 の点検の結果を資料にまとめることになった",
        posts: [
          { id: "TH-4-1", author: "user", body: "移し替えの手順（版ごとの YAML）は、プレビューのどこかで見られる？", created: at("00:10") },
          { id: "TH-4-2", author: "ai", body: "今のプレビューには手順を出す画面がありません。手順の YAML はプラグインの migrations/ の下にあり、ワークスペースの記録ではないためです。", created: at("00:12") },
          { id: "TH-4-3", author: "user", body: "それなら、手順の点検（T-6）の結果だけでも資料で読めるようにしてほしい。版ごとに、どの操作を当てるかが一覧で見たい。長くなってもよいので、版・操作の種類・対象のファイル・確認の要否を並べてほしい", created: at("00:30") },
          { id: "TH-4-4", author: "ai", body: "T-6 の点検の結果を、版ごとの一覧にした資料 A-9 を足しました。操作の種類は D-15 で決めた 5 つに揃えています。確認が要る操作（消す・名前を変える）は D-6 のとおり印を付けました。", created: at("00:41") },
        ],
      },
      {
        id: "TH-5", status: "closed", tags: ["画面"], target: "D-2",
        summary: "D-2 の版の置き場所の質問。config.yaml に書くと回答",
        posts: [
          { id: "TH-5-1", author: "user", body: "版はどこに書く？", created: at("02:00") },
          { id: "TH-5-2", author: "ai", body: "D-2 で決めたとおり、ワークスペースの config.yaml の version に書きます。", created: at("02:03") },
        ],
      },
      {
        id: "TH-6", status: "closed", tags: ["起票"], target: "T-4",
        summary: "T-4 の Issue の起票の確認。起票して完了",
        posts: [
          { id: "TH-6-1", author: "ai", body: "T-4 の Issue 案を起票してよいですか。", created: at("03:00") },
          { id: "TH-6-2", author: "user", body: "起票してよい", created: at("03:05") },
          { id: "TH-6-3", author: "ai", body: "起票しました（#43）。T-4 を完了にしました。", created: at("03:07") },
        ],
      },
    ];

  // ===== サーバーの配信の代わり =====
  /** JSON の応答 */
  const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  /** 送る・書き換える要求の待ち（送っている表示を見せる） */
  const wait = () => new Promise((resolve) => setTimeout(resolve, 600));
  /** 今の日時（UTC） */
  const now = () => new Date().toISOString().replace(/\.\d+Z$/, "+00:00");
  /** 書き換えの知らせの受け手 */
  const listeners = [];
  /** 開いている画面へ書き換えを知らせる */
  const notifyChanged = () => {
    for (const listener of listeners) listener(new Event("changed"));
  };
  /** スレッドの ID の連番 */
  let threadSeq = threads.length;

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = new URL(String(input), location.href);
    const path = url.pathname.replace(/^.*\/api\//, "api/");
    // 配信の受け口でないものは、そのまま取りに行く
    if (!url.pathname.includes("/api/")) return realFetch(input, init);
    const method = init.method ?? "GET";
    const payload = init.body ? JSON.parse(init.body) : null;
    // 届かない見本: 送る・書き換える要求だけ届かない（読むのはつながっている間に読めた写し）
    if (method !== "GET" && params.get("offline") === "1" && path.startsWith("api/threads")) {
      await wait();
      throw new TypeError("Failed to fetch");
    }
    if (path === "api/records") return json(records);
    if (path === "api/opened") return json({ previous: null });
    if (path === "api/drafts") return new Response(null, { status: 204 });
    if (path === "api/comments" && method === "GET") return json({ items: review, drafts: [] });
    if (path === "api/comments" && method === "POST") {
      const item = { id: `C-${43 + review.length}`, target: payload.target ?? null, target_title: null, loc: payload.loc ?? null, body: payload.body, created: now() };
      review.push(item);
      return json({ id: item.id, created: item.created, count: review.length });
    }
    // まとめて送る: 1 件ごとに、利用者の書き込みから始まるスレッドにする
    if (path === "api/comments/send") {
      await wait();
      const sent = now();
      for (const id of payload.ids) {
        const position = review.findIndex((item) => item.id === id);
        const [item] = review.splice(position, 1);
        threadSeq += 1;
        threads.push({ id: `TH-${threadSeq}`, status: "open", tags: [], target: item.target, summary: null, posts: [{ id: `TH-${threadSeq}-1`, author: "user", body: item.body, created: sent }] });
      }
      return json({ sent, items: [], entered: params.get("entered") !== "0" });
    }
    if (path === "api/threads") return json({ threads });
    // スレッドへの返信: 利用者の書き込みを末尾に足す
    const postMatch = path.match(/^api\/threads\/([^/]+)\/posts$/);
    if (postMatch !== null) {
      await wait();
      const thread = threads.find((entry) => entry.id === decodeURIComponent(postMatch[1]));
      const post = { id: `${thread.id}-${thread.posts.length + 1}`, author: "user", body: payload.body, created: now() };
      thread.posts.push(post);
      return json({ post, entered: params.get("entered") !== "0" });
    }
    // スレッドの状態の書き換え（クローズ・オープンへの戻し）
    const threadMatch = path.match(/^api\/threads\/([^/]+)$/);
    if (threadMatch !== null && method === "PATCH") {
      await wait();
      const thread = threads.find((entry) => entry.id === decodeURIComponent(threadMatch[1]));
      thread.status = payload.status;
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

  /** 操作列のリンクの行き先と、開いている見本の印を今のクエリから決める */
  const refreshLinks = () => {
    for (const link of document.querySelectorAll(".mockbar a[data-set]")) {
      const next = new URLSearchParams();
      for (const pair of link.dataset.set.split("&").filter(Boolean)) {
        const [key, value] = pair.split("=");
        next.set(key, value);
      }
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

  // モックの操作: AI がスレッドへ返信する（TH-3 に返信して要約を書き直す）・AI がスレッドを立てる
  const actions = {
    "ai-reply": () => {
      const thread = threads.find((entry) => entry.id === "TH-3");
      thread.posts.push({ id: `TH-3-${thread.posts.length + 1}`, author: "ai", body: "A-1 の背景の節を 3 行にまとめ、経緯は会話ログ L-1 へのリンクにしました。", created: now() });
      thread.summary = "A-1 の背景の節を短くする依頼。3 行にまとめて直した";
      notifyChanged();
    },
    "ai-thread": () => {
      threadSeq += 1;
      threads.push({
        id: `TH-${threadSeq}`, status: "open", tags: ["起票"], target: "D-9",
        summary: "D-9 の開発側の点検を Issue に起票してよいかの確認。返事待ち",
        posts: [{ id: `TH-${threadSeq}-1`, author: "ai", body: "D-9 で決めた開発側の点検を Issue に起票してよいですか。", created: now() }],
      });
      notifyChanged();
    },
  };
  for (const button of document.querySelectorAll(".mockbar [data-mock-act]")) {
    button.addEventListener("click", () => actions[button.dataset.mockAct]());
  }

  // 見本: コメントの一覧を開いた状態で始める。filter があればその状態で絞り、tag があればそのタグで絞り、open があればそのスレッドを開く
  if (params.get("drawer") === "1" || params.has("open") || params.has("tag") || params.has("filter")) {
    waitFor(".comments-btn", (button) => {
      button.click();
      if (!params.has("open") && !params.has("tag") && !params.has("filter")) return;
      waitFor('.comments-panel [data-focus="tab:talk"]', (tab) => {
        tab.click();
        if (params.has("filter")) document.querySelector(`.comments-panel [data-focus="filter:${params.get("filter")}"]`).click();
        if (params.has("tag")) waitFor(`.comments-panel .th-tag[data-focus$=":${params.get("tag")}"]`, (tag) => tag.click());
        if (params.has("open")) waitFor(`.comments-panel [data-focus="thread:${params.get("open")}"]`, (row) => row.click());
      });
    });
  }
  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
