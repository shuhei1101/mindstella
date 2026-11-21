// 画面のストーリーの記録。プリセットはチェックで表せる式と、除外を含む式を持つ
import { RECORDS } from "@/testing/msw/handlers";

const at = "2026-11-21T00:00:00+00:00";

export const STORY_RECORDS = {
  ...RECORDS,
  settings: {
    ...RECORDS.settings,
    presets: [
      { name: "画面の設計", description: "タグ「画面」を持ち「廃止」を持たない項目", filter: { and: [{ field: "tags", op: "eq", values: ["画面"] }, { field: "tags", op: "ne", values: ["廃止"] }] } },
      { name: "廃止する画面", description: "タグ「画面」と「廃止」を両方持つ項目", filter: { field: "tags", op: "eq", values: ["画面", "廃止"], match: "all" } },
      { name: "保存の仕組み", description: "タグ「保存」を持つ項目", filter: { field: "tags", op: "eq", values: ["保存"] } },
      { name: "通知", description: "タグ「通知」を持つ項目", filter: { field: "tags", op: "eq", values: ["通知"] } },
    ],
  },
  tasks: [
    { id: "T-1", title: "一覧の画面を作る", status: "未着手", kind: "作業", tags: [{ name: "画面" }], created: at, updated: at },
    { id: "T-2", title: "廃止した設定の画面を削除する", status: "未着手", kind: "作業", tags: [{ name: "画面" }, { name: "廃止" }], created: at, updated: at },
    { id: "T-3", title: "詳細パネルを作る", status: "完了", kind: "作業", tags: [{ name: "画面" }], created: at, updated: at },
    { id: "T-4", title: "保存の形式を調べる", status: "未着手", kind: "調査", tags: [{ name: "保存" }], created: at, updated: at },
  ],
};
