// 見本の記録の足し分: #237 の見本の記録（data.js が埋め込み先へ入れたもの）に、検討事項 D-1 の本文と、それを書き換えたまとまり（V-7）を足す
// D-1 は資料ではないので、詳細パネルの幅が 480px になり、本文の幅が足りないときの見本になる
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);

  /** D-1 の今の本文 */
  const body = [
    "移し替えの仕組みの目的を、版ごとの手順の当て方から決める。",
    "",
    "## 背景",
    "",
    "形式の変更が続く予定で、版を持たない今の migrate は当てる手順を決められない。",
    "",
    "## 決めたこと",
    "",
    "ワークスペースに版を記録し、プラグインの版と比べて、間の版の手順を順に当てる。",
    "",
    "- 当てる前に git のコミットで写しを取る",
    "- 当てた後に点検を流し、通らなければ写しへ戻す",
    "",
  ].join("\n");
  data.bodies["D-1.md"] = body;

  // V-7: D-1 の段落を 1 つ変え、箇条書きの項目を 1 つ足した
  const at = "2026-10-10T01:00:00+00:00";
  const decision = data.decisions.find((item) => item.id === "D-1");
  Object.assign(decision, {
    body: "D-1.md",
    updated: at,
    seq: 41,
    history: [
      {
        seq: 41,
        at,
        by: "ai",
        before: {},
        body_diff: [
          { line: 9, now: ["ワークスペースに版を記録し、プラグインの版と比べて、間の版の手順を順に当てる。"], before: ["ワークスペースに版を記録し、古い版のときだけ手順を当てる。"] },
          { line: 12, now: ["- 当てた後に点検を流し、通らなければ写しへ戻す"], before: [] },
        ],
      },
    ],
  });
  data.changes.last_seq = 41;
  data.changes.sets.unshift({ id: "V-7", at, summary: "移し替えの目的に当て方を書く", until_seq: 41, added: [], changed: ["D-1"] });

  element.textContent = JSON.stringify(data);
})();
