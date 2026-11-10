// 部品のモックの見本。app.js（起動はしない）が出すスレッドの書き込みへ、状態ごとの引数を渡し、案 A と案 B を並べて台に置く
(() => {
  /** 見本の日時（UTC。画面は JST で出す） */
  const at = (hhmm) => `2026-10-12T${hhmm}:00+00:00`;

  /** 見本の項目のタイトル（記録に無い ID は null） */
  const TITLES = {
    "A-14": "プレビューの差分の読み方（手引き）",
    "A-11": "設定のパネルの画面の流れ（モック）",
    "D-12": "移し替えが途中で失敗したときの扱い",
    "R-1": "プレビューの差分を別のライブラリで計算できるか",
    "T-14": "移し替えの失敗の扱いを書く",
  };
  /** 記録にあるまとまり（V-99 は保持する回数を超えて消えたもの） */
  const CHANGE_SETS = new Set(["V-2", "V-5", "V-6"]);

  /** 見本の本文 */
  const BODIES = {
    ai: "A-14 の手引きを書き直しました。直したところは [A-14 の手引きの書き直し](#diff=V-6) で見られます。\n表の行の消し方は D-12 で決めたとおりにしています。\n前に相談した版は [古い手引き](#diff=V-99) にありましたが、保持する回数を超えて消えています。",
    user: "[A-14 の手引きの書き直し](#diff=V-6) を見た。図の凡例は R-1 の結果に合わせたい。\n[since から](#diff=since) と [ハッシュの例](#tab=docs) は押せなくてよい",
    pending: "[A-14 の手引きの書き直し](#diff=V-6) で消した表の行は戻してほしい。T-14 にも関わる。\n[古い手引き](#diff=V-99) は要らない",
    long: "A-11 の段落を [設定のパネルの画面の流れのうち、既定として保存するまでの段落と確かめのダイアログの説明](#tab=docs&id=A-11&diff=V-5) のとおりに直しました。",
  };

  const noop = () => {};
  /** 書き込みの部品へ渡す、押したときの知らせ */
  const on = { openId: noop, changeSet: noop, edit: noop, saveEdit: noop, cancelEdit: noop, remove: noop };
  /** 引きの関数 */
  const titles = (id) => TITLES[id] ?? null;
  const changeSets = (id) => CHANGE_SETS.has(id);

  /** 案（a・b）を選んで、要素を作る（部品は描くときの body の data-variant で見た目を選ぶ） */
  const withVariant = (variant, draw) => {
    document.body.dataset.variant = variant;
    return draw();
  };
  /** 書き込みの並びに入れる */
  const posts = (items) => MindmapPreview.h({ tag: "ol", attrs: { class: "posts" }, children: items });
  /** 案の見出しを付けた列 */
  const column = (label, node) => MindmapPreview.h({ tag: "div", attrs: { class: "cat-col" }, children: [MindmapPreview.h({ tag: "p", attrs: { class: "cat-col-label" }, children: [label] }), node] });

  /** 台（id）に、案 A と案 B の列を並べる */
  const both = (id, draw) => {
    const stage = document.getElementById(id);
    stage.append(column("案 A 本文のリンク", withVariant("a", draw)), column("案 B ID のボタン", withVariant("b", draw)));
    return stage;
  };

  /** 書き込み 1 件 */
  const post = (author, body) => posts([MindmapPreview.threadPost({ post: { id: "TH-1-1", author, body, created: at("01:24") }, titles, changeSets, on })]);
  /** スレッドの中のレビュー中の書き込み 1 件 */
  const pending = (body) => posts([MindmapPreview.threadPost({ pending: { id: "C-41", target: null, target_title: null, loc: null, thread: "TH-1", body, created: at("05:10") }, titles, changeSets, on })]);
  /** レビュー中を確かめる画面の行の本文 */
  const reviewBody = (body) => MindmapPreview.h({ tag: "div", attrs: { class: "review-row-sample" }, children: [MindmapPreview.postDiffBody({ body, className: "review-body", changeSets, onChangeSet: noop })] });

  both("s-ai", () => post("ai", BODIES.ai));
  both("s-user", () => post("user", BODIES.user));
  both("s-pending", () => pending(BODIES.pending));
  both("s-review", () => reviewBody(BODIES.pending));
  both("s-hover", () => post("ai", BODIES.ai)).querySelectorAll(".cat-col").forEach((col) => col.querySelector(".post-diff")?.classList.add("is-hover"));
  both("s-focus", () => post("ai", BODIES.ai)).querySelectorAll(".cat-col").forEach((col) => col.querySelector(".post-diff")?.classList.add("is-focus"));
  both("s-long", () => post("ai", BODIES.long));
  both("s-narrow", () => post("ai", BODIES.long));
  delete document.body.dataset.variant;

  // ライト / ダークの切り替え（ページ全体）
  document.querySelector("[data-act='theme']").addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  });
  const theme = new URLSearchParams(location.search).get("theme");
  if (theme !== null) document.documentElement.dataset.theme = theme;
})();
