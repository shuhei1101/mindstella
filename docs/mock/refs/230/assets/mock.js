// モックの操作。app.js の起動の前にハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（本文を送る）を作る
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

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

  /** 操作列のリンクの行き先と、開いている見本の印を今のクエリとハッシュから決める */
  const refreshLinks = () => {
    for (const link of document.querySelectorAll(".mockbar a")) {
      // 案・画面のリンクは、今の見本（クエリとハッシュ）のまま移る
      if (link.dataset.set === undefined) {
        if (link.dataset.keep === undefined) continue;
        link.dataset.base ??= link.getAttribute("href");
        link.href = `${link.dataset.base}${location.search}${location.hash}`;
        continue;
      }
      // 見本のリンクは、クエリ（見本）とハッシュ（開いている項目）を組み替えて移る
      const next = new URLSearchParams(location.search);
      for (const pair of link.dataset.set.split("&")) {
        const [key, value] = pair.split("=");
        if (value === "") next.delete(key);
        else next.set(key, value);
      }
      // 開いている見本を選択中にする
      if (link.dataset.set.split("&").every((pair) => {
        const [key, value] = pair.split("=");
        return (params.get(key) ?? "") === value;
      }) && (link.dataset.hash ?? "") === location.hash.replace(/^#/, "")) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      const hash = link.dataset.hash ?? location.hash.replace(/^#/, "");
      link.href = `?${next.toString()}#${hash}`;
    }
  };
  refreshLinks();
  addEventListener("hashchange", refreshLinks);

  /** 条件の要素が描かれるまで待つ */
  const waitFor = (selector, callback) => {
    const timer = setInterval(() => {
      const found = document.querySelector(selector);
      if (found === null) return;
      clearInterval(timer);
      callback(found);
    }, 50);
  };

  // 見本: クエリの scroll の px だけ詳細の本文の領域を送る（詳細パネルが滑り込み終わってから。ハッシュだけ変わる見本の移り先でも送り直す）
  const scroll = params.get("scroll");
  if (scroll !== null) {
    const scrollBody = () => waitFor(".panel-body", () => setTimeout(() => {
      document.querySelector(".panel-body").scrollTop = Number(scroll);
    }, 600));
    scrollBody();
    addEventListener("hashchange", scrollBody);
  }
  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
