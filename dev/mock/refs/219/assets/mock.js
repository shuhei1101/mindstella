// モックの操作。app.js の起動の前にハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（ツールチップを出す・絞り込む）を作る
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

  // 操作列のリンクは、クエリ（見本）とハッシュ（開いている項目）を組み替えて移る
  for (const link of document.querySelectorAll(".mockbar a[data-set]")) {
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
    const hash = link.dataset.hash ?? location.hash.replace(/^#/, "");
    link.href = `?${next.toString()}#${hash}`;
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

  // 見本: クエリの tip の語の印に乗せたツールチップを出し、edge で最初の印を詳細の本文の領域の上端へ送ってから出し、pin で押して残し、q で絞り込む。mark に渡した CSS セレクタの要素に撮影用の赤枠を付ける
  const word = params.get("tip");
  if (word !== null) {
    // 詳細パネルが滑り込み終わってから出す（動いている間は印の位置が定まらない）
    waitFor(".md a.term", () => setTimeout(() => {
      // 印は本文の最後のもの（edge のときは最初のもの）を使う
      const marks = [...document.querySelectorAll(".md a.term")].filter((node) => node.textContent === word);
      const mark = params.get("edge") !== null ? marks[0] : marks.at(-1);
      if (mark === undefined) return;
      if (params.get("edge") !== null) {
        const region = mark.closest(".panel-body");
        region.scrollTop += mark.getBoundingClientRect().top - region.getBoundingClientRect().top - 12;
      }
      mark.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
      if (params.get("pin") !== null) mark.click();
      const query = params.get("q");
      const input = document.querySelector("#term-tip input");
      if (query !== null && input !== null) {
        input.value = query;
        input.dispatchEvent(new Event("input"));
      }
      if (params.get("scroll") !== null) {
        const tip = document.getElementById("term-tip");
        tip.scrollTop = tip.scrollHeight;
      }
    }, 500));
  }
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
