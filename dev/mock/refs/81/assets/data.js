// 設定の見本のデータ: 52 の見本の分野 1 つを、並べたプレイブックの名前の配列に置き換える
(() => {
  const W = window.MINDMAP.workspace;
  W.playbooks = ["壁打ち", "システム開発"];
  delete W.field;
})();
