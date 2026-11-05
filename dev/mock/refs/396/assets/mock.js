// モックの操作。app.js の起動の前に開く見本を整え、描いた後にモック専用の操作列を一番上へ戻す。
// クエリの order で開くときの並びを、remove で消した行の見本を決める
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 差分を出さない。クエリの order=oldest で古い順を選んだ状態で開く（並びは読み込み直しても保つ）
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
  if (params.has("order")) prefs.reviewOrder = params.get("order") === "oldest" ? "oldest" : null;
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** 操作列のリンクの行き先と、開いている見本の印を今のクエリとハッシュから決める */
  const refreshLinks = () => {
    for (const link of document.querySelectorAll(".mockbar a[data-hash]")) {
      const [hash, query = ""] = link.dataset.hash.split("?");
      if (location.hash === `#${hash}` && location.search === (query === "" ? "" : `?${query}`)) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = `${query === "" ? location.pathname : `?${query}`}#${hash}`;
    }
  };
  refreshLinks();
  window.addEventListener("hashchange", refreshLinks);

  // 見本に戻す: 選んだ並びを消して、新しい順で開き直す
  for (const link of document.querySelectorAll(".mockbar a[data-reset]")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const saved = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
      delete saved.reviewOrder;
      localStorage.setItem("mindmap-preview", JSON.stringify(saved));
      location.href = `${location.pathname}#${body.dataset.initial}`;
    });
  }

  /** 条件の要素が描かれるまで待つ */
  const waitFor = (selector, callback) => {
    const timer = setInterval(() => {
      const found = document.querySelector(selector);
      if (found === null) return;
      clearInterval(timer);
      callback(found);
    }, 50);
  };

  // 消した行の見本（remove=C-2）: その行の「削除」を押した状態で開く
  const removeId = params.get("remove");
  if (removeId !== null) {
    waitFor(`.d-review [data-comment="${removeId}"] .row-actions .icon-btn:last-child`, (button) => button.click());
  }

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
