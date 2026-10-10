// モックの操作。app.js の起動の前にハッシュを整え、案（押したときの動き・絞り込みの入力を出す条件）を body に移し、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（ツールチップを出す・絞り込む）を作る
(() => {
  const body = document.body;
  const params = new URLSearchParams(location.search);

  // 案: クエリの click（first = A 先頭へ移る / pin = B ツールチップを残す）と filter（count = A 件数で出す / always = B 常に出す）
  body.dataset.click = params.get("click") ?? "pin";
  body.dataset.filter = params.get("filter") ?? "count";

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

  // 操作列のリンクは、クエリ（案と見本）とハッシュ（開いている項目）を組み替えて移る
  for (const link of document.querySelectorAll(".mockbar a[data-set]")) {
    const next = new URLSearchParams(location.search);
    for (const pair of link.dataset.set.split("&")) {
      const [key, value] = pair.split("=");
      if (value === "") next.delete(key);
      else next.set(key, value);
    }
    // 開いている案・見本を選択中にする
    if (link.dataset.set.split("&").every((pair) => {
      const [key, value] = pair.split("=");
      return (params.get(key) ?? { click: "pin", filter: "count" }[key] ?? "") === value;
    })) link.setAttribute("aria-current", "true");
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

  // 見本: クエリの tip の語の印に乗せたツールチップを出し、pin で押して残し、q で絞り込む。mark に渡した CSS セレクタの要素に撮影用の赤枠を付ける
  const word = params.get("tip");
  if (word !== null) {
    waitFor(".md a.term", () => {
      const mark = [...document.querySelectorAll(".md a.term")].find((node) => node.textContent === word);
      if (mark === undefined) return;
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
    });
  }
  const markSelector = params.get("mark");
  if (markSelector !== null) waitFor(markSelector, () => {
    for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
  });
})();
