// モックの操作。app.js の起動の前に、開く見本・残した幅・区切りの状態の見本を整え、描いた後にモック専用の操作列を一番上へ戻す
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 差分を出さない（幅の見比べに差分の印を混ぜない）
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  // 残した幅の見本（クエリの w。reset: 残した幅を消して既定の幅から / 数値: その幅を残す）。当てたらクエリから外し、ドラッグした幅を読み込み直しても保てるようにする
  const WIDTH_KEY = "mindmap-preview-panel-width";
  const width = params.get("w");
  if (width !== null) {
    if (width === "reset") sessionStorage.removeItem(WIDTH_KEY);
    else sessionStorage.setItem(WIDTH_KEY, width);
    params.delete("w");
    const query = params.toString();
    history.replaceState(null, "", `${location.pathname}${query === "" ? "" : `?${query}`}${location.hash}`);
  }

  // 区切りの状態の見本（クエリの state。hover: 乗せた / focus: フォーカスした / drag: ドラッグ中）
  body.dataset.state = params.get("state") ?? "";

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** 操作列のリンクの行き先と、開いている見本の印を今のクエリとハッシュから決める */
  const refreshLinks = () => {
    const now = new URLSearchParams(location.search);
    for (const link of document.querySelectorAll(".mockbar a")) {
      // 開く項目のリンクは、今のクエリのままハッシュだけを変える
      if (link.dataset.hash !== undefined) {
        if (location.hash === `#${link.dataset.hash}`) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
        link.href = `${location.search}#${link.dataset.hash}`;
        continue;
      }
      if (link.dataset.set === undefined) continue;
      // 見本のリンクは、クエリを組み替えて開き直す
      const [key, value] = link.dataset.set.split("=");
      const next = new URLSearchParams(location.search);
      if (value === "") next.delete(key);
      else next.set(key, value);
      // 区切りの状態は、開いている見本を選択中にする（幅の見本は当てた後にクエリから外すので印を付けない）
      if (key === "state" && (now.get(key) ?? "") === value) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      const query = next.toString();
      link.href = `${query === "" ? location.pathname : `?${query}`}${location.hash}`;
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

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
