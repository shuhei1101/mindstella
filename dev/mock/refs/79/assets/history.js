// 差分の表示の見本のデータ: 52 の見本を今の版にし、書き換えのまとまり（変更履歴）と、まだまとめていない書き換えを持たせる
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

  // ===== A-004: まだまとめていない書き換え =====
  const a004Before = M.bodies["A-004"];
  M.bodies["A-004"] = a004Before + "\n\nカードには状態と納品物の印を出す。";

  // ===== 前回開いた後に足された項目 =====
  M.decisions.push({
    id: "D-037", title: "差分の時点の選び方", target: "プレビュー", status: "未決定", weight: "中",
    lead: "変更履歴から書き換えのまとまりを選び、その時点の差分を画面全体に出す。",
    tags: ["差分"], depends_on: [], related: ["D-005"], sources: [], updated: "2026-10-04", category: "画面", stage: "インターフェース",
  });
  M.notes.push({ id: "N-004", title: "差分の印の見た目", content: "足した・消したを色だけで示さず、記号と取り消し線を併せる", tags: ["UI"], related: ["D-037"], updated: "2026-10-04" });

  // ===== 変更履歴: 書き換えのまとまり =====
  // 1 つのまとまりの changes は、項目ごとにそのまとまりの書き換えの前の値（変わったキーと本文）を持つ
  // added: そのまとまりで足された項目。trimmed: 保持する回数を超えて変更履歴が消え、前後を組み立てられない
  // bodyUnavailable: 変更履歴の本文の差分が今の本文に当たらない。diagram: 図の差分（flowchart のノードの鍵・消したノードと辺の表示名）
  window.MINDMAP_HISTORY = {
    // 端末に残っている「前回開いた日時」
    lastOpened: "2026-10-04T13:05:00+09:00",
    // まだまとめていない書き換え（commit を呼ぶ前）
    pending: {
      id: "pending", at: "2026-10-04T15:02:00+09:00",
      changes: { "A-004": { keys: {}, body: a004Before } },
    },
    // commit したまとまり。新しい順
    sets: [
      { id: "cs5", at: "2026-10-04T14:50:00+09:00", desc: "差分の印の見た目をメモに残す", changes: { "N-004": { added: true } } },
      {
        id: "cs4", at: "2026-10-04T14:45:00+09:00", desc: "フェーズの切り方を見直しに戻す",
        changes: {
          "D-005": {
            keys: { status: "決定済み", answer: "目的 / 要件 / 構成 / インターフェース / コンテンツ" }, body: d005Before1,
            diagram: { colored: true, changed: ["I"], added: ["MD"], addedEdges: ["I_MD"], removed: ["モジュール構成（M）", "インターフェース → モジュール構成"] },
          },
          "D-037": { added: true },
        },
      },
      {
        id: "cs3", at: "2026-10-04T14:40:00+09:00", desc: "仕様書の段取りを直す",
        // gantt はノード・辺に色を付けず、変わった図の枠に色を付ける
        changes: { "A-005": { keys: { status: "下書き" }, body: a005Before, diagram: { colored: false } } },
      },
      {
        id: "cs2", at: "2026-10-04T14:32:00+09:00", desc: "steps の一覧と取り込みの流れを直す",
        changes: {
          "D-019": { keys: { weight: "中" }, bodyUnavailable: true },
          "A-003": { keys: {}, body: a003Before, diagram: { colored: true, changedText: ["記録・派生の検討事項・未整理を追加"], removed: [] } },
        },
      },
      {
        id: "cs1", at: "2026-10-03T18:02:00+09:00", desc: "フェーズの切り方を決める",
        changes: { "D-005": { keys: { status: "未決定", weight: "中" }, body: d005Before2, trimmed: true } },
      },
    ],
    // モックの操作列の「書き換えを受け取る」で、開いたまま届く書き換え（まだまとめていない変更に積む）
    live: { id: "D-022", keys: { status: "未決定", answer: undefined }, apply: { status: "決定済み", answer: "開発者ツール × スイス" } },
  };
  find("docs", "A-005").status = "確認中";
})();
