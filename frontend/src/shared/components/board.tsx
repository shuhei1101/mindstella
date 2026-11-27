// 状態ごとの列にカードを並べたボードと、項目のカード
import { useRef, type MouseEvent, type PointerEvent, type ReactNode, type RefCallback } from "react";

import { CommentMark } from "@/shared/components/comment-mark";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { FavoriteToggle } from "@/shared/components/favorite-toggle";
import { ItemDates } from "@/shared/components/item-dates";
import { StatusMark } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { RecordText } from "@/shared/components/record-text";
import { sortItems } from "@/shared/components/card-sort";
import { addedTitle } from "@/shared/components/table";
import { TagList } from "@/shared/components/tag-list";
import type { PendingMarkKind, ScreenEdit } from "@/shared/core/edits";
import type { LookupRecordId } from "@/shared/core/record-ids";
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
  /** カードを描く。`order` はそのカードの列の描いた並びの ID */
  card: (item: Item, order: string[]) => ReactNode;
  /** 列の中の並び（`sortRows` の `sort`）。無ければ渡した列の順 */
  sort?: string;
  emptyText: string;
  /** 状態の列の先頭に置く追加する項目のカード */
  added?: (status: string) => ReactNode[];
  /** ボードのスクロール領域に付ける ref（スクロール位置の復元） */
  scrollRef?: RefCallback<HTMLElement>;
};

/** ドラッグを始めない要素（カード・ボタン・リンク・入力欄） */
const NO_DRAG_SELECTOR = "[data-card], [data-new-id], button, a, input, textarea, select";

/** 縦の 1 列に並べる幅（ドラッグで横にスクロールしない） */
const SINGLE_COLUMN_QUERY = "(max-width: 720px)";

/** これ以上動かしたら、離した後の click を止める距離（px） */
const DRAG_CLICK_THRESHOLD_PX = 4;

type Drag = { pointerId: number; startX: number; startScroll: number; moved: boolean };

/** ボードの背景をマウスで押したまま動かして横にスクロールする操作 */
const useDragScroll = () => {
  const drag = useRef<Drag | null>(null);
  // 4px 以上動かした直後の click を止める
  const suppressClick = useRef(false);
  const end = (event: PointerEvent<HTMLDivElement>): void => {
    if (drag.current?.pointerId !== event.pointerId) return;
    suppressClick.current = drag.current.moved;
    drag.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    event.currentTarget.style.removeProperty("cursor");
    event.currentTarget.style.removeProperty("user-select");
  };
  return {
    onPointerDown: (event: PointerEvent<HTMLDivElement>): void => {
      // マウスの左ボタンだけ。指はブラウザのスクロールに任せる
      if (event.pointerType !== "mouse" || event.button !== 0) return;
      // カード・ボタン・リンクの上からは始めない
      if (event.target instanceof Element && event.target.closest(NO_DRAG_SELECTOR) !== null) return;
      // 縦の 1 列では動かさない（matchMedia を持たない環境は横に並べた幅として扱う）
      if (typeof window.matchMedia === "function" && window.matchMedia(SINGLE_COLUMN_QUERY).matches) return;
      drag.current = { pointerId: event.pointerId, startX: event.clientX, startScroll: event.currentTarget.scrollLeft, moved: false };
      suppressClick.current = false;
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    onPointerMove: (event: PointerEvent<HTMLDivElement>): void => {
      const current = drag.current;
      if (current?.pointerId !== event.pointerId) return;
      const delta = current.startX - event.clientX;
      // 動かし始めた: 文字を選ばせず、カーソルをつかんでいる形にする
      if (!current.moved && Math.abs(delta) >= DRAG_CLICK_THRESHOLD_PX) {
        current.moved = true;
        event.currentTarget.style.cursor = "grabbing";
        event.currentTarget.style.userSelect = "none";
      }
      event.currentTarget.scrollLeft = current.startScroll + delta;
    },
    onPointerUp: end,
    onPointerCancel: end,
    onClickCapture: (event: MouseEvent<HTMLDivElement>): void => {
      if (!suppressClick.current) return;
      suppressClick.current = false;
      event.preventDefault();
      event.stopPropagation();
    },
  };
};

export const Board = ({ columns, card, sort, emptyText, added, scrollRef }: BoardProps) => {
  const dragHandlers = useDragScroll();
  return (
  // 横にスクロールする領域。カードが 0 枚でもキーボードで送れるようにする
  // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
  <div ref={scrollRef} tabIndex={0} role="region" aria-label="ボード" className="flex min-h-0 flex-1 gap-3 overflow-x-auto px-3 pb-2" {...dragHandlers}>
    {columns.map(({ status, items: columnItems, excluded }) => {
      const adds = added?.(status) ?? [];
      const items = sort === undefined ? columnItems : sortItems(columnItems, sort);
      const order = items.map((item) => item.id);
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
        {excluded ? null : items.map((item) => card(item, order))}
      </section>
      );
    })}
  </div>
  );
};

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
  /** タイトルと関係する項目のタイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
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
  /** 渡すとカードの右上に星を配置し、押すとお気に入りに登録・解除する */
  favorite?: { on: boolean; onToggle: () => void };
};

export const ItemCard = ({ index, lookup, item, meta, links, selected, marks, comments, edit, onOpen, onSelectTag, favorite }: ItemCardProps) => {
  const mark = marks?.[item.id];
  const pending = edit?.marks[item.id];
  const count = comments[item.id] ?? 0;
  // タイトルのボタンの aria-describedby が指す、タイトルと関係する項目のタイトルの中の ID の説明
  const titleIdsId = `card-ids-${item.id}`;
  const linkIdsId = (id: string): string => `card-ids-${item.id}-${id}`;
  return (
    // カードの中にタグのボタンを置くため、外枠は div にし、タイトルのボタンの ::after をカード全体へ広げる
    <div data-card={item.id} className={cn("relative flex w-full flex-col gap-1 rounded-card border border-border-soft bg-card p-2 text-left hover:bg-row-hover has-focus-visible:outline-2 has-focus-visible:outline-ring", selected && "border-mark bg-row-selected", pending === "remove" && "opacity-60", favorite !== undefined && "pr-9")}>
      {favorite === undefined ? null : <FavoriteToggle title={item.title} on={favorite.on} onToggle={favorite.onToggle} className="absolute top-1.5 right-1.5" />}
      <button type="button" data-id={item.id} aria-current={selected ? "true" : undefined} aria-describedby={[titleIdsId, ...links.map(linkIdsId)].join(" ")} className="cursor-pointer text-left text-small font-medium outline-none after:absolute after:inset-0 after:rounded-card" onClick={() => { onOpen(item.id); }}>
        <RecordText text={item.title} mode="marker" lookup={lookup} descriptionId={titleIdsId} />
      </button>
      <span className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
        {mark === undefined ? null : <DiffMark kind={mark} />}
        <span className="font-mono">{item.id}</span>
        {meta.filter((value) => value !== undefined && value !== "").map((value) => (
          <span key={value}>{value}</span>
        ))}
        {pending === undefined ? null : <PendingMark kind={pending} />}
      </span>
      <ItemDates created={item.created} updated={item.updated} />
      {links.map((id) => (
        <span key={id} className="text-xs text-muted-foreground">
          <span className="font-mono">{id}</span> <RecordText text={titleOf(index, id)} mode="marker" lookup={lookup} descriptionId={linkIdsId(id)} />
        </span>
      ))}
      {onSelectTag !== undefined && (item.tags ?? []).length > 0 ? (
        <span className="flex flex-wrap gap-x-1 gap-y-1.5">
          <TagList values={item.tags} onSelect={onSelectTag} />
        </span>
      ) : null}
      {count > 0 ? (
        <span className="flex justify-end">
          <CommentMark count={count} />
        </span>
      ) : null}
    </div>
  );
};
