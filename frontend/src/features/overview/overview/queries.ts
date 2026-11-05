// 概要が読む query（記録・レビュー中のコメント・保存待ちの編集・スレッド）。生成した queryOptions を成功の本文で選ぶ
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

/** ルートの loader で先読みする、概要が読む query */
export const overviewQueries = () => [recordsQuery(), commentsQuery(), editsQuery(), threadsQuery()] as const;
