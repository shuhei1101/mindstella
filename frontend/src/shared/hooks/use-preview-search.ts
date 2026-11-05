// search の読み書き。履歴に積むかをインターフェース定義『SPAを開く』の制約「履歴」のとおりに分ける
import { getRouteApi } from "@tanstack/react-router";

import type { PreviewSearch, PreviewTab } from "@/shared/core/preview-search";

const route = getRouteApi("/");

/** search の変更 */
type Patch = Partial<PreviewSearch>;

/** search と操作 */
export type PreviewSearchApi = {
  search: PreviewSearch;
  /** 項目を開く・移る（履歴に積む） */
  openItem: (id: string) => void;
  /** 詳細を閉じる（置き換える） */
  closeItem: () => void;
  /** 画面を移る（履歴に積む）。`id`・`diff` を残し、`view`・`f.{列}`・`sort` を外す */
  setTab: (tab: PreviewTab) => void;
  setView: (view: PreviewSearch["view"]) => void;
  setFull: (full: boolean) => void;
  setHeading: (h: string | undefined) => void;
  setFilters: (f: Record<string, string>) => void;
  setSort: (sort: string | undefined) => void;
  setDiff: (diff: string | undefined) => void;
  setPanel: (panel: PreviewSearch["panel"]) => void;
  /** 別の画面の項目か一覧を開く（履歴に積む） */
  openList: (tab: PreviewTab, patch: Patch) => void;
  /** 記録に合わない値を外した search へ置き換える */
  replaceSearch: (search: PreviewSearch) => void;
};

export const usePreviewSearch = (): PreviewSearchApi => {
  const search = route.useSearch();
  const navigate = route.useNavigate();
  const apply = (patch: Patch, replace: boolean): void => {
    void navigate({ search: (previous) => ({ ...previous, ...patch }), replace });
  };
  return {
    search,
    openItem: (id) => {
      apply({ id, full: search.full, h: undefined }, false);
    },
    closeItem: () => {
      apply({ id: undefined, full: undefined, h: undefined }, true);
    },
    setTab: (tab) => {
      apply({ tab, view: undefined, f: {}, sort: undefined }, false);
    },
    setView: (view) => {
      apply({ view }, true);
    },
    setFull: (full) => {
      apply({ full: full ? "1" : undefined }, true);
    },
    setHeading: (h) => {
      apply({ h }, true);
    },
    setFilters: (f) => {
      apply({ f }, true);
    },
    setSort: (sort) => {
      apply({ sort }, true);
    },
    setDiff: (diff) => {
      apply({ diff }, true);
    },
    setPanel: (panel) => {
      apply({ panel }, true);
    },
    openList: (tab, patch) => {
      void navigate({ search: { f: {}, tab, ...patch } });
    },
    replaceSearch: (next) => {
      void navigate({ search: next, replace: true });
    },
  };
};
