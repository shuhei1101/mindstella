// モックの操作。app.js の起動の前に開く見本を整え、描いた後にモック専用の操作列を一番上へ戻し、クエリの edit で詳細パネルを編集の表示にする
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 差分を出さない（主題のマーカーの見比べに差分の印を混ぜない）
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

  // 見本に戻す: 保存待ちの編集と、保存した項目を消して開き直す
  for (const link of document.querySelectorAll(".mockbar a[data-reset]")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      sessionStorage.removeItem("mock-385-edits");
      sessionStorage.removeItem("mock-385-saved");
      location.reload();
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

  // 編集の表示の見本（edit=1）: 詳細パネルの「編集する」を押した状態で開く
  if (params.get("edit") === "1") {
    waitFor('.pe-edit-toggle[aria-pressed="false"]', (button) => button.click());
  }

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
