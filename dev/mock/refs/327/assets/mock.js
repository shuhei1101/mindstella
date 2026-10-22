// モックの操作。app.js の起動の前に、選んだ時点・列の幅の案・見出しの開閉の案・表示の設定の上書き・ハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（本文を送る・表示の設定を開く）を作る
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 「前回開いてから」の始まり: V-2 と V-3 の間（10/07 09:00 JST）に固定する
  sessionStorage.setItem("mindmap-since", "2026-10-07T00:00:00+00:00");

  // 列の幅（クエリの cols。full は今の表示の本文の幅いっぱい）と、境目の案（クエリの bounds。「短い列の上限,長文の列の下限」）
  if (params.get("cols") === "full") body.dataset.cols = "full";
  const bounds = params.get("bounds");
  if (bounds !== null) body.dataset.colBounds = bounds;
  // 見出しの開閉の案（クエリの fold。icon: 矢印だけを押せる / text: 文言ごと押せる）
  body.dataset.foldToggle = params.get("fold") ?? body.dataset.foldToggle ?? "icon";

  // 選んだ時点（クエリの diff。none は差分を出さない）と、表示の設定の上書き（クエリの md。default は上書きを外す）を端末の設定へ入れる
  const diff = params.get("diff") ?? body.dataset.diff;
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = diff === "none" ? null : diff;
  // 本文の差分の並べ方（クエリの layout。side: 左右に並べるで開く）
  const layout = params.get("layout");
  if (layout !== null) prefs.bodyLayout = layout === "side" ? "side" : null;
  const md = params.get("md");
  if (md !== null) {
    const set = new Set(md.split(","));
    prefs.mdPin = set.has("pin-off") ? false : null;
    prefs.mdHead = set.has("head-off") ? false : null;
    prefs.mdStripes = set.has("stripes-on") ? true : null;
    prefs.mdFold = set.has("fold-off") ? false : null;
  }
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  // 見本: 端末の保存領域に書けない（クエリの storage が ng）
  if (params.get("storage") === "ng") {
    Storage.prototype.setItem = function () {
      throw new DOMException("書けない保存領域の見本", "QuotaExceededError");
    };
  }

  /** `data-set` のキーの今の値（クエリに無い時点は画面の見本の時点、表示の設定は既定、ほかは空） */
  const currentOf = (key) => params.get(key) ?? ({ diff: body.dataset.diff, md: "default" }[key] ?? "");

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
      // 画面のリンクは、今の見本（クエリ）のまま移る。data-keep が hash のリンクは開いている項目も引き継ぐ
      if (link.dataset.set === undefined) {
        if (link.dataset.keep === undefined) continue;
        link.dataset.base ??= link.getAttribute("href");
        link.href = `${link.dataset.base}${location.search}${link.dataset.keep === "hash" ? location.hash : ""}`;
        continue;
      }
      // 見本のリンクは、クエリ（見本）とハッシュ（開いている項目）を組み替えて開き直す
      const pairs = link.dataset.set.split("&").map((pair) => pair.split("="));
      const next = new URLSearchParams(location.search);
      for (const [key, value] of pairs) {
        if (value === "") next.delete(key);
        else next.set(key, value);
      }
      // 開いている見本を選択中にする
      const same = pairs.every(([key, value]) => currentOf(key) === value) && (link.dataset.hash ?? hashNow) === hashNow;
      if (same) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = `?${next.toString()}#${link.dataset.hash ?? hashNow}`;
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

  // 詳細パネルが滑り込み終わるまで待つ時間（ミリ秒）
  const PANEL_SETTLE_MS = 600;

  // 見本: クエリの scroll の px だけ詳細の本文の領域を送る
  const scroll = params.get("scroll");
  if (scroll !== null) {
    waitFor(".panel-body .md", () => setTimeout(() => {
      const scroller = document.querySelector("dialog.full .panel-body") ?? document.querySelector(".panel-body");
      scroller.scrollTop = Number(scroll);
    }, PANEL_SETTLE_MS));
  }
  // 見本: 表示の設定のパネルを開く
  if ((params.get("open") ?? body.dataset.open) === "settings") waitFor(".settings-btn", (button) => button.click());
  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
