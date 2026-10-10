// モックの操作。app.js の起動の前にハッシュを整え、描いた後にモック専用の操作列を一番上へ戻し、見本の状態（行を直している・空白で直そうとした・消した・直せなかった）を作る
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

  // 操作列の見本の状態のリンクに、今のハッシュ（開いている項目・全画面）を引き継ぐ
  for (const link of document.querySelectorAll(".mockbar a[data-state]")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      location.href = `${link.getAttribute("href")}${location.hash}`;
    });
    const state = new URL(link.href).searchParams.get("state");
    if ((params.get("state") ?? null) === state) link.setAttribute("aria-current", "true");
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

  /** 開いている詳細（全画面か詳細パネル）の中の要素 */
  const inDetail = (selector) => `dialog.full[open] ${selector}, aside.panel.open ${selector}`;

  // 撮影用: クエリの `mark` に渡した CSS セレクタの要素に赤枠を付ける（撮影の枠はモーダルの上に重ならないため、モーダルの中の要素はこちらで示す）
  const mark = params.get("mark");
  const applyMark = () => {
    if (mark === null) return;
    waitFor(mark, () => {
      for (const target of document.querySelectorAll(mark)) target.classList.add("mock-mark");
    });
  };

  /** 見本の状態を作る（直す行は C-2、消す行は C-3） */
  const state = params.get("state");
  waitFor(inDetail(".d-review"), () => {
    if (state === null) return applyMark();
    if (state === "removed") {
      document.querySelector(inDetail('[data-focus="d-remove:C-3"]'))?.click();
      return waitFor(inDetail(".review-removed"), applyMark);
    }
    document.querySelector(inDetail('[data-focus="d-edit-open:C-2"]'))?.click();
    waitFor(inDetail("form.row-edit textarea"), (field) => {
      if (state === "editing") return applyMark();
      // 空白だけで直そうとした・届かずに直せなかった
      field.value = state === "blank" ? "   " : `${field.value}\n文言は「この分野では何と呼びますか」でどうでしょう。`;
      field.closest("form").requestSubmit();
      waitFor(inDetail("form.row-edit .send-msg:not(:empty)"), applyMark);
    });
  });
})();
