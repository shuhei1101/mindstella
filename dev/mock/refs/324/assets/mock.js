// モックの操作。app.js の起動の前に、日付の出し方の案・表の列の既定・ハッシュを整え、描いた後にモック専用の操作列を一番上へ戻す
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 日付の出し方の案（クエリの date。iso: 記録の値のまま / locale: 曜日を添える）
  body.dataset.date = params.get("date") ?? "iso";

  // 差分の表示は出さず、タスクの表の列は案の既定（body の data-cols）で開く
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
  if (prefs.columns !== undefined) delete prefs.columns.tasks;
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  /** `data-set` のキーの今の値 */
  const currentOf = (key) => params.get(key) ?? ({ date: "iso" }[key] ?? "");

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** 操作列のリンクの行き先と、開いている見本の印を今のクエリとハッシュから決める */
  const refreshLinks = () => {
    const hashNow = location.hash.replace(/^#/, "");
    for (const link of document.querySelectorAll(".mockbar a")) {
      // 案・画面のリンクは、今の見本（クエリ）のまま移る。data-keep が hash のリンクは開いている項目も引き継ぐ
      if (link.dataset.set === undefined) {
        if (link.dataset.keep === undefined) continue;
        link.dataset.base ??= link.getAttribute("href");
        link.href = `${link.dataset.base}${location.search}${link.dataset.keep === "hash" ? location.hash : ""}`;
        continue;
      }
      // 見本のリンクは、クエリ（日付の出し方）とハッシュ（開いている項目）を組み替えて開き直す
      const pairs = link.dataset.set.split("&").filter(Boolean).map((pair) => pair.split("="));
      const next = new URLSearchParams(location.search);
      for (const [key, value] of pairs) next.set(key, value);
      // 開いている見本を選択中にする
      const same = pairs.every(([key, value]) => currentOf(key) === value) && (link.dataset.hash ?? hashNow) === hashNow;
      if (same) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = `?${next.toString()}#${link.dataset.hash ?? hashNow}`;
    }
  };
  refreshLinks();
  addEventListener("hashchange", refreshLinks);

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) {
    const timer = setInterval(() => {
      const targets = document.querySelectorAll(markSelector);
      if (targets.length === 0) return;
      clearInterval(timer);
      for (const target of targets) target.classList.add("mock-mark");
    }, 50);
  }
})();
