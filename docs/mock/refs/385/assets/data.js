// 見本の記録: #237 の見本の項目の `tags` を `{name, main}` の並びにし、主題のタグを持たせたもの（../237/assets/data.js の後に読む）
// D-1: 主題の `画面` と、主題でない `記録の形`（単一ユースケース『画面で項目を編集して保存する』の見本）
// D-27・A-2: 主題を 2 つ持つ / A-6: 長いタグ名を主題に持つ / D-13: 主題を持たない
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);

  /** 項目ごとに置き換えるタグの名前 */
  const TAGS = {
    "D-1": ["画面", "記録の形"],
    "A-6": ["すべての画面の絞り込みとドロワーの並び", "ゴールと設定", "タスク", "mindstella"],
  };
  /** 項目ごとに主題にするタグの名前（ここに無い項目は、`mindstella` 以外の先頭のタグを主題にする） */
  const MAIN_TAGS = {
    "D-1": ["画面"],
    "D-13": [],
    "D-27": ["ゴールと設定", "画面"],
    "A-2": ["画面", "記録の形"],
    "A-6": ["すべての画面の絞り込みとドロワーの並び"],
  };

  for (const kind of ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]) {
    for (const item of data[kind] ?? []) {
      const names = TAGS[item.id] ?? item.tags;
      if (names === undefined) continue;
      const main = MAIN_TAGS[item.id] ?? names.filter((name) => name !== "mindstella").slice(0, 1);
      item.tags = names.map((name) => (main.includes(name) ? { name, main: true } : { name }));
    }
  }
  element.textContent = JSON.stringify(data);
})();
