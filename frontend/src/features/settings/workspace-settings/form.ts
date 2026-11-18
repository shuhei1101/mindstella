// 設定の画面の入力の検証
import { z } from "zod";

/** 保持する回数は 1 以上の整数 */
export const HistoryLimitSchema = z.coerce.number().int().min(1);
