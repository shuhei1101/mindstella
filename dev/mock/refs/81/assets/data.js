// 設定の見本のデータ: 52 の見本の分野 1 つを、並べたプレイブックの名前の配列に置き換え、話し合いの概要を足す
(() => {
  const W = window.MINDMAP.workspace;
  W.playbooks = ["壁打ち", "システム開発"];
  delete W.field;
  W.description = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。";
})();
