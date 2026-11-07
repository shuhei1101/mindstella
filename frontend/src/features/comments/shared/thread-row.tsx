// スレッドの行（部品設計『スレッドの行.tsx』）。状態の札・題・向けた項目・最後の書き手と日時・レビュー中の印・タグを出し、押すとそのスレッドを開く
import { AUTHOR_LABELS, PendingMark, ThreadState, UnseenMark, type ThreadStateKind } from "@/features/comments/shared/thread-state";
import { hasUnseen, threadTitle, type ReviewItem, type Thread } from "@/shared/core/comments";
import { formatJst } from "@/shared/core/format";
import { cn } from "@/shared/lib/cn";

export type ThreadRowProps = {
  /** 送ったスレッド。`pending` とどちらか片方 */
  thread?: Thread | null;
  /** まだ送っていない新しいスレッドの最初の書き込み */
  pending?: ReviewItem | null;
  hasPendingReply?: boolean;
  activeTag?: string | null;
  onOpen: (id: string) => void;
  onTag: (tag: string) => void;
};

// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
export const ThreadRow = ({ thread = null, pending = null, hasPendingReply = false, activeTag = null, onOpen, onTag }: ThreadRowProps) => {
  const last = thread?.posts.at(-1) ?? null;
  const sent = thread !== null && last !== null;
  const id = sent ? thread.id : (pending?.id ?? "");
  const target = sent ? thread.target : (pending?.target ?? null);
  const author = sent ? last.author : "user";
  const created = sent ? last.created : (pending?.created ?? "");
  const title = sent ? threadTitle(thread) : ((pending?.body ?? "").split("\n")[0] ?? "");
  const status: ThreadStateKind = sent ? thread.status : "pending";
  const unseen = sent && hasUnseen(thread);
  return (
    <li data-thread={sent ? id : undefined} data-pending={sent ? undefined : id} className={cn("grid gap-1 border-b border-border", unseen && "bg-accent")}>
      <button type="button" className="grid w-full cursor-pointer gap-1 px-3 py-2 text-left hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring" data-focus={sent ? `thread:${id}` : `thread:new:${id}`} onClick={() => onOpen(id)}>
        <span className="flex min-w-0 items-center gap-2">
          <ThreadState status={status} />
          <span className="truncate font-medium">{title}</span>
        </span>
        <span className="flex min-w-0 items-center gap-2 text-small text-muted-foreground">
          {unseen ? <UnseenMark /> : null}
          {target === null ? null : <span className="truncate font-mono">{target}</span>}
          <span>{AUTHOR_LABELS[author]}</span>
          <time dateTime={created} className="flex-none">
            {created === "" ? "" : formatJst(created)}
          </time>
          {hasPendingReply ? <PendingMark /> : null}
        </span>
      </button>
      {!sent || thread.tags.length === 0 ? null : (
        <span className="flex flex-wrap gap-1 px-3 pb-2">
          {thread.tags.map((tag) => (
            <button key={tag} type="button" aria-pressed={tag === activeTag} aria-label={`タグ「${tag}」で絞る`} className={cn("cursor-pointer rounded-control border border-border px-1.5 text-small", tag === activeTag && "bg-accent")} onClick={() => onTag(tag)}>
              #{tag}
            </button>
          ))}
        </span>
      )}
    </li>
  );
};
