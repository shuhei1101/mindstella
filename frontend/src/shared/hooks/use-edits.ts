// 保存待ちの編集を溜める・取り消す・まとめて保存する mutation
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { addEdit, cancelEdit, saveEdits } from "@/shared/api/generated/preview";
import type { EditInput } from "@/shared/api/generated/model";
import { AppError } from "@/shared/core/app-error";
import type { BlockedEdit } from "@/shared/core/edits";
import { editsQuery, invalidatePreview } from "@/shared/hooks/preview-queries";

/** 編集を溜め、保存待ちの編集を読み直す */
export const useAddEdit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EditInput) => addEdit(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: editsQuery().queryKey }),
  });
};

/** 編集を取り消し、保存待ちの編集を読み直す */
export const useCancelEdit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => cancelEdit(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: editsQuery().queryKey }),
  });
};

/** まとめて保存した結果。書き込めない編集があれば `blocked` を返す */
export type SaveOutcome = { blocked: BlockedEdit[] };

/** まとめて保存する。409 の `blocked` は結果として返す */
export const useSaveEdits = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<SaveOutcome> => {
      try {
        await saveEdits();
        await invalidatePreview(queryClient);
        return { blocked: [] };
      } catch (error) {
        if (error instanceof AppError && error.statusCode === 409) {
          return { blocked: (error.body as { blocked?: BlockedEdit[] }).blocked ?? [] };
        }
        throw error;
      }
    },
  });
};
