// モックの操作。app.js の起動の前にハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、全体の検索を開いて見本の言葉を入れる
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);
  // 見本の言葉: クエリの `q`、無ければ body の data-query
  const query = params.get("q") ?? body.dataset.query ?? "";

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  // 案のタブは、開いている見本の言葉を引き継いで移る
  for (const link of document.querySelectorAll(".mockbar a[data-variant]")) {
    link.search = location.search;
  }
  // 見本の言葉のリンクは、今の言葉のものを選択中にする
  for (const link of document.querySelectorAll(".mockbar a[data-query]")) {
    if (link.dataset.query === query) link.setAttribute("aria-current", "true");
  }

  /** トップバーが描かれるまで待ってから、見本の状態を作る */
  const whenDrawn = (callback) => {
    const timer = setInterval(() => {
      if (document.querySelector("#top .topbar") === null) return;
      clearInterval(timer);
      callback();
    }, 50);
  };

  // 全体の検索を開き、見本の言葉を入れる
  whenDrawn(() => {
    document.querySelector("[data-act='search']")?.click();
    const input = document.querySelector("dialog.search input");
    if (input === null) return;
    input.value = query;
    input.dispatchEvent(new Event("input"));
    // 撮影用: クエリの `mark` に渡した CSS セレクタの要素に赤枠を付ける（撮影の枠はモーダルの上に重ならないため、モーダルの中の要素はこちらで示す）
    const mark = params.get("mark");
    if (mark !== null) for (const target of document.querySelectorAll(mark)) target.classList.add("mock-mark");
  });
})();