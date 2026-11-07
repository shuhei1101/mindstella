// コメントの一覧・スレッド・レビュー中の書き込みの画面が読む値（レビュー中の書き込み・書きかけ・スレッド・項目のタイトル・まとまりの説明）
import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";

import { AppError } from "@/shared/core/app-error";
import type { Draft, ReviewItem, Thread } from "@/shared/core/comments";
import type { LookupTitle } from "@/shared/core/post-links";
import { commentsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { useRecords } from "@/shared/hooks/use-records";

const NO_ITEMS: readonly ReviewItem[] = [];
const NO_DRAFTS: readonly Draft[] = [];
const NO_THREADS: readonly Thread[] = [];

export type CommentData = {
  items: readonly ReviewItem[];
  drafts: readonly Draft[];
  threads: readonly Thread[];
  /** スレッドを読めたか */
  threadsLoaded: boolean;
  /** スレッドを読めなかった理由（届かなければ `detail` が null）。読めていれば null */
  threadsError: { detail: string | null } | null;
  titles: LookupTitle;
  changeSets: LookupTitle;
};

export const useCommentData = (): CommentData => {
  const comments = useQuery(commentsQuery());
  const threadsResult = useQuery(threadsQuery());
  const { index } = useRecords();
  const body = comments.data?.status === 200 ? (comments.data.data as { items?: ReviewItem[]; drafts?: Draft[] }) : undefined;
  const threads = threadsResult.data?.status === 200 ? (threadsResult.data.data.threads as unknown as Thread[]) : undefined;
  const error = threadsResult.error;
  const titles = useCallback<LookupTitle>((id) => index?.byId.get(id)?.item.title ?? null, [index]);
  const changeSets = useCallback<LookupTitle>((id) => index?.data.changes.sets.find((set) => set.id === id)?.summary ?? null, [index]);
  return {
    items: body?.items ?? NO_ITEMS,
    drafts: body?.drafts ?? NO_DRAFTS,
    threads: threads ?? NO_THREADS,
    threadsLoaded: threads !== undefined,
    threadsError: error === null ? null : { detail: error instanceof AppError ? error.message : null },
    titles,
    changeSets,
  };
};
