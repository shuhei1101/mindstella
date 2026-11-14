// 詳細のコメント。詳細パネル・詳細の全画面の下端のコメントの入力と、レビュー中のコメントの一覧（並びの切り替え・修正・削除・元に戻す・続きを読む）と、本文の選択から出す選んだ箇所のコメントの入口を描く
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

import { Icon } from "@/shared/components/icon";
import { ReviewEditForm } from "@/features/comments/shared/review-edit-form";
import { ReviewBodyFold } from "@/shared/components/review-body-fold";
import { SelectionComment } from "@/shared/components/selection-comment";
import { SendForm, type SendStatus } from "@/shared/components/send-form";
import { Button } from "@/shared/components/ui/button";
import { AppError } from "@/shared/core/app-error";
import { selectionLocation } from "@/shared/core/body-links";
import { commentNumber, reviewLabel, type Draft, type ReviewItem } from "@/shared/core/comments";
import { locationLabel, type Location } from "@/shared/core/records";
import { commentsQuery } from "@/shared/hooks/preview-queries";
import { useAddComment, useRemoveComment, useSaveDraft, useUpdateComment } from "@/shared/hooks/use-comments";
import { useVoiceInput } from "@/shared/hooks/use-voice-input";
import { usePrefs, writePrefs } from "@/shared/stores/prefs-store";

export type DetailCommentsProps = {
  /** 開いている項目の ID */
  id: string;
  /** 本文の中の項目の ID・まとまりの説明 */
  titles: (id: string) => string | null;
  changeSets: (id: string) => string | null;
  onOpenItem: (id: string) => void;
  onOpenChangeSet: (id: string) => void;
};

/** 選んだ箇所の入口を出す位置 */
type Entry = { anchor: { first: DOMRect; last: DOMRect }; area: { viewport: { width: number; height: number }; scroller: DOMRect }; loc: Location };

/** 範囲の最初と最後の矩形（矩形を測れない環境では空の矩形） */
const rectsOf = (range: Range): { first: DOMRect; last: DOMRect } => {
  const rects = typeof range.getClientRects === "function" ? [...range.getClientRects()] : [];
  const empty = new DOMRect();
  return { first: rects[0] ?? empty, last: rects.at(-1) ?? empty };
};

const NO_ITEMS: readonly ReviewItem[] = [];

export const DetailComments = ({ id, titles, changeSets, onOpenItem, onOpenChangeSet }: DetailCommentsProps) => {
  const comments = useQuery(commentsQuery());
  const body = comments.data?.status === 200 ? (comments.data.data as { items?: ReviewItem[]; drafts?: Draft[] }) : undefined;
  const items = (body?.items ?? NO_ITEMS).filter((item) => item.target === id && item.thread === null);
  const host = useRef<HTMLDivElement>(null);
  const prefs = usePrefs();
  const order = prefs.reviewOrder === "oldest" ? "oldest" : "newest";
  const formOpen = prefs.commentFormClosed !== true;
  const add = useAddComment();
  const update = useUpdateComment();
  const remove = useRemoveComment();
  const saveDraft = useSaveDraft();
  const [loc, setLoc] = useState<Location | null>(null);
  const draft = (body?.drafts ?? []).find((one) => one.target === id && one.thread === null && JSON.stringify(one.loc) === JSON.stringify(loc))?.body ?? "";
  const [form, setForm] = useState<{ body: string | null; status: SendStatus; count: number | null; detail: string | null }>({ body: null, status: "idle", count: null, detail: null });
  const [entry, setEntry] = useState<Entry | null>(null);
  const [removed, setRemoved] = useState<ReviewItem[]>([]);
  const [editing, setEditing] = useState<{ id: string; body: string; error: string | null } | null>(null);
  const [opened, setOpened] = useState<Record<string, boolean>>({});

  // 本文の選択（ブラウザの選択の API）と同期して、選んだ箇所の入口を出す
  useEffect(() => {
    const element = host.current;
    if (element === null) return undefined;
    const sync = (): void => {
      const scroller = element.closest(".panel-body");
      const selection = window.getSelection();
      if (scroller === null || selection === null || selection.rangeCount === 0 || selection.isCollapsed) {
        setEntry(null);
        return;
      }
      const range = selection.getRangeAt(0);
      // 本文の外と、コメントの区画の中の選択では出さない
      if (!scroller.contains(range.commonAncestorContainer) || element.contains(range.commonAncestorContainer)) {
        setEntry(null);
        return;
      }
      const location = selectionLocation(range);
      if (location === null) {
        setEntry(null);
        return;
      }
      setEntry({ anchor: rectsOf(range), area: { viewport: { width: window.innerWidth, height: window.innerHeight }, scroller: scroller.getBoundingClientRect() }, loc: location });
    };
    // 入口を押した操作（click）を先に通すため、離した後の確かめは次の順番に回す
    const later = (): void => {
      window.setTimeout(sync, 0);
    };
    document.addEventListener("pointerup", later);
    document.addEventListener("keyup", later);
    return () => {
      document.removeEventListener("pointerup", later);
      document.removeEventListener("keyup", later);
    };
  }, []);

  // 書き換えを描き終えてから、その行の要素へフォーカスを移す（行の修正・入力欄・元に戻す）
  const focusAfter = (update: () => void, selector: string): void => {
    flushSync(update);
    host.current?.querySelector<HTMLElement>(selector)?.focus();
  };
  const shown = [...items, ...removed.map((item) => ({ ...item, gone: true as const }))].sort((a, b) => (order === "newest" ? commentNumber(b.id) - commentNumber(a.id) : commentNumber(a.id) - commentNumber(b.id)));
  const text = form.body ?? draft;
  // 音声入力（録音・文字起こし・レビュー中に溜める・すぐ送る）。向けた先が変わっても録音は続ける
  const voice = useVoiceInput({
    key: `${id}#${loc === null ? "" : JSON.stringify(loc)}`,
    destination: { target: id, loc },
    view: "panel",
    label: `${id} へのコメント`,
    body: text,
    onBodyChange: (next) => {
      if (next === "") setLoc(null);
      setForm({ body: next, status: "idle", count: null, detail: null });
      saveDraft({ target: id, loc, thread: null, body: next }, true);
    },
    getSelection: () => {
      const field = document.querySelector<HTMLTextAreaElement>(`form[data-id="${CSS.escape(id)}"] textarea`);
      return { start: field?.selectionStart ?? text.length, end: field?.selectionEnd ?? text.length };
    },
  });
  return (
    <div ref={host} className="sticky bottom-0 grid gap-2 bg-card">
      {shown.length === 0 ? (
        <section className="grid gap-2 border-t border-border pt-2">
          <h3 className="m-0 text-small font-medium">レビュー中のコメント</h3>
          <p className="m-0 text-small text-muted-foreground">レビュー中のコメントはありません。</p>
        </section>
      ) : (
        <section className="grid gap-2 border-t border-border pt-2">
          <div className="flex items-center gap-2">
            <h3 className="m-0 flex-1 text-small font-medium">レビュー中のコメント</h3>
            {shown.length >= 2 ? (
              <Button variant="ghost" aria-label={`コメントの並び: ${order === "newest" ? "新しい順" : "古い順"}`} onClick={() => { writePrefs({ reviewOrder: order === "newest" ? "oldest" : null }); }}>
                {order === "newest" ? "新しい順" : "古い順"}
                <Icon name="updown" />
              </Button>
            ) : null}
          </div>
          <ul className="m-0 grid list-none gap-2 p-0">
            {shown.map((item) => {
              const label = reviewLabel(item);
              if ("gone" in item) {
                return (
                  <li key={item.id} className="flex items-center gap-2 text-small">
                    <span role="status" className="flex-1">コメントを削除しました。</span>
                    <Button variant="ghost" data-focus={`undo:${item.id}`} onClick={() => { add.mutate({ id: item.id, created: item.created, target: item.target, loc: item.loc, body: item.body }, { onSuccess: () => { focusAfter(() => { setRemoved((current) => current.filter((one) => one.id !== item.id)); }, `[data-focus="edit:${item.id}"]`); } }); }}>
                      <Icon name="undo" />
                      元に戻す
                    </Button>
                  </li>
                );
              }
              return (
                <li key={item.id} data-comment={item.id} className="grid gap-1 rounded-card border border-dashed border-border p-2">
                  <div className="flex items-center gap-1 text-small">
                    <span className="flex-1">{item.loc === null ? "" : locationLabel(item.loc)}</span>
                    {editing?.id === item.id ? null : (
                      <>
                        <Button variant="ghost" size="icon" aria-label={`${label}を修正`} title="修正" data-focus={`edit:${item.id}`} onClick={() => { focusAfter(() => { setEditing({ id: item.id, body: item.body, error: null }); }, `[data-comment="${item.id}"] textarea`); }}>
                          <Icon name="edit" />
                        </Button>
                        <Button variant="ghost" size="icon" aria-label={`${label}を削除`} title="削除" onClick={() => { remove.mutate(item.id, { onSuccess: () => { focusAfter(() => { setRemoved((current) => [...current, item]); }, `[data-focus="undo:${item.id}"]`); } }); }}>
                          <Icon name="trash" />
                        </Button>
                      </>
                    )}
                  </div>
                  {editing?.id === item.id ? (
                    <ReviewEditForm
                      id={item.id}
                      label={label}
                      body={item.body}
                      error={editing.error}
                      saving={update.isPending}
                      onCancel={() => {
                        focusAfter(() => { setEditing(null); }, `[data-focus="edit:${item.id}"]`);
                      }}
                      onSubmit={(target, body) => {
                        update.mutate({ id: target, body }, { onSuccess: () => { focusAfter(() => { setEditing(null); }, `[data-focus="edit:${target}"]`); }, onError: (error) => { setEditing({ id: target, body, error: error instanceof AppError ? error.message : "サーバーが止まっています。立ち上げ直してから直してください。" }); } });
                      }}
                    />
                  ) : (
                    <ReviewBodyFold id={item.id} label={label} body={item.body} titles={titles} changeSets={changeSets} focus="detail-" open={opened[item.id] ?? false} onToggle={(target, open) => { setOpened((current) => ({ ...current, [target]: open })); }} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet}>
                      {(content, toggle) => (
                        <>
                          {content}
                          {toggle === null ? null : <div className="flex">{toggle}</div>}
                        </>
                      )}
                    </ReviewBodyFold>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
      <SendForm
        target={id}
        loc={loc}
        body={text}
        status={voice.status === "idle" ? form.status : voice.status}
        count={form.count}
        detail={voice.status === "idle" ? form.detail : voice.detail}
        voice={voice.voice}
        voiceReason={voice.voiceReason}
        elapsed={voice.elapsed}
        levels={voice.levels}
        entered={voice.entered}
        onVoiceStart={() => void voice.onVoiceStart()}
        onVoiceCancel={voice.onVoiceCancel}
        onVoiceDone={() => void voice.onVoiceDone()}
        onVoiceBlocked={voice.onVoiceBlocked}
        open={formOpen}
        onToggleOpen={(next) => { writePrefs({ commentFormClosed: next ? null : true }); }}
        onInput={(next) => {
          voice.clearResult();
          setForm({ body: next, status: "idle", count: null, detail: null });
          saveDraft({ target: id, loc, thread: null, body: next });
        }}
        onClearLoc={() => { setLoc(null); }}
        onCopyBody={(value) => { void navigator.clipboard.writeText(value); }}
        onBlur={(value) => { saveDraft({ target: id, loc, thread: null, body: value }, true); }}
        onSubmit={(target, location, value) => {
          setForm((current) => ({ ...current, status: "saving" }));
          add.mutate(
            { target, loc: location, body: value },
            {
              onSuccess: (result) => {
                setLoc(null);
                setForm({ body: "", status: "saved", count: (result as { count?: number }).count ?? null, detail: null });
              },
              onError: (error) => { setForm((current) => ({ ...current, status: "failed", detail: error instanceof AppError ? error.message : null })); },
            },
          );
        }}
      />
      {entry === null ? null : (
        <SelectionComment
          anchor={entry.anchor}
          area={entry.area}
          onOpen={() => {
            focusAfter(() => {
              // 閉じていれば開いて残してから、箇所を添えた入力欄へ移る
              if (!formOpen) writePrefs({ commentFormClosed: null });
              setLoc(entry.loc);
              setEntry(null);
            }, "textarea[name=body]");
          }}
          onClose={() => { setEntry(null); }}
        />
      )}
    </div>
  );
};
