// スレッド（画面設計『スレッド.tsx』）。書き込みと状態の変更を書いた順に並べ、下端で返信を溜め、上端でクローズとオープンへの戻しをする
import { useEffect, useId, useRef, useState } from "react";

import { ReplyForm, type ReplyStatus } from "@/features/comments/shared/reply-form";
import { ThreadPost } from "@/features/comments/shared/thread-post";
import { ThreadState } from "@/features/comments/shared/thread-state";
import type { CommentData } from "@/features/comments/shared/use-comment-data";
import { useMarkThreadSeen, useSetThreadStatus } from "@/features/comments/shared/use-threads";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { AppError } from "@/shared/core/app-error";
import { hasUnseen, threadTimeline, threadTitle, type ReviewItem } from "@/shared/core/comments";
import { useAddComment, useRemoveComment, useSaveDraft, useUpdateComment } from "@/shared/hooks/use-comments";

export type ThreadViewProps = {
  /** 開くスレッドの ID（まだ送っていない新しいスレッドはコメントの ID） */
  id: string;
  data: CommentData;
  onBack: () => void;
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
};

/** 失敗の理由（届かなければ null） */
const detailOf = (error: unknown): string | null => (error instanceof AppError ? error.message : null);

// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
export const ThreadView = ({ id, data, onBack, onOpenItem, onOpenChangeSet }: ThreadViewProps) => {
  const { threads, items, drafts, titles, changeSets } = data;
  const thread = threads.find((one) => one.id === id) ?? null;
  const pendingNew = thread === null ? (items.find((item) => item.id === id && item.thread === null) ?? null) : null;
  const replies = items.filter((item) => item.thread === id);
  const markSeen = useMarkThreadSeen();
  const setStatus = useSetThreadStatus();
  const addComment = useAddComment();
  const updateComment = useUpdateComment();
  const removeComment = useRemoveComment();
  const saveDraft = useSaveDraft();
  // 開いている間に既読を呼んだスレッド（失敗して読み直しても、開いている間は呼び直さない）
  const seenCalled = useRef(new Set<string>());
  useEffect(() => {
    if (thread === null || !hasUnseen(thread) || seenCalled.current.has(thread.id)) return;
    seenCalled.current.add(thread.id);
    markSeen.mutate(thread.id);
  }, [thread, markSeen]);
  const draft = drafts.find((one) => one.thread === id && one.target === null)?.body ?? "";
  const [reply, setReply] = useState<{ body: string; status: ReplyStatus; count: number | null; detail: string | null }>({ body: draft, status: "idle", count: null, detail: null });
  const reasonId = useId();
  const [reason, setReason] = useState<{ open: boolean; body: string; detail: string | null; failed: boolean }>({ open: false, body: "", detail: null, failed: false });
  const [editing, setEditing] = useState<{ id: string; error: string | null } | null>(null);
  const [opened, setOpened] = useState<Record<string, boolean>>({});

  const closed = thread?.status === "closed";
  const nextStatus = closed ? "open" : "closed";
  const actionLabel = closed ? "オープンに戻す" : "クローズにする";
  const submitStatus = (): void => {
    if (thread === null) return;
    const text = reason.body.trim();
    setStatus.mutate(
      { id: thread.id, status: nextStatus, reason: text === "" ? null : text },
      {
        onSuccess: () => {
          setReason({ open: false, body: "", detail: null, failed: false });
        },
        onError: (error) => {
          setReason((current) => ({ ...current, detail: detailOf(error), failed: true }));
        },
      },
    );
  };
  const submitReply = (target: string, body: string): void => {
    setReply((current) => ({ ...current, status: "saving" }));
    addComment.mutate(
      { target: null, loc: null, thread: target, body },
      {
        onSuccess: (result) => {
          setReply({ body: "", status: "saved", count: (result as { count?: number }).count ?? null, detail: null });
        },
        onError: (error) => {
          setReply((current) => ({ ...current, status: "failed", detail: detailOf(error) }));
        },
      },
    );
  };
  const pendingPost = (item: ReviewItem) => (
    <li key={item.id}>
      <ThreadPost
        pending={item}
        titles={titles}
        changeSets={changeSets}
        editing={editing?.id === item.id}
        editError={editing?.id === item.id ? editing.error : null}
        open={opened[item.id] ?? false}
        onOpenItem={onOpenItem}
        onOpenChangeSet={onOpenChangeSet}
        onEditStart={(target) => {
          setEditing({ id: target, error: null });
        }}
        onEditCancel={() => {
          setEditing(null);
        }}
        onEditSubmit={(target, body) => {
          updateComment.mutate(
            { id: target, body },
            {
              onSuccess: () => {
                setEditing(null);
              },
              onError: (error) => {
                setEditing({ id: target, error: detailOf(error) ?? "サーバーが止まっています。立ち上げ直してから直してください。" });
              },
            },
          );
        }}
        onRemove={(target) => {
          removeComment.mutate(target);
        }}
        onToggle={(target, open) => {
          setOpened((current) => ({ ...current, [target]: open }));
        }}
      />
    </li>
  );
  const title = thread === null ? ((pendingNew?.body ?? "").split("\n")[0] ?? "") : threadTitle(thread);
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Button variant="ghost" onClick={onBack}>
          <Icon name="back" />
          一覧へ戻る
        </Button>
        <span className="flex-1" />
        {thread === null || reason.open ? null : (
          <Button variant="outline" onClick={() => { setReason({ open: true, body: "", detail: null, failed: false }); }}>
            <Icon name={closed ? "undo" : "check"} />
            {actionLabel}
          </Button>
        )}
      </div>
      {reason.open && thread !== null ? (
        <div className="grid gap-1.5 border-b border-border px-3 py-2">
          <label htmlFor={reasonId} className="grid gap-1 text-small">
            理由（任意）
            <Input id={reasonId} ref={(element) => { element?.focus(); }} value={reason.body} onChange={(event) => { setReason((current) => ({ ...current, body: event.target.value })); }} onKeyDown={(event) => {
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
                event.preventDefault();
                submitStatus();
              }
            }} />
          </label>
          {reason.failed ? (
            <p role="alert" className="m-0 flex items-start gap-1 text-small text-destructive">
              <Icon name="alert" />
              <span>{`${closed ? "オープンに戻せませんでした。" : "クローズにできませんでした。"}${reason.detail ?? "サーバーが止まっています。立ち上げ直してから押してください。"}`}</span>
            </p>
          ) : null}
          <div className="flex justify-end gap-1.5">
            <Button variant="ghost" onClick={() => { setReason({ open: false, body: "", detail: null, failed: false }); }}>
              キャンセル
            </Button>
            <Button disabled={setStatus.isPending} onClick={submitStatus}>
              {actionLabel}
            </Button>
          </div>
        </div>
      ) : null}
      <div className="grid gap-1 border-b border-border px-3 py-2">
        <h2 className="m-0 flex items-center gap-2 text-body font-medium">
          <ThreadState status={thread === null ? "pending" : thread.status} />
          <span>{title}</span>
        </h2>
        {thread?.target === null || thread?.target === undefined ? null : (
          <button type="button" className="flex cursor-pointer items-center gap-1 text-left text-small" disabled={titles(thread.target) === null} onClick={() => { onOpenItem(thread.target ?? ""); }}>
            <span className="font-mono">{thread.target}</span>
            <span className="truncate">{titles(thread.target) ?? ""}</span>
          </button>
        )}
        {thread === null || thread.tags.length === 0 ? null : (
          <span className="flex flex-wrap gap-1 text-small text-muted-foreground">
            {thread.tags.map((tag) => (
              <span key={tag}>#{tag}</span>
            ))}
          </span>
        )}
      </div>
      <ol className="m-0 grid min-h-0 flex-1 list-none content-start gap-2 overflow-y-auto p-3">
        {thread === null
          ? pendingNew === null
            ? null
            : pendingPost(pendingNew)
          : threadTimeline(thread).map((entry) => ("post" in entry ? (
            <li key={entry.post.id}>
              <ThreadPost post={entry.post} titles={titles} changeSets={changeSets} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />
            </li>
          ) : (
            <li key={`${entry.event.kind}-${entry.event.created}`}>
              <ThreadPost event={entry.event} />
            </li>
          )))}
        {replies.map(pendingPost)}
      </ol>
      {thread === null ? (
        <p className="m-0 flex items-center gap-1 border-t border-border p-3 text-small text-muted-foreground">
          <Icon name="edit" />
          まだ送っていないスレッドです。
        </p>
      ) : closed ? (
        <p className="m-0 flex items-center gap-1 border-t border-border p-3 text-small text-muted-foreground">
          <Icon name="check" />
          クローズにしたスレッドです。
        </p>
      ) : (
        <ReplyForm
          thread={thread.id}
          body={reply.body}
          status={reply.status}
          count={reply.count}
          detail={reply.detail}
          onInput={(body) => {
            setReply({ body, status: "idle", count: null, detail: null });
            saveDraft({ target: null, loc: null, thread: thread.id, body });
          }}
          onSubmit={submitReply}
        />
      )}
    </div>
  );
};
