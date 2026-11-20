// 項目の確認済みの付け外し。応答を待つ間は押した後の値を返し、失敗したら記録の値に戻して文を返す
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { setItemConfirmed } from "@/shared/api/generated/preview";
import { AppError } from "@/shared/core/app-error";
import { recordsQuery } from "@/shared/hooks/preview-queries";

/** 失敗の文の頭 */
const FAILED_PREFIX = "確認済みを書き換えられませんでした。";

/** サーバーに届かなかったときに続ける文 */
const UNREACHABLE_MESSAGE = "サーバーが止まっています。再起動してから押してください。";

export type ItemConfirmed = {
  /** 描く確認済み（応答を待つ間は押した後の値） */
  confirmed: boolean;
  saving: boolean;
  /** 直前の失敗の文（無ければ null） */
  error: string | null;
  toggle: () => void;
};

/** 開いている項目の確認済みと、付け外しの操作を返す */
export const useItemConfirmed = (id: string, confirmed: boolean): ItemConfirmed => {
  const queryClient = useQueryClient();
  // 失敗の文は失敗した項目の ID と組で持ち、別の項目では出さない
  const [failure, setFailure] = useState<{ id: string; message: string } | null>(null);
  const mutation = useMutation({
    mutationFn: async (next: boolean) => (await setItemConfirmed(id, { confirmed: next })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: recordsQuery().queryKey }),
    onError: (reason) => {
      setFailure({ id, message: `${FAILED_PREFIX}${reason instanceof AppError ? reason.message : UNREACHABLE_MESSAGE}` });
    },
  });
  const toggle = () => {
    setFailure(null);
    mutation.mutate(!confirmed);
  };
  return {
    confirmed: mutation.isPending && mutation.variables !== undefined ? mutation.variables : confirmed,
    saving: mutation.isPending,
    error: failure?.id === id ? failure.message : null,
    toggle,
  };
};
