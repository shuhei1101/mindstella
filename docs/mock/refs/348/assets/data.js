// 見本の記録の追加: #237 の見本（data.js が埋め込み先へ入れたもの）に、埋め込んだ HTML を持つ資料 A-20 と、A-20 を書き換えたまとまり（V-7）と、用語 G-7 を足す
// A-20: 段落・`<!-- html -->` の範囲（段落 3 つ・チャート・スライダーとコピーのボタン・<script>）・範囲の外の html のコードブロック。V-7 で範囲の 2 つ目の段落を書き換えた
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);

  /** 範囲の 2 つ目の段落（V-7 で書き換えた後と前） */
  const SECOND_NOW = "<p>分類: 書き込みの種類を分け、急ぎのものを先に回す。</p>";
  const SECOND_BEFORE = "<p>分類: 書き込みの種類を分ける。</p>";

  /** A-20 の本文。`second` に範囲の 2 つ目の段落を入れる */
  const body = (second) => [
    "返信の速さを、応答時間で測って見直す。詳しい測り方は A-2 にまとめた。",
    "",
    "<!-- html -->",
    "",
    "```html",
    "<p>受け取り: 届いた書き込みに時刻を残し、応答時間を記録する（A-2）。</p>",
    second,
    "<p>返信: 下書きを用意し、30 秒以内に返す。</p>",
    "<mdmark-chart>",
    JSON.stringify({
      type: "line",
      title: "曜日ごとの返信",
      scope: "10 月の第 2 週",
      updated: "2026-10-17",
      x: { label: "曜日", ticks: ["月", "火", "水", "木", "金"] },
      y: { label: "秒" },
      series: [{ name: "平均", points: [12, 9, 14, 8, 11] }],
    }, null, 2),
    "</mdmark-chart>",
    "<mdmark-param>",
    JSON.stringify({
      title: "返信の速さの見積もり",
      knob: { key: "strength", label: "反応の強さ", min: 0, max: 2, step: 1, value: 1 },
      chart: {
        title: "反応の強さごとの返信の進み",
        scope: "経過 0〜4 秒",
        updated: "2026-10-18",
        x: { label: "経過（秒）", ticks: ["0", "2", "4"] },
        y: { label: "返信の進み（%）", min: 0, max: 100, step: 25 },
      },
      table: { 0: [0, 0, 0], 1: [0, 40, 70], 2: [0, 60, 90] },
    }, null, 2),
    "</mdmark-param>",
    '<script>document.title = "動いた";</script>',
    "```",
    "",
    "<!-- /html -->",
    "",
    "範囲の外の html のコードブロックは、今のまま HTML の本文の枠で描く。",
    "",
    "```html",
    '<p style="padding: 8px 12px; border: 1px dashed currentColor">範囲の外の html のコードブロック</p>',
    "```",
    "",
  ].join("\n");

  const now = body(SECOND_NOW);
  // 書き換えた段落の行（1 始まり）
  const changedLine = now.split("\n").indexOf(SECOND_NOW) + 1;
  const seq = data.changes.last_seq + 1;
  const at = "2026-10-10T01:00:00+00:00";

  data.terms.push({
    id: "G-7",
    title: "レスポンスタイム",
    meaning: "書き込みを受け取ってから返信を返すまでの時間",
    aliases: ["応答時間"],
    tags: ["プレビュー"],
    created: "2026-10-09T02:00:00+00:00",
    updated: "2026-10-09T02:00:00+00:00",
  });
  data.docs.push({
    id: "A-20",
    title: "返信の速さの検討（埋め込んだ HTML とチャート）",
    target: "スキルと画面",
    kind: "文書",
    deliverable: false,
    status: "確認中",
    related: ["A-2"],
    tags: ["プレビュー"],
    body: "A-20.md",
    created: "2026-10-09T02:00:00+00:00",
    updated: at,
    seq,
    history: [{ seq, at, by: "ai", before: {}, body_diff: [{ line: changedLine, now: [SECOND_NOW], before: [SECOND_BEFORE] }] }],
  });
  data.bodies["A-20.md"] = now;
  data.changes.sets.unshift({ id: "V-7", at, summary: "返信の速さの検討の分類の段を書き直す", until_seq: seq, added: [], changed: ["A-20"] });
  data.changes.last_seq = seq;

  element.textContent = JSON.stringify(data);
})();
