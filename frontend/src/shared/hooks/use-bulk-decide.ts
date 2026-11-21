// 検討事項をまとめて推奨の案で決める操作。決めた後は記録を再取得し、決められなかった検討事項と理由を返却する
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/shared/adapters/api-client";
import type { BulkDecideFailure } from "@/shared/components/bulk-decide-bar";
import { AppError } from "@/shared/core/app-error";
import { recordsQuery } from "@/shared/hooks/preview-queries";

/** まとめて決める API のパス */
const BULK_DECIDE_PATH = "/api/decisions/decide";

/** サーバーに届かなかったときの理由 */
const UNREACHABLE_REASON = "サーバーが止まっています。再起動してから押してください。";

export type BulkDecide = {
  pending: boolean;
  /** 直前の決定で決められなかった検討事項 */
  failures: BulkDecideFailure[];
  /** 選んだ検討事項を決め、成功したら `onDecided` を呼ぶ */
  decide: (input: { ids: readonly string[]; onDecided: () => void }) => void;
};

/** 失敗の応答の本文から、決められなかった検討事項を取り出す */
const failuresOf = (reason: unknown): BulkDecideFailure[] => {
  if (!(reason instanceof AppError)) return [{ id: "-", reason: UNREACHABLE_REASON }];
  const body = reason.body as { failures?: BulkDecideFailure[] } | null;
  return body?.failures ?? [{ id: "-", reason: reason.message }];
};

export const useBulkDecide = (): BulkDecide => {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (ids: readonly string[]) =>
      apiClient<{ data: unknown }>(BULK_DECIDE_PATH, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }) }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: recordsQuery().queryKey }),
  });
  return {
    pending: mutation.isPending,
    failures: mutation.isError ? failuresOf(mutation.error) : [],
    decide: ({ ids, onDecided }) => {
      mutation.mutate(ids, { onSuccess: onDecided });
    },
  };
};
