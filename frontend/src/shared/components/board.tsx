// 状態ごとの列にカードを並べたボードと、項目のカード
import type { ReactNode } from "react";

import { CommentMark } from "@/shared/components/comment-mark";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { StatusMark } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import type { ScreenEdit } from "@/shared/core/edits";
import { compareIds, titleOf, type Item, type RecordIndex } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** ボードの 1 列 */
export type BoardColumn = { status: string; items: Item[]; excluded: boolean };

/** 状態の並びの順に、状態ごとの項目を返す（0 件の列も返す） */
export const boardColumns = ({ items, statuses, statusFilter = [] }: { items: readonly Item[]; statuses: readonly string[]; statusFilter?: readonly string[] }): BoardColumn[] =>
  statuses.map((status) => ({
    status,
    items: items.filter((item) => item.status === status).sort((a, b) => compareIds(a.id, b.id)),
    excluded: statusFilter.length > 0 && !statusFilter.includes(status),
  }));

export type BoardProps = { columns: BoardColumn[]; card: (item: Item) => ReactNode; emptyText: string };

export const Board = ({ columns, card, emptyText }: BoardProps) => (
  <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto pb-2">
    {columns.map(({ status, items, excluded }) => (
      <section key={status} aria-label={status} className="flex w-72 flex-none flex-col gap-2">
        <h2 className="flex items-center gap-1 text-small font-medium">
          <StatusMark status={status} />
          {status}
          <span className="font-mono text-xs text-muted-foreground">{items.length}</span>
        </h2>
        {excluded ? <p className="text-small text-muted-foreground">状態の条件で外しています。</p> : null}
        {!excluded && items.length === 0 ? <p className="text-small text-muted-foreground">{emptyText}</p> : null}
        {excluded ? null : items.map(card)}
      </section>
    ))}
  </div>
);

export type ItemCardProps = {
  index: RecordIndex;
  item: Item;
  meta: (string | undefined)[];
  links: readonly string[];
  selected: boolean;
  marks: DiffMarks | undefined;
  comments: Record<string, number>;
  edit: ScreenEdit | null;
  onOpen: (id: string) => void;
};

export const ItemCard = ({ index, item, meta, links, selected, marks, comments, edit, onOpen }: ItemCardProps) => {
  const mark = marks?.[item.id];
  const pending = edit?.marks[item.id];
  const count = comments[item.id] ?? 0;
  return (
    <button type="button" data-id={item.id} aria-current={selected ? "true" : undefined} className={cn("flex w-full cursor-pointer flex-col gap-1 rounded-card border border-border-soft bg-card p-2 text-left hover:bg-row-hover", selected && "border-mark-line bg-row-selected", pending === "remove" && "opacity-60")} onClick={() => { onOpen(item.id); }}>
      <span className="text-small font-medium">{item.title}</span>
      <span className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
        {mark === undefined ? null : <DiffMark kind={mark} />}
        <span className="font-mono">{item.id}</span>
        {meta.filter((value) => value !== undefined && value !== "").map((value) => (
          <span key={value}>{value}</span>
        ))}
        {pending === undefined ? null : <PendingMark kind={pending} />}
        {count > 0 ? <CommentMark count={count} /> : null}
      </span>
      {links.map((id) => (
        <span key={id} className="text-xs text-muted-foreground">
          <span className="font-mono">{id}</span> {titleOf(index, id)}
        </span>
      ))}
    </button>
  );
};
