import type { QueryClient } from "@tanstack/react-query";

import { getGetRecordsQueryKey } from "@/shared/api/generated/preview";

// 書き換えの知らせ（Server-Sent Events）を受けたら記録の query を読み直す
export const subscribeEvents = (queryClient: QueryClient): (() => void) => {
  const source = new EventSource("/api/events");
  source.addEventListener("changed", () => {
    void queryClient.invalidateQueries({ queryKey: getGetRecordsQueryKey() });
  });
  return () => {
    source.close();
  };
};
