// モックの操作。見本の記録（data.js が埋め込み先へ入れたもの）を、サーバーの配信の代わりに返す。
// app.js の起動の前に、埋め込み先を空にしてサーバーの配信として起動させ、記録・レビュー中の書き込み・スレッドの受け口と書き換えの知らせを置き換える。
// 見本の状態はクエリで切り替える。
//   review=0: レビュー中の書き込み 0 件 / threads=0: スレッド 0 件 / blocked=1: クローズのスレッドへの返信をレビュー中に持つ
//   offline=1: 溜める・送る・書き換える要求が届かない / entered=0: Claude Code へ入力できない
//   filter: スレッドの一覧をその状態で絞る / tag: そのタグで絞る / open: そのスレッドを開く / view=review: レビュー中を確かめる画面を開く / compose=1: 新しいスレッドの入力を開く
//   drawer=1: コメントの一覧を開いた状態で始める
//   unread: 利用者の未読の書き込みの見本（無し: TH-2・TH-4・TH-6 が未読 / 0: 未読なし / closed: クローズの TH-6 だけが未読）
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

  /** 見本のスレッド（書き込みは書いた順。events はクローズ・オープンへの戻しの記録で、author は状態を変えた書き手） */
  const threads = params.get("threads") === "0"
    ? []
    : [
      {
        id: "TH-1", status: "open", tags: ["画面"], target: "D-12", events: [],
        summary: "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった",
        posts: [
          { id: "TH-1-1", author: "user", body: "D-12 は案 B にしたい。失敗したら写しから戻せるなら十分", created: at("01:20") },
          { id: "TH-1-2", author: "ai", body: "D-12 を案 B（写しから戻す）で決定にしました。戻す手順を書くタスクを T-14 に足しています。", created: at("01:24") },
        ],
      },
      {
        id: "TH-2", status: "open", tags: ["起票"], target: "D-16", events: [],
        summary: "D-16 の比べた結果を Issue に起票してよいかの確認。返事待ち",
        posts: [
          { id: "TH-2-1", author: "ai", body: "D-16 の比べた結果を Issue に起票してよいですか。\n起票先は shuhei1101/mindstella、題は「版の範囲を渡して、当てる手順を返すコマンド」です。", created: at("04:02") },
        ],
      },
      {
        id: "TH-3", status: "open", tags: ["資料"], target: "A-1", events: [],
        summary: null,
        posts: [
          { id: "TH-3-1", author: "user", body: "A-1 の背景の節が長いので、3 行にまとめてほしい。経緯は会話ログへのリンクで足りる", created: at("05:01") },
        ],
      },
      {
        id: "TH-4", status: "open", tags: ["調査", "画面"], target: null,
        events: [
          { kind: "closed", author: "user", reason: "手順は画面に出さないと分かった", created: at("00:20") },
          { kind: "reopened", author: "user", reason: null, created: at("00:29") },
        ],
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
        events: [{ kind: "closed", author: "user", reason: "config.yaml に書くと分かった", created: at("02:10") }],
        summary: "D-2 の版の置き場所の質問。config.yaml に書くと回答",
        posts: [
          { id: "TH-5-1", author: "user", body: "版はどこに書く？", created: at("02:00") },
          { id: "TH-5-2", author: "ai", body: "D-2 で決めたとおり、ワークスペースの config.yaml の version に書きます。", created: at("02:03") },
        ],
      },
      {
        id: "TH-6", status: "closed", tags: ["起票"], target: "T-4",
        events: [{ kind: "closed", author: "user", reason: null, created: at("03:09") }],
        summary: "T-4 の Issue の起票の確認。起票して完了",
        posts: [
          { id: "TH-6-1", author: "ai", body: "T-4 の Issue 案を起票してよいですか。", created: at("03:00") },
          { id: "TH-6-2", author: "user", body: "起票してよい", created: at("03:05") },
          { id: "TH-6-3", author: "ai", body: "起票しました（#43）。T-4 を完了にしました。", created: at("03:07") },
        ],
      },
      // 利用者の「了解」で終わるオープンのスレッド（操作「AI がクローズにする」で、AI が返信せずに理由つきでクローズにする）
      {
        id: "TH-7", status: "open", tags: ["画面"], target: "D-6", events: [],
        summary: "D-6 の確認を出す操作の質問。消す・名前を変えるの 2 つと回答",
        posts: [
          { id: "TH-7-1", author: "user", body: "D-6 の確認は、どの操作で出る？", created: at("04:30") },
          { id: "TH-7-2", author: "ai", body: "D-6 で決めたとおり、消す・名前を変えるの 2 つで出ます。", created: at("04:32") },
          { id: "TH-7-3", author: "user", body: "了解", created: at("04:35") },
        ],
      },
      // AI が返信せずにクローズにしたスレッド（返事の要らない書き込み）
      {
        id: "TH-8", status: "closed", tags: ["調査"], target: "D-15",
        events: [{ kind: "closed", author: "ai", reason: "返事の要らない書き込みで、D-15 は今のままにする", created: at("03:33") }],
        summary: "D-15 の操作の種類は今の 5 つのままにする",
        posts: [
          { id: "TH-8-1", author: "user", body: "D-15 の操作の種類は今の 5 つのままでよい。足さない", created: at("03:30") },
        ],
      },
      // 利用者が質問を送ってからクローズにしたスレッド（操作「AI がオープンに戻して返信する」で、AI が理由つきでオープンに戻して返信する）
      {
        id: "TH-9", status: "closed", tags: ["資料"], target: "A-9",
        events: [{ kind: "closed", author: "user", reason: null, created: at("02:42") }],
        summary: null,
        posts: [
          { id: "TH-9-1", author: "user", body: "A-9 の一覧に、確認の要否の列はある？", created: at("02:40") },
        ],
      },
    ];

  /** 利用者の未読にする書き込み（AI が立てた TH-2・オープンの TH-4 の最後の返信・クローズの TH-6 の最後の返信） */
  const unreadPosts = {
    "0": [],
    closed: ["TH-6-3"],
  }[params.get("unread") ?? ""] ?? ["TH-2-1", "TH-4-4", "TH-6-3"];
  // 書き込みに利用者の既読を持たせる（キーの名前は ER 図の更新で決める。モックの仮の名前 seen）
  for (const thread of threads) {
    for (const post of thread.posts) post.seen = !unreadPosts.includes(post.id);
  }

  /** 見本のレビュー中の書き込み（thread を持つものはそのスレッドへの返信、持たないものは新しいスレッドの最初の書き込み） */
  const review = params.get("review") === "0" || threads.length === 0
    ? []
    : [
      { id: "C-41", target: "D-5", target_title: null, loc: null, thread: null, body: "写しは git のコミットで取るほうが戻しやすいと思う", created: at("05:10") },
      { id: "C-42", target: null, target_title: null, loc: null, thread: null, body: "移し替えの手順の名前は版の番号だけでよい？", created: at("05:12") },
      { id: "C-43", target: null, target_title: null, loc: null, thread: "TH-1", body: "了解。T-14 は今週中に書いてほしい", created: at("05:14") },
      ...(params.get("blocked") === "1" ? [{ id: "C-44", target: null, target_title: null, loc: null, thread: "TH-5", body: "version は文字列で持つ？", created: at("05:16") }] : []),
    ];
  /** レビュー中の書き込みの ID の連番 */
  let reviewSeq = 44;

  /** 返信の書きかけ（スレッドの ID → 本文）。サーバーの drafts.yaml の代わりに、読み込み直しても残るようタブの間だけ保つ */
  const threadDrafts = (() => {
    try {
      return new Map(JSON.parse(sessionStorage.getItem("mock-258-drafts") ?? "[]"));
    } catch {
      return new Map();
    }
  })();
  /** 返信の書きかけを保つ */
  const keepDrafts = () => {
    try {
      sessionStorage.setItem("mock-258-drafts", JSON.stringify([...threadDrafts]));
    } catch {
      // 保てない端末では、開いている間だけ残る
    }
  };

  // ===== サーバーの配信の代わり =====
  /** JSON の応答 */
  const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  /** 溜める・送る・書き換える要求の待ち（送っている表示を見せる） */
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
    // 届かない見本: 溜める・送る・状態を書き換える要求が届かない（読むのはつながっている間に読めた写し）
    const writes = path === "api/comments" || path === "api/comments/send" || path.startsWith("api/threads");
    if (method !== "GET" && params.get("offline") === "1" && writes) {
      await wait();
      throw new TypeError("Failed to fetch");
    }
    if (path === "api/records") return json(records);
    if (path === "api/opened") return json({ previous: null });
    // 書きかけの保存: スレッドへの返信の書きかけはスレッドごとに保つ（空なら消す）
    if (path === "api/drafts") {
      if (payload?.thread !== undefined) {
        if (payload.body === "") threadDrafts.delete(payload.thread);
        else threadDrafts.set(payload.thread, payload.body);
        keepDrafts();
      }
      return new Response(null, { status: 204 });
    }
    if (path === "api/comments" && method === "GET") return json({ items: review, drafts: [...threadDrafts].map(([thread, text]) => ({ thread, body: text })) });
    // レビュー中の書き込みを足す（id を持つ要求は、消した書き込みを同じ ID で戻す）
    if (path === "api/comments" && method === "POST") {
      await wait();
      const item = {
        id: payload.id ?? `C-${(reviewSeq += 1)}`,
        target: payload.target ?? null,
        target_title: null,
        loc: payload.loc ?? null,
        thread: payload.thread ?? null,
        body: payload.body,
        created: payload.created ?? now(),
      };
      review.push(item);
      review.sort((a, b) => Number(a.id.slice(2)) - Number(b.id.slice(2)));
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
      await wait();
      const sent = now();
      for (const id of payload.ids) {
        const position = review.findIndex((item) => item.id === id);
        const [item] = review.splice(position, 1);
        if (item.thread !== null) {
          const thread = threads.find((entry) => entry.id === item.thread);
          thread.posts.push({ id: `${thread.id}-${thread.posts.length + 1}`, author: "user", body: item.body, created: sent, seen: true });
          continue;
        }
        threadSeq += 1;
        threads.push({ id: `TH-${threadSeq}`, status: "open", tags: [], target: item.target, summary: null, events: [], posts: [{ id: `TH-${threadSeq}-1`, author: "user", body: item.body, created: sent, seen: true }] });
      }
      return json({ sent, items: [], entered: params.get("entered") !== "0" });
    }
    if (path === "api/threads") return json({ threads });
    // 既読にする: スレッド 1 件の利用者の未読の書き込みを全て既読にし、書いたら書き換えの知らせを送る（未読が無ければ書かずに返す）
    const seenMatch = path.match(/^api\/threads\/([^/]+)\/seen$/);
    if (seenMatch !== null && method === "POST") {
      const thread = threads.find((entry) => entry.id === decodeURIComponent(seenMatch[1]));
      const unread = thread.posts.filter((post) => !post.seen);
      for (const post of unread) post.seen = true;
      if (unread.length > 0) setTimeout(notifyChanged, 0);
      return json({ id: thread.id, changed: unread.length > 0 });
    }
    // スレッドの状態の書き換え（クローズ・オープンへの戻し。書き手・任意の理由・日時を記録に残す）
    const threadMatch = path.match(/^api\/threads\/([^/]+)$/);
    if (threadMatch !== null && method === "PATCH") {
      await wait();
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

  /** 操作列の見本のリンクの行き先と、開いている見本の印を今のクエリから決める。案のリンクは今の見本のまま移る */
  const refreshLinks = () => {
    for (const link of document.querySelectorAll(".mockbar a[data-keep]")) {
      link.href = `${link.getAttribute("href").split("?")[0]}${location.search}`;
    }
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

  // モックの操作: AI がスレッドへ返信する（TH-3 に返信して要約を書き直す）・AI がスレッドを立てる・AI がクローズにする（TH-7）・AI がオープンに戻して返信する（TH-9）
  const actions = {
    "ai-reply": () => {
      const thread = threads.find((entry) => entry.id === "TH-3");
      thread.posts.push({ id: `TH-3-${thread.posts.length + 1}`, author: "ai", body: "A-1 の背景の節を 3 行にまとめ、経緯は会話ログ L-1 へのリンクにしました。", created: now(), seen: false });
      thread.summary = "A-1 の背景の節を短くする依頼。3 行にまとめて直した";
      notifyChanged();
    },
    "ai-thread": () => {
      threadSeq += 1;
      threads.push({
        id: `TH-${threadSeq}`, status: "open", tags: ["起票"], target: "D-9", events: [],
        summary: "D-9 の開発側の点検を Issue に起票してよいかの確認。返事待ち",
        posts: [{ id: `TH-${threadSeq}-1`, author: "ai", body: "D-9 で決めた開発側の点検を Issue に起票してよいですか。", created: now(), seen: false }],
      });
      notifyChanged();
    },
    // AI が、利用者の「了解」を読んで、返信せずに理由つきでクローズにする
    "ai-close": () => {
      const thread = threads.find((entry) => entry.id === "TH-7");
      if (thread.status === "closed") return;
      thread.status = "closed";
      thread.events.push({ kind: "closed", author: "ai", reason: "了解を受けた", created: now() });
      thread.summary = "D-6 の確認を出す操作の質問。消す・名前を変えるの 2 つと回答し、了解を受けた";
      notifyChanged();
    },
    // AI が、利用者がクローズにしたスレッドの質問に、理由つきでオープンに戻してから返信する
    "ai-reopen": () => {
      const thread = threads.find((entry) => entry.id === "TH-9");
      if (thread.status === "open") return;
      const reopened = new Date();
      thread.status = "open";
      thread.events.push({ kind: "reopened", author: "ai", reason: "質問に答えるため", created: reopened.toISOString().replace(/\.\d+Z$/, "+00:00") });
      // 返信は、オープンに戻した記録の後ろに並ぶ日時にする
      thread.posts.push({ id: `TH-9-${thread.posts.length + 1}`, author: "ai", body: "A-9 の一覧の右端に、確認の要否の列があります。確認が要るのは D-6 で決めた 2 つの操作です。", created: new Date(reopened.getTime() + 1000).toISOString().replace(/\.\d+Z$/, "+00:00"), seen: false });
      thread.summary = "A-9 の一覧に確認の要否の列があるかの質問。あると回答";
      notifyChanged();
    },
  };
  for (const button of document.querySelectorAll(".mockbar [data-mock-act]")) {
    button.addEventListener("click", () => actions[button.dataset.mockAct]());
  }

  // 見本: コメントの一覧を開いた状態で始め、クエリの順（絞り込み → タグ → 新しいスレッドの入力 → スレッド → レビュー中を確かめる画面）に操作する
  const steps = ["filter", "tag", "compose", "open", "view"].filter((key) => params.has(key));
  if (params.get("drawer") === "1" || steps.length > 0) {
    const panel = (key) => `.comments-panel [data-focus="${key}"]`;
    const selectors = {
      filter: () => panel(`filter:${params.get("filter")}`),
      tag: () => `.comments-panel .th-tag[data-focus$=":${params.get("tag")}"]`,
      compose: () => panel("compose"),
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
  }
  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
