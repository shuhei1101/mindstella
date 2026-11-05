// 一覧の画面の枠。表示形式の切り替え・項目の追加・消した項目の帯・絞り込みのドロワーと、表の状態を持つ
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import type { DiffMarks } from "@/shared/components/diff-mark";
import { FilterChips } from "@/shared/components/filter-chips";
import { FilterDrawer } from "@/shared/components/filter-drawer";
import { Icon } from "@/shared/components/icon";
import { ItemAddForm } from "@/shared/components/item-add-form";
import { RemovedBand } from "@/shared/components/removed-band";
import { Table, type Row, type TableColumn } from "@/shared/components/table";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import { ViewSwitch, type View } from "@/shared/components/view-switch";
import { removedOf } from "@/shared/core/diff";
import type { ScreenEdit } from "@/shared/core/edits";
import { TEXT_FILTER_PREFIX, withoutKey, type Filters } from "@/shared/core/filters";
import { drawerGroups, filterRows, nextSort, sortRows, type ListColumn } from "@/shared/core/list-rows";
import { KIND_LABEL, type Item, type Kind, type RecordIndex } from "@/shared/core/records";
import { commentsQuery } from "@/shared/hooks/preview-queries";
import { useDiffView } from "@/shared/hooks/use-diff-view";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useScreenEdit } from "@/shared/hooks/use-screen-edit";
import { useScreenFilters } from "@/shared/hooks/use-screen-filters";
import { readPrefs, writePrefs } from "@/shared/stores/prefs-store";

/** 画面の枠が中身に渡す値 */
export type ListContext = {
  index: RecordIndex;
  view: View;
  shown: Item[];
  filters: Filters;
  marks: DiffMarks | undefined;
  comments: Record<string, number>;
  edit: ScreenEdit | null;
  onOpen: (id: string) => void;
  selectedId: string | undefined;
  /** 表（並べ替え・列の表示・固定は URL と端末の保存領域で持つ） */
  table: ReactNode;
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

export const ListScreen = ({ kind, views, columnsOf, drawerOpen, onCloseDrawer, content }: ListScreenProps) => {
  const { search, openItem, setSort, setView } = usePreviewSearch();
  const { index } = useRecords();
  const { point } = useDiffView();
  const { filters, setFilters } = useScreenFilters(kind);
  const comments = useQuery(commentsQuery());
  const [adding, setAdding] = useState(false);
  const [saved, setSaved] = useState(() => readPrefs().columns?.[kind]);
  const onAdd = useCallback(() => { setAdding(true); }, []);
  const edit = useScreenEdit(kind, point !== null, onAdd);
  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const { target } of (comments.data?.status === 200 ? comments.data.data.items : [])) {
      if (typeof target === "string") result[target] = (result[target] ?? 0) + 1;
    }
    return result;
  }, [comments.data]);
  const columnKeys = index === null ? null : columnsOf(index, openItem).map((column) => column.key);
  // 記録に合わない並べ替えの列は URL から外す
  useEffect(() => {
    if (search.sort !== undefined && columnKeys !== null && !columnKeys.includes(search.sort.replace(/^-/, ""))) setSort(undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 列の並びと並べ替えが変わったときだけ確かめる
  }, [search.sort, columnKeys?.join()]);
  if (index === null) return null;
  const columns = columnsOf(index, openItem);
  const list = asColumns(columns);
  const rows = index.data[kind] as unknown as Row[];
  const filtered = filterRows({ rows, columns: list, filters });
  const sorted = sortRows({ rows: filtered, columns: list, sort: search.sort });
  const view = search.view ?? views?.[0]?.key ?? "table";
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
        setSort(undefined);
      }}
      onOpenItem={openItem}
    />
  );
  const conditions = columns.filter((column) => column.filterable === true);
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 p-3">
      <div className="flex items-center gap-2">
        {views === null ? null : <ViewSwitch views={views} current={view} onChange={setView} />}
        {edit === null ? null : (
          <Button variant="outline" aria-label={`${KIND_LABEL[kind]}の項目を追加`} title="項目を追加" className="ml-auto" onClick={edit.onAdd}>
            <Icon name="plus" />
            <span className="max-sm:sr-only">項目を追加</span>
          </Button>
        )}
      </div>
      {view === "table" ? null : <FilterChips filters={filters} labels={labels} onFilter={setFilters} />}
      <RemovedBand items={removedOf({ point, kind })} />
      {view === "table" || content === undefined ? table : content({ index, view, shown: filtered as unknown as Item[], filters, marks, comments: counts, edit, onOpen: openItem, selectedId: search.id, table })}
      {drawerOpen ? (
        <FilterDrawer
          groups={drawerGroups({ rows, columns: list, conditions: asColumns(conditions), filters })}
          selected={filters}
          total={rows.length}
          shown={filtered.length}
          texts={columns.filter((column) => column.filterable !== true && column.key !== "id").map((column) => ({ key: column.key, label: column.label, value: filters[`${TEXT_FILTER_PREFIX}${column.key}`]?.[0] ?? "" }))}
          onToggleValue={(key, value) => {
            const current = filters[key] ?? [];
            const next = current.includes(value) ? current.filter((candidate) => candidate !== value) : [...current, value];
            setFilters(next.length === 0 ? withoutKey(filters, key) : { ...filters, [key]: next });
          }}
          onClearGroup={(key) => { setFilters(withoutKey(filters, key)); }}
          onClearAll={() => { setFilters({}); }}
          onClose={onCloseDrawer}
          onTextChange={(key, text) => {
            const name = `${TEXT_FILTER_PREFIX}${key}`;
            setFilters(text === "" ? withoutKey(filters, name) : { ...filters, [name]: [text] });
          }}
        />
      ) : null}
      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent>
          <DialogTitle className="mb-2 text-h2 font-semibold">項目を追加</DialogTitle>
          <ItemAddForm kind={kind} onClose={() => { setAdding(false); }} />
        </DialogContent>
      </Dialog>
    </div>
  );
};
