// スレッド（画面設計『スレッド.tsx』）。書き込みと状態の変更を書いた順に並べ、下端で返信を溜め、上端でクローズとオープンへの戻しをする
import { useEffect, useId, useRef, useState } from "react";
import { flushSync } from "react-dom";

import { ReplyForm, type ReplyStatus } from "@/features/comments/shared/reply-form";
import { ThreadPost } from "@/features/comments/shared/thread-post";
import { ThreadState } from "@/features/comments/shared/thread-state";
import type { CommentData } from "@/features/comments/shared/use-comment-data";
import { useMarkThreadSeen, useSetThreadStatus } from "@/features/comments/shared/use-threads";
import { Icon } from "@/shared/components/icon";
import { focusAfterAdded } from "@/shared/components/send-form";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { AppError } from "@/shared/core/app-error";
import { commentNumber, hasUnseen, reviewLabel, threadTimeline, threadTitle, type ReviewItem } from "@/shared/core/comments";
import { useAddComment, useRemoveComment, useSaveDraft, useUpdateComment } from "@/shared/hooks/use-comments";
import { useVoiceInput } from "@/shared/hooks/use-voice-input";
import { showLocation } from "@/shared/stores/location-highlight-store";
import { voiceEditingOf } from "@/shared/stores/voice-store";
import { useFocusAfterAddTarget } from "@/shared/stores/prefs-store";
import { useThreadLinks } from "@/shared/hooks/use-thread-links";
import { useSingleFlight } from "@/shared/hooks/use-single-flight";
import { ThreadTitle } from "@/shared/components/thread-title";

export type ThreadViewProps = {
  /** 開くスレッドの ID（まだ送っていない新規スレッドはコメントの ID） */
  id: string;
  data: CommentData;
  onBack: () => void;
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
};

/** 失敗の理由（届かなければ null） */
const detailOf = (error: unknown): string | null => (error instanceof AppError ? error.message : null);

// eslint-disable-next-line sonarjs/cognitive-complexity -- 分岐を 1 か所で読めるように保つ
export const ThreadView = ({ id, data, onBack, onOpenItem, onOpenChangeSet }: ThreadViewProps) => {
  const { threads, items, drafts, titles, changeSets, index } = data;
  const thread = threads.find((one) => one.id === id) ?? null;
  const pendingNew = thread === null ? (items.find((item) => item.id === id && item.thread === null) ?? null) : null;
  const replies = items.filter((item) => item.thread === id);
  const markSeen = useMarkThreadSeen();
  const threadLinks = useThreadLinks();
  const setStatus = useSetThreadStatus();
  const addComment = useAddComment();
  const focusTarget = useFocusAfterAddTarget();
  // 溜めた後にフォーカスを移す、返信の入力の form
  const replyForm = useRef<HTMLFormElement>(null);
  const updateComment = useUpdateComment();
  const removeComment = useRemoveComment();
  const flight = useSingleFlight();
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
  // 音声入力（録音・文字起こし・レビュー中に溜める・すぐ送る）。開くスレッドが変わっても録音は続ける
  const voice = useVoiceInput({
    key: `thread:${id}`,
    destination: { thread: id },
    view: "thread",
    label: `${id} への返信`,
    body: reply.body,
    onBodyChange: (next) => {
      setReply({ body: next, status: "idle", count: null, detail: null });
      saveDraft({ target: null, loc: null, thread: id, body: next }, true);
    },
    getSelection: () => {
      const field = document.querySelector<HTMLTextAreaElement>('form[data-part="reply"] textarea');
      return { start: field?.selectionStart ?? reply.body.length, end: field?.selectionEnd ?? reply.body.length };
    },
  });
  const reasonId = useId();
  const [reason, setReason] = useState<{ open: boolean; body: string; detail: string | null; failed: boolean }>({ open: false, body: "", detail: null, failed: false });
  // 書き換えている行。録音中か結果待ちの修正の入力があれば、その行を書き換えている状態で開く
  const [editing, setEditing] = useState<{ id: string; body: string; error: string | null } | null>(() => {
    const voiced = voiceEditingOf("thread");
    const item = voiced === null ? undefined : items.find((one) => one.id === voiced);
    return item === undefined ? null : { id: item.id, body: item.body, error: null };
  });
  const editingItem = editing === null ? null : (items.find((one) => one.id === editing.id) ?? null);
  // 修正の入力の音声入力（挿入だけ）。返信の入力とは別の入力欄で、画面で同時に 1 つだけ録音する
  const editVoice = useVoiceInput({
    key: `review:${editing?.id ?? ""}`,
    destination: { review: editing?.id ?? "", thread: editingItem?.thread ?? null, target: editingItem?.target ?? null },
    view: "thread",
    label: editingItem === null ? "" : `${reviewLabel(editingItem)}の修正`,
    body: editing?.body ?? "",
    onBodyChange: (next) => {
      setEditing((current) => (current === null ? current : { ...current, body: next }));
    },
    getSelection: () => {
      const field = document.querySelector<HTMLTextAreaElement>(`[data-comment="${CSS.escape(editing?.id ?? "")}"] form[data-part="edit"] textarea`);
      const length = editing?.body.length ?? 0;
      return { start: field?.selectionStart ?? length, end: field?.selectionEnd ?? length };
    },
  });
  const [opened, setOpened] = useState<Record<string, boolean>>({});
  const [removed, setRemoved] = useState<ReviewItem[]>([]);
  // 理由の入力を閉じた後、次に描いた「状態を変える」へフォーカスを戻すか
  const focusStatusButton = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  // 開いたときに見出しへフォーカスを移す（パネルが Esc を受ける）
  useEffect(() => {
    heading.current?.focus();
  }, []);
  // 理由の入力を閉じ、描き直した「状態を変える」へフォーカスを戻す
  const closeReason = (): void => {
    focusStatusButton.current = true;
    setReason({ open: false, body: "", detail: null, failed: false });
  };
  const statusButtonRef = (element: HTMLButtonElement | null): void => {
    if (element === null || !focusStatusButton.current) return;
    focusStatusButton.current = false;
    element.focus();
  };

  const closed = thread?.status === "closed";
  const nextStatus = closed ? "open" : "closed";
  const actionLabel = closed ? "オープンに戻す" : "クローズにする";
  const submitStatus = (): void => {
    if (thread === null) return;
    const text = reason.body.trim();
    flight.run(() => setStatus.mutateAsync(
      { id: thread.id, status: nextStatus, reason: text === "" ? null : text },
      {
        onSuccess: () => {
          closeReason();
        },
        onError: (error) => {
          setReason((current) => ({ ...current, detail: detailOf(error), failed: true }));
        },
      },
    ));
  };
  const submitReply = (target: string, body: string): void => {
    setReply((current) => ({ ...current, status: "saving" }));
    flight.run(() => addComment.mutateAsync(
      { target: null, loc: null, thread: target, body },
      {
        onSuccess: (result) => {
          flushSync(() => { setReply({ body: "", status: "saved", count: (result as { count?: number }).count ?? null, detail: null }); });
          focusAfterAdded(replyForm.current, focusTarget);
        },
        onError: (error) => {
          setReply((current) => ({ ...current, status: "failed", detail: detailOf(error) }));
        },
      },
    ));
  };
  const pendingPost = (item: ReviewItem) => (
    <li key={item.id}>
      <ThreadPost
        pending={item}
        titles={titles}
        index={index}
        changeSets={changeSets}
        editing={editing?.id === item.id}
        busy={(updateComment.isPending && updateComment.variables.id === item.id) || (removeComment.isPending && removeComment.variables === item.id)}
        editError={editing?.id === item.id ? editing.error : null}
        editBody={editing?.id === item.id ? editing.body : null}
        voice={editVoice.voice}
        voiceReason={editVoice.voiceReason}
        elapsed={editVoice.elapsed}
        levels={editVoice.levels}
        voiceStatus={editVoice.status}
        voiceDetail={editVoice.detail}
        onEditInput={(_target, body) => {
          editVoice.clearResult();
          setEditing((current) => (current === null ? current : { ...current, body }));
        }}
        onEditVoiceStart={() => void editVoice.onVoiceStart()}
        onEditVoiceCancel={editVoice.onVoiceCancel}
        onEditVoiceDone={() => void editVoice.onVoiceDone()}
        onEditVoiceBlocked={editVoice.onVoiceBlocked}
        open={opened[item.id] ?? false}
        onOpenItem={onOpenItem}
        onOpenChangeSet={onOpenChangeSet}
        onEditStart={(target) => {
          setEditing({ id: target, body: item.body, error: null });
        }}
        onEditCancel={() => {
          setEditing(null);
        }}
        onEditSubmit={(target, body) => {
          flight.run(() => updateComment.mutateAsync(
            { id: target, body },
            {
              onSuccess: () => {
                setEditing(null);
              },
              onError: (error) => {
                setEditing({ id: target, body, error: detailOf(error) ?? "サーバーが止まっています。再起動してから修正してください。" });
              },
            },
          ));
        }}
        onRemove={(target) => {
          flight.run(() => removeComment.mutateAsync(target, { onSuccess: () => { setRemoved((current) => [...current, item]); } }));
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
          <Button ref={statusButtonRef} variant="outline" onClick={() => { setReason({ open: true, body: "", detail: null, failed: false }); }}>
            <Icon name={closed ? "undo" : "check"} />
            {actionLabel}
          </Button>
        )}
      </div>
      {reason.open && thread !== null ? (
        <div className="grid gap-1.5 border-b border-border px-3 py-2">
          <label htmlFor={reasonId} className="grid gap-1 text-small">
            理由（任意）
            <Input id={reasonId} ref={(element) => { element?.focus(); }} value={reason.body} readOnly={setStatus.isPending} onChange={(event) => { setReason((current) => ({ ...current, body: event.target.value })); }} onKeyDown={(event) => {
              // Esc は理由の入力だけを閉じる（一覧へは戻らない）
              if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                closeReason();
                return;
              }
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
                event.preventDefault();
                submitStatus();
              }
            }} />
          </label>
          {reason.failed ? (
            <p role="alert" className="m-0 flex items-start gap-1 text-small text-destructive">
              <Icon name="alert" />
              <span>{`${closed ? "オープンに戻せませんでした。" : "クローズにできませんでした。"}${reason.detail ?? "サーバーが止まっています。再起動してから押してください。"}`}</span>
            </p>
          ) : null}
          <div className="flex justify-end gap-1.5">
            <Button variant="ghost" onClick={closeReason}>
              キャンセル
            </Button>
            <Button pending={setStatus.isPending} onClick={submitStatus}>
              {actionLabel}
            </Button>
          </div>
        </div>
      ) : null}
      <div className="grid gap-1 border-b border-border px-3 py-2">
        <h2 ref={heading} tabIndex={-1} className="m-0 flex items-center gap-2 text-body font-medium focus-visible:outline-none">
          <ThreadState status={thread === null ? "pending" : thread.status} />
          <ThreadTitle title={title} collapsed={false} />
        </h2>
        {thread?.target === null || thread?.target === undefined ? null : (
          <button type="button" className="flex cursor-pointer items-center gap-1 text-left text-small" disabled={titles(thread.target) === null} onClick={() => { showLocation({ target: thread.target ?? "", loc: thread.loc }); onOpenItem(thread.target ?? ""); }}>
            <span className="font-mono">{thread.target}</span>
            <span className="truncate">{titles(thread.target) ?? ""}</span>
          </button>
        )}
        {thread === null || thread.tags.length === 0 ? null : (
          <span data-part="thread-tags" className="flex flex-wrap gap-1 text-small text-muted-foreground">
            {thread.tags.map((tag) => (
              <span key={tag}>#{tag}</span>
            ))}
          </span>
        )}
      </div>
      <ol className="m-0 grid min-h-0 flex-1 list-none grid-cols-1 content-start gap-2 overflow-y-auto p-3">
        {thread === null
          ? pendingNew === null
            ? null
            : pendingPost(pendingNew)
          : threadTimeline(thread).map((entry) => ("post" in entry ? (
            <li key={entry.post.id}>
              <ThreadPost post={entry.post} titles={titles} index={index} changeSets={changeSets} threadTitles={threadLinks.threads} onOpenThread={threadLinks.onOpenThread} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} />
            </li>
          ) : (
            <li key={`${entry.event.kind}-${entry.event.created}`}>
              <ThreadPost event={entry.event} />
            </li>
          )))}
        {[...replies, ...removed.filter((one) => one.thread === id && !replies.some((reply) => reply.id === one.id))]
          .sort((a, b) => commentNumber(a.id) - commentNumber(b.id))
          .map((item) =>
            removed.includes(item) && !replies.includes(item) ? (
              <li key={item.id} className="flex items-center gap-2 rounded-card border border-border p-2 text-small">
                <span role="status" className="flex-1">
                  コメントを削除しました。
                </span>
                <Button
                  variant="ghost"
                  pending={addComment.isPending && addComment.variables.id === item.id}
                  disabled={flight.running}
                  onClick={() => {
                    flight.run(() => addComment.mutateAsync({ id: item.id, created: item.created, target: item.target, loc: item.loc, thread: item.thread, body: item.body }, { onSuccess: () => { setRemoved((current) => current.filter((one) => one.id !== item.id)); } }));
                  }}
                >
                  <Icon name="undo" />
                  元に戻す
                </Button>
              </li>
            ) : (
              pendingPost(item)
            ),
          )}
      </ol>
      {thread === null ? (
        <p className="m-0 flex items-center gap-1 border-t border-border p-3 text-small text-muted-foreground">
          <Icon name="edit" />
          まだ送信していないスレッドです。
        </p>
      ) : closed ? (
        <p className="m-0 flex items-center gap-1 border-t border-border p-3 text-small text-muted-foreground">
          <Icon name="check" />
          クローズにしたスレッドです。
        </p>
      ) : (
        <ReplyForm
          formRef={replyForm}
          thread={thread.id}
          body={reply.body}
          status={voice.status === "idle" ? reply.status : voice.status}
          count={reply.count}
          detail={voice.status === "idle" ? reply.detail : voice.detail}
          voice={voice.voice}
          voiceReason={voice.voiceReason}
          elapsed={voice.elapsed}
          levels={voice.levels}
          entered={voice.entered}
          onVoiceStart={() => void voice.onVoiceStart()}
          onVoiceCancel={voice.onVoiceCancel}
          onVoiceDone={() => void voice.onVoiceDone()}
          onVoiceBlocked={voice.onVoiceBlocked}
          onInput={(body) => {
            voice.clearResult();
            setReply({ body, status: "idle", count: null, detail: null });
            saveDraft({ target: null, loc: null, thread: thread.id, body });
          }}
          onSubmit={submitReply}
        />
      )}
    </div>
  );
};
