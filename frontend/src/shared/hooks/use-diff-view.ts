// 差分の表示の時点と、項目ごとの印を返す。前回開いた時点は `sessionStorage` に持つ（インターフェース定義『SPAを開く』の制約「「前回開いてから」の範囲」）
import { useEffect, useState } from "react";

import { postOpened } from "@/shared/api/generated/preview";
import { resolveDiffPoint, type DiffPoint, type OpenedPoint } from "@/shared/core/diff";
import { useRecords } from "@/shared/hooks/use-records";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { usePrefs } from "@/shared/stores/prefs-store";

/** そのタブの「前回開いてから」の始まりを残す sessionStorage のキー（今の画面と同じ） */
export const OPENED_SESSION_KEY = "mindmap-preview-opened";

/** 差分の表示 */
export type DiffView = {
  point: DiffPoint | null;
  /** 前回開いた時点。読めていなければ null */
  since: OpenedPoint | null;
};

const isOpenedPoint = (value: unknown): value is OpenedPoint => {
  if (typeof value !== "object" || value === null) return false;
  const { at, seq } = value as Partial<OpenedPoint>;
  return typeof at === "string" && typeof seq === "number" && Number.isInteger(seq) && seq >= 0;
};

const readStored = (): OpenedPoint | null => {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(OPENED_SESSION_KEY) ?? "null");
    return isOpenedPoint(value) ? value : null;
  } catch {
    return null;
  }
};

/** タブで 1 度だけ `POST /api/opened` を呼ぶ */
let opening: Promise<OpenedPoint | null> | null = null;
const openOnce = (): Promise<OpenedPoint | null> => {
  opening ??= postOpened()
    .then((reply) => {
      const body = reply.data;
      const point = isOpenedPoint(body.previous) ? body.previous : body.opened;
      sessionStorage.setItem(OPENED_SESSION_KEY, JSON.stringify(point));
      return point;
    })
    .catch(() => null)
    .finally(() => {
      opening = null;
    });
  return opening;
};

export const useDiffView = (): DiffView => {
  const { search, setDiff } = usePreviewSearch();
  const { rawIndex } = useRecords();
  const [since, setSince] = useState<OpenedPoint | null>(readStored);
  useEffect(() => {
    if (since !== null) return;
    let alive = true;
    void openOnce().then((point) => {
      if (alive) setSince(point);
    });
    return () => {
      alive = false;
    };
  }, [since]);
  const saved = usePrefs().diffSel ?? null;
  const sel = search.diff ?? saved;
  const fallback: OpenedPoint = since ?? { at: rawIndex?.data.built_at ?? "", seq: rawIndex?.data.changes.sets[0]?.until_seq ?? 0 };
  const point = rawIndex === null ? null : resolveDiffPoint(rawIndex.data.changes, sel, fallback);
  // 端末の時点で差分を出せたときは、その時点を URL に書く
  useEffect(() => {
    if (search.diff === undefined && point !== null) setDiff(point.sel);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setDiff は描画ごとに作り直される
  }, [search.diff, point?.sel]);
  return { point, since };
};
