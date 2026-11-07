// search の読み書き。履歴に積むかをインターフェース定義『SPAを開く』の制約「履歴」のとおりに分ける
import { getRouteApi, useRouterState, type HistoryState } from "@tanstack/react-router";

import type { PreviewSearch, PreviewTab } from "@/shared/core/preview-search";

const route = getRouteApi("/");

/** 詳細パネルと全画面の中で見てきた項目と、今の位置。その履歴の項目の `history.state` に持つ */
export type DetailTrail = { items: string[]; position: number };

const EMPTY_TRAIL: DetailTrail = { items: [], position: -1 };

declare module "@tanstack/react-router" {
  // 宣言のマージで history.state の型を足すには interface が要る
  // eslint-disable-next-line @typescript-eslint/consistent-type-definitions
  interface HistoryState {
    trail?: DetailTrail;
  }
}

/** search の変更 */
type Patch = Partial<PreviewSearch>;

/** search と操作 */
export type PreviewSearchApi = {
  search: PreviewSearch;
  /** 見てきた項目の向きに項目があるか（`history.state` の `trail` から決める） */
  canBack: boolean;
  canForward: boolean;
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
  /** 左のパネルを開閉する（置き換える）。コメントの一覧でないときは `thread`・`review`・`tstatus`・`ttag` を外す */
  setPanel: (panel: PreviewSearch["panel"]) => void;
  /** コメントの一覧の中の画面と絞り込みを移る（置き換える） */
  setComments: (patch: Pick<Patch, "thread" | "review" | "tstatus" | "ttag">) => void;
  /** 別の画面の項目か一覧を開く（履歴に積む） */
  openList: (tab: PreviewTab, patch: Patch) => void;
  /** 記録に合わない値を外した search へ置き換える */
  replaceSearch: (search: PreviewSearch) => void;
};

export const usePreviewSearch = (): PreviewSearchApi => {
  const search = route.useSearch();
  const navigate = route.useNavigate();
  const location = useRouterState({ select: (state) => state.location.state });
  const trail: DetailTrail = location.trail ?? (search.id === undefined ? EMPTY_TRAIL : { items: [search.id], position: 0 });
  // 項目を変えない移動では、見てきた項目の履歴を引き継ぐ
  const keepTrail = (previous: HistoryState | undefined): HistoryState => ({ ...previous, ...(previous?.trail === undefined ? {} : { trail: previous.trail }) });
  const apply = (patch: Patch, replace: boolean): void => {
    void navigate({ search: (previous) => ({ ...previous, ...patch }), replace, state: keepTrail });
  };
  return {
    search,
    canBack: trail.position > 0,
    canForward: trail.position < trail.items.length - 1,
    openItem: (id) => {
      const items = [...trail.items.slice(0, trail.position + 1), id];
      const next: DetailTrail = { items, position: trail.position + 1 };
      // 戻った先で「進む」を押せるよう、今の履歴の項目にも次の項目を残す
      window.history.replaceState({ ...(window.history.state as object), trail: { items, position: trail.position } }, "");
      void navigate({ search: (previous) => ({ ...previous, id, full: search.full, h: undefined }), state: (previous) => ({ ...previous, trail: next }) });
    },
    closeItem: () => {
      void navigate({ search: (previous) => ({ ...previous, id: undefined, full: undefined, h: undefined }), replace: true, state: (previous) => ({ ...previous, trail: EMPTY_TRAIL }) });
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
      apply(panel === "comments" ? { panel } : { panel, thread: undefined, review: undefined, tstatus: undefined, ttag: undefined }, true);
    },
    setComments: (patch) => {
      apply(patch, true);
    },
    openList: (tab, patch) => {
      const next = patch.id === undefined ? EMPTY_TRAIL : { items: [patch.id], position: 0 };
      void navigate({ search: { f: {}, tab, ...patch }, state: (previous) => ({ ...previous, trail: next }) });
    },
    replaceSearch: (next) => {
      void navigate({ search: next, replace: true, state: keepTrail });
    },
  };
};
