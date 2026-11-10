// 見本の記録: #127 の見本（../../127/assets/data.js が埋め込み先へ入れたもの）に、単一 UC『項目を表で絞り込む』の調査 R-1（確度: 高）・R-2（確度: 低）・R-3（確度: 高）と、表が縦に送れるだけの調査を足す
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);
  const at = "2026-10-06T03:00:00+00:00";
  /** 調査 1 件 */
  const research = ({ id, title, question, conclusion, confidence, tags, related }) => ({
    id, title, question, conclusion, confidence, tags, related,
    created: at, updated: at, updated_by: "ai",
  });
  data.research = [
    research({ id: "R-1", title: "表の列を選ぶボタンの呼び名", question: "ほかの表のツールは列の表示を何と呼んでいるか", conclusion: "「列」「列の表示」「表示する列」が多く、アイコンを添える", confidence: "高", tags: ["プレビュー", "表"], related: ["D-17"] }),
    research({ id: "R-2", title: "ポップオーバーの位置を自前で決めるか", question: "anchor positioning で置けるか", conclusion: "対応していないブラウザがあり、今は自前で決める", confidence: "低", tags: ["プレビュー"], related: [] }),
    research({ id: "R-3", title: "列の選びを端末に残す場所", question: "localStorage に残して読み込み直しで戻るか", conclusion: "表ごとの key で残し、初期設定に戻すと消す", confidence: "高", tags: ["プレビュー", "表"], related: ["D-18"] }),
  ];
  // 表が画面に収まらず縦に送れる件数にする（単一 UC の記録の「そのほかに 40 件」）
  const confidences = ["高", "中", "低"];
  for (let n = 4; n <= 43; n += 1) {
    data.research.push(research({
      id: `R-${n}`,
      title: `表の見本の調査 ${n}`,
      question: `見本の問い ${n}`,
      conclusion: `見本の結論 ${n}`,
      confidence: confidences[n % confidences.length],
      tags: ["見本"],
      related: [],
    }));
  }
  element.textContent = JSON.stringify(data);
})();
