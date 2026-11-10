// モックの操作。app.js の起動の前に開く見本を整え、描いた後にモック専用の操作列を一番上へ戻し、クエリの menu でエクスポートのメニューを開いた状態にする
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 差分の時点はハッシュの diff だけで選ぶ（端末に残った時点を持ち込まない）
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
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

  /** 条件の要素が描かれるまで待つ */
  const waitFor = (selector, callback) => {
    const timer = setInterval(() => {
      const found = document.querySelector(selector);
      if (found === null) return;
      clearInterval(timer);
      callback(found);
    }, 50);
  };

  // HTML のエクスポートの見本（busy: 組み立てている間 / error: 組み立てられなかった）。app.js の組み立てがこの値を見る
  const exportState = params.get("export");
  window.MindmapPreview = { mockExport: exportState };

  // エクスポートのメニューの見本（open: 形式を選ぶ / warn: Markdown の警告 / closed: 閉じている）。クエリが無いときは body の data-menu
  const menu = params.get("menu") ?? body.dataset.menu ?? "closed";
  if (menu !== "closed" || exportState !== null) {
    waitFor(".panel-export", (button) => {
      button.click();
      if (menu === "warn") waitFor('.doc-export [data-format="md"]', (item) => item.click());
      if (exportState !== null) waitFor('.doc-export [data-format="html"]', (item) => item.click());
    });
  }

  // 差分の見せ方の見本（before: 変更前 / after: 変更後）
  const range = params.get("range");
  if (range !== null) waitFor(`.range-diff [data-view="${range}"]`, (button) => button.click());

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
