// 画面の絞り込みの条件とタグの組み合わせ方を、URL とそのタブの保存領域で持つ（インターフェース定義『SPAを開く』の制約「保存した絞り込みの条件」）
import { useEffect, useRef } from "react";

import { defaultFilters, filtersFromSearch, filtersToSearch, TAG_FILTER_KEY, type Filters, type TagMatch } from "@/shared/core/filters";
import type { PreviewTab } from "@/shared/core/preview-search";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { readScreenState, useScreenState, writeScreenState } from "@/shared/stores/screen-state-store";

/** 絞り込みを持たない画面 */
const FILTERLESS_TABS: readonly PreviewTab[] = ["overview", "settings"];

/** 画面の絞り込みの条件・タグの組み合わせ方と操作 */
export type ScreenFilters = {
  filters: Filters;
  tagMatch: TagMatch;
  setFilters: (filters: Filters) => void;
  setTagMatch: (tagMatch: TagMatch) => void;
  /** タグを条件に加えて履歴に積む（既にあれば何もしない）。絞り込みを持たない画面では `kindTab` の画面へ移って加える */
  addTag: (tag: string, kindTab?: PreviewTab) => void;
};

export const useScreenFilters = (tab: PreviewTab): ScreenFilters => {
  const { search, setFilters: writeSearch, pushFilters, setTagMatch: writeTagMatch, openList } = usePreviewSearch();
  const filterless = FILTERLESS_TABS.includes(tab);
  const inUrl = Object.keys(search.f).length > 0;
  const state = useScreenState();
  const saved = state.filters?.[tab];
  const savedTagMatch = state.tagMatch?.[tab] ?? "all";
  const filters = inUrl ? filtersFromSearch(search.f) : (saved ?? defaultFilters(tab));
  // URL に条件がある: URL の組み合わせ方（無ければ all）。無い: 保存した組み合わせ方
  const tagMatch: TagMatch = inUrl ? (search.tagmatch ?? "all") : savedTagMatch;
  // 保存した条件を URL に戻し終えた画面（画面へ入ったときに 1 度だけ戻す）
  const entered = useRef<PreviewTab | null>(null);
  // URL と、そのタブの保存領域（ブラウザの sessionStorage）を同期する
  useEffect(() => {
    if (filterless) return;
    const current = readScreenState();
    const entering = entered.current !== tab;
    entered.current = tab;
    if (inUrl) {
      // URL に条件がある: 保存領域を URL に合わせる
      writeScreenState({
        filters: { ...current.filters, [tab]: filtersFromSearch(search.f) },
        tagMatch: { ...current.tagMatch, [tab]: search.tagmatch ?? "all" },
      });
    } else if (entering && saved !== undefined && Object.keys(saved).length > 0) {
      // 画面へ入ったときに URL に無く保存した条件がある: 条件と組み合わせ方を 1 回の移動で URL に記載する
      writeSearch(filtersToSearch(saved), { tagmatch: savedTagMatch === "any" ? "any" : undefined });
    } else if (!entering && saved !== undefined) {
      // 同じ画面で URL の条件が無くなった（戻る・進む）: 保存した条件を除き、画面の既定の条件に戻す
      writeScreenState({
        filters: Object.fromEntries(Object.entries(current.filters ?? {}).filter(([name]) => name !== tab)),
        tagMatch: Object.fromEntries(Object.entries(current.tagMatch ?? {}).filter(([name]) => name !== tab)),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- writeSearch は描画ごとに作り直される
  }, [tab, inUrl, JSON.stringify(search.f), search.tagmatch]);
  return {
    filters,
    tagMatch,
    setFilters: (next) => {
      writeScreenState({ filters: { ...readScreenState().filters, [tab]: next } });
      writeSearch(filtersToSearch(next));
    },
    setTagMatch: (next) => {
      writeScreenState({ tagMatch: { ...readScreenState().tagMatch, [tab]: next } });
      writeTagMatch(next === "any" ? "any" : undefined);
    },
    addTag: (tag, kindTab) => {
      // 絞り込みを持たない画面: 項目の種類の画面へ移ってタグで絞る
      if (filterless) {
        if (kindTab !== undefined) openList(kindTab, { f: { [TAG_FILTER_KEY]: tag } });
        return;
      }
      const tags = filters[TAG_FILTER_KEY] ?? [];
      if (tags.includes(tag)) return;
      pushFilters(filtersToSearch({ ...filters, [TAG_FILTER_KEY]: [...tags, tag] }));
    },
  };
};
