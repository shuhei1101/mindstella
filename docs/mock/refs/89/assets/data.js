// 話題のタグの見本のデータ: 52 の見本のタグを、AI が話題ごとに付けたタグに置き換える
// 話題はカテゴリーから決め、話題をまたぐ項目には 2 つ目のタグを足す。長い名前のタグを 1 つ混ぜる
(() => {
  const M = window.MINDMAP;
  const TOPIC_OF_CATEGORY = {
    "分け方": "記録の形", "データ構造": "記録の形",
    "進め方": "話し合いの進め方", "聞き方": "話し合いの進め方",
    "調査": "調べ方", "配布": "配布と導入",
    "画面": "プレビュー", "デザイン": "プレビュー",
  };
  // 話題をまたぐ項目: ID → 足すタグ
  const EXTRA = {
    "D-012": ["プレビュー"], "D-013": ["話し合いの進め方"], "D-019": ["調べ方"], "D-021": ["配布と導入"],
    "D-022": ["プレビューの画面で項目を探す操作"], "D-023": ["プレビューの画面で項目を探す操作"],
    "T-002": ["プレビューの画面で項目を探す操作"], "T-003": ["調べ方"],
    "A-003": ["話し合いの進め方"],
  };
  const byId = new Map();
  for (const k of ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]) for (const it of M[k]) byId.set(it.id, it);
  for (const k of ["decisions", "tasks", "research", "docs"]) for (const it of M[k]) {
    it.tags = [...new Set([TOPIC_OF_CATEGORY[it.category], ...(EXTRA[it.id] || [])].filter(Boolean))];
  }
  // 用語集はどの話題でも使う記録の言葉のため「記録の形」、メモ・会話ログは関連する項目の話題を引き継ぐ
  for (const it of M.terms) it.tags = ["記録の形"];
  for (const k of ["notes", "logs"]) for (const it of M[k]) {
    it.tags = [...new Set((it.related || []).flatMap((id) => byId.get(id)?.tags?.slice(0, 1) || []))];
  }
  // タグを持たない項目を 1 つ残す（タグの条件を選ぶと外れる）
  byId.get("T-007").tags = [];
})();
