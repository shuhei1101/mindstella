// 返信の入力（部品設計『返信の入力.tsx』）。スレッドの下端に留める、返信をレビュー中に溜める入力欄と「レビューに追加」のボタン
import { useId, useRef, type SyntheticEvent, type KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";
import { fieldLocked, useVoiceFocus, VoiceButtons, VoiceProgress, VoiceResult, VoiceWave, type VoiceProps } from "@/shared/components/send-form";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { cn } from "@/shared/lib/cn";

/** 返信を溜める状態。idle は結果を出さない */
export type ReplyStatus = "idle" | "saving" | "saved" | "failed" | "sent" | "inserted" | "reviewed" | "voice-failed";

/** 本文の最大の文字数（『レビュー中のコメントの追加』の body） */
const COMMENT_BODY_MAX_LENGTH = 10000;

export type ReplyFormProps = VoiceProps & {
  thread: string;
  body: string;
  status: ReplyStatus;
  count?: number | null;
  detail?: string | null;
  onSubmit: (thread: string, body: string) => void;
  onInput: (body: string) => void;
  /** 録音中の ✓（スレッドの ID と入力欄の中身そのまま） */
  onVoiceDone?: (thread: string, body: string) => void;
};

const ReplyResult = ({ status, count, detail }: { status: ReplyStatus; count: number | null; detail: string | null }) => {
  if (status === "saving") {
    return (
      <>
        <Icon name="spin" className="animate-spin" />
        <span>レビューに追加しています</span>
      </>
    );
  }
  if (status === "saved") {
    return (
      <>
        <Icon name="check" className="text-mark" />
        <span>{`レビューに追加しました（レビュー中 ${String(count ?? 0)} 件）。`}</span>
      </>
    );
  }
  if (status === "failed") {
    return (
      <>
        <Icon name="alert" className="text-st-review" />
        <span>{`レビューに追加できませんでした。${detail ?? "サーバーが止まっています。立ち上げ直してから追加してください。"}`}</span>
      </>
    );
  }
  return null;
};

export const ReplyForm = ({ thread, body, status, count = null, detail = null, voice = "idle", voiceReason = null, elapsed = 0, levels = [], entered = false, onSubmit, onInput, onVoiceStart, onVoiceCancel, onVoiceDone, onVoiceBlocked }: ReplyFormProps) => {
  const fieldId = useId();
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const doneRef = useRef<HTMLButtonElement>(null);
  useVoiceFocus(voice, fieldRef, doneRef);
  const messageId = `${fieldId}-msg`;
  const saving = status === "saving";
  const trySave = (): void => {
    if (saving || body.trim() === "") return;
    onSubmit(thread, body);
  };
  const handleSubmit = (event: SyntheticEvent<HTMLFormElement>): void => {
    event.preventDefault();
    trySave();
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
      event.preventDefault();
      trySave();
    }
    // Esc は入力から外れるだけにする（使う側の「一覧へ戻る」へ伝えない）
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      event.currentTarget.blur();
    }
  };
  return (
    <form noValidate data-part="reply" className="grid gap-1.5 border-t border-border p-3" onSubmit={handleSubmit}>
      <label htmlFor={fieldId} className="text-small text-muted-foreground">
        返信
      </label>
      {/* 入力欄と、その右の「レビューに追加」（アイコンだけのボタン）の行。結果は行の下に幅いっぱいで出す */}
      <div className="flex items-end gap-2">
        <Textarea ref={fieldRef} id={fieldId} name="body" rows={1} maxLength={COMMENT_BODY_MAX_LENGTH} value={body} readOnly={fieldLocked(saving, voice)} hidden={voice === "recording"} aria-keyshortcuts="Control+Enter" aria-describedby={messageId} className="field-sizing-content min-w-0 flex-1 resize-y field-send pointer-coarse:min-h-11" onChange={(event) => onInput(event.target.value)} onKeyDown={handleKeyDown} />
        <VoiceWave voice={voice} levels={levels} />
        <VoiceButtons doneRef={doneRef} voice={voice} voiceReason={voiceReason} onStart={onVoiceStart} onCancel={onVoiceCancel} onBlocked={onVoiceBlocked} onDone={() => onVoiceDone?.(thread, body)} submit={<Button type="submit" size="icon" className="size-send disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 pointer-coarse:size-11" aria-label="レビューに追加" title="レビューに追加（Ctrl+Enter）" data-focus="reply-send" disabled={saving || body.trim() === ""}>
          <Icon name="comment" />
        </Button>} />
      </div>
      <p id={messageId} role="status" className={cn("m-0 flex items-start gap-1 text-small text-muted-foreground empty:hidden", (status === "failed" || status === "voice-failed") && "text-foreground")}>
        {voice === "recording" || voice === "transcribing" ? (
          <VoiceProgress voice={voice} elapsed={elapsed} />
        ) : status === "sent" || status === "inserted" || status === "reviewed" || status === "voice-failed" ? (
          <VoiceResult status={status} detail={detail} entered={entered} />
        ) : (
          <ReplyResult status={status} count={count} detail={detail} />
        )}
      </p>
    </form>
  );
};
