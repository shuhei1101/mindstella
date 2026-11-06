// 表示する種類（端末の上書き、無ければワークスペースの既定、それも無ければ全ての種類）
import { useQuery } from "@tanstack/react-query";

import { KIND_KEYS, type Kind } from "@/shared/core/records";
import { recordsQuery } from "@/shared/hooks/preview-queries";
import { usePrefs } from "@/shared/stores/prefs-store";

export const useVisibleKinds = (): Set<Kind> => {
  const records = useQuery(recordsQuery());
  const { kinds } = usePrefs();
  if (Array.isArray(kinds)) return new Set(KIND_KEYS.filter((kind) => kinds.includes(kind)));
  const data = records.data?.status === 200 ? records.data.data : undefined;
  return new Set(data?.settings.display?.visible_kinds ?? KIND_KEYS);
};
