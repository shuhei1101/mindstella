// コメントの一覧（画面設計『コメントの一覧.tsx』）。スレッドを状態とタグで絞って並べ、新しいスレッドを立てる左のパネル。パネルの中をスレッド・レビュー中の書き込みの画面と切り替える
import { useEffect, useRef, useState } from "react";

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
import { useVoiceInput } from "@/shared/hooks/use-voice-input";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { cn } from "@/shared/lib/cn";
import { usePrefs, writePrefs } from "@/shared/stores/prefs-store";
import { readVoiceState } from "@/shared/stores/voice-store";

const FILTERS = [
  { key: "open", label: "オープン" },
  { key: "closed", label: "クローズ" },
  { key: "all", label: "すべて" },
] as const satisfies readonly { key: ThreadFilter; label: string }[];

export type CommentsPanelProps = {
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
};

/** 新しいスレッドの入力の、音声入力の識別 */
const NEW_THREAD_VOICE_KEY = "new-thread";

type FreeState = { body: string; status: SendStatus; count: number | null; detail: string | null };

/** 新しいスレッドの入力。閉じて外れても録音と文字起こしは続ける */
const NewThreadForm = ({ free, setFree }: { free: FreeState; setFree: (next: FreeState | ((current: FreeState) => FreeState)) => void }) => {
  const add = useAddComment();
  const saveDraft = useSaveDraft();
  const voice = useVoiceInput({
    key: NEW_THREAD_VOICE_KEY,
    destination: { target: null, loc: null },
    view: "comments",
    label: "新しいスレッド",
    body: free.body,
    onBodyChange: (next) => {
      setFree({ body: next, status: "idle", count: null, detail: null });
      saveDraft({ target: null, loc: null, thread: null, body: next }, true);
    },
    getSelection: () => {
      const field = document.querySelector<HTMLTextAreaElement>('form[data-collapsed] textarea, form:not([data-id]) textarea[aria-label="新しいスレッド"]');
      return { start: field?.selectionStart ?? free.body.length, end: field?.selectionEnd ?? free.body.length };
    },
  });
  return (
            <SendForm
              target={null}
              loc={null}
              label="新しいスレッド"
              body={free.body}
              status={voice.status === "idle" ? free.status : voice.status}
              count={free.count}
              detail={voice.status === "idle" ? free.detail : voice.detail}
              voice={voice.voice}
              voiceReason={voice.voiceReason}
              elapsed={voice.elapsed}
              levels={voice.levels}
              entered={voice.entered}
              onVoiceStart={() => void voice.onVoiceStart()}
              onVoiceCancel={voice.onVoiceCancel}
              onVoiceDone={() => void voice.onVoiceDone()}
              onVoiceBlocked={voice.onVoiceBlocked}
              onInput={(next) => {
                voice.clearResult();
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
  );
};

export const CommentsPanel = ({ onOpenItem, onOpenChangeSet }: CommentsPanelProps) => {
  const { search, setPanel, setComments } = usePreviewSearch();
  const data = useCommentData();
  const pinned = usePrefs().commentsPinned === true;
  const filter: ThreadFilter = search.tstatus ?? "open";
  const tag = search.ttag ?? null;
  const freeDraft = data.drafts.find((draft) => draft.target === null && draft.thread === null)?.body ?? "";
  // 新しいスレッドの入力で音声入力中なら、入力を出して開く
  const [composing, setComposing] = useState(() => readVoiceState().session?.key === NEW_THREAD_VOICE_KEY);
  const heading = useRef<HTMLHeadingElement>(null);
  const composer = useRef<HTMLDivElement>(null);
  // 開いたときに見出しへフォーカスを移す（パネルが Esc を受ける）
  useEffect(() => {
    heading.current?.focus();
  }, []);
  // 新しいスレッドの入力を出したら、入力欄へフォーカスを移す
  useEffect(() => {
    if (composing) composer.current?.querySelector("textarea")?.focus();
  }, [composing]);
  const [free, setFree] = useState<{ body: string; status: SendStatus; count: number | null; detail: string | null }>({ body: freeDraft, status: "idle", count: null, detail: null });
  const close = (): void => {
    setPanel(undefined);
  };
  // 一覧へ戻った後、次に描いた一覧でフォーカスを戻すスレッドの ID
  const focusRow = useRef<string | null>(null);
  // スレッドの一覧へ戻り、描き直した一覧の開いていた行へフォーカスを戻す
  const backToList = (): void => {
    focusRow.current = search.thread ?? null;
    setComments({ thread: undefined });
  };
  // 一覧を描いた後に 1 回だけ、開いていた行へフォーカスを移す（行が無ければ移さない）
  useEffect(() => {
    const from = focusRow.current;
    if (from === null || search.thread !== undefined || search.review !== undefined) return;
    focusRow.current = null;
    document.querySelector<HTMLElement>(`[data-focus="thread:${from}"], [data-focus="thread:new:${from}"]`)?.focus();
  }, [search.thread, search.review]);
  const counts = threadCounts({ threads: data.threads, tag });
  const rows = visibleThreads({ threads: data.threads, filter, tag });
  const pending = pendingThreads({ items: data.items, filter, tag });
  const repliesOf = new Set(data.items.map((item) => item.thread).filter((thread): thread is string => thread !== null));
  const header = (
    <div className="flex items-center gap-2 border-b border-border px-3 py-2">
      <h2 ref={heading} tabIndex={-1} className="m-0 flex-1 text-body font-medium focus-visible:outline-none">
        コメント
      </h2>
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
      return <ThreadView key={search.thread} id={search.thread} data={data} onBack={backToList} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />;
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
          <div ref={composer} className="grid border-t border-border">
            <div className="flex items-center px-3 pt-2">
              <h3 className="m-0 flex-1 text-small font-medium">新しいスレッド</h3>
              <Button variant="ghost" size="icon" aria-label="新しいスレッドの入力を閉じる" onClick={() => { setComposing(false); }}>
                <Icon name="x" />
              </Button>
            </div>
            <NewThreadForm free={free} setFree={setFree} />
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
      {pinned ? null : <div data-scrim aria-hidden="true" className="fixed inset-0 z-20 bg-foreground/40 max-lg:hidden" onClick={close} />}
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- パネルが Esc を受ける */}
      <section
        role="dialog"
        aria-modal={!pinned}
        aria-label="コメント"
        className="fixed inset-y-0 left-0 z-30 flex w-96 max-w-full flex-col border-r border-border bg-card max-lg:w-full"
        onKeyDown={(event) => {
          if (event.key !== "Escape") return;
          event.stopPropagation();
          if (search.review !== undefined) setComments({ review: undefined });
          else if (search.thread !== undefined) backToList();
          else close();
        }}
      >
        {header}
        {body}
      </section>
    </>
  );
};
