// 見本の記録: #127 の見本（../../127/assets/data.js が埋め込み先へ入れたもの）の 4 件を、単一 UC『項目を検索する』のシナリオの記録に書き換える
// 「シナリオの依頼」: タイトルが完全に一致する用語 G-1・タイトルに含む検討事項 D-1・本文にだけ含む資料 A-1
// 「保存先」: 決定内容にだけ含む検討事項 D-1・タイトルに含む資料 A-2
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);
  /** 種類の中の ID の項目 */
  const find = (kind, id) => data[kind].find((item) => item.id === id);

  const term = find("terms", "G-1");
  term.title = "シナリオの依頼";
  term.meaning = "利用者が画面から送る、E2E のシナリオを書いてほしいという依頼";
  term.aliases = [];

  const decision = find("decisions", "D-1");
  decision.title = "シナリオの依頼の受け方";
  decision.answer = "画面から届いた依頼は送信として受け、保存先は .mindstella/submissions/ にする";
  decision.reason = "話し合いの記録と分けて置き、取り込んだかを送信ごとに持てるため";
  decision.options[0].content = decision.answer;

  const doc = find("docs", "A-1");
  data.bodies[doc.body] = `画面から届いたシナリオの依頼をきっかけに、この案を書いた。\n\n${data.bodies[doc.body]}`;

  find("docs", "A-2").title = "書き出しの保存先の一覧";

  element.textContent = JSON.stringify(data);
})();