// search の読み書き。履歴に積むかをインターフェース定義『SPAを開く』の制約「履歴」のとおりに分ける
import { getRouteApi, useRouter, useRouterState, type HistoryState } from "@tanstack/react-router";

import type { PreviewSearch, PreviewTab } from "@/shared/core/preview-search";

const route = getRouteApi("/");

/** 詳細パネルと全画面の中で見てきた項目と、今の位置。その履歴の項目の `history.state` に持つ。`seqs` は各位置の項目を開いた履歴の行の連番 */
export type DetailTrail = { items: string[]; position: number; seqs?: number[] };

const EMPTY_TRAIL: DetailTrail = { items: [], position: -1, seqs: [] };

declare module "@tanstack/react-router" {
  // 宣言のマージで history.state の型を足すには interface が要る
  // eslint-disable-next-line @typescript-eslint/consistent-type-definitions
  interface HistoryState {
    trail?: DetailTrail;
    /** 一覧（表・ボード・カード）から開いた項目か */
    fromList?: boolean;
    /** 履歴の行の連番。積むたびに 1 増やし、置き換えでは変えない */
    seq?: number;
  }
}

/** search の変更 */
type Patch = Partial<PreviewSearch>;

/** 音声入力の入力欄の画面（詳細パネル・詳細の全画面の項目か、コメントの一覧のスレッドか新規スレッド） */
export type VoiceTarget = { item: string; full: boolean } | { thread: string | null } | { review: true };

/** search と操作 */
export type PreviewSearchApi = {
  search: PreviewSearch;
  /** 見てきた項目の向きに項目があるか（`history.state` の `trail` から決める） */
  canBack: boolean;
  canForward: boolean;
  /** 今の履歴の行が一覧から開いた項目か */
  fromList: boolean;
  /** 項目を開く・移る（履歴に積む）。一覧から開くときは `fromList` を渡す */
  openItem: (id: string, options?: { fromList: boolean }) => void;
  /** 一覧の並びの前後の項目を開く（履歴に積む） */
  openSibling: (id: string) => void;
  /** 詳細の履歴の 1 つ前・後の項目へ戻る・進む（間の絞り込み・並べ替えの履歴を飛ばし、今の条件と画面を残す） */
  backItem: () => void;
  forwardItem: () => void;
  /** 詳細を閉じる（置き換える） */
  closeItem: () => void;
  /** 画面を移る（置き換える）。`id`・`diff` を残し、`view`・`f.{列}`・`sort` を外す */
  setTab: (tab: PreviewTab) => void;
  setView: (view: PreviewSearch["view"]) => void;
  setFull: (full: boolean) => void;
  setHeading: (h: string | undefined) => void;
  /** 絞り込みの条件を書き換える（置き換える）。`tagmatch` を指定すると組み合わせ方も同じ移動で書き換える */
  setFilters: (f: Record<string, string>, options?: { tagmatch: PreviewSearch["tagmatch"] }) => void;
  /** 絞り込みの条件を変えて履歴に積む */
  pushFilters: (f: Record<string, string>) => void;
  /** タグの組み合わせ方を書き換える（置き換える）。`all` は `tagmatch` を外す */
  setTagMatch: (tagmatch: PreviewSearch["tagmatch"]) => void;
  /** タグの条件の式 `tx` を書き換えて履歴に積む（タグを押して絞り込むとき） */
  pushTagExpr: (tx: string) => void;
  /** タグの条件（`f.tags`・`tagmatch`・`tx`）をまとめて書き換える（置き換える） */
  setTagCondition: (patch: { f: Record<string, string>; tagmatch: PreviewSearch["tagmatch"]; tx: string | undefined }) => void;
  /** タグの条件（`f.tags`・`tagmatch`・`tx`）をまとめて書き換えて履歴に積む（ドロワーで変えるとき） */
  pushTagCondition: (patch: { f: Record<string, string>; tagmatch: PreviewSearch["tagmatch"]; tx: string | undefined }) => void;
  /** タグの組み合わせ方を書き換えて履歴に積む（ドロワーで変えるとき）。`all` は `tagmatch` を外す */
  pushTagMatch: (tagmatch: PreviewSearch["tagmatch"]) => void;
  /** 表の並べ替えを変えて履歴に積む。`replace` を渡すと置き換える（列が無くなった並びの解除・初期設定に戻すとき） */
  setSort: (sort: string | undefined, options?: { replace: boolean }) => void;
  setDiff: (diff: string | undefined) => void;
  /** 左のパネルを開閉する（置き換える）。コメントの一覧でないときは `thread`・`review`・`tstatus`・`ttag`・`ttarget` を外す */
  setPanel: (panel: PreviewSearch["panel"]) => void;
  /** コメントの一覧の中の画面と絞り込みを移る（置き換える） */
  setComments: (patch: Pick<Patch, "thread" | "review" | "tstatus" | "ttag" | "ttarget">) => void;
  /** コメントの一覧を項目で絞ったスレッドの一覧で開く（置き換える）。開いたままなら `tstatus`・`ttag` を残す */
  openItemComments: (id: string) => void;
  /** 別の画面の項目か一覧を開く（履歴に積む） */
  openList: (tab: PreviewTab, patch: Patch) => void;
  /** 記録に合わない値を外した search へ置き換える */
  replaceSearch: (search: PreviewSearch) => void;
  /** 音声入力の入力欄の画面を開く（項目を開くときは履歴に積み、パネルの中を移るときは置き換える） */
  openVoiceInput: (target: VoiceTarget) => void;
  /** コメントの一覧を開き、スレッドを渡せばそのスレッドを開く（履歴に積む） */
  openThread: (thread: string | null) => void;
  /** 全体の検索を開閉し、検索の言葉を書き換える（置き換える） */
  setSearch: (patch: Pick<Patch, "search" | "q">) => void;
  /** 全体の検索の結果の項目を、その種類の画面（`undefined` は概要）で開く。画面が今と違えば履歴に積み、同じなら置き換える。`diff` と左のパネルを残し、ほかの値を外す */
  openFromSearch: (tab: PreviewTab | undefined, id: string) => void;
};

export const usePreviewSearch = (): PreviewSearchApi => {
  const search = route.useSearch();
  const navigate = route.useNavigate();
  const router = useRouter();
  const location = useRouterState({ select: (state) => state.location.state });
  const seq = location.seq ?? 0;
  const trail: DetailTrail = location.trail ?? (search.id === undefined ? EMPTY_TRAIL : { items: [search.id], position: 0, seqs: [seq] });
  // 項目を変えない移動では、見てきた項目の履歴と一覧から開いたマーカーを引き継ぎ、積むときは連番を 1 増やす
  const keepTrail =
    (replace: boolean) =>
    (previous: HistoryState | undefined): HistoryState => ({
      ...previous,
      ...(previous?.trail === undefined ? {} : { trail: previous.trail }),
      seq: replace ? (previous?.seq ?? 0) : (previous?.seq ?? 0) + 1,
    });
  const apply = (patch: Patch, replace: boolean): void => {
    void navigate({ search: (previous) => ({ ...previous, ...patch }), replace, state: keepTrail(replace) });
  };
  // 詳細の履歴の位置を `delta` だけ動かし、移った後に今の画面と絞り込み・並べ替えで置き換える
  const goItem = (position: number): void => {
    const target = trail.seqs?.[position];
    if (target === undefined) return;
    const delta = target - seq;
    if (delta === 0) return;
    const keep: Patch = { tab: search.tab, view: search.view, f: search.f, tagmatch: search.tagmatch, tx: search.tx, sort: search.sort };
    const unsubscribe = router.history.subscribe(() => {
      unsubscribe();
      void navigate({ search: (previous) => ({ ...previous, ...keep }), replace: true, state: keepTrail(true) });
    });
    router.history.go(delta);
  };
  const openItem = (id: string, options?: { fromList: boolean }): void => {
    const nextSeq = seq + 1;
    const items = [...trail.items.slice(0, trail.position + 1), id];
    const seqs = [...(trail.seqs ?? []).slice(0, trail.position + 1), nextSeq];
    const next: DetailTrail = { items, position: trail.position + 1, seqs };
    // 戻った先で「進む」を押せるよう、今の履歴の項目にも次の項目を残す
    window.history.replaceState({ ...(window.history.state as object), trail: { items, position: trail.position, seqs } }, "");
    void navigate({ search: (previous) => ({ ...previous, id, full: search.full, h: undefined }), state: (previous) => ({ ...previous, trail: next, fromList: options?.fromList === true, seq: nextSeq }) });
  };
  return {
    search,
    canBack: trail.position > 0,
    canForward: trail.position < trail.items.length - 1,
    fromList: location.fromList === true,
    openItem,
    openSibling: (id) => {
      openItem(id, { fromList: true });
    },
    backItem: () => {
      goItem(trail.position - 1);
    },
    forwardItem: () => {
      goItem(trail.position + 1);
    },
    closeItem: () => {
      void navigate({ search: (previous) => ({ ...previous, id: undefined, full: undefined, h: undefined }), replace: true, state: (previous) => ({ ...previous, trail: EMPTY_TRAIL }) });
    },
    setTab: (tab) => {
      apply({ tab, view: undefined, f: {}, sort: undefined, tagmatch: undefined, tx: undefined }, true);
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
    setFilters: (f, options) => {
      apply(options === undefined ? { f } : { f, tagmatch: options.tagmatch }, true);
    },
    pushFilters: (f) => {
      apply({ f }, false);
    },
    pushTagExpr: (tx) => {
      apply({ tx }, false);
    },
    setTagCondition: (patch) => {
      apply(patch, true);
    },
    setTagMatch: (tagmatch) => {
      apply({ tagmatch }, true);
    },
    pushTagCondition: (patch) => {
      apply(patch, false);
    },
    pushTagMatch: (tagmatch) => {
      apply({ tagmatch }, false);
    },
    setSort: (sort, options) => {
      apply({ sort }, options?.replace === true);
    },
    setDiff: (diff) => {
      apply({ diff }, true);
    },
    setPanel: (panel) => {
      apply(panel === "comments" ? { panel } : { panel, thread: undefined, review: undefined, tstatus: undefined, ttag: undefined, ttarget: undefined }, true);
    },
    setComments: (patch) => {
      apply(patch, true);
    },
    openItemComments: (id) => {
      const keep = search.panel === "comments" ? {} : { tstatus: undefined, ttag: undefined };
      apply({ panel: "comments", ttarget: id, thread: undefined, review: undefined, ...keep }, true);
    },
    openList: (tab, patch) => {
      const next = patch.id === undefined ? EMPTY_TRAIL : { items: [patch.id], position: 0, seqs: [seq + 1] };
      void navigate({ search: { f: {}, tab, ...patch }, state: (previous) => ({ ...previous, trail: next, fromList: false, seq: seq + 1 }) });
    },
    replaceSearch: (next) => {
      void navigate({ search: next, replace: true, state: keepTrail(true) });
    },
    setSearch: (patch) => {
      apply(patch, true);
    },
    openThread: (thread) => {
      apply({ panel: "comments", thread: thread ?? undefined, review: undefined }, true);
    },
    openVoiceInput: (target) => {
      // 修正の入力をレビュー中の書き込みの画面で録音した
      if ("review" in target) {
        apply({ panel: "comments", thread: undefined, review: "1" }, true);
        return;
      }
      if ("thread" in target) {
        apply({ panel: "comments", thread: target.thread ?? undefined, review: undefined }, true);
        return;
      }
      const full = target.full ? "1" : undefined;
      if (search.id === target.item && search.full === full) {
        apply({ panel: undefined, thread: undefined, review: undefined, tstatus: undefined, ttag: undefined, ttarget: undefined }, true);
        return;
      }
      const items = [...trail.items.slice(0, trail.position + 1), target.item];
      void navigate({ search: (previous) => ({ ...previous, id: target.item, full, h: undefined, panel: undefined, thread: undefined, review: undefined, tstatus: undefined, ttag: undefined, ttarget: undefined }), state: (previous) => ({ ...previous, trail: { items, position: trail.position + 1, seqs: [...(trail.seqs ?? []).slice(0, trail.position + 1), seq + 1] }, fromList: false, seq: seq + 1 }) });
    },
    openFromSearch: (tab, id) => {
      const { diff, panel, thread, review, tstatus, ttag, ttarget } = search;
      const next: PreviewSearch = { f: {}, tab, id, diff, panel, thread, review, tstatus, ttag, ttarget };
      const same = (tab ?? "overview") === (search.tab ?? "overview");
      const nextSeq = same ? seq : seq + 1;
      void navigate({ search: next, replace: same, state: (previous) => ({ ...previous, trail: { items: [id], position: 0, seqs: [nextSeq] }, fromList: false, seq: nextSeq }) });
    },
  };
};
