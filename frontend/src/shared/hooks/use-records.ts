// 記録に保存待ちの編集を重ねた索引を読む
import { useQuery } from "@tanstack/react-query";

import { applyEdits, type PendingEdit } from "@/shared/core/edits";
import { buildIndex, type MindmapData, type RecordIndex } from "@/shared/core/records";
import { editsQuery, recordsQuery } from "@/shared/hooks/preview-queries";

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
  const items = (edits.data?.data as { items?: PendingEdit[] } | undefined)?.items ?? [];
  const data = records.data?.status === 200 ? (records.data.data as unknown as MindmapData) : null;
  return {
    index: data === null ? null : buildIndex(applyEdits(data, items)),
    rawIndex: data === null ? null : buildIndex(data),
    edits: items,
    error: records.error as Error | null,
  };
};
