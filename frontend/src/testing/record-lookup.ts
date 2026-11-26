// ストーリーと単体テストが部品『記録の文字』に指定する、見本の記録の ID の検索（D-1・D-2・TH-1 が記録にあり、D-99 は記録に無い）
import type { LookupRecordId, RecordIdTarget } from "@/shared/core/record-ids";

const SAMPLE_TARGETS: Readonly<Record<string, RecordIdTarget>> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "D-2": { id: "D-2", kind: "item", title: "D-1 の見直し", kindLabel: "検討事項", status: "決定済み" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

export const sampleRecordLookup: LookupRecordId = (id) => SAMPLE_TARGETS[id] ?? null;
