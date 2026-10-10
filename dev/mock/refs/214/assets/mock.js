// モックの操作。app.js の起動の前に、選んだ時点・「前回開いてから」の始まりを整え、描いた後にモック専用の操作列を一番上へ戻す。
// 案（カードの形式のバッジの置き場所 `data-badge`・HTML の本文の差分の見せ方 `data-htmldiff`）は、案の index.html の body が持つ
(() => {
  const body = document.body;
  const query = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 「前回開いてから」の始まり: V-2 と V-3 の間（10/07 09:00 JST）に固定する（同じタブの読み込み直しでも変えない）
  try {
    sessionStorage.setItem("mindmap-since", "2026-10-07T00:00:00+00:00");
  } catch {
    // 残せない環境では、app.js が開いた日時から決める
  }

  // 選んだ時点: クエリの `diff`（`none` は差分を出さない）か、画面の見本の時点（`data-diff`）を端末の設定へ入れる
  const diff = query.get("diff") ?? body.dataset.diff ?? "none";
  try {
    const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
    prefs.diffSel = diff === "none" ? null : diff;
    localStorage.setItem("mindmap-preview", JSON.stringify(prefs));
  } catch {
    // 残せない環境では、差分を出さずに開く
  }

  /** `data-set` のキーの今の値 */
  const currentOf = (key) => {
    if (key === "diff") return diff;
    if (key === "q") return query.get("q") ?? body.dataset.query;
    return query.get(key);
  };

  /** モック専用の操作列のリンク: 今のクエリに `data-set` の値を重ね、ハッシュを保って開き直す。今の値のリンクに aria-current を付ける */
  for (const link of document.querySelectorAll(".mockbar a[data-set]")) {
    const [key, value] = link.dataset.set.split("=");
    const next = new URLSearchParams(location.search);
    next.set(key, value);
    link.href = `?${next.toString()}${location.hash}`;
    if (currentOf(key) === value) link.setAttribute("aria-current", "true");
    // 開き直すときは、今のハッシュ（開いている画面・項目）を引き継ぐ
    link.addEventListener("click", (event) => {
      event.preventDefault();
      location.href = `?${next.toString()}${location.hash}`;
    });
  }
  // 同じ階層の案のタブ: クエリとハッシュを引き継ぐ
  for (const link of document.querySelectorAll(".mockbar a[data-case]")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      location.href = `${link.getAttribute("href")}${location.search}${location.hash}`;
    });
  }

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  // 本文のスクリプトが動いた印: A-12 の本文は、動けば body の data-ran に印を残す。その有無を操作列に写す
  const ran = document.querySelector(".mockbar [data-ran]");
  if (ran !== null) {
    const show = () => {
      ran.textContent = body.dataset.ran === undefined ? "動いていない" : `動いた（${body.dataset.ran}）`;
    };
    show();
    new MutationObserver(show).observe(body, { attributes: true, attributeFilter: ["data-ran"] });
  }

  /** 画面の土台が描かれるまで待ってから、見本の状態を作る */
  const whenDrawn = (callback) => {
    const timer = setInterval(() => {
      if (document.querySelector("#top .topbar") === null) return;
      clearInterval(timer);
      callback();
    }, 50);
  };

  whenDrawn(() => {
    // 全体の検索に言葉を入れた見本（クエリの `q`、無ければ画面の見本の `data-query`）
    if (body.dataset.open === "search") {
      document.querySelector("[data-act='search']")?.click();
      const input = document.querySelector("dialog.search input");
      if (input !== null) {
        input.value = query.get("q") ?? body.dataset.query ?? "";
        input.dispatchEvent(new Event("input"));
      }
    }
  });

  // 撮影用: クエリの `mark` に渡した CSS セレクタの要素に赤枠を付ける（撮影の枠はモーダルの上に重ならないため、モーダルの中の要素はこちらで示す）
  const mark = query.get("mark");
  if (mark !== null) {
    const timer = setInterval(() => {
      const targets = document.querySelectorAll(mark);
      if (targets.length === 0) return;
      clearInterval(timer);
      for (const target of targets) target.classList.add("mock-mark");
    }, 100);
  }
})();
