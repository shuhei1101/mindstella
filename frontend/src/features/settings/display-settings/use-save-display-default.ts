// ワークスペースの既定の書き換えの mutation
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { putConfigDisplay } from "@/shared/api/generated/preview";
import type { DisplayInput, DisplayReplyDisplay } from "@/shared/api/generated/model";
import { recordsQuery } from "@/shared/hooks/preview-queries";

/** 見た目と表示する種類をワークスペースの既定にし、記録を読み直す。書いた後の `display` を返す */
export const useSaveDisplayDefault = () => {
  const queryClient = useQueryClient();
  return useMutation<DisplayReplyDisplay, Error, DisplayInput>({
    mutationFn: async (input) => ((await putConfigDisplay(input)).data as { display: DisplayReplyDisplay }).display,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: recordsQuery().queryKey }),
  });
};
