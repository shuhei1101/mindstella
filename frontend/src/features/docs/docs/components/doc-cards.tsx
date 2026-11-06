// 資料のカード。納品物の印・種類・形式・状態・カテゴリー・フェーズ・タグを並べる
import { CommentMark } from "@/shared/components/comment-mark";
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { Icon, StatusMark } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { TagList } from "@/shared/components/tag-list";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";
import type { ScreenEdit } from "@/shared/core/edits";
import { bodyFormatOf, compareIds, type Item } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** 納品物を先頭に、それぞれ連番の順に並べる */
export const orderDocs = (docs: readonly Item[]): Item[] => [...docs].sort((a, b) => Number(b.deliverable === true) - Number(a.deliverable === true) || compareIds(a.id, b.id));

/** 納品物の札 */
export const DeliverableBadge = () => <span className="rounded-control bg-mark-weak px-1 text-xs text-mark">納品物</span>;

export type DocCardProps = { doc: Item; inBoard: boolean; selected: boolean; marks: DiffMarks | undefined; comments: Record<string, number>; edit: ScreenEdit | null; onOpen: (id: string) => void };

export const DocCard = ({ doc, inBoard, selected, marks, comments, edit, onOpen }: DocCardProps) => {
  const format = bodyFormatOf(doc.body);
  const mark = marks?.[doc.id];
  const pending = edit?.marks[doc.id];
  const count = comments[doc.id] ?? 0;
  return (
    <button type="button" data-id={doc.id} aria-current={selected ? "true" : undefined} className={cn("flex w-full cursor-pointer flex-col gap-1 rounded-card border border-border-soft bg-card p-3 text-left hover:bg-row-hover", doc.deliverable === true && "border-mark-line", selected && inBoard && "bg-row-selected", pending === "remove" && "opacity-60")} onClick={() => { onOpen(doc.id); }}>
      {doc.deliverable === true ? <DeliverableBadge /> : null}
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        <Icon name={doc.kind === "図" ? "graph" : "cards"} className="size-3" />
        {doc.kind}
        {format === null ? null : <BodyFormatBadge format={format} />}
      </span>
      <h3 className="m-0 text-small font-medium">{doc.title}</h3>
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
        <span>{[doc.category, doc.phase].filter(Boolean).join(" · ")}</span>
        {pending === undefined ? null : <PendingMark kind={pending} />}
        {count > 0 ? <CommentMark count={count} /> : null}
      </span>
      {(doc.tags ?? []).length > 0 ? (
        <span className="flex flex-wrap gap-1">
          <TagList values={doc.tags} />
        </span>
      ) : null}
    </button>
  );
};
