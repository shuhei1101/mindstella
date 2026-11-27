// 差分の表示の時点と、項目ごとの印を返す。まとまりを開いたら既読にする（インターフェース定義『プレビューを開く』の制約「既読のまとまり」）
import { useEffect } from "react";

import { isEmbedded } from "@/shared/core/embedded";
import { resolveDiffPoint, type DiffPoint } from "@/shared/core/diff";
import { workspaceIdOf } from "@/shared/core/workspace-path";
import { useRecords } from "@/shared/hooks/use-records";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { markRead } from "@/shared/stores/read-changes-store";
import { useScreenState } from "@/shared/stores/screen-state-store";

/** 差分の表示 */
export type DiffView = {
  point: DiffPoint | null;
};

export const useDiffView = (): DiffView => {
  const { search, setDiff } = usePreviewSearch();
  const { rawIndex } = useRecords();
  const saved = useScreenState().diffSel ?? null;
  const sel = search.diff ?? saved;
  const changes = rawIndex?.data.changes ?? null;
  const point = changes === null ? null : resolveDiffPoint(changes, sel);
  // 開いたのがまとまりなら既読にする（まだまとめていない変更は数えない。配る書き出しでは既読にしない）
  const openedSet = point !== null && changes !== null && changes.sets.some((set) => set.id === point.sel) ? point.sel : null;
  useEffect(() => {
    if (openedSet !== null && !isEmbedded()) markRead(workspaceIdOf(), [openedSet]);
  }, [openedSet]);
  // 端末の時点で差分を出せたときはその時点を URL に書き、解決できない時点は URL から外す
  const unresolved = changes !== null && search.diff !== undefined && point === null;
  useEffect(() => {
    if (search.diff === undefined && point !== null) setDiff(point.sel);
    if (unresolved) setDiff(undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setDiff は描画ごとに作り直される
  }, [search.diff, point?.sel, unresolved]);
  return { point };
};
