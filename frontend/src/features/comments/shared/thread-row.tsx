// スレッドの行（部品設計『スレッドの行.tsx』）。状態の札・題・向けた項目・最後の書き手と日時・レビュー中の印・タグを出し、押すとそのスレッドを開く
import { AUTHOR_LABELS, PendingMark, STATE_LABELS, ThreadState, UnseenMark, type ThreadStateKind } from "@/features/comments/shared/thread-state";
import { Icon } from "@/shared/components/icon";
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
  const summarized = sent && thread.summary !== null && thread.summary !== "";
  const status: ThreadStateKind = sent ? thread.status : "pending";
  const unseen = sent && hasUnseen(thread);
  // 未読の行は、読み上げの名前が状態の次に「未読」を読む
  const openLabel = unseen ? [STATE_LABELS[status].label, "未読", title, target, AUTHOR_LABELS[author], formatJst(created), hasPendingReply ? "レビュー中の返信あり" : null].filter((part) => part !== null).join("、") : undefined;
  return (
    <li data-thread={sent ? id : undefined} data-pending={sent ? undefined : id} data-unread={unseen ? "" : undefined} className={cn("grid rounded-control border border-border bg-card hover:bg-accent", !sent && "border-dashed")}>
      <button type="button" aria-label={openLabel} className={cn("grid w-full cursor-pointer gap-1 px-3 py-2 text-left focus-visible:outline-2 focus-visible:outline-ring", sent && thread.tags.length > 0 && "pb-1")} data-focus={sent ? `thread:${id}` : `thread:new:${id}`} onClick={() => onOpen(id)}>
        <span data-part="line1" className="flex min-w-0 items-start gap-2">
          <ThreadState status={status} />
          <span data-part="title" className={cn("line-clamp-2 min-w-0 wrap-anywhere", summarized ? "font-semibold" : "font-normal")}>
            {title}
          </span>
        </span>
        <span data-part="line2" className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-xs text-muted-foreground tabular-nums">
          {unseen ? <UnseenMark /> : null}
          {target === null ? null : <span data-part="target" className="font-mono text-foreground">{target}</span>}
          <span data-part="author" className={cn("font-semibold", unseen && "text-foreground")}>{AUTHOR_LABELS[author]}</span>
          <time dateTime={created} className={cn("flex-none", unseen && "text-foreground")}>
            {created === "" ? "" : formatJst(created)}
          </time>
          {hasPendingReply ? <PendingMark /> : null}
        </span>
      </button>
      {!sent || thread.tags.length === 0 ? null : (
        <span data-part="tags" className="flex flex-wrap gap-1.5 px-3 pb-2.5">
          {thread.tags.map((tag) => (
            <button key={tag} type="button" aria-pressed={tag === activeTag} aria-label={`タグ「${tag}」で絞る`} data-focus={`tag:${id}:${tag}`} className={cn("inline-flex min-h-6 cursor-pointer items-center gap-0.5 rounded-kbd border border-border-soft bg-muted pr-2 pl-1 text-xs text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring", tag === activeTag && "border-mark-line bg-mark-weak text-foreground")} onClick={() => onTag(tag)}>
              <Icon name="hash" className="size-3" />
              {tag}
            </button>
          ))}
        </span>
      )}
    </li>
  );
};
