// 見本の記録: #237 の見本の項目の `related` を `{to, type, when}` の並びにしたもの（../237/assets/data.js の後に読む）
// D-27・D-42: 互いに「同時に変更」を書いた組 / A-6: 種類の違う関連と長い `when` を持つ / N-2: 記録に無い D-99 を指す
// D-27 の参照元: A-4・A-6 が D-27 への関連を書いている / D-13: 関連を持たない
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);
  const KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"];

  /** 項目ごとに置き換える関連 */
  const RELATED = {
    "D-27": [
      { to: "D-42", type: "change_together", when: "タグの絞り込みの並びを変えるとき" },
      { to: "N-2", type: "references", when: "1 つのワークスペースで話題を並べる使い方から、絞り込みの単位を確かめるとき" },
    ],
    "D-42": [{ to: "D-27", type: "change_together", when: "タグで絞り込む操作の入口を変えるとき" }],
    "A-6": [
      { to: "D-20", type: "requires", when: "#47 の Issue の本文に、話題のタグの持ち方を書く前" },
      { to: "D-24", type: "references", when: "話題をタグに決めた理由を書くとき" },
      { to: "D-26", type: "references", when: "絞り込みのドロワーの開き方を書くとき" },
      {
        to: "D-27",
        type: "requires",
        when: "すべての画面の絞り込みの並びと、ドロワーの中の条件の順番・件数の出し方・0 件の値の扱いを、Issue の本文の受け入れ条件として 1 つずつ書き出すとき",
      },
      { to: "D-42", type: "references", when: "タグの絞り込みを表の列の絞り込みと揃えるかを書くとき" },
      { to: "D-44", type: "references", when: "絞り込みを URL に残すかを書くとき" },
    ],
    "A-4": [
      { to: "D-19", type: "references", when: "#45 の MCP のツールの一覧を書くとき" },
      { to: "D-27", type: "part_of", when: "#45 のうち、タグで絞り込む検索の引数を書くとき" },
      { to: "D-46", type: "references", when: "利用者の編集を MCP から読む方法を書くとき" },
      { to: "D-50", type: "replaces", when: "記録の読み取りの古い決め方を見直すとき" },
    ],
    "N-2": [
      { to: "D-20", type: "references", when: "話題ごとにタグを付ける決め方を確かめるとき" },
      { to: "D-99", type: "references", when: "消した検討事項の経緯を確かめるとき" },
    ],
  };

  /** ID → タイトル */
  const titles = new Map(KINDS.flatMap((kind) => (data[kind] ?? []).map((item) => [item.id, item.title])));

  /** ほかの関連の種類と `when`（種類ごとの決まった言い方） */
  const defaultRelation = (kind, item, to) => {
    if (kind === "logs") return { to, type: "references", when: `この会話で ${to} を更新した経緯を確かめるとき` };
    if (kind === "tasks") return { to, type: "references", when: `作った成果の資料 ${to} を確かめるとき` };
    if (item.id.startsWith("A-") && to.startsWith("A-")) return { to, type: "part_of", when: `${titles.get(to) ?? to} の全体を読むとき` };
    return { to, type: "references", when: `${item.title} の判断の材料を確かめるとき` };
  };

  for (const kind of KINDS) {
    for (const item of data[kind] ?? []) {
      // 見本に決めた項目は置き換え、ほかは ID の並びを要素の並びにする
      if (RELATED[item.id] !== undefined) item.related = RELATED[item.id];
      else if (Array.isArray(item.related)) item.related = item.related.map((to) => defaultRelation(kind, item, to));
    }
  }
  element.textContent = JSON.stringify(data);
})();
