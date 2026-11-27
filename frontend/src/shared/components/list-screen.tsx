// 一覧の画面の枠。表示形式の切り替え・項目の追加・削除した項目の帯・絞り込みのドロワーと、表の状態を持つ
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useEffectEvent, useLayoutEffect, useMemo, useRef, useState, type ComponentProps, type ReactNode, type RefCallback } from "react";

import { CardSort, cardSortFromParam, cardSortToParam, cardSortToRowSort, INITIAL_CARD_SORT, isCardSortParam, sortItems } from "@/shared/components/card-sort";
import type { DiffMarks } from "@/shared/components/diff-mark";
import { favoriteColumn } from "@/shared/components/list-columns";
import { FilterChips } from "@/shared/components/filter-chips";
import { FilterDrawer, type FilterGroup } from "@/shared/components/filter-drawer";
import { Icon } from "@/shared/components/icon";
import type { PresetSaveProps, PresetSaveResult } from "@/shared/components/preset-save";
import { RemovedBand } from "@/shared/components/removed-band";
import { Table, type Row, type TableColumn } from "@/shared/components/table";
import { Button } from "@/shared/components/ui/button";
import { ViewSwitch, type View } from "@/shared/components/view-switch";
import { removedOf } from "@/shared/core/diff";
import { favoritesFirst, favoritesOnly } from "@/shared/core/favorites";
import { NEW_ID_PREFIX, type ScreenEdit } from "@/shared/core/edits";
import { isEmbedded } from "@/shared/core/embedded";
import { TAG_FILTER_KEY, TEXT_FILTER_PREFIX, withoutKey, type Filters, type TagMatch } from "@/shared/core/filters";
import { drawerGroups, filterRows, nextSort, sortRows, type ListColumn } from "@/shared/core/list-rows";
import { describeTagExpr, matchesTagExpr, presetChoicesOf, simpleTagsOf } from "@/shared/core/presets";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { KIND_LABEL, tagNames, type Item, type Kind, type RecordIndex } from "@/shared/core/records";
import { commentsQuery } from "@/shared/hooks/preview-queries";
import { useDiffView } from "@/shared/hooks/use-diff-view";
import { useFavorites } from "@/shared/hooks/use-favorites";
import { useListScroll } from "@/shared/hooks/use-list-scroll";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecordLookup } from "@/shared/hooks/use-record-lookup";
import { useRecords } from "@/shared/hooks/use-records";
import { useScreenEdit } from "@/shared/hooks/use-screen-edit";
import { usePresetSave } from "@/shared/hooks/use-preset-save";
import { useScreenFilters } from "@/shared/hooks/use-screen-filters";
import { useEditSessionStore } from "@/shared/stores/edit-session-store";
import { useFilterCandidatesStore } from "@/shared/stores/filter-candidates-store";
import { useListOrderStore } from "@/shared/stores/list-order-store";
import { readPrefs, writePrefs } from "@/shared/stores/prefs-store";

/** 画面の枠が中身に渡す値 */
export type ListContext = {
  index: RecordIndex;
  /** タイトルの中の ID から記録の項目・スレッドを検索する（部品『記録の文字』の `lookup`） */
  lookup: LookupRecordId;
  view: View;
  shown: Item[];
  filters: Filters;
  tagMatch: TagMatch;
  marks: DiffMarks | undefined;
  comments: Record<string, number>;
  edit: ScreenEdit | null;
  /** 一覧から項目を開く（一覧の並びの前後で移れるように、一覧から開いたマーカーを付ける） */
  onOpen: (id: string) => void;
  /** カード・ボードの並び（`sortRows` の `sort`）。`shown` はこの順 */
  sort: string;
  onOpenAdded: (id: string) => void;
  selectedId: string | undefined;
  /** 押したタグを画面の絞り込みに加える */
  onSelectTag: (name: string) => void;
  /** 一覧のスクロール領域に付ける ref（スクロール位置の復元） */
  scrollRef: RefCallback<HTMLElement>;
  /** 表（並べ替え・列の表示・固定は URL と端末の保存領域で持つ） */
  table: ReactNode;
  /** お気に入りに登録した項目の ID */
  favorites: ReadonlySet<string>;
  /** カードの一覧でお気に入りを先頭に並べるか（`shown` は並べた後の順） */
  favoritesFirst: boolean;
  /** 項目をお気に入りに登録・解除する */
  onToggleFavorite: (id: string) => void;
};

export type ListScreenProps = {
  kind: Kind;
  views: { key: View; label: string }[] | null;
  columnsOf: (index: RecordIndex, onOpen: (id: string) => void) => TableColumn[];
  drawerOpen: boolean;
  onCloseDrawer: () => void;
  /** 表の他の表示形式の中身 */
  content?: (context: ListContext) => ReactNode;
};

const asColumns = (columns: TableColumn[]): ListColumn<Row>[] => columns.map((column) => ({ key: column.key, label: column.label, get: column.get ?? ((row) => row[column.key]), ...(column.order === undefined ? {} : { order: column.order }) }));

/** タグのほかに条件（状態・種類・列の文字）があるか */
const hasOtherConditions = (filters: Filters): boolean => Object.entries(filters).some(([key, values]) => key !== TAG_FILTER_KEY && values.length > 0);

/** ドロワーのプリセットの保存。配る書き出しでは出さない */
const presetSaveOf = (filters: Filters, onSave: (name: string) => Promise<PresetSaveResult>): { presetSave?: Omit<PresetSaveProps, "hasTagCondition"> } =>
  isEmbedded() ? {} : { presetSave: { hasOtherConditions: hasOtherConditions(filters), onSave } };

/** 値を条件に加えて履歴に積む。既にあれば何もしない。タグは押したタグと同じ加え方にする */
const addValue = ({ filters, key, value, setFilters, addTag }: { filters: Filters; key: string; value: string; setFilters: (next: Filters, options: { push: boolean }) => void; addTag: (tag: string) => void }): void => {
  if (key === TAG_FILTER_KEY) {
    addTag(value);
    return;
  }
  const current = filters[key] ?? [];
  if (!current.includes(value)) setFilters({ ...filters, [key]: [...current, value] }, { push: true });
};

/** 描いている間、絞り込みの値と値を加える処理を全体の検索へ渡す。中身が変わったときだけ登録し直す */
const PublishCandidates = ({ groups, apply }: { groups: readonly FilterGroup[]; apply: (key: string, value: string) => void }) => {
  const latest = useRef(apply);
  useLayoutEffect(() => {
    latest.current = apply;
  });
  const publish = useEffectEvent(() => {
    useFilterCandidatesStore.getState().publish(groups, (key, value) => { latest.current(key, value); });
  });
  const signature = JSON.stringify(groups);
  useEffect(() => {
    publish();
    return useFilterCandidatesStore.getState().clear;
  }, [signature]);
  return null;
};

/** 描いた並びを一覧の並びとして置き換え、画面を離れたら空にする */
const PublishOrders = ({ orders }: { orders: readonly (readonly string[])[] }) => {
  const signature = JSON.stringify(orders);
  const publish = useEffectEvent(() => {
    useListOrderStore.getState().setOrders(orders);
  });
  useEffect(() => {
    publish();
  }, [signature]);
  useEffect(() => useListOrderStore.getState().clear, []);
  return null;
};

/** ボードの並び。項目を状態ごとにまとめ、まとめの中は渡した順 */
const boardOrders = (items: readonly Item[]): string[][] => {
  const byStatus = new Map<string, string[]>();
  for (const item of items) {
    const key = item.status ?? "";
    byStatus.set(key, [...(byStatus.get(key) ?? []), item.id]);
  }
  return [...byStatus.values()];
};

/** 「お気に入りだけを表示する」がオンならお気に入りの行だけにする */
const onlyFavoritesIfSet = <T extends { id: string }>(rows: T[], favorites: { ids: ReadonlySet<string>; only: boolean }): T[] => (favorites.only ? favoritesOnly(rows, favorites.ids) : rows);

/** 「お気に入りだけを表示する」の間だけ、絞り込みのチップに「お気に入りのみ」を出す引数 */
const favoritesChipOf = (favorites: { only: boolean; clearOnly: () => void }): { onClearFavoritesOnly?: () => void } => (favorites.only ? { onClearFavoritesOnly: favorites.clearOnly } : {});

/** カード・ボードの表示で受け付けない `sort`（表の列の並べ替え）は、無いものとして URL から外す（置き換える） */
const useDropCardSort = ({ view, sort, setSort }: { view: View; sort: string | undefined; setSort: (sort: string | undefined, options: { replace: boolean }) => void }): void => {
  useEffect(() => {
    if (view !== "table" && sort !== undefined && !isCardSortParam(sort)) setSort(undefined, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 表示形式と並べ替えが変わったときだけ確かめる
  }, [view, sort]);
};

/** カード・ボードの表示のときだけ「並べ替え」を出す */
const CardSortControl = ({ shown, ...props }: { shown: boolean } & ComponentProps<typeof CardSort>) => (shown ? <CardSort {...props} /> : null);

/** カード・ボードの「並べ替え」の並び（資料は更新日時の新しい順、ほかは連番が既定）と、詳細の一覧の並びの前後に使う描いた並び */
const listOrders = ({ kind, view, sort, filtered, sorted, favorites }: { kind: Kind; view: View; sort: string | undefined; filtered: Item[]; sorted: Row[]; favorites: { ids: ReadonlySet<string>; first: boolean } }) => {
  const initialCardSort = kind === "docs" ? INITIAL_CARD_SORT.docs : INITIAL_CARD_SORT.other;
  const cardSort = cardSortFromParam(sort, initialCardSort);
  const cardRowSort = cardSortToRowSort(cardSort);
  const sortedCards = view === "table" ? [] : sortItems(filtered, cardRowSort);
  // カードの一覧だけお気に入りを先頭に寄せる（ボードは並びを変えない）
  const cards = view === "cards" && favorites.first ? favoritesFirst(sortedCards, favorites.ids) : sortedCards;
  const orders = view === "table" ? [sorted.map((row) => row.id)] : view === "board" ? boardOrders(cards) : [cards.map((item) => item.id)];
  return { initialCardSort, cardSort, cardRowSort, cards, orders };
};

export const ListScreen = ({ kind, views, columnsOf, drawerOpen, onCloseDrawer, content }: ListScreenProps) => {
  const { search, openItem, closeItem, setSort, setView } = usePreviewSearch();
  const { index } = useRecords();
  const record = useRecordLookup({ index, onOpenItem: openItem });
  const { point } = useDiffView();
  const { filters, tagMatch, setFilters, setTagMatch, clearAll, setTextFilter, commitTextFilter, addTag, tagExpr, setTagExpr } = useScreenFilters(kind);
  const view = search.view ?? views?.[0]?.key ?? "table";
  // 一覧のスクロール位置は画面と表示形式ごとに残し、記録を読み終えて行を描いたら戻す
  const scrollRef = useListScroll(`${kind}:${view}`, index !== null);
  useDropCardSort({ view, sort: search.sort, setSort });
  const onSelectTag = (name: string): void => {
    addTag(name);
  };
  const savePreset = usePresetSave(tagExpr);
  const favorites = useFavorites();
  const comments = useQuery(commentsQuery());
  const startAdd = useEditSessionStore((state) => state.startAdd);
  const openAdded = useEditSessionStore((state) => state.openAdded);
  const closeAdd = useEditSessionStore((state) => state.closeAdd);
  const [saved, setSaved] = useState(() => readPrefs().columns?.[kind]);
  const onAdd = useCallback(() => {
    closeItem();
    startAdd(kind);
  }, [closeItem, startAdd, kind]);
  const openItemFromList = (id: string): void => {
    closeAdd();
    openItem(id, { fromList: true });
  };
  const onOpenAdded = (id: string): void => {
    closeItem();
    openAdded(kind, id);
  };
  // 差分の表示の間と配る書き出しは項目の追加を出さない
  const edit = useScreenEdit(kind, point !== null || isEmbedded(), onAdd);
  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const { target } of (comments.data?.status === 200 ? comments.data.data.items : [])) {
      if (typeof target === "string") result[target] = (result[target] ?? 0) + 1;
    }
    return result;
  }, [comments.data]);
  const columnsWithFavorite = (records: RecordIndex): TableColumn[] => [favoriteColumn(favorites.ids, favorites.toggle), ...columnsOf(records, openItem)];
  const columnKeys = index === null ? null : columnsWithFavorite(index).map((column) => column.key);
  // 記録に合わない並べ替えの列は URL から外す
  useEffect(() => {
    if (search.sort !== undefined && columnKeys !== null && !columnKeys.includes(search.sort.replace(/^-/, ""))) setSort(undefined, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 列の並びと並べ替えが変わったときだけ確かめる
  }, [search.sort, columnKeys?.join()]);
  if (index === null) return null;
  const columns = columnsWithFavorite(index);
  const presets = index.data.settings.presets ?? [];
  const list = asColumns(columns);
  // 追加する項目は絞り込みに関わらず先頭に置く
  const rows = index.data[kind].filter((item) => !item.id.startsWith(NEW_ID_PREFIX)) as unknown as Row[];
  // 簡易で表せないタグの式は、簡易の条件の代わりに式で絞る
  const complexExpr = tagExpr !== null && simpleTagsOf(tagExpr) === null ? tagExpr : null;
  const matched = filterRows({ rows, columns: list, filters, tagMatch }).filter((row) => complexExpr === null || matchesTagExpr(tagNames((row as unknown as Item).tags), complexExpr));
  // 「お気に入りだけを表示する」はカード・ボード・表のどれでも絞る
  const filtered = onlyFavoritesIfSet(matched, favorites);
  const exprChip = complexExpr === null ? {} : { tagExprText: describeTagExpr(complexExpr), onClearTagExpr: () => { setTagExpr(null); } };
  // 「お気に入りだけを表示する」の間は、絞り込みのチップの先頭に「お気に入りのみ」を出す
  const favoritesChip = favoritesChipOf(favorites);
  const sorted = sortRows({ rows: filtered, columns: list, sort: search.sort });
  const { initialCardSort, cardSort, cardRowSort, cards, orders } = listOrders({ kind, view, sort: search.sort, filtered: filtered as unknown as Item[], sorted, favorites });
  const marks: DiffMarks | undefined = point === null ? undefined : Object.fromEntries([...[...point.added].map((id) => [id, "new"] as const), ...[...point.changed].map((id) => [id, "changed"] as const)]);
  const hidden = saved?.hidden ?? columns.filter((column) => column.hidden === true).map((column) => column.key);
  const pinTo = saved?.pinTo ?? null;
  const store = (next: { hidden: string[]; pinTo: string | null } | undefined): void => {
    const all = { ...(readPrefs().columns ?? {}) };
    if (next === undefined) delete all[kind];
    else all[kind] = next;
    writePrefs({ columns: all });
    setSaved(next);
  };
  const labels = Object.fromEntries(columns.map((column) => [column.key, column.label]));
  const table = (
    <Table
      kind={kind}
      lookup={record.lookup}
      columns={columns}
      rows={sorted}
      sort={search.sort === undefined ? null : { key: search.sort.replace(/^-/, ""), dir: search.sort.startsWith("-") ? "desc" : "asc" }}
      filters={filters}
      pinTo={pinTo}
      hiddenColumns={hidden}
      marks={marks}
      comments={counts}
      pendingMarks={edit?.marks}
      onSort={(key) => { setSort(nextSort(search.sort, key)); }}
      onFilter={setFilters}
      onPin={(key) => { store({ hidden, pinTo: pinTo === key ? null : key }); }}
      onHiddenColumnsChange={(next) => { store({ hidden: next, pinTo }); }}
      onResetColumns={() => {
        store(undefined);
        setSort(undefined, { replace: true });
      }}
      onOpenItem={openItemFromList}
      addedRows={edit?.adds ?? []}
      onOpenAdded={onOpenAdded}
      tagMatch={tagMatch}
      onSelectTag={onSelectTag}
      scrollRef={view === "table" ? scrollRef : undefined}
      {...exprChip}
      {...favoritesChip}
    />
  );
  const conditions = columns.filter((column) => column.filterable === true);
  const groups = drawerGroups({ rows, columns: list, conditions: asColumns(conditions), filters, tagMatch });
  const applyCandidate = (key: string, value: string): void => {
    addValue({ filters, key, value, setFilters, addTag });
  };
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 p-3">
      <div className="flex flex-wrap items-center gap-2">
        {views === null ? null : <ViewSwitch views={views} current={view} onChange={setView} />}
        <CardSortControl shown={view !== "table" && content !== undefined} value={cardSort} onChange={(next) => { setSort(cardSortToParam(next, initialCardSort)); }} />
        {edit === null ? null : (
          <Button variant="outline" aria-label={`${KIND_LABEL[kind]}の項目を追加`} title="項目追加" className="ml-auto" onClick={edit.onAdd}>
            <Icon name="plus" />
            <span className="max-sm:sr-only">項目追加</span>
          </Button>
        )}
      </div>
      {view === "table" ? null : <FilterChips filters={filters} labels={labels} tagMatch={tagMatch} onFilter={setFilters} {...exprChip} {...favoritesChip} />}
      <RemovedBand items={removedOf({ point, kind })} lookup={record.lookup} onOpen={record.onOpen} />
      {view === "table" || content === undefined ? table : content({ index, lookup: record.lookup, view, shown: cards, sort: cardRowSort, filters, tagMatch, marks, comments: counts, edit, onOpen: openItemFromList, onOpenAdded, selectedId: search.id, onSelectTag, scrollRef, table, favorites: favorites.ids, favoritesFirst: favorites.first, onToggleFavorite: favorites.toggle })}
      <PublishOrders orders={orders} />
      <PublishCandidates groups={groups} apply={applyCandidate} />
      {drawerOpen ? (
        <FilterDrawer
          groups={groups}
          selected={filters}
          total={rows.length}
          shown={filtered.length}
          tagMatch={tagMatch}
          onTagMatchChange={setTagMatch}
          presets={presetChoicesOf({ presets, rowTags: rows.map((row) => tagNames((row as unknown as Item).tags)), current: tagExpr })}
          onApplyPreset={(name) => {
            const preset = presets.find((one) => one.name === name);
            if (preset !== undefined) setTagExpr(preset.filter, { push: true });
          }}
          {...presetSaveOf(filters, savePreset)}
          tagExpr={tagExpr}
          onTagExprChange={(expr) => { setTagExpr(expr, { push: true }); }}
          texts={columns.filter((column) => column.filterable !== true && column.key !== "id").map((column) => ({ key: column.key, label: column.label, value: filters[`${TEXT_FILTER_PREFIX}${column.key}`]?.[0] ?? "" }))}
          onToggleValue={(key, value) => {
            const current = filters[key] ?? [];
            const next = current.includes(value) ? current.filter((candidate) => candidate !== value) : [...current, value];
            setFilters(next.length === 0 ? withoutKey(filters, key) : { ...filters, [key]: next }, { push: true });
          }}
          onClearGroup={(key) => {
            if (key === TAG_FILTER_KEY) setTagExpr(null, { push: true });
            else setFilters(withoutKey(filters, key), { push: true });
          }}
          onClearAll={clearAll}
          onClose={onCloseDrawer}
          onTextChange={setTextFilter}
          onTextCommit={commitTextFilter}
        />
      ) : null}
    </div>
  );
};
