// 記録の文字の中の項目の ID・スレッドの ID を見つけ、記録の項目・スレッドに結ぶ
import { KIND_LABEL, type RecordIndex } from "@/shared/core/records";
import { type LookupThread, resolveThreadId } from "@/shared/core/thread-ids";

/** スレッドの ID・書き込みの ID・項目の ID（前が英数字・`-` のときと、後ろが数字のときはヒットさせない） */
export const RECORD_ID_PATTERN = /(?<![A-Za-z0-9-])(?:TH-[0-9]+(?:-[0-9]+)?|[A-Z]+-[0-9]+)(?![0-9])/g;

/** ツールチップと読み上げに出す、ID が指す項目・スレッドの中身 */
export type RecordIdTarget = {
  /** 項目・スレッドの ID（書き込みの ID のときはその ID） */
  id: string;
  /** 部品『本文のマーカーのツールチップ』の種類 */
  kind: "item" | "thread";
  title: string;
  /** 種類の名前（検討事項・スレッド など） */
  kindLabel: string;
  /** 状態の名前。状態を持たない種類は持たない */
  status?: string;
};

/** ID から記録の項目・スレッドを検索し、記録に無い ID は `null` を返却する */
export type LookupRecordId = (id: string) => RecordIdTarget | null;

/** 記録にある ID と、文字の中の開始・終了の位置 */
export type FoundRecordId = { start: number; end: number; target: RecordIdTarget };

/** 文字の中の ID のうち、記録にあるものを位置とともに並びの順で返却する */
export const findRecordIds = ({ text, lookup }: { text: string; lookup: LookupRecordId }): FoundRecordId[] =>
  [...text.matchAll(RECORD_ID_PATTERN)].flatMap((match) => {
    const target = lookup(match[0]);
    return target === null ? [] : [{ start: match.index, end: match.index + match[0].length, target }];
  });

/** スレッドの状態の名前 */
const THREAD_STATUS_LABEL = { open: "オープン", closed: "クローズ" } as const satisfies Record<"open" | "closed", string>;

/** 記録の索引の項目とスレッドの検索から、ID を記録の項目・スレッドに結ぶ関数を作る（`threads` が `null` の配る書き出しではスレッドの ID を結ばない） */
export const recordLookupOf = ({ index, threads }: { index: RecordIndex; threads: LookupThread | null }): LookupRecordId => {
  return (id) => {
    if (id.startsWith("TH-")) {
      const resolved = threads === null ? null : resolveThreadId(id, threads);
      const thread = resolved === null || threads === null ? null : threads(resolved.threadId);
      if (thread === null) return null;
      return { id, kind: "thread", title: thread.title, kindLabel: "スレッド", ...(thread.status === undefined ? {} : { status: THREAD_STATUS_LABEL[thread.status] }) };
    }
    const found = index.byId.get(id);
    if (found === undefined) return null;
    return { id, kind: "item", title: found.item.title, kindLabel: KIND_LABEL[found.kind], ...(found.item.status === undefined ? {} : { status: found.item.status }) };
  };
};
