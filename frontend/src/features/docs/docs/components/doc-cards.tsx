// 資料のカード。種類・形式・状態・タグを並べる
import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { CommentMark } from "@/shared/components/comment-mark";
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { Icon, StatusMark } from "@/shared/components/icon";
import { ItemDates } from "@/shared/components/item-dates";
import { PendingMark } from "@/shared/components/pending-mark";
import { TagList } from "@/shared/components/tag-list";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";
import type { ScreenEdit } from "@/shared/core/edits";
import { cardSortToRowSort, INITIAL_CARD_SORT, sortItems } from "@/shared/components/card-sort";
import { bodyFormatOf, type Item } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";


export type DocCardProps = {
  doc: Item;
  /** タイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  inBoard: boolean;
  selected: boolean;
  marks: DiffMarks | undefined;
  comments: Record<string, number>;
  edit: ScreenEdit | null;
  onOpen: (id: string) => void;
  /** 渡すとタグを押せるようにし、押したタグを絞り込みに加える */
  onSelectTag?: (name: string) => void;
};

export const DocCard = ({ doc, lookup, inBoard, selected, marks, comments, edit, onOpen, onSelectTag }: DocCardProps) => {
  const format = bodyFormatOf(doc.body);
  const mark = marks?.[doc.id];
  const pending = edit?.marks[doc.id];
  const count = comments[doc.id] ?? 0;
  return (
    // カードの中にタグのボタンを置くため、外枠は div にし、タイトルのボタンの ::after をカード全体へ広げる
    <div data-card={doc.id} className={cn("relative flex w-full flex-col gap-1 rounded-card border border-border-soft bg-card p-3 text-left hover:bg-row-hover has-focus-visible:outline-2 has-focus-visible:outline-ring", selected && inBoard && "border-mark bg-row-selected", pending === "remove" && "opacity-60")}>
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        <Icon name={doc.kind === "図" ? "graph" : "cards"} className="size-3" />
        {doc.kind}
        {format === null ? null : <BodyFormatBadge format={format} />}
      </span>
      <h2 className="m-0 text-small font-medium">
        <button type="button" data-id={doc.id} aria-current={selected ? "true" : undefined} aria-describedby={`doc-card-ids-${doc.id}`} className="cursor-pointer text-left outline-none after:absolute after:inset-0 after:rounded-card" onClick={() => { onOpen(doc.id); }}>
          <RecordText text={doc.title} mode="marker" lookup={lookup} descriptionId={`doc-card-ids-${doc.id}`} />
        </button>
      </h2>
      {doc.withdrawn === true ? <WithdrawnBadge /> : null}
      <span className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
        {mark === undefined ? null : <DiffMark kind={mark} />}
        <span className="font-mono">{doc.id}</span>
        {inBoard || doc.status === undefined ? null : (
          <span className="inline-flex items-center gap-1">
            <StatusMark status={doc.status} />
            {doc.status}
          </span>
        )}
        {pending === undefined ? null : <PendingMark kind={pending} />}
      </span>
      <ItemDates created={doc.created} updated={doc.updated} />
      {(doc.tags ?? []).length > 0 ? (
        <span className="flex flex-wrap gap-x-1 gap-y-1.5">
          <TagList values={doc.tags} onSelect={onSelectTag} />
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

export type DocCardsProps = {
  docs: readonly Item[];
  /** カードのタイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  /** 並び（`sortRows` の `sort`）。無ければ更新日時の新しい順 */
  sort?: string;
  selectedId: string | null | undefined;
  marks: DiffMarks | undefined;
  comments: Record<string, number>;
  edit: ScreenEdit | null;
  /** カードを押した。`order` は描いた並びの ID */
  onOpen: (id: string, order: string[]) => void;
  onSelectTag?: (name: string) => void;
};

/** 資料のカードを並びの順に描く */
export const DocCards = ({ docs, lookup, sort = cardSortToRowSort(INITIAL_CARD_SORT.docs), selectedId, marks, comments, edit, onOpen, onSelectTag }: DocCardsProps) => {
  const ordered = sortItems(docs, sort);
  const order = ordered.map((doc) => doc.id);
  return ordered.map((doc) => <DocCard key={doc.id} doc={doc} lookup={lookup} inBoard={false} selected={doc.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={(id) => { onOpen(id, order); }} {...(onSelectTag === undefined ? {} : { onSelectTag })} />);
};
