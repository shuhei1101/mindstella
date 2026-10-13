// モックの操作。app.js の起動の前に、選んだ時点・ミニマップの上書き・ハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（本文を送る・表示の設定を開く）を作る
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 「前回開いてから」の始まり: V-2 と V-3 の間（10/07 09:00 JST）に固定する
  sessionStorage.setItem("mindmap-since", "2026-10-07T00:00:00+00:00");

  // 選んだ時点（クエリの diff。none は差分を出さない）と、ミニマップの上書き（クエリの minimap。off は表示しない、on は上書きなし）を端末の設定へ入れる
  const diff = params.get("diff") ?? body.dataset.diff;
  const minimap = params.get("minimap");
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = diff === "none" ? null : diff;
  // 表示の設定で選んだ値は、クエリで指定しない限り読み込み直しても残す
  if (minimap !== null) prefs.minimap = minimap === "off" ? false : null;
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  /** `data-set` のキーの今の値（クエリに無い時点は画面の見本の時点、ミニマップは表示する） */
  const currentOf = (key) => params.get(key) ?? ({ diff: body.dataset.diff, minimap: "on" }[key] ?? "");

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
    waitFor(".panel-body", () => setTimeout(() => {
      document.querySelector(".panel-body").scrollTop = Number(scroll);
    }, PANEL_SETTLE_MS));
  }
  // 撮影用: クエリの drag の px だけ、見えている範囲の面をマウスでつかんで下へ動かす（撮影の手順はマウスを押したまま動かせないため）。release が 1 なら離すところまで行う
  const drag = params.get("drag");
  if (drag !== null) {
    waitFor(".df-map-view[style]", () => setTimeout(() => {
      const map = document.querySelector(".df-map");
      const face = map.querySelector(".df-map-view").getBoundingClientRect();
      const x = face.left + face.width / 2;
      const y = face.top + face.height / 2;
      // 押している間は左ボタンを押した状態（buttons: 1）で送り、離すときだけ外す
      const send = (type, clientY) => map.dispatchEvent(new PointerEvent(type, { bubbles: true, pointerId: 1, pointerType: "mouse", button: 0, buttons: type === "pointerup" ? 0 : 1, clientX: x, clientY }));
      // 作った指の位置は捕まえられないため、捕まえる呼び出しだけを空にする
      map.setPointerCapture = () => {};
      send("pointerdown", y);
      send("pointermove", y + Number(drag) / 2);
      send("pointermove", y + Number(drag));
      if (params.get("release") === "1") send("pointerup", y + Number(drag));
    }, PANEL_SETTLE_MS));
  }
  // 見本: 表示の設定のパネルを開く
  if (body.dataset.open === "settings") waitFor(".settings-btn", (button) => button.click());
  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
