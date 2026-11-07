// レビュー中の書き込み（画面設計『レビュー中の書き込み.tsx』）。新しいスレッドの最初の書き込みとスレッドへの返信を溜めた順に並べ、チェックしたものだけをまとめて送る
import { useState } from "react";

import { ReviewEditForm } from "@/features/comments/shared/review-edit-form";
import { ThreadState } from "@/features/comments/shared/thread-state";
import type { CommentData } from "@/features/comments/shared/use-comment-data";
import { Icon } from "@/shared/components/icon";
import { ReviewBodyFold } from "@/shared/components/review-body-fold";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { AppError } from "@/shared/core/app-error";
import { commentNumber, isBlockedReply, reviewLabel, threadTitle, type ReviewItem } from "@/shared/core/comments";
import { formatJst } from "@/shared/core/format";
import { locationLabel } from "@/shared/core/records";
import { useAddComment, useRemoveComment, useSendComments, useUpdateComment } from "@/shared/hooks/use-comments";
import { cn } from "@/shared/lib/cn";

export type ReviewViewProps = {
  data: CommentData;
  /** 開く前に見ていたスレッド（その書き込みの行を示す） */
  highlight: string | null;
  onBack: () => void;
  onOpenThread: (id: string) => void;
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
};

/** まとめて送った結果 */
type SendOutcome = { kind: "sending" } | { kind: "sent"; count: number; at: string; entered: boolean } | { kind: "stale"; count: number } | { kind: "failed"; detail: string | null };

const OutcomeText = ({ outcome }: { outcome: SendOutcome }) => {
  if (outcome.kind === "sending") {
    return (
      <>
        <Icon name="spin" className="animate-spin" />
        <span>送っています</span>
      </>
    );
  }
  if (outcome.kind === "sent") {
    const time = formatJst(outcome.at).slice(-5);
    return outcome.entered ? (
      <>
        <Icon name="check" />
        <span>{`${String(outcome.count)} 件を送り、Claude Code に入力しました（${time}）。`}</span>
      </>
    ) : (
      <>
        <Icon name="alert" />
        <span>{`${String(outcome.count)} 件を送りましたが、Claude Code には入力できませんでした（${time}）。送った内容は保存されていて、次に話し合いを始めたときに取り込まれます。`}</span>
      </>
    );
  }
  if (outcome.kind === "stale") {
    return (
      <>
        <Icon name="alert" />
        <span>{`送れませんでした。送れない書き込みが ${String(outcome.count)} 件あります。`}</span>
      </>
    );
  }
  return (
    <>
      <Icon name="alert" />
      <span>{outcome.detail === null ? "送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。" : `送れませんでした。${outcome.detail}`}</span>
    </>
  );
};

export const ReviewView = ({ data, highlight, onBack, onOpenThread, onOpenItem, onOpenChangeSet }: ReviewViewProps) => {
  const { items, threads, titles, changeSets } = data;
  const sorted = [...items].sort((a, b) => commentNumber(a.id) - commentNumber(b.id));
  const sendable = sorted.filter((item) => !isBlockedReply({ item, threads }));
  // チェックを外した書き込み（開いたときと新しく溜めた書き込みはチェックした状態で入る）
  const [unchecked, setUnchecked] = useState<ReadonlySet<string>>(new Set());
  const [removed, setRemoved] = useState<ReviewItem[]>([]);
  const [stale, setStale] = useState<Record<string, string>>({});
  const [outcome, setOutcome] = useState<SendOutcome | null>(null);
  const [editing, setEditing] = useState<{ id: string; error: string | null } | null>(null);
  const [opened, setOpened] = useState<Record<string, boolean>>({});
  const send = useSendComments();
  const update = useUpdateComment();
  const remove = useRemoveComment();
  const add = useAddComment();
  const checked = sendable.filter((item) => !unchecked.has(item.id));
  const allChecked = checked.length === sendable.length && sendable.length > 0;
  const toggle = (id: string): void => {
    setUnchecked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const sendChecked = (): void => {
    const ids = checked.map((item) => item.id);
    if (ids.length === 0 || send.isPending) return;
    setOutcome({ kind: "sending" });
    send.mutate(ids, {
      onSuccess: (reply) => {
        setStale({});
        setOutcome({ kind: "sent", count: ids.length, at: reply.sent, entered: reply.entered });
      },
      onError: (error) => {
        if (error instanceof AppError && error.statusCode === 409) {
          const list = (error.body as { stale?: { id: string; reason: string }[] } | null)?.stale ?? [];
          setStale(Object.fromEntries(list.map((entry) => [entry.id, entry.reason])));
          setOutcome({ kind: "stale", count: list.length });
          return;
        }
        setOutcome({ kind: "failed", detail: error instanceof AppError ? error.message : null });
      },
    });
  };
  const rows: (ReviewItem & { gone?: boolean })[] = [...sorted, ...removed.map((item) => ({ ...item, gone: true }))].sort((a, b) => commentNumber(a.id) - commentNumber(b.id));
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Button variant="ghost" onClick={onBack}>
          <Icon name="back" />
          戻る
        </Button>
        <h2 className="m-0 flex-1 text-body font-medium">{`レビュー中の書き込み（${String(items.length)}）`}</h2>
      </div>
      {items.length === 0 && removed.length === 0 ? (
        <p className="m-0 flex items-center gap-1 p-3 text-small text-muted-foreground">
          <Icon name="comment" />
          レビュー中の書き込みはありません。
        </p>
      ) : (
        <>
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Checkbox
              aria-label="すべて選ぶ"
              title="すべて選ぶ"
              checked={allChecked}
              ref={(element) => {
                if (element !== null) element.indeterminate = checked.length > 0 && !allChecked;
              }}
              onChange={() => {
                setUnchecked(allChecked ? new Set(sendable.map((item) => item.id)) : new Set());
              }}
            />
            <span className="flex-1 text-small">{`${String(checked.length)} / ${String(sendable.length)} 件`}</span>
            <Button disabled={checked.length === 0 || send.isPending} onClick={sendChecked}>
              <Icon name="comment" />
              {`まとめて送る（${String(checked.length)} 件）`}
            </Button>
          </div>
          {outcome === null ? null : (
            <p role="status" className="m-0 flex items-start gap-1 px-3 py-2 text-small">
              <OutcomeText outcome={outcome} />
            </p>
          )}
          <ul className="m-0 grid min-h-0 flex-1 list-none content-start gap-2 overflow-y-auto p-3">
            {/* eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ */}
            {rows.map((item) => {
              const label = reviewLabel(item);
              if (item.gone === true) {
                return (
                  <li key={item.id} className="flex items-center gap-2 rounded-card border border-border p-2 text-small">
                    <span role="status" className="flex-1">
                      コメントを削除しました。
                    </span>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        add.mutate({ id: item.id, created: item.created, target: item.target, loc: item.loc, thread: item.thread, body: item.body }, { onSuccess: () => { setRemoved((current) => current.filter((one) => one.id !== item.id)); } });
                      }}
                    >
                      <Icon name="undo" />
                      元に戻す
                    </Button>
                  </li>
                );
              }
              const blocked = isBlockedReply({ item, threads });
              const staleReason = stale[item.id];
              const replyTo = item.thread === null ? null : (threads.find((one) => one.id === item.thread) ?? null);
              return (
                <li key={item.id} data-comment={item.id} className={cn("grid gap-1 rounded-card border p-2", staleReason === undefined ? "border-border" : "border-destructive", highlight !== null && (item.thread === highlight || item.id === highlight) && "bg-accent")}>
                  <div className="flex items-center gap-2 text-small">
                    <Checkbox aria-label={item.thread === null ? `${item.target ?? "項目を指さない"}${item.target === null ? "コメントを送る" : " へのコメントを送る"}` : `${item.thread} への返信を送る`} checked={!blocked && !unchecked.has(item.id)} disabled={blocked} onChange={() => { toggle(item.id); }} />
                    <span className="rounded-control border border-border px-1.5">{item.thread === null ? "新しいスレッド" : "返信"}</span>
                    {replyTo === null ? null : (
                      <button type="button" className="flex min-w-0 cursor-pointer items-center gap-1" onClick={() => { onOpenThread(replyTo.id); }}>
                        <ThreadState status={replyTo.status} />
                        <span className="truncate">{threadTitle(replyTo)}</span>
                      </button>
                    )}
                    {item.thread === null && item.target !== null ? (
                      <button type="button" className="flex min-w-0 cursor-pointer items-center gap-1" disabled={titles(item.target) === null} onClick={() => { onOpenItem(item.target ?? ""); }}>
                        <span className="font-mono">{item.target}</span>
                        <span className="truncate">{titles(item.target) ?? ""}</span>
                      </button>
                    ) : null}
                    <span className="flex-1" />
                    {editing?.id === item.id ? null : (
                      <>
                        <Button variant="ghost" size="icon" aria-label={`${label}を修正`} title="修正" onClick={() => { setEditing({ id: item.id, error: null }); }}>
                          <Icon name="edit" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`${label}を削除`}
                          title="削除"
                          onClick={() => {
                            remove.mutate(item.id, { onSuccess: (content) => { setRemoved((current) => [...current, { id: content.id, target: content.target ?? null, loc: (content.loc as ReviewItem["loc"] | undefined) ?? null, thread: content.thread ?? null, body: content.body, created: content.created }]); } });
                          }}
                        >
                          <Icon name="trash" />
                        </Button>
                      </>
                    )}
                  </div>
                  {item.loc === null ? null : (
                    <div className="grid gap-0.5 text-small">
                      <span className="font-medium">{locationLabel(item.loc)}</span>
                      <blockquote className="m-0 line-clamp-3 text-muted-foreground">{item.loc.text}</blockquote>
                    </div>
                  )}
                  {editing?.id === item.id ? (
                    <ReviewEditForm
                      id={item.id}
                      label={label}
                      body={item.body}
                      error={editing.error}
                      onCancel={() => { setEditing(null); }}
                      onSubmit={(target, body) => {
                        update.mutate({ id: target, body }, { onSuccess: () => { setEditing(null); }, onError: (error) => { setEditing({ id: target, error: error instanceof AppError ? error.message : "サーバーが止まっています。立ち上げ直してから直してください。" }); } });
                      }}
                    />
                  ) : (
                    <ReviewBodyFold id={item.id} label={label} body={item.body} titles={titles} changeSets={changeSets} open={opened[item.id] ?? false} onToggle={(id, open) => { setOpened((current) => ({ ...current, [id]: open })); }} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet}>
                      {(content, toggleButton) => (
                        <>
                          {content}
                          <div className="flex flex-wrap items-center gap-1">
                            {item.thread === null ? (
                              <Button variant="ghost" onClick={() => { onOpenThread(item.id); }}>
                                スレッドを開く
                              </Button>
                            ) : null}
                            {toggleButton}
                          </div>
                        </>
                      )}
                    </ReviewBodyFold>
                  )}
                  {blocked ? (
                    <p className="m-0 flex flex-wrap items-center gap-1 text-small">
                      <Icon name="alert" />
                      <span>クローズのスレッドへの返信は送れません。オープンに戻すと送れます。</span>
                      <Button variant="ghost" onClick={() => { onOpenThread(item.thread ?? ""); }}>
                        スレッドを開く
                      </Button>
                    </p>
                  ) : null}
                  {staleReason === undefined ? null : (
                    <div className="grid gap-1">
                      <p role="alert" className="m-0 flex items-start gap-1 text-small text-destructive">
                        <Icon name="alert" />
                        <span>{staleReason}</span>
                      </p>
                      <Button
                        variant="outline"
                        className="justify-self-start"
                        onClick={() => {
                          update.mutate({ id: item.id, loc: null }, { onSuccess: () => { setStale((current) => Object.fromEntries(Object.entries(current).filter(([key]) => key !== item.id))); } });
                        }}
                      >
                        箇所を外す
                      </Button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
};
