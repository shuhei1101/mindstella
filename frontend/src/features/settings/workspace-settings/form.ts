// 設定の画面の入力の検証
import { z } from "zod";

import type { RecordIndex } from "@/shared/core/records";

/** 保持する回数は 1 以上の整数 */
export const HistoryLimitSchema = z.coerce.number().int().min(1);

/** 使っている件数を数える設定のキー */
export type UsedSettingKey = "phases" | "targets" | "categories";

/** フェーズ・対象・カテゴリーの 1 つの値を持つ項目の件数 */
export const usageCount = (index: RecordIndex, key: UsedSettingKey, value: string): number => {
  let count = 0;
  for (const { item } of index.byId.values()) {
    if (key === "phases" && item.phase === value) count += 1;
    if (key === "targets" && item.target === value) count += 1;
    if (key === "categories" && item.category === value) count += 1;
  }
  if (key === "targets") count += index.data.settings.categories.filter((category) => category.target === value).length;
  return count;
};
