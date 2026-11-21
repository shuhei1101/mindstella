// 状態ごとの列にカードを並べたボードと、項目のカード
import type { ReactNode, RefCallback } from "react";

import { CommentMark } from "@/shared/components/comment-mark";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { StatusMark } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { addedTitle } from "@/shared/components/table";
import { TagList } from "@/shared/components/tag-list";
import { Checkbox } from "@/shared/components/ui/checkbox";
import type { PendingMarkKind, ScreenEdit } from "@/shared/core/edits";
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

export type BoardProps = {
  columns: BoardColumn[];
  card: (item: Item) => ReactNode;
  emptyText: string;
  /** 状態の列の先頭に置く追加する項目のカード */
  added?: (status: string) => ReactNode[];
  /** ボードのスクロール領域に付ける ref（スクロール位置の復元） */
  scrollRef?: RefCallback<HTMLElement>;
};

export const Board = ({ columns, card, emptyText, added, scrollRef }: BoardProps) => (
  <div ref={scrollRef} className="flex min-h-0 flex-1 gap-3 overflow-x-auto pb-2">
    {columns.map(({ status, items, excluded }) => {
      const adds = added?.(status) ?? [];
      return (
      <section key={status} aria-label={status} className="flex w-72 flex-none flex-col gap-2">
        <h2 className="flex items-center gap-1 text-h2 font-medium">
          <StatusMark status={status} />
          {status}
          <span className="font-mono text-xs text-muted-foreground">{items.length}</span>
        </h2>
        {excluded ? <p className="text-small text-muted-foreground">状態の条件で外しています。</p> : null}
        {!excluded && items.length === 0 && adds.length === 0 ? <p className="text-small text-muted-foreground">{emptyText}</p> : null}
        {excluded ? null : adds}
        {excluded ? null : items.map(card)}
      </section>
      );
    })}
  </div>
);

export type AddedCardProps = { item: Item; mark: PendingMarkKind; onOpen: (id: string) => void };

/** 追加する項目のカード。破線の枠で、ID の場所に「ID は保存時に決定」を置く */
export const AddedCard = ({ item, mark, onOpen }: AddedCardProps) => (
  <button type="button" data-new-id={item.id} className="flex w-full cursor-pointer flex-col gap-1 rounded-card border border-dashed border-mark-line bg-card p-2 text-left hover:bg-row-hover" onClick={() => { onOpen(item.id); }}>
    <span className="text-small font-medium">{addedTitle(item.title)}</span>
    <span className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
      <span>ID は保存時に決定</span>
      <PendingMark kind={mark} />
    </span>
  </button>
);

/** 追加する項目が属する列（状態が並びに無ければ最初の列）のカードを返す関数を作る */
export const addedCards = (edit: ScreenEdit | null, statuses: readonly string[], onOpen: (id: string) => void) => (status: string): ReactNode[] =>
  (edit?.adds ?? [])
    .filter((item) => (statuses.includes(item.status ?? "") ? item.status : statuses[0]) === status)
    .map((item) => <AddedCard key={item.id} item={item} mark={edit?.marks[item.id] ?? "pending"} onOpen={onOpen} />);

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
  /** 渡すとタグを並べ、押したタグを絞り込みに加える */
  onSelectTag?: (name: string) => void;
  /** 渡すとカードの右上に選ぶチェックボックスを置く */
  pick?: CardPick;
};

/** カードを選ぶチェックボックスの状態と、選んだ・解除したときに呼ぶ関数 */
export type CardPick = { checked: boolean; disabled: boolean; label: string; onChange: (checked: boolean) => void };

export const ItemCard = ({ index, item, meta, links, selected, marks, comments, edit, onOpen, onSelectTag, pick }: ItemCardProps) => {
  const mark = marks?.[item.id];
  const pending = edit?.marks[item.id];
  const count = comments[item.id] ?? 0;
  return (
    // カードの中にタグのボタンを置くため、外枠は div にし、タイトルのボタンの ::after をカード全体へ広げる
    <div data-card={item.id} className={cn("relative flex w-full flex-col gap-1 rounded-card border border-border-soft bg-card p-2 text-left hover:bg-row-hover has-focus-visible:outline-2 has-focus-visible:outline-ring", selected && "border-mark-line bg-row-selected", pending === "remove" && "opacity-60")}>
      <button type="button" data-id={item.id} aria-current={selected ? "true" : undefined} className={cn("cursor-pointer text-left text-small font-medium outline-none after:absolute after:inset-0 after:rounded-card", pick !== undefined && "pr-7")} onClick={() => { onOpen(item.id); }}>
        {item.title}
      </button>
      {pick === undefined ? null : (
        // カード全体を覆うタイトルのボタンと重なるため、チェックボックスの押せる範囲を 24px 四方にする
        <Checkbox
          aria-label={pick.label}
          checked={pick.checked}
          disabled={pick.disabled}
          className="absolute top-1 right-1 z-10 size-6 cursor-pointer disabled:cursor-default"
          onChange={(event) => {
            pick.onChange(event.target.checked);
          }}
        />
      )}
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
      {onSelectTag !== undefined && (item.tags ?? []).length > 0 ? (
        <span className="flex flex-wrap gap-x-1 gap-y-1.5">
          <TagList values={item.tags} onSelect={onSelectTag} />
        </span>
      ) : null}
    </div>
  );
};
