// 画面のストーリーの記録とスレッド。誰が決めたか（`decided_by`）は論理名の利用者・AI を仮の値で持つ
import { RECORDS } from "@/testing/msw/handlers";

const option = (key: string, content: string, recommended = false, adopted = false) => ({ key, content, ...(recommended ? { recommended: true } : {}), ...(adopted ? { adopted: true } : {}) });

const at = "2026-11-21T00:00:00+00:00";

export const STORY_RECORDS = {
  ...RECORDS,
  settings: {
    ...RECORDS.settings,
    presets: [
      { name: "画面の設計", description: "タグ「画面」を持ち「廃止」を持たない項目", filter: { and: [{ field: "tags", op: "eq", values: ["画面"] }, { field: "tags", op: "ne", values: ["廃止"] }] } },
      { name: "保存の仕組み", description: "タグ「保存」を持つ項目", filter: { field: "tags", op: "eq", values: ["保存"] } },
      { name: "通知", description: "タグ「通知」を持つ項目", filter: { field: "tags", op: "eq", values: ["通知"] } },
    ],
  },
  preset_counts: { 画面の設計: 2, 保存の仕組み: 1, 通知: 0 },
  decisions: [
    { id: "D-1", title: "再送の回数", status: "決定済み", decided_by: "ai", options: [option("A", "3 回", true, true), option("B", "5 回")], created: at, updated: at },
    { id: "D-2", title: "通知に含める内容", status: "未決定", options: [option("A", "題名と要約", true), option("B", "本文の全て")], created: at, updated: at },
    { id: "D-3", title: "通知を送信する時機", status: "未決定", options: [option("A", "すぐ"), option("B", "まとめて 1 日 1 回", true)], created: at, updated: at },
    { id: "D-4", title: "通知の文面の言語", status: "未決定", options: [option("A", "日本語"), option("B", "英語")], created: at, updated: at },
    { id: "D-5", title: "ログインの方式", status: "決定済み", decided_by: "user", options: [option("A", "メールとパスワード", true, true)], created: at, updated: at },
    { id: "D-6", title: "保存の形式", status: "決定済み", options: [option("A", "YAML", false, true)], created: at, updated: at },
  ],
  tasks: [
    { id: "T-1", title: "一覧の画面を作る", status: "未着手", kind: "作業", tags: [{ name: "画面" }], created: at, updated: at },
    { id: "T-2", title: "廃止した設定の画面を削除する", status: "未着手", kind: "作業", tags: [{ name: "画面" }, { name: "廃止" }], created: at, updated: at },
    { id: "T-3", title: "詳細パネルを作る", status: "完了", kind: "作業", tags: [{ name: "画面" }], created: at, updated: at },
    { id: "T-4", title: "保存の形式を調べる", status: "未着手", kind: "調査", tags: [{ name: "保存" }], created: at, updated: at },
  ],
  derived: { ready: ["D-2", "D-3", "D-4"] },
};

/** AI の通知のスレッド。最初の書き込みが追加した検討事項と AI が決めた検討事項を表で並べる */
export const STORY_THREADS = {
  threads: [
    {
      id: "TH-1",
      status: "open",
      summary: "通知の検討事項",
      tags: [],
      target: null,
      loc: null,
      events: [],
      posts: [
        {
          id: "TH-1-1",
          author: "ai",
          body: "| ID | 質問 | 推奨 |\n| --- | --- | --- |\n| D-2 | 通知に含める内容 | A |\n| D-3 | 通知を送信する時機 | B |\n\nAI が決めた検討事項\n\n| ID | 質問 | 採用した案 |\n| --- | --- | --- |\n| D-1 | 再送の回数 | A |",
          created: at,
          seen: true,
        },
      ],
    },
  ],
};
