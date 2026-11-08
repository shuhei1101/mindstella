// スレッドの状態の書き換えと利用者の既読の mutation
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { markThreadSeen, setThreadStatus } from "@/shared/api/generated/preview";
import type { Threads } from "@/shared/api/generated/model";
import { withSeen, type Thread } from "@/shared/core/comments";
import { threadsQuery } from "@/shared/hooks/preview-queries";

/** スレッドの query に入る値（orval の応答） */
type ThreadsResponse = { data: Threads; status: number };

/** スレッドをクローズにするかオープンに戻し、スレッドを読み直す */
export const useSetThreadStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status, reason }: { id: string; status: "open" | "closed"; reason: string | null }) => (await setThreadStatus(id, { status, reason })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: threadsQuery().queryKey }),
  });
};

/** スレッドを既読にする。応答を待たずにスレッドの query の値を既読にし、失敗したらスレッドを読み直してサーバーの値に戻す（失敗は画面に出さない） */
export const useMarkThreadSeen = () => {
  const queryClient = useQueryClient();
  const { queryKey } = threadsQuery();
  return useMutation({
    mutationFn: async (id: string) => (await markThreadSeen(id)).data,
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey });
      queryClient.setQueryData<ThreadsResponse>(queryKey, (current) => {
        if (current?.status !== 200) return current;
        return { ...current, data: { ...current.data, threads: withSeen({ threads: current.data.threads as unknown as Thread[], id }) as unknown as Threads["threads"] } };
      });
    },
    // 画面が読んでいない間でも戻すため、使われていない query も読み直す
    onError: () => queryClient.refetchQueries({ queryKey }),
  });
};
