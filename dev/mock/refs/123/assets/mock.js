// モックの操作。app.js の起動の前に、ハッシュからモック専用の値を読んで見本の状態（ロック・鍵とコメントの印の順・コメントの件数・見た目・ライト / ダーク）を作り、
// 描いた後にモック専用の操作列を一番上へ戻す。操作列の切り替えは、状態をハッシュに持たせてページを読み込み直す
(() => {
  const body = document.body;
  const PREFS_KEY = "mindmap-preview";       // app.js が個人の上書きを置く保存領域のキー
  const HOST = "D-10";                       // 鍵を置く見本の項目（前提 D-8・後続 D-13 ほか・成果物 A-1 とつながる）
  const OTHER = "D-13";                      // ロック中に開く、ほかの項目
  const SHAKE_REPEAT_MS = 1800;              // 鍵の震えの見本で、震えを繰り返す間隔
  const DEMOS = [["", "なし"], ["open", "開いた鍵"], ["locked", "閉じた鍵"], ["other", "ほかを開く"], ["shake", "鍵の震え"]];
  const ORDERS = [["A", "A 名前・鍵・コメント"], ["B", "B 名前・コメント・鍵"]];
  const COMMENTS = [["1", "あり"], ["0", "なし"]];
  const LOOKS = ["glow", "starlight", "constellation", "deep", "dust"];

  // ===== ハッシュからモック専用の値を読み、app.js が読むハッシュからは外す =====
  const params = new URLSearchParams(location.hash.replace(/^#/, "") || body.dataset.initial || "");
  const take = (key) => { const value = params.get(key); params.delete(key); return value; };
  const state = {
    demo: DEMOS.some(([value]) => value !== "" && value === params.get("demo")) ? params.get("demo") : "",
    order: params.get("order") === "B" ? "B" : "A",
    cm: params.get("cm") === "0" ? "0" : "1",
  };
  for (const key of ["demo", "order", "cm"]) params.delete(key);
  const look = take("look");
  const theme = take("theme");
  const tab = params.get("tab") ?? "overview";
  const lockKey = tab === "graph" ? "graph" : tab === "decisions" ? "map" : null;

  // 見た目とライト / ダークは、app.js と同じ個人の上書きへ先に書いておく
  if (LOOKS.includes(look) || ["light", "dark"].includes(theme)) {
    let prefs = {};
    try { prefs = JSON.parse(localStorage.getItem(PREFS_KEY)) ?? {}; } catch { /* 読めない保存領域では、今の値を足さずに書く */ }
    if (LOOKS.includes(look)) prefs.look = look;
    if (["light", "dark"].includes(theme)) prefs.theme = theme;
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* 保存できない環境では、既定の見た目で開く */ }
  }

  // ロックの見本: 詳細を開く項目と、ロックした項目を置く
  if (state.demo !== "" && lockKey !== null) {
    params.set("id", state.demo === "other" || state.demo === "shake" ? OTHER : HOST);
    // マップは既定で決定済みを出さないため、見本の項目（決定済み）が出る条件で開く
    if (lockKey === "map") params.set("f.status", "決定済み");
  }
  // コメントの印の見本の件数（鍵を置く項目は「あり / なし」で切り替える）
  const comments = { "D-8": 1, "D-13": 3, "D-14": 12, "D-15": 2, "D-11": 1, "A-1": 4, "D-1": 2, "T-1": 1 };
  if (state.cm === "1") comments[HOST] = 2;
  window.MOCK123 = {
    order: state.order,
    demo: state.demo,
    comments,
    lock: { [lockKey ?? "graph"]: state.demo === "" || state.demo === "open" ? null : HOST },
  };
  history.replaceState(null, "", `#${params.toString()}`);

  // ===== モック専用の操作列 =====
  /** 今の画面とモックの状態を持たせたハッシュ */
  const hashWith = (changes) => {
    const next = new URLSearchParams({ tab: new URLSearchParams(location.hash.replace(/^#/, "")).get("tab") ?? tab });
    if (tab === "decisions") next.set("view", "map");
    for (const [key, value] of Object.entries({ ...state, ...changes })) if (value !== "" && !(key === "order" && value === "A") && !(key === "cm" && value === "1")) next.set(key, value);
    return `#${next.toString()}`;
  };
  /** 1 つのまとまり（見出しと、状態ごとのボタン） */
  const group = (label, key, choices) => {
    const wrap = document.createElement("span");
    wrap.className = "mock-group";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", label);
    const head = document.createElement("span");
    head.className = "mock-label";
    head.textContent = label;
    wrap.append(head);
    for (const [value, text] of choices) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = text;
      button.setAttribute("aria-pressed", String(state[key] === value));
      // 状態をハッシュに持たせて読み込み直す（見本の状態は起動の前に作るため）
      button.addEventListener("click", () => { location.hash = hashWith({ [key]: value }); location.reload(); });
      wrap.append(button);
    }
    return wrap;
  };
  const states = document.getElementById("mock-states");
  if (states !== null && lockKey !== null) {
    states.append(group("ロック", "demo", DEMOS));
    states.append(group("鍵の項目のコメント", "cm", COMMENTS));
    // 鍵とコメントの印の順は、名前の右に並べるネットワークだけの論点
    if (lockKey === "graph") states.append(group("鍵とコメントの印の順", "order", ORDERS));
  }

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** トップバーが描かれるまで待ってから、見本の状態を作る */
  const whenDrawn = (callback) => {
    const timer = setInterval(() => {
      if (document.querySelector("#top .topbar") === null) return;
      clearInterval(timer);
      callback();
    }, 50);
  };
  whenDrawn(() => {
    // 表示の設定のパネルを開いた見本
    if (body.dataset.open === "settings") document.querySelector("[data-act='settings']")?.click();
    // マップの鍵の震えの見本: 押さなくても一定の間隔で震えを繰り返す（ネットワークは app.js が毎コマ見る）
    if (state.demo === "shake" && lockKey === "map") {
      setInterval(() => window.MindmapPreview.shakeKeyElement(() => document.querySelector("#decision-map .n-item.locked .lk")), SHAKE_REPEAT_MS);
    }
  });
})();
