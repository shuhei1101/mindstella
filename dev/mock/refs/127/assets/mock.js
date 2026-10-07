// モックの操作。app.js の起動の前にハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（ドロワー・検索を開く）を作る
(() => {
  const body = document.body;

  // ハッシュが無いときは、その画面の見本の状態で開く
  if (location.hash === "" && body.dataset.initial) {
    history.replaceState(null, "", `#${body.dataset.initial}`);
  }

  // 見出しを指すハッシュ（`h`）は、app.js が起動でハッシュを書き直す前に控える
  const heading = new URLSearchParams(location.hash.replace(/^#/, "")).get("h");
  if (heading !== null) body.dataset.heading = heading;

  /** モック専用の操作列を、app.js が先頭に入れた画面の土台より上へ戻す */
  const keepBarOnTop = () => {
    const bar = document.querySelector(".mockbar");
    if (bar !== null && body.firstElementChild !== bar) body.prepend(bar);
  };
  new MutationObserver(keepBarOnTop).observe(body, { childList: true });

  /** トップバーが描かれるまで待ってから、見本の状態を作る */
  const whenDrawn = (callback) => {
    const timer = setInterval(() => {
      if (document.querySelector("#top .topbar") === null) return;
      clearInterval(timer);
      callback();
    }, 50);
  };

  // 撮影用: クエリの `mark` に渡した CSS セレクタの要素に赤枠を付ける（撮影の枠はモーダルの上に重ならないため、モーダルの中の要素はこちらで示す）
  const mark = new URLSearchParams(location.search).get("mark");
  if (mark !== null) {
    const timer = setInterval(() => {
      const targets = document.querySelectorAll(mark);
      if (targets.length === 0) return;
      clearInterval(timer);
      for (const target of targets) target.classList.add("mock-mark");
    }, 100);
  }

  whenDrawn(() => {
    // ドロワーを開いた見本
    if (body.dataset.open === "drawer") document.querySelector("[data-act='filter']")?.click();
    // 検索に言葉を入れた見本
    if (body.dataset.open === "search") {
      document.querySelector("[data-act='search']")?.click();
      const input = document.querySelector("dialog.search input");
      if (input !== null) {
        input.value = body.dataset.query ?? "";
        input.dispatchEvent(new Event("input"));
      }
    }
  });
})();
