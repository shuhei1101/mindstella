// 記録の文字の中の ID を記録の項目・スレッドに結ぶ検索と、ID を押したときに項目の詳細かスレッドを開く関数
import { useCallback, useMemo } from "react";

import { recordLookupOf, type LookupRecordId } from "@/shared/core/record-ids";
import type { RecordIndex } from "@/shared/core/records";
import { resolveThreadId } from "@/shared/core/thread-ids";
import { useThreadLinks } from "@/shared/hooks/use-thread-links";

/** 記録の索引と読み込んだスレッドから、部品『記録の文字』の `lookup` と `onOpen` を作る（スレッドを読み込んでいない配る書き出しではスレッドの ID を結ばない。記録を読み込む前はどの ID も結ばない） */
export const useRecordLookup = ({ index, onOpenItem }: { index: RecordIndex | null; onOpenItem: (id: string) => void }): { lookup: LookupRecordId; onOpen: (id: string) => void } => {
  const { threads, onOpenThread } = useThreadLinks();
  const lookup = useMemo<LookupRecordId>(() => (index === null ? () => null : recordLookupOf({ index, threads })), [index, threads]);
  const onOpen = useCallback(
    (id: string) => {
      const thread = threads === null ? null : resolveThreadId(id, threads);
      if (thread === null) onOpenItem(id);
      else onOpenThread(thread.threadId, thread.postId);
    },
    [threads, onOpenThread, onOpenItem],
  );
  return { lookup, onOpen };
};
