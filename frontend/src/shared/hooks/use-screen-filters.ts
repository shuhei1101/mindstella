// 画面の絞り込みの条件を URL と端末の保存領域で持つ（インターフェース定義『SPAを開く』の制約「保存した絞り込みの条件」）
import { useEffect } from "react";

import { defaultFilters, filtersFromSearch, filtersToSearch, type Filters } from "@/shared/core/filters";
import type { PreviewTab } from "@/shared/core/preview-search";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { readPrefs, writePrefs } from "@/shared/stores/prefs-store";

/** 画面の絞り込みの条件と操作 */
export type ScreenFilters = {
  filters: Filters;
  setFilters: (filters: Filters) => void;
};

export const useScreenFilters = (tab: PreviewTab): ScreenFilters => {
  const { search, setFilters: writeSearch } = usePreviewSearch();
  const inUrl = Object.keys(search.f).length > 0;
  const saved = readPrefs().filters?.[tab];
  const filters = inUrl ? filtersFromSearch(search.f) : (saved ?? defaultFilters(tab));
  useEffect(() => {
    if (inUrl) {
      const all = readPrefs().filters ?? {};
      writePrefs({ filters: { ...all, [tab]: filtersFromSearch(search.f) } });
    } else if (saved !== undefined && Object.keys(saved).length > 0) {
      writeSearch(filtersToSearch(saved));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- writeSearch は描画ごとに作り直される
  }, [tab, inUrl, JSON.stringify(search.f)]);
  return {
    filters,
    setFilters: (next) => {
      writePrefs({ filters: { ...(readPrefs().filters ?? {}), [tab]: next } });
      writeSearch(filtersToSearch(next));
    },
  };
};
