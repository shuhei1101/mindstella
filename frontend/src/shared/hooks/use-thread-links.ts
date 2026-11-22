// 本文と書き込みのスレッドの ID のリンクに渡す、スレッドの引き方と開き方
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { type LookupThread, type OpenThread, revealPost, threadLookupOf } from "@/shared/core/thread-ids";
import { threadsQuery } from "@/shared/hooks/preview-queries";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";

/** スレッドの読み取りからスレッドの引き方を作り、押したスレッドをコメントの一覧で開いて書き込みまでスクロールする（配る書き出しではスレッドが無いので null） */
export const useThreadLinks = (): { threads: LookupThread | null; onOpenThread: OpenThread } => {
  // スレッドは外枠が読む。ここでは読み込みを起こさず、読み込んだ分を使う
  const { data } = useQuery({ ...threadsQuery(), enabled: false });
  const { openThread } = usePreviewSearch();
  const list = data?.status === 200 ? (data.data.threads as unknown as Parameters<typeof threadLookupOf>[0]) : undefined;
  const threads = useMemo(() => (list === undefined ? null : threadLookupOf(list)), [list]);
  // 開き方は描くたびに替わるので、本文を描き直さないよう最新の開き方を参照する関数を 1 つに保つ
  const open = useRef(openThread);
  useEffect(() => {
    open.current = openThread;
  }, [openThread]);
  const onOpenThread = useCallback<OpenThread>((threadId, postId) => {
    open.current(threadId);
    if (postId !== null) requestAnimationFrame(() => { revealPost(postId); });
  }, []);
  return { threads, onOpenThread };
};
