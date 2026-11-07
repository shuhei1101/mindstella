// コメントの一覧（画面設計『コメントの一覧.tsx』）。スレッドを状態とタグで絞って並べ、新しいスレッドを立てる左のパネル。パネルの中をスレッド・レビュー中の書き込みの画面と切り替える
import { useState } from "react";

import { ReviewView } from "@/features/comments/review/review-view";
import { ThreadRow } from "@/features/comments/shared/thread-row";
import { useCommentData } from "@/features/comments/shared/use-comment-data";
import { ThreadView } from "@/features/comments/thread/thread-view";
import { Icon } from "@/shared/components/icon";
import { SendForm, type SendStatus } from "@/shared/components/send-form";
import { Button } from "@/shared/components/ui/button";
import { AppError } from "@/shared/core/app-error";
import { pendingThreads, threadCounts, visibleThreads, type ThreadFilter } from "@/shared/core/comments";
import { useAddComment, useSaveDraft } from "@/shared/hooks/use-comments";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { cn } from "@/shared/lib/cn";
import { usePrefs, writePrefs } from "@/shared/stores/prefs-store";

const FILTERS = [
  { key: "open", label: "オープン" },
  { key: "closed", label: "クローズ" },
  { key: "all", label: "すべて" },
] as const satisfies readonly { key: ThreadFilter; label: string }[];

export type CommentsPanelProps = {
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
};

export const CommentsPanel = ({ onOpenItem, onOpenChangeSet }: CommentsPanelProps) => {
  const { search, setPanel, setComments } = usePreviewSearch();
  const data = useCommentData();
  const pinned = usePrefs().commentsPinned === true;
  const filter: ThreadFilter = search.tstatus ?? "open";
  const tag = search.ttag ?? null;
  const add = useAddComment();
  const saveDraft = useSaveDraft();
  const freeDraft = data.drafts.find((draft) => draft.target === null && draft.thread === null)?.body ?? "";
  const [composing, setComposing] = useState(false);
  const [free, setFree] = useState<{ body: string; status: SendStatus; count: number | null; detail: string | null }>({ body: freeDraft, status: "idle", count: null, detail: null });
  const close = (): void => {
    setPanel(undefined);
  };
  const counts = threadCounts({ threads: data.threads, tag });
  const rows = visibleThreads({ threads: data.threads, filter, tag });
  const pending = pendingThreads({ items: data.items, filter, tag });
  const repliesOf = new Set(data.items.map((item) => item.thread).filter((thread): thread is string => thread !== null));
  const header = (
    <div className="flex items-center gap-2 border-b border-border px-3 py-2">
      <h2 className="m-0 flex-1 text-body font-medium">コメント</h2>
      {search.review === undefined ? (
        <Button variant="outline" aria-label={`レビュー中の書き込みを確かめる（${String(data.items.length)} 件）`} onClick={() => { setComments({ review: "1" }); }}>
          レビュー中
          <span className={cn("rounded-full px-1.5 text-small", data.items.length > 0 && "bg-primary text-primary-foreground")}>{data.items.length}</span>
        </Button>
      ) : null}
      <Button variant="ghost" size="icon" aria-pressed={pinned} aria-label={pinned ? "ピン止めを外す（外側を押したら閉じる）" : "ピン止めする（外側を押しても閉じない）"} title={pinned ? "ピン止めを外す" : "ピン止めする"} onClick={() => { writePrefs({ commentsPinned: pinned ? null : true }); }}>
        <Icon name="lock" className={cn(!pinned && "-rotate-45", pinned && "text-primary")} />
      </Button>
      <Button variant="ghost" size="icon" aria-label="コメントの一覧を閉じる" onClick={close}>
        <Icon name="x" />
      </Button>
    </div>
  );
  const body = (() => {
    if (search.review !== undefined) {
      return <ReviewView data={data} highlight={search.thread ?? null} onBack={() => { setComments({ review: undefined }); }} onOpenThread={(id) => { setComments({ review: undefined, thread: id }); }} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />;
    }
    if (search.thread !== undefined) {
      return <ThreadView key={search.thread} id={search.thread} data={data} onBack={() => { setComments({ thread: undefined }); }} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />;
    }
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <div role="group" aria-label="スレッドの状態で絞る" className="flex gap-1 border-b border-border px-3 py-2">
          {FILTERS.map((entry) => (
            <Button key={entry.key} variant={filter === entry.key ? "secondary" : "ghost"} aria-pressed={filter === entry.key} onClick={() => { setComments({ tstatus: entry.key === "open" ? undefined : entry.key }); }}>
              {entry.label}
              <span className="font-mono text-small">{counts[entry.key]}</span>
            </Button>
          ))}
        </div>
        {tag === null ? null : (
          <div className="flex items-center gap-1 border-b border-border px-3 py-1 text-small">
            <span>#{tag}</span>
            <Button variant="ghost" size="icon" aria-label={`タグ「${tag}」の絞り込みを外す`} onClick={() => { setComments({ ttag: undefined }); }}>
              <Icon name="x" />
            </Button>
            <span className="text-muted-foreground">{`${String(rows.length)} / ${String(visibleThreads({ threads: data.threads, filter, tag: null }).length)} 件`}</span>
          </div>
        )}
        {data.threadsError === null ? null : (
          <p role="alert" className="m-0 flex items-start gap-1 px-3 py-2 text-small text-destructive">
            <Icon name="alert" />
            <span>{`スレッドを読めませんでした。${data.threadsError.detail ?? "サーバーが止まっています。立ち上げ直してから開いてください。"}`}</span>
          </p>
        )}
        <ul className="m-0 min-h-0 flex-1 list-none overflow-y-auto p-0">
          {pending.map((item) => (
            <ThreadRow key={item.id} pending={item} onOpen={(id) => { setComments({ thread: id }); }} onTag={() => undefined} />
          ))}
          {rows.map((thread) => (
            <ThreadRow key={thread.id} thread={thread} hasPendingReply={repliesOf.has(thread.id)} activeTag={tag} onOpen={(id) => { setComments({ thread: id }); }} onTag={(next) => { setComments({ ttag: next === tag ? undefined : next }); }} />
          ))}
        </ul>
        {pending.length === 0 && rows.length === 0 && data.threadsError === null ? (
          <p className="m-0 flex items-center gap-1 px-3 py-2 text-small text-muted-foreground">
            <Icon name="comment" />
            {`${tag === null ? "" : `タグ「${tag}」の`}${filter === "open" ? "オープンの" : filter === "closed" ? "クローズの" : ""}スレッドはありません。`}
          </p>
        ) : null}
        {composing ? (
          <div className="grid border-t border-border">
            <div className="flex items-center px-3 pt-2">
              <h3 className="m-0 flex-1 text-small font-medium">新しいスレッド</h3>
              <Button variant="ghost" size="icon" aria-label="新しいスレッドの入力を閉じる" onClick={() => { setComposing(false); }}>
                <Icon name="x" />
              </Button>
            </div>
            <SendForm
              target={null}
              loc={null}
              label="新しいスレッド"
              body={free.body}
              status={free.status}
              count={free.count}
              detail={free.detail}
              onInput={(next) => {
                setFree({ body: next, status: "idle", count: null, detail: null });
                saveDraft({ target: null, loc: null, thread: null, body: next });
              }}
              onSubmit={(_target, _loc, text) => {
                setFree((current) => ({ ...current, status: "saving" }));
                add.mutate(
                  { body: text },
                  {
                    onSuccess: (result) => { setFree({ body: "", status: "saved", count: (result as { count?: number }).count ?? null, detail: null }); },
                    onError: (error) => { setFree((current) => ({ ...current, status: "failed", detail: error instanceof AppError ? error.message : null })); },
                  },
                );
              }}
            />
          </div>
        ) : (
          <div className="border-t border-border p-3">
            <Button variant="outline" onClick={() => { setComposing(true); }}>
              <Icon name="plus" />
              新しいスレッド
            </Button>
          </div>
        )}
      </div>
    );
  })();
  return (
    <>
      {pinned ? null : <div data-scrim aria-hidden="true" className="fixed inset-0 z-20 bg-foreground/40" onClick={close} />}
      <aside
        role="dialog"
        aria-modal={!pinned}
        aria-label="コメント"
        className="fixed inset-y-0 left-0 z-30 flex w-96 max-w-full flex-col border-r border-border bg-card"
        onKeyDown={(event) => {
          if (event.key !== "Escape") return;
          event.stopPropagation();
          if (search.review !== undefined) setComments({ review: undefined });
          else if (search.thread !== undefined) setComments({ thread: undefined });
          else close();
        }}
      >
        {header}
        {body}
      </aside>
    </>
  );
};
