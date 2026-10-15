// モックの操作。app.js の起動の前にハッシュとボタンの文言の案を整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（ポップオーバーを開いた状態）を作る
(() => {
  const body = document.body;
  const query = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // ボタンの文言の案: クエリの `label`（long = 案 A「列の表示」、short = 案 B「列」）。app.js が起動のときに読む
  body.dataset.label = query.get("label") === "short" ? "short" : "long";

  /** 開き直す: クエリとハッシュを渡して読み込み直す（app.js は起動のときにだけ文言・ハッシュの条件を読む） */
  const reopen = (search, hash) => {
    const text = search.toString();
    if (`?${text}` === location.search || (text === "" && location.search === "")) {
      // クエリが同じときはハッシュを替えるだけでは読み込み直さないので、替えてから読み込み直す
      history.replaceState(null, "", hash);
      location.reload();
      return;
    }
    location.href = `${location.pathname}?${text}${hash}`;
  };

  // モック専用の操作列のクエリのリンク: 今のクエリに `data-set` の値を重ね、ハッシュを保って開き直す。今の値のリンクに aria-current を付ける
  for (const link of document.querySelectorAll(".mockbar a[data-set]")) {
    const [key, value] = link.dataset.set.split("=");
    const next = new URLSearchParams(location.search);
    next.set(key, value);
    link.href = `?${next.toString()}${location.hash}`;
    const current = key === "label" ? body.dataset.label : query.get(key);
    if (current === value) link.setAttribute("aria-current", "true");
    link.addEventListener("click", (event) => {
      event.preventDefault();
      reopen(next, location.hash);
    });
  }
  // モック専用の操作列のハッシュのリンク: クエリを保ってハッシュを `data-hash` に替えて開き直す（開いたポップオーバーは閉じる）
  for (const link of document.querySelectorAll(".mockbar a[data-hash]")) {
    const hash = `#${link.dataset.hash}`;
    if (decodeURIComponent(location.hash) === hash) link.setAttribute("aria-current", "true");
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const next = new URLSearchParams(location.search);
      next.delete("open");
      reopen(next, hash);
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

  // 列を選ぶポップオーバーを開いた見本（クエリの `open=columns`）
  if (query.get("open") === "columns") {
    const timer = setInterval(() => {
      const button = document.querySelector('[data-popover="columns"]');
      if (button === null) return;
      clearInterval(timer);
      button.click();
    }, 50);
  }
})();
