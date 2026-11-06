// 一覧の画面の編集の入口。差分の表示の間は渡さない
import { useMemo } from "react";

import { NEW_ID_PREFIX, pendingMarkOf, type PendingMarkKind, type ScreenEdit } from "@/shared/core/edits";
import type { Item, Kind } from "@/shared/core/records";
import { useRecords } from "@/shared/hooks/use-records";

const NO_BLOCKED: ReadonlySet<string> = new Set();

export const useScreenEdit = (kind: Kind, diffActive: boolean, onAdd: () => void): ScreenEdit | null => {
  const { index, edits } = useRecords();
  return useMemo(() => {
    if (diffActive || index === null) return null;
    const items: Item[] = index.data[kind];
    const marks: Record<string, PendingMarkKind> = {};
    for (const item of items) {
      const mark = pendingMarkOf({ edits, blocked: NO_BLOCKED, target: item.id });
      if (mark !== null) marks[item.id] = mark;
    }
    return { marks, adds: items.filter((item) => item.id.startsWith(NEW_ID_PREFIX)), onAdd };
  }, [diffActive, index, kind, edits, onAdd]);
};
