// 画面のテストが使う記録の差し替え
import { http, HttpResponse } from "msw";

import { RECORDS } from "@/testing/msw/handlers";
import { server } from "@/testing/msw/server";

/** 記録の一部を差し替えて返す */
export const useRecords = (patch: Record<string, unknown>): void => {
  server.use(http.get("/api/records", () => HttpResponse.json({ ...RECORDS, ...patch })));
};

/** 保存待ちの編集を返す */
export const useEdits = (items: unknown[]): void => {
  server.use(http.get("/api/edits", () => HttpResponse.json({ items, count: items.length })));
};
