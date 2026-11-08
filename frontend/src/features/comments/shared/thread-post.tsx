// スレッドの書き込み（部品設計『スレッドの書き込み.tsx』）。利用者と AI の書き込み・クローズとオープンへの戻しの記録・レビュー中の書き込みのどれか 1 つを出す
import { ReviewEditForm } from "@/features/comments/shared/review-edit-form";
import { AUTHOR_LABELS, PendingMark } from "@/features/comments/shared/thread-state";
import { Icon } from "@/shared/components/icon";
import { PostBody } from "@/shared/components/post-body";
import { ReviewBodyFold } from "@/shared/components/review-body-fold";
import { Button } from "@/shared/components/ui/button";
import { reviewLabel, type ReviewItem, type ThreadEvent, type ThreadPostData } from "@/shared/core/comments";
import { formatJst } from "@/shared/core/format";
import type { LookupTitle } from "@/shared/core/post-links";
import { cn } from "@/shared/lib/cn";

export type ThreadPostProps = {
  post?: ThreadPostData | null;
  event?: ThreadEvent | null;
  pending?: ReviewItem | null;
  titles?: LookupTitle;
  changeSets?: LookupTitle;
  editing?: boolean;
  editError?: string | null;
  editBody?: string | null;
  open?: boolean;
  onOpenItem?: (id: string) => void;
  onEditStart?: (id: string) => void;
  onEditSubmit?: (id: string, body: string) => void;
  onEditCancel?: (id: string) => void;
  onRemove?: (id: string) => void;
  onOpenChangeSet?: (id: string) => void;
  onToggle?: (id: string, open: boolean) => void;
};

const noop = (): void => undefined;

/** 状態の記録（枠の無い 1 行に、書き手・したこと・日時と、あれば理由） */
const EventItem = ({ event }: { event: ThreadEvent }) => {
  const closed = event.kind === "closed";
  return (
    <article data-event={event.kind} data-author={event.author} className="grid gap-0.5 px-1 text-small text-muted-foreground">
      <div data-part="event-line" className="flex items-center gap-1">
        <Icon name={closed ? "check" : "undo"} />
        <span>{`${event.author === "ai" ? "AI が" : "あなたが"}${closed ? "クローズにしました" : "オープンに戻しました"}`}</span>
        <time dateTime={event.created}>{formatJst(event.created)}</time>
      </div>
      {event.reason === null ? null : <p data-part="reason" className="m-0 pl-5">{event.reason}</p>}
    </article>
  );
};

export const ThreadPost = ({
  post = null,
  event = null,
  pending = null,
  titles,
  changeSets,
  editing = false,
  editError = null,
  editBody = null,
  open = false,
  onOpenItem,
  onEditStart = noop,
  onEditSubmit = noop,
  onEditCancel = noop,
  onRemove = noop,
  onOpenChangeSet,
  onToggle = noop,
}: ThreadPostProps) => {
  if (event !== null) return <EventItem event={event} />;
  if (pending !== null) {
    const label = reviewLabel(pending);
    return (
      <article data-author="user" data-comment={pending.id} className="ml-8 grid gap-1 rounded-card border border-dashed border-border bg-card p-2 max-md:ml-4">
        <div className="flex items-center gap-2 text-small">
          <span data-part="author" className="font-medium">{AUTHOR_LABELS.user}</span>
          <PendingMark />
          <span className="flex-1" />
          {editing ? null : (
            <>
              <Button variant="ghost" size="icon" aria-label={`${label}を修正`} title="修正" onClick={() => onEditStart(pending.id)}>
                <Icon name="edit" />
              </Button>
              <Button variant="ghost" size="icon" aria-label={`${label}を削除`} title="削除" onClick={() => onRemove(pending.id)}>
                <Icon name="trash" />
              </Button>
            </>
          )}
        </div>
        {editing ? (
          <ReviewEditForm id={pending.id} label={label} body={editBody ?? pending.body} error={editError} onSubmit={onEditSubmit} onCancel={onEditCancel} />
        ) : (
          <ReviewBodyFold id={pending.id} label={label} body={pending.body} titles={titles} changeSets={changeSets} open={open} onToggle={onToggle} onOpenChangeSet={onOpenChangeSet} onOpenItem={onOpenItem}>
            {(content, toggle) => (
              <>
                {content}
                {toggle === null ? null : (
                  <div data-part="more-row" className="flex">
                    {toggle}
                  </div>
                )}
              </>
            )}
          </ReviewBodyFold>
        )}
      </article>
    );
  }
  if (post === null) throw new Error("ThreadPost には post・event・pending のどれか 1 つを渡す");
  return (
    <article data-author={post.author} className={cn("grid gap-1 rounded-card p-2", post.author === "user" ? "ml-8 border border-border bg-card max-md:ml-4" : "mr-8 bg-muted max-md:mr-4")}>
      <div className="flex items-center gap-2 text-small">
        <span data-part="author" className="font-medium">{AUTHOR_LABELS[post.author]}</span>
        <time dateTime={post.created} className="text-muted-foreground">
          {formatJst(post.created)}
        </time>
      </div>
      <PostBody body={post.body} titles={titles} changeSets={changeSets} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />
    </article>
  );
};
