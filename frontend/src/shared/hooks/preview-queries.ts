// SPA が読む query（記録・レビュー中のコメント・保存待ちの編集・スレッド）と読み直し
import type { QueryClient } from "@tanstack/react-query";

import {
  getGetCommentsQueryOptions,
  getGetEditsQueryOptions,
  getGetRecordsQueryOptions,
  getGetThreadsQueryOptions,
} from "@/shared/api/generated/preview";

/** 記録の query */
export const recordsQuery = () => getGetRecordsQueryOptions();

/** レビュー中のコメントの query */
export const commentsQuery = () => getGetCommentsQueryOptions();

/** 保存待ちの編集の query */
export const editsQuery = () => getGetEditsQueryOptions();

/** スレッドの query */
export const threadsQuery = () => getGetThreadsQueryOptions();

/** ルートの loader で先読みする query */
export const previewQueries = () => [recordsQuery(), commentsQuery(), editsQuery(), threadsQuery()] as const;

/** 書き換えの知らせと編集の後に 4 つの query を読み直す */
export const invalidatePreview = async (queryClient: QueryClient): Promise<void> => {
  await Promise.all(previewQueries().map((query) => queryClient.invalidateQueries({ queryKey: query.queryKey })));
};
