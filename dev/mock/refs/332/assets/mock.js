// モックの操作。app.js の起動の前に、入口の見た目の案とハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の選んだ範囲を作って入口を出す
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 見た目の案: 文字（クエリの label。icon: 印だけ / text: 印と小さい「コメント」）と面（クエリの bg。solid: 不透明 / clear: 半透明）
  body.dataset.label = params.get("label") ?? "icon";
  body.dataset.bg = params.get("bg") ?? "solid";

  // 差分を出さない（入口の見比べに差分の印を混ぜない）
  const prefs = JSON.parse(localStorage.getItem("mindmap-preview") ?? "{}");
  prefs.diffSel = null;
  localStorage.setItem("mindmap-preview", JSON.stringify(prefs));

  /** `data-set` のキーの今の値（クエリに無いときは既定の見本） */
  const currentOf = (key) => params.get(key) ?? ({ label: "icon", bg: "solid", sel: "mid" }[key] ?? "");

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** 操作列のリンクの行き先と、開いている見本の印を今のクエリとハッシュから決める */
  const refreshLinks = () => {
    for (const link of document.querySelectorAll(".mockbar a")) {
      // 画面と案のリンクは、今の見本（クエリ）のまま移る
      if (link.dataset.set === undefined) {
        if (link.dataset.keep === undefined) continue;
        link.dataset.base ??= link.getAttribute("href");
        link.href = `${link.dataset.base}${location.search}`;
        continue;
      }
      // 見本のリンクは、クエリを組み替えて開き直す
      const pairs = link.dataset.set.split("&").map((pair) => pair.split("="));
      const next = new URLSearchParams(location.search);
      for (const [key, value] of pairs) {
        if (value === "") next.delete(key);
        else next.set(key, value);
      }
      // 開いている見本を選択中にする
      if (pairs.every(([key, value]) => currentOf(key) === value)) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
      link.href = `?${next.toString()}${location.hash}`;
    }
  };
  refreshLinks();

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
  // 見本の選んだ範囲（A-14 の「長い資料で変わった箇所を探す」の段落）。mid と top は 2 つ目の段落の頭の近くから、inner は 1 つ目の段落の 2 行目から 2 つ目の段落まで
  const SAMPLES = {
    mid: { from: "何が変わったかの見当を付けると", to: "変えた理由を 1 行で書いている" },
    inner: { from: "飛ばすことになる", to: "何が変わったかの見当を付けると" },
    top: { from: "何が変わったかの見当を付けると", to: "変えた理由を 1 行で書いている" },
  };
  // 見本の段落を本文の区画の上端から離す量（px。top の見本で、選んだ範囲の上に入口が収まらないようにする）
  const TOP_OFFSET = 4;

  /** 段落の中の文字の位置を、テキストのノードとその中の位置にする */
  const pointAt = (root, index) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let rest = index;
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
      if (rest <= node.data.length) return { node, offset: rest };
      rest -= node.data.length;
    }
    return null;
  };

  // 見本の選んだ範囲（クエリの sel。mid: 段落の頭の近くから 2 行 / inner: 段落の途中の行から次の段落まで / top: 本文の区画の上端の行 / none: 選ばない）
  const sample = SAMPLES[currentOf("sel")];
  if (sample !== undefined) {
    waitFor(".panel-body .md p", () => setTimeout(() => {
      const scroller = document.querySelector("dialog.full[open] .panel-body") ?? document.querySelector("aside.panel .panel-body");
      const paragraphs = [...scroller.querySelectorAll(".md p")];
      const first = paragraphs.find((p) => p.textContent.includes(sample.from));
      const last = paragraphs.find((p) => p.textContent.includes(sample.to));
      // 選ぶ段落を、top は区画の上端、ほかは区画の上から 3 分の 1 へ送る
      const offset = first.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
      scroller.scrollTop += currentOf("sel") === "top" ? offset - TOP_OFFSET : offset - scroller.clientHeight / 3;
      const start = pointAt(first, first.textContent.indexOf(sample.from));
      const end = pointAt(last, last.textContent.indexOf(sample.to) + sample.to.length);
      const range = document.createRange();
      range.setStart(start.node, start.offset);
      range.setEnd(end.node, end.offset);
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      // 選び終えたことにして、入口を出す
      document.dispatchEvent(new PointerEvent("pointerup"));
    }, PANEL_SETTLE_MS));
  }

  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
