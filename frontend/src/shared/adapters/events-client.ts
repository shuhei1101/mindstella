// 書き換えの知らせ（インターフェース定義『書き換えの知らせ』）へつなぎ、記録の query を読み直す
import type { QueryClient } from "@tanstack/react-query";

import { useConnectionStore } from "@/shared/stores/connection-store";
import { useDuplicateIdsStore } from "@/shared/stores/duplicate-ids-store";

/** 書き換えの知らせのパス */
export const EVENTS_URL = "/api/events";

/** 書き換えで読み直す query の頭（生成した queryKey の先頭の要素） */
const RECORD_QUERY_KEYS = ["/api/records", "/api/comments", "/api/edits", "/api/threads"] as const;

/** `duplicate_ids` の `data`（ID の JSON の配列）を読む。読めなければ null */
const parseDuplicateIds = (data: unknown): string[] | null => {
  if (typeof data !== "string") return null;
  try {
    const value: unknown = JSON.parse(data);
    return Array.isArray(value) && value.every((entry) => typeof entry === "string") ? value : null;
  } catch {
    return null;
  }
};

/** `EVENTS_URL` へつなぎ、`changed` で記録の query を読み直し、`duplicate_ids` で重なった ID を、接続の状態を書き換える。つなぎ直しは EventSource に任せ、閉じる関数を返す */
export const connectEvents = (queryClient: QueryClient): (() => void) => {
  const source = new EventSource(EVENTS_URL);
  const { setConnection } = useConnectionStore.getState();
  const invalidateAll = (): void => {
    for (const key of RECORD_QUERY_KEYS) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  };
  source.addEventListener("open", () => {
    setConnection("online");
    // 切れている間の書き換えを拾う
    void queryClient.invalidateQueries({ queryKey: ["/api/records"] });
  });
  source.addEventListener("changed", invalidateAll);
  source.addEventListener("duplicate_ids", (event) => {
    const ids = parseDuplicateIds((event as MessageEvent<unknown>).data);
    // 読めない知らせは捨てる（次の知らせで描き直す）
    if (ids !== null) useDuplicateIdsStore.getState().setIds(ids);
  });
  source.addEventListener("error", () => {
    // 前に読んだ記録の query は残し、トップバーに切れたことを出す
    setConnection("offline");
  });
  return () => {
    source.close();
  };
};
