// 記録に保存待ちの編集を重ねた索引を読む
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { applyEdits, type PendingEdit } from "@/shared/core/edits";
import { buildIndex, type MindmapData, type RecordIndex } from "@/shared/core/records";
import { editsQuery, recordsQuery } from "@/shared/hooks/preview-queries";

const NO_EDITS: readonly PendingEdit[] = [];

/** 読んだ記録の状態 */
export type RecordsState = {
  /** 編集を重ねた索引。読めていなければ null */
  index: RecordIndex | null;
  /** 編集を重ねる前の索引 */
  rawIndex: RecordIndex | null;
  edits: readonly PendingEdit[];
  error: Error | null;
};

export const useRecords = (): RecordsState => {
  const records = useQuery(recordsQuery());
  const edits = useQuery(editsQuery());
  const items = (edits.data?.data as { items?: PendingEdit[] } | undefined)?.items ?? NO_EDITS;
  const data = records.data?.status === 200 ? (records.data.data as unknown as MindmapData) : null;
  // 索引の同一性で本文を描き直すので、記録と編集が変わったときだけ作り直す
  const index = useMemo(() => (data === null ? null : buildIndex(applyEdits(data, items))), [data, items]);
  const rawIndex = useMemo(() => (data === null ? null : buildIndex(data)), [data]);
  return { index, rawIndex, edits: items, error: records.error as Error | null };
};
