// コメントの一覧（画面設計『コメントの一覧.tsx』）。スレッドを状態・タグ・項目で絞って並べ、新規スレッドを立てる左のパネル。パネルの中をスレッド・レビュー中の書き込みの画面と切り替える
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

import { ReviewView } from "@/features/comments/review/review-view";
import { ThreadRow } from "@/features/comments/shared/thread-row";
import { useCommentData } from "@/features/comments/shared/use-comment-data";
import { ThreadView } from "@/features/comments/thread/thread-view";
import { LeftPanel } from "@/shared/components/left-panel";
import { Icon } from "@/shared/components/icon";
import { RecordText } from "@/shared/components/record-text";
import { focusAfterAdded, SendForm, type SendStatus } from "@/shared/components/send-form";
import { Button } from "@/shared/components/ui/button";
import { AppError } from "@/shared/core/app-error";
import { pendingThreads, threadCounts, visibleThreads, type ThreadFilter } from "@/shared/core/comments";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { useAddComment, useSaveDraft } from "@/shared/hooks/use-comments";
import { useVoiceInput } from "@/shared/hooks/use-voice-input";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecordLookup } from "@/shared/hooks/use-record-lookup";
import { useRecords } from "@/shared/hooks/use-records";
import { cn } from "@/shared/lib/cn";
import { SEGMENTED_GROUP_CLASS, SEGMENTED_ITEM_CLASS, SEGMENTED_SELECTED_CLASS } from "@/shared/lib/segmented";
import { useFocusAfterAddTarget, usePrefs, writePrefs } from "@/shared/stores/prefs-store";
import { readVoiceState } from "@/shared/stores/voice-store";
import { useSingleFlight } from "@/shared/hooks/use-single-flight";

const FILTERS = [
  { key: "open", label: "オープン" },
  { key: "closed", label: "クローズ" },
  { key: "all", label: "すべて" },
] as const satisfies readonly { key: ThreadFilter; label: string }[];

export type CommentsPanelProps = {
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
  /** この一覧から開いた詳細パネルをグレーアウトの上に出しているか。真の間はモーダルにしない */
  detailRaised?: boolean;
};

/** 新規スレッドの入力の、音声入力の識別 */
const NEW_THREAD_VOICE_KEY = "new-thread";

type FreeState = { body: string; status: SendStatus; count: number | null; detail: string | null };

/** 新規スレッドの入力の見出し（項目で絞っている間は、その項目へ向ける） */
const newThreadLabel = (target: string | null): string => (target === null ? "新規スレッド" : `${target} への新規スレッド`);

/** 新規スレッドの入力。閉じて外れても録音と文字起こしは続ける。項目で絞っている間は、溜めるスレッドと下書き・音声入力をその項目への箇所を持たない入力に向ける（詳細パネルの下端の入力と下書きを共有する） */
const NewThreadForm = ({ free, setFree, target }: { free: FreeState; setFree: (next: FreeState | ((current: FreeState) => FreeState)) => void; target: string | null }) => {
  const add = useAddComment();
  const flight = useSingleFlight();
  const saveDraft = useSaveDraft();
  const focusTarget = useFocusAfterAddTarget();
  // 溜めた後にフォーカスを移す、新規スレッドの入力の form
  const sendForm = useRef<HTMLFormElement>(null);
  const voice = useVoiceInput({
    key: NEW_THREAD_VOICE_KEY,
    destination: { target, loc: null },
    view: "comments",
    label: newThreadLabel(target),
    body: free.body,
    onBodyChange: (next) => {
      setFree({ body: next, status: "idle", count: null, detail: null });
      saveDraft({ target, loc: null, thread: null, body: next }, true);
    },
    getSelection: () => {
      const field = document.querySelector<HTMLTextAreaElement>(`form[data-collapsed] textarea, form:not([data-id]) textarea[aria-label="${newThreadLabel(target)}"]`);
      return { start: field?.selectionStart ?? free.body.length, end: field?.selectionEnd ?? free.body.length };
    },
  });
  return (
            <SendForm
              formRef={sendForm}
              target={null}
              loc={null}
              label={newThreadLabel(target)}
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
                saveDraft({ target, loc: null, thread: null, body: next });
              }}
              onSubmit={(_target, _loc, text) => {
                setFree((current) => ({ ...current, status: "saving" }));
                flight.run(() => add.mutateAsync(
                  target === null ? { body: text } : { body: text, target },
                  {
                    onSuccess: (result) => {
                      flushSync(() => { setFree({ body: "", status: "saved", count: (result as { count?: number }).count ?? null, detail: null }); });
                      focusAfterAdded(sendForm.current, focusTarget);
                    },
                    onError: (error) => { setFree((current) => ({ ...current, status: "failed", detail: error instanceof AppError ? error.message : null })); },
                  },
                ));
              }}
            />
  );
};

/** 項目の絞り込みのチップ（ID とタイトルと外す ×。件数は状態の絞り込みが出す） */
const TargetChip = ({ target, title, lookup, onOpen, onClear }: { target: string; title: string | undefined; lookup: LookupRecordId; onOpen: (id: string) => void; onClear: () => void }) => (
  <div className="flex min-w-0 items-center gap-1 border-b border-border px-3 py-1 text-small">
    <Icon name="comment" />
    <span className="font-mono">{target}</span>
    {title === undefined ? null : (
      <span className="min-w-0 truncate">
        <RecordText text={title} mode="link" lookup={lookup} onOpen={onOpen} />
      </span>
    )}
    <Button variant="ghost" size="icon" aria-label={`項目「${target}」の絞り込みを外す`} onClick={onClear}>
      <Icon name="x" />
    </Button>
  </div>
);

const STATE_TEXT: Record<ThreadFilter, string> = { open: "オープンの", closed: "クローズの", all: "" };

/** 0 件のときの文言（項目で絞っていれば頭に「{ID} への」、タグで絞っていれば「タグ「{タグ}」の」を付ける） */
const emptyText = ({ filter, tag, target }: { filter: ThreadFilter; tag: string | null; target: string | null }): string =>
  `${target === null ? "" : `${target} への`}${tag === null ? "" : `タグ「${tag}」の`}${STATE_TEXT[filter]}スレッドはありません。`;

export const CommentsPanel = ({ onOpenItem, onOpenChangeSet, detailRaised = false }: CommentsPanelProps) => {
  const { search, setPanel, setComments } = usePreviewSearch();
  const data = useCommentData();
  const pinned = usePrefs().commentsPinned === true;
  const filter: ThreadFilter = search.tstatus ?? "open";
  const tag = search.ttag ?? null;
  const target = search.ttarget ?? null;
  const { index } = useRecords();
  const record = useRecordLookup({ index, onOpenItem });
  // 新規スレッドの下書き（項目で絞っている間は、その項目への箇所を持たない下書き。詳細パネルの下端の入力と同じ）
  const draftOf = (of: string | null): string => data.drafts.find((draft) => draft.target === of && draft.loc === null && draft.thread === null)?.body ?? "";
  // 新規スレッドの入力で音声入力中なら、入力を出して開く
  const [composing, setComposing] = useState(() => readVoiceState().session?.key === NEW_THREAD_VOICE_KEY);
  const heading = useRef<HTMLHeadingElement>(null);
  const composer = useRef<HTMLDivElement>(null);
  // 開いたときに見出しへフォーカスを移す（パネルが Esc を受ける）
  useEffect(() => {
    heading.current?.focus();
  }, []);
  // 新規スレッドの入力を出したら、入力欄へフォーカスを移す
  useEffect(() => {
    if (composing) composer.current?.querySelector("textarea")?.focus();
  }, [composing]);
  // 向ける項目が変わったら、その項目の下書きから始める
  const [freeEntry, setFreeEntry] = useState<{ target: string | null; state: FreeState }>(() => ({ target, state: { body: draftOf(target), status: "idle", count: null, detail: null } }));
  const free: FreeState = freeEntry.target === target ? freeEntry.state : { body: draftOf(target), status: "idle", count: null, detail: null };
  const setFree = (next: FreeState | ((current: FreeState) => FreeState)): void => {
    setFreeEntry((current) => {
      const base = current.target === target ? current.state : { body: draftOf(target), status: "idle" as const, count: null, detail: null };
      return { target, state: typeof next === "function" ? next(base) : next };
    });
  };
  const close = (): void => {
    setPanel(undefined);
  };
  const counts = threadCounts({ threads: data.threads, tag, target });
  const rows = visibleThreads({ threads: data.threads, filter, tag, target });
  const pending = pendingThreads({ items: data.items, filter, tag, target });
  // 一覧に並ぶスレッドの ID の順（開いているスレッドが一覧から消えた後も、消える前の順を保つ）
  const order = [...pending.map((item) => item.id), ...rows.map((thread) => thread.id)];
  const lastOrder = useRef(order);
  useEffect(() => {
    if (search.thread === undefined || order.includes(search.thread)) lastOrder.current = order;
  });
  // 一覧へ戻った後、次に描いた一覧でフォーカスを戻すスレッドの ID と、行が無いときに移す先の候補の順（「一覧へ戻る」では空）
  const focusRow = useRef<{ from: string; fallback: string[] } | null>(null);
  const emptyRef = useRef<HTMLParagraphElement>(null);
  // スレッドの一覧へ戻り、描き直した一覧の開いていた行へフォーカスを戻す
  const backToList = (): void => {
    focusRow.current = search.thread === undefined ? null : { from: search.thread, fallback: [] };
    setComments({ thread: undefined });
  };
  // クローズにして一覧へ戻り、開いていた行、無ければ次の行、無ければ前の行、行が 1 件も無ければ空の表示へフォーカスを移す
  const backAfterClosed = (): void => {
    const from = search.thread;
    if (from === undefined) return;
    const ids = lastOrder.current;
    const at = ids.indexOf(from);
    focusRow.current = { from, fallback: at < 0 ? [] : [...ids.slice(at + 1), ...ids.slice(0, at).reverse()] };
    setComments({ thread: undefined });
  };
  // 一覧を描いた後に 1 回だけ、開いていた行へフォーカスを移す（「一覧へ戻る」で行が無ければ移さない）
  useEffect(() => {
    const entry = focusRow.current;
    if (entry === null || search.thread !== undefined || search.review !== undefined) return;
    focusRow.current = null;
    const rowOf = (id: string): HTMLElement | null => document.querySelector<HTMLElement>(`[data-focus="thread:${id}"], [data-focus="thread:new:${id}"]`);
    const found = [entry.from, ...entry.fallback].map(rowOf).find((element) => element !== null);
    if (found !== undefined) {
      found.focus();
      return;
    }
    if (entry.fallback.length > 0 || order.length === 0) emptyRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 一覧へ戻ったときだけ移す
  }, [search.thread, search.review]);
  const targetTitle = target === null ? undefined : index?.byId.get(target)?.item.title;
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
        <Icon name={pinned ? "lock" : "unlock"} className={cn(pinned && "text-primary")} />
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
      return <ThreadView key={search.thread} id={search.thread} data={data} onBack={backToList} onClosed={backAfterClosed} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />;
    }
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="border-b border-border px-3 py-2">
          <div role="group" aria-label="スレッドの状態で絞る" className={SEGMENTED_GROUP_CLASS}>
          {FILTERS.map((entry) => (
            <Button key={entry.key} variant="ghost" aria-pressed={filter === entry.key} className={cn(SEGMENTED_ITEM_CLASS, "h-7 font-normal", filter === entry.key && SEGMENTED_SELECTED_CLASS)} onClick={() => { setComments({ tstatus: entry.key === "open" ? undefined : entry.key }); }}>
              {entry.label}
              <span className="font-mono text-small">{counts[entry.key]}</span>
            </Button>
          ))}
          </div>
        </div>
        {target === null ? null : <TargetChip target={target} title={targetTitle} lookup={record.lookup} onOpen={record.onOpen} onClear={() => { setComments({ ttarget: undefined }); }} />}
        {tag === null ? null : (
          <div className="flex items-center gap-1 border-b border-border px-3 py-1 text-small">
            <span>#{tag}</span>
            <Button variant="ghost" size="icon" aria-label={`タグ「${tag}」の絞り込みを外す`} onClick={() => { setComments({ ttag: undefined }); }}>
              <Icon name="x" />
            </Button>
            <span className="text-muted-foreground">{`${String(rows.length)} / ${String(visibleThreads({ threads: data.threads, filter, tag: null, target }).length)} 件`}</span>
          </div>
        )}
        {data.threadsError === null ? null : (
          <p role="alert" className="m-0 flex items-start gap-1 px-3 py-2 text-small text-destructive">
            <Icon name="alert" />
            <span>{`スレッドを読めませんでした。${data.threadsError.detail ?? "サーバーが止まっています。再起動してから開いてください。"}`}</span>
          </p>
        )}
        <ul className="m-0 min-h-0 flex-1 list-none overflow-y-auto p-0">
          {pending.map((item) => (
            <ThreadRow key={item.id} pending={item} lookup={record.lookup} onOpen={(id) => { setComments({ thread: id }); }} onTag={() => undefined} />
          ))}
          {rows.map((thread) => (
            <ThreadRow key={thread.id} thread={thread} hasPendingReply={repliesOf.has(thread.id)} activeTag={tag} lookup={record.lookup} onOpen={(id) => { setComments({ thread: id }); }} onTag={(next) => { setComments({ ttag: next === tag ? undefined : next }); }} />
          ))}
        </ul>
        {pending.length === 0 && rows.length === 0 && data.threadsError === null ? (
          <p ref={emptyRef} tabIndex={-1} className="m-0 flex items-center gap-1 px-3 py-2 text-small text-muted-foreground focus-visible:outline-none">
            <Icon name="comment" />
            {emptyText({ filter, tag, target })}
          </p>
        ) : null}
        {composing ? (
          <div ref={composer} className="grid border-t border-border">
            <div className="flex items-center px-3 pt-2">
              <h3 className="m-0 flex-1 text-small font-medium">{newThreadLabel(target)}</h3>
              <Button variant="ghost" size="icon" aria-label="新規スレッドの入力を閉じる" onClick={() => { setComposing(false); }}>
                <Icon name="x" />
              </Button>
            </div>
            <NewThreadForm free={free} setFree={setFree} target={target} />
          </div>
        ) : (
          <div className="border-t border-border p-3">
            <Button variant="outline" onClick={() => { setComposing(true); }}>
              <Icon name="plus" />
              新規スレッド
            </Button>
          </div>
        )}
      </div>
    );
  })();
  return (
    <>
      {pinned ? null : <div data-scrim aria-hidden="true" className="fixed inset-x-0 top-below-topbar bottom-0 z-20 bg-foreground/40 max-lg:hidden" onClick={close} />}
      <LeftPanel
        as="section"
        role="dialog"
        aria-modal={!pinned && !detailRaised}
        aria-label="コメント"
        resizerLabel="コメントの一覧の幅"
        className="fixed top-below-topbar bottom-0 left-0 z-30 flex w-96 max-w-full flex-col border-r border-border bg-card max-lg:w-full"
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
      </LeftPanel>
    </>
  );
};
