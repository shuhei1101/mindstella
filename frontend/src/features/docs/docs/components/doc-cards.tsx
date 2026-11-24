// 資料のカード。種類・形式・状態・タグを並べる
import { CommentMark } from "@/shared/components/comment-mark";
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { Icon, StatusMark } from "@/shared/components/icon";
import { ItemDates } from "@/shared/components/item-dates";
import { PendingMark } from "@/shared/components/pending-mark";
import { TagList } from "@/shared/components/tag-list";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";
import type { ScreenEdit } from "@/shared/core/edits";
import { bodyFormatOf, compareIds, type Item } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** 連番の順に並べる */
export const orderDocs = (docs: readonly Item[]): Item[] => [...docs].sort((a, b) => compareIds(a.id, b.id));

export type DocCardProps = {
  doc: Item;
  inBoard: boolean;
  selected: boolean;
  marks: DiffMarks | undefined;
  comments: Record<string, number>;
  edit: ScreenEdit | null;
  onOpen: (id: string) => void;
  /** 渡すとタグを押せるようにし、押したタグを絞り込みに加える */
  onSelectTag?: (name: string) => void;
};

export const DocCard = ({ doc, inBoard, selected, marks, comments, edit, onOpen, onSelectTag }: DocCardProps) => {
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
        <button type="button" data-id={doc.id} aria-current={selected ? "true" : undefined} className="cursor-pointer text-left outline-none after:absolute after:inset-0 after:rounded-card" onClick={() => { onOpen(doc.id); }}>
          {doc.title}
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
