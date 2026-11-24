// 画面から今のタグの条件の式をプリセットとして保存する（インターフェース定義『画面からのプリセットの作成』）
import { useCallback } from "react";

import { postPreset } from "@/shared/api/generated/preview";
import type { PresetSaveResult } from "@/shared/components/preset-save";
import { AppError } from "@/shared/core/app-error";
import type { PresetFilter } from "@/shared/core/presets";

/** 問題の応答の `detail` をそのまま出すステータス */
const DETAIL_STATUSES = new Set([400, 409, 422]);

const NO_TAG_CONDITION = "タグの条件を選ぶと、プリセットとして保存できます。";
const SAVE_FAILED = "保存できませんでした。もう一度お試しください。";

/** 名前を受けて今のタグの条件の式を保存する関数を返す */
export const usePresetSave = (tagExpr: PresetFilter | null): ((name: string) => Promise<PresetSaveResult>) =>
  useCallback(
    async (name: string): Promise<PresetSaveResult> => {
      if (tagExpr === null) return { error: NO_TAG_CONDITION };
      try {
        await postPreset({ name, filter: tagExpr });
        return { error: null };
      } catch (error) {
        if (error instanceof AppError && DETAIL_STATUSES.has(error.statusCode)) return { error: error.message };
        return { error: SAVE_FAILED };
      }
    },
    [tagExpr],
  );
