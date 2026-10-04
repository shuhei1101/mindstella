// 差分の表示の見本のデータ: 52 の見本を今の版にし、項目ごとの変更履歴と、前回開いた後に足された項目を持たせる
// 変更履歴の 1 回分は、その書き換えの前の値（変わったキーと本文）を持つ。並びは新しい順
(() => {
  const M = window.MINDMAP;
  const FENCE = "```";
  const lines = (...xs) => xs.join("\n");
  const find = (kind, id) => M[kind].find((x) => x.id === id);

  // ===== D-005: 2 回分の変更履歴。前回は状態・決定内容・本文（段落・表の行・図）を書き換えた =====
  const phaseTable = (structure, contents) => lines(
    "| フェーズ | 決めること |",
    "| --- | --- |",
    "| 目的 | 目的・成功の基準・制約・スコープ |",
    "| 要件 | できること（ユースケース）・品質の目標・運用 |",
    `| 構成 | ${structure} |`,
    "| インターフェース | 入出力の情報と型・DB のスキーマ・設定のキー・MCP / API |",
    `| コンテンツ | ${contents} |`,
  );
  M.bodies["D-005"] = lines(
    "システム開発のフェーズの並び。モジュール構成をフェーズに含めるかを見直している。",
    "",
    phaseTable("サブシステム・外部システム・ライブラリ・データの置き場所・主な処理の流れ", "システムが扱う中身そのもの（キャラの設定・プロンプトの文面・ノウハウ）"),
    "",
    FENCE + "mermaid",
    "flowchart LR",
    "  P[目的] --> R[要件] --> S[構成] --> I[インターフェースと設定] --> C[コンテンツ]",
    "  I -.->|選んだとき| MD[モジュール構成]",
    FENCE,
    "",
    "ゴールに「モジュール構成まで」を選んだときの扱いは、ゴール判定の書き出しと合わせて決め直す。",
  );
  const d005Before1 = lines(
    "システム開発のフェーズの並び。",
    "",
    phaseTable("サブシステム・外部システム・ライブラリ・データの置き場所", "システムが扱う中身そのもの（キャラの設定・プロンプトの文面・ノウハウ）"),
    "",
    FENCE + "mermaid",
    "flowchart LR",
    "  P[目的] --> R[要件] --> S[構成] --> I[インターフェース] --> C[コンテンツ]",
    "  I --> M[モジュール構成]",
    FENCE,
    "",
    "ゴールに「モジュール構成まで」を選んだときは、インターフェースの後にモジュール構成のフェーズを足す。",
    "",
    "モジュール構成は、ゴールで選ばなくても常にフェーズに含める。",
  );
  const d005Before2 = lines(
    "システム開発のフェーズの並び。",
    "",
    phaseTable("サブシステム・外部システム・ライブラリ・データの置き場所", "システムが扱う中身そのもの"),
    "",
    FENCE + "mermaid",
    "flowchart LR",
    "  P[目的] --> R[要件] --> S[構成] --> I[インターフェース] --> C[コンテンツ]",
    "  I --> M[モジュール構成]",
    FENCE,
    "",
    "モジュール構成は、ゴールで選ばなくても常にフェーズに含める。",
  );
  find("decisions", "D-005").answer = "目的 / 要件 / 構成 / インターフェースと設定 / コンテンツ（モジュール構成は見直し中）";

  // ===== D-019: 前回の書き換えの後に本文を手で書き換えたため、本文の前の版を組み立てられない =====
  M.bodies["D-019"] = M.bodies["D-019"].replace("| プレビュー | HTML を作って開く |", "| プレビュー | サーバーが配るプレビューを開く場所を示す |");

  // ===== A-003: 色を付ける種類の図（sequenceDiagram）のメッセージを変えた =====
  const a003Before = M.bodies["A-003"];
  M.bodies["A-003"] = a003Before.replace("記録・派生の検討事項を追加", "記録・派生の検討事項・未整理を追加");

  // ===== A-005: 色を付けない種類の図（gantt）のタスクの期間を変えた =====
  const gantt = (spec) => lines(
    FENCE + "mermaid",
    "gantt",
    "  dateFormat YYYY-MM-DD",
    "  section 仕様書",
    "    目次を決める :a1, 2026-10-05, 2d",
    `    決めたことを書き写す :a2, after a1, ${spec}`,
    "    受け取る人に見せる :a3, after a2, 1d",
    FENCE,
  );
  const a005Before = M.bodies["A-005"] + "\n\n" + gantt("3d");
  M.bodies["A-005"] = M.bodies["A-005"] + "\n\n" + gantt("5d");

  // ===== 前回開いた後に足された項目 =====
  M.decisions.push({
    id: "D-037", title: "差分の表示で比べる回を選べるか", target: "プレビュー", status: "未決定", weight: "中",
    lead: "保持する回数を 2 回分以上にしたときに、前回より前の変更も読めるようにするか。",
    tags: ["差分"], depends_on: [], related: ["D-005"], sources: [], updated: "2026-10-04", category: "画面", stage: "インターフェース",
  });
  M.notes.push({ id: "N-004", title: "差分の印の見た目", content: "足した・消したを色だけで示さず、記号と取り消し線を併せる", tags: ["UI"], related: ["D-037"], updated: "2026-10-04" });

  // ===== 変更履歴 =====
  window.MINDMAP_HISTORY = {
    // 端末に残っている「前回開いた日時」
    lastOpened: "2026-10-04T13:05:00+09:00",
    // 前回開いた後に足された項目と、足された日時
    added: { "D-037": "2026-10-04T14:45:00+09:00", "N-004": "2026-10-04T14:50:00+09:00" },
    items: {
      "D-005": {
        rounds: [
          { at: "2026-10-04T14:20:00+09:00", keys: { status: "決定済み", answer: "目的 / 要件 / 構成 / インターフェース / コンテンツ" }, body: d005Before1 },
          { at: "2026-10-03T18:02:00+09:00", keys: { status: "未決定", weight: "中" }, body: d005Before2 },
        ],
        // 図の差分: flowchart のノードの鍵（記法の ID）と、消したノード・辺の表示名
        diagram: { colored: true, changed: ["I"], added: ["MD"], addedEdges: ["I_MD"], removed: ["モジュール構成（M）", "インターフェース → モジュール構成"] },
      },
      "D-019": {
        rounds: [{ at: "2026-10-04T14:32:00+09:00", keys: { weight: "中" }, body: null }],
        // 変更履歴の本文の差分が、今の本文に当たらない
        bodyUnavailable: true,
      },
      "A-003": {
        rounds: [{ at: "2026-10-04T14:25:00+09:00", keys: {}, body: a003Before }],
        diagram: { colored: true, changedText: ["記録・派生の検討事項・未整理を追加"], removed: [] },
      },
      "A-005": {
        rounds: [{ at: "2026-10-04T14:40:00+09:00", keys: { status: "下書き" }, body: a005Before }],
        // gantt はノード・辺に色を付けず、変わった図の枠に色を付ける
        diagram: { colored: false },
      },
    },
    // モックの操作列の「書き換えを受け取る」で、開いたまま届く書き換え
    live: { id: "D-022", at: null, keys: { status: "未決定", answer: undefined }, apply: { status: "決定済み", answer: "開発者ツール × スイス" } },
  };
  find("docs", "A-005").status = "確認中";
})();
