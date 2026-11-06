// 項目の一覧の表（部品設計『表.tsx』）。TanStack Table と shadcn の data-table のガイドで組む。並べ替えと絞り込みの状態は使う側が URL から渡す
import { toText } from "@/shared/core/format";
import { columnVisibilityFeature, tableFeatures, useTable, type ColumnDef } from "@tanstack/react-table";
import type { ReactNode } from "react";

import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { CommentMark } from "@/shared/components/comment-mark";
import { FilterChips } from "@/shared/components/filter-chips";
import { Icon } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTitle, PopoverTrigger } from "@/shared/components/ui/popover";
import { TableBody, TableCell, TableHead, TableHeader, TableRoot, TableRow } from "@/shared/components/ui/table";
import type { PendingMarkKind } from "@/shared/core/edits";
import type { Filters } from "@/shared/core/filters";
import { KIND_LABEL, type Kind } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** 表の行 */
export type Row = { id: string } & Record<string, unknown>;

/** 列の定義 */
export type TableColumn = {
  key: string;
  label: string;
  /** 絞り込みと並べ替えに使う値。無ければ行の同じキーの値 */
  get?: (row: Row) => unknown;
  /** 値の並びの順 */
  order?: readonly string[];
  filterable?: boolean;
  fixed?: boolean;
  hidden?: boolean;
  num?: boolean;
  /** セルを描く。無ければ値を文字にする */
  cell?: (row: Row) => ReactNode;
};

export type TableProps = {
  kind: string;
  columns: TableColumn[];
  rows: Row[];
  /** 並べている列と向き */
  sort?: { key: string; dir: "asc" | "desc" } | null | undefined;
  filters?: Filters;
  pinTo?: string | null;
  hiddenColumns?: string[];
  marks?: DiffMarks | undefined;
  comments?: Record<string, number> | undefined;
  pendingMarks?: Record<string, PendingMarkKind> | undefined;
  onSort: (key: string) => void;
  onFilter: (filters: Filters) => void;
  onPin: (key: string) => void;
  onHiddenColumnsChange: (hiddenColumns: string[]) => void;
  onResetColumns: () => void;
  onOpenItem: (id: string) => void;
  /** 追加する項目（先頭の行に置く） */
  addedRows?: Row[];
  onOpenAdded?: (id: string) => void;
};

/** 追加する項目のタイトル（まだ書いていなければ「（タイトル未入力）」） */
export const addedTitle = (title: string): string => (title === "" ? "（タイトル未入力）" : title);

const features = tableFeatures({ columnVisibilityFeature });

const cellText = (value: unknown): string => {
  if (Array.isArray(value)) return value.map(String).join("・");
  return value === undefined || value === null ? "" : toText(value);
};

/** 見出しの並べ替えの向き */
const sortOf = (sort: TableProps["sort"], key: string): "ascending" | "descending" | undefined => {
  if (sort?.key !== key) return undefined;
  return sort.dir === "asc" ? "ascending" : "descending";
};

export const Table = ({ kind, columns, rows, sort, filters = {}, pinTo = null, hiddenColumns, marks, comments, pendingMarks, addedRows = [], onOpenAdded, onSort, onFilter, onPin, onHiddenColumnsChange, onResetColumns, onOpenItem }: TableProps) => {
  const hidden = hiddenColumns ?? columns.filter((column) => column.hidden === true).map((column) => column.key);
  const defs: ColumnDef<typeof features, Row>[] = columns.map((column) => ({ id: column.key, accessorFn: (row: Row) => cellText(column.get === undefined ? row[column.key] : column.get(row)), header: column.label }));
  const table = useTable({ features, columns: defs, data: rows, state: { columnVisibility: Object.fromEntries(hidden.map((key) => [key, false])) }, getRowId: (row) => row.id });
  const visible = columns.filter((column) => !hidden.includes(column.key));
  const pinIndex = pinTo === null ? -1 : visible.findIndex((column) => column.key === pinTo);
  const labels = Object.fromEntries(columns.map((column) => [column.key, column.label]));
  return (
    <div data-kind={kind} className="flex min-h-0 flex-col gap-1">
      <div className="flex items-start gap-2">
        <FilterChips filters={filters} labels={labels} onFilter={onFilter} />
        <Popover>
          <PopoverTrigger render={<Button variant="outline" aria-label="列の表示" className="ml-auto flex-none" />}>
            <Icon name="cols" />
            <span className="max-sm:sr-only">列の表示</span>
          </PopoverTrigger>
          <PopoverContent>
            <PopoverTitle className="mb-1 text-small font-medium">列の表示</PopoverTitle>
            {columns.map((column) => (
              <label key={column.key} className="flex items-center gap-1 py-0.5 text-small">
                <Checkbox
                  checked={!hidden.includes(column.key)}
                  disabled={column.fixed === true}
                  onChange={(event) => {
                    onHiddenColumnsChange(event.target.checked ? hidden.filter((key) => key !== column.key) : [...hidden, column.key]);
                  }}
                />
                {column.label}
              </label>
            ))}
            <Button variant="ghost" onClick={onResetColumns}>
              列・並べ替え・固定を初期設定に戻す
            </Button>
          </PopoverContent>
        </Popover>
      </div>
      <div className="min-h-0 overflow-auto rounded-control border border-border-soft">
        <TableRoot>
          <TableHeader>
            <tr>
              {visible.map((column, position) => {
                const direction = sortOf(sort, column.key);
                return (
                  <TableHead key={column.key} aria-sort={direction} className={cn(position <= pinIndex && "sticky left-0 z-20 bg-thead", column.num === true && "text-right")}>
                    <span className="inline-flex items-center gap-1">
                      <button type="button" data-sort={column.key} aria-label={`${column.label}で並べ替え`} className="inline-flex min-h-6 min-w-6 cursor-pointer items-center gap-0.5" onClick={() => { onSort(column.key); }}>
                        {column.label}
                        <Icon name="updown" className={cn("size-3", direction === undefined && "text-subtle-foreground")} />
                      </button>
                      <button type="button" data-pin={column.key} aria-pressed={pinTo === column.key} aria-label={`${column.label}まで固定`} className="inline-flex size-6 cursor-pointer items-center justify-center text-subtle-foreground hover:text-foreground" onClick={() => { onPin(column.key); }}>
                        <Icon name={pinTo === column.key ? "lock" : "unlock"} className="size-3" />
                      </button>
                    </span>
                  </TableHead>
                );
              })}
            </tr>
          </TableHeader>
          <TableBody>
            {addedRows.map((row) => (
              <TableRow key={row.id} data-new-id={row.id} className="border-dashed">
                {visible.map((column) => (
                  <TableCell key={column.key}>
                    {column.key === "id" ? (
                      <span className="text-muted-foreground">—</span>
                    ) : column.key === "title" ? (
                      <span className="inline-flex flex-wrap items-center gap-1">
                        <button type="button" className="cursor-pointer text-left underline-offset-2 hover:underline" onClick={() => { onOpenAdded?.(row.id); }}>
                          {addedTitle(cellText(row["title"]))}
                        </button>
                        <PendingMark kind={pendingMarks?.[row.id] ?? "pending"} />
                      </span>
                    ) : (
                      (column.cell?.(row) ?? cellText(column.get === undefined ? row[column.key] : column.get(row)))
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {table.getRowModel().rows.length === 0 && addedRows.length === 0 ? (
              <tr>
                <td colSpan={visible.length} className="p-4 text-center text-muted-foreground">
                  {`該当する${KIND_LABEL[kind as Kind]}はありません。別の条件を試してください。`}
                </td>
              </tr>
            ) : null}
            {table.getRowModel().rows.map(({ original: row }) => (
              <TableRow key={row.id} data-id={row.id} className={cn(row["withdrawn"] === true && "text-muted-foreground")}>
                {visible.map((column, position) => {
                  const content = column.cell?.(row) ?? cellText(column.get === undefined ? row[column.key] : column.get(row));
                  const kindMark = marks?.[row.id];
                  const pendingMark = pendingMarks?.[row.id];
                  const count = comments?.[row.id] ?? 0;
                  return (
                    <TableCell key={column.key} className={cn(position <= pinIndex && "sticky left-0 bg-card", column.num === true && "text-right")}>
                      {column.key === "title" ? (
                        <span className="inline-flex flex-wrap items-center gap-1">
                          <button type="button" data-id={row.id} className="cursor-pointer text-left underline-offset-2 hover:underline" onClick={() => { onOpenItem(row.id); }}>
                            {content}
                          </button>
                          {row["withdrawn"] === true ? <WithdrawnBadge /> : null}
                          {kindMark === undefined ? null : <DiffMark kind={kindMark} />}
                          {count > 0 ? <CommentMark count={count} /> : null}
                          {pendingMark === undefined ? null : <PendingMark kind={pendingMark} />}
                        </span>
                      ) : (
                        content
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </TableRoot>
      </div>
    </div>
  );
};
