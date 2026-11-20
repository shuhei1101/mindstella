// レビュー中の書き込みの本文をその場で書き換える入力欄と「キャンセル」「修正」（スレッドの書き込みとレビュー中の書き込みの画面と詳細のコメントが使う）
import { useRef, useState, type KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";
import { fieldLocked, VoiceButtons, VoiceProgress, VoiceResult, VoiceWave, useVoiceFocus, type VoiceProps } from "@/shared/components/send-form";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import type { VoiceStatus } from "@/shared/hooks/use-voice-input";

export type ReviewEditFormProps = VoiceProps & {
  id: string;
  label: string;
  /** 入力欄の中身（使う側が持つ） */
  body: string;
  error?: string | null;
  saving?: boolean;
  /** 音声入力の結果（修正の入力は挿入だけのため `inserted` か `voice-failed`） */
  voiceStatus?: VoiceStatus;
  /** 文字起こしできなかった理由（`voiceStatus` が `voice-failed` のとき） */
  voiceDetail?: string | null;
  onBodyChange: (body: string) => void;
  onSubmit: (id: string, body: string) => void;
  onCancel: (id: string) => void;
  /** 録音中の ✓ */
  onVoiceDone?: () => void;
};

/** 結果の行の中身（録音中・文字起こし中、修正できなかった理由、音声入力の結果の順に選ぶ） */
const EditMessage = ({ voice, elapsed, message, voiceStatus, voiceDetail }: { voice: NonNullable<VoiceProps["voice"]>; elapsed: number; message: string | null; voiceStatus: VoiceStatus; voiceDetail: string | null }) => {
  if (voice === "recording" || voice === "transcribing") {
    return (
      <p role="status" data-part="message" className="m-0 flex items-start gap-1 text-small text-muted-foreground">
        <VoiceProgress voice={voice} elapsed={elapsed} />
      </p>
    );
  }
  if (message !== null) {
    return (
      <p role="alert" data-part="message" className="m-0 flex items-start gap-1 text-small">
        <Icon name="alert" className="text-st-review" />
        <span>{message}</span>
      </p>
    );
  }
  if (voiceStatus === "idle") return null;
  return (
    <p role="status" data-part="message" className="m-0 flex items-start gap-1 text-small text-muted-foreground">
      <VoiceResult status={voiceStatus} detail={voiceDetail} entered={false} />
    </p>
  );
};

export const ReviewEditForm = ({ id, label, body, error = null, saving = false, voice, voiceReason = null, elapsed = 0, levels = [], voiceStatus = "idle", voiceDetail = null, onBodyChange, onSubmit, onCancel, onVoiceStart, onVoiceCancel, onVoiceDone, onVoiceBlocked }: ReviewEditFormProps) => {
  const [empty, setEmpty] = useState(false);
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const doneRef = useRef<HTMLButtonElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const phase = voice ?? "idle";
  useVoiceFocus(phase, fieldRef, doneRef, submitRef, voiceStatus);
  const trySave = (): void => {
    if (saving) return;
    if (body.trim() === "") {
      setEmpty(true);
      return;
    }
    onSubmit(id, body);
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    // Esc は書き換えを捨てる（使う側の「戻る」へ伝えない）
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      onCancel(id);
      return;
    }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
      event.preventDefault();
      trySave();
    }
  };
  const message = empty ? "コメントを入れてから修正してください。" : error;
  const actions = (
    <>
      <Button variant="ghost" disabled={saving} onClick={() => onCancel(id)}>
        キャンセル
      </Button>
      <Button ref={submitRef} type="submit" title="修正（Ctrl+Enter）" disabled={saving}>
        修正
      </Button>
    </>
  );
  return (
    <form
      noValidate
      data-part="edit"
      className="grid gap-1.5"
      onSubmit={(event) => {
        event.preventDefault();
        trySave();
      }}
    >
      {/* 録音中は入力欄の場所に波形を出す（返信の入力と同じ横並びの行に置き、入力欄の幅に広げる） */}
      <div className="flex items-end gap-2">
        <Textarea
          ref={fieldRef}
          aria-label={`${label}の本文`}
          aria-keyshortcuts="Control+Enter"
          value={body}
          readOnly={fieldLocked(saving, phase)}
          // 録音中は波形と入れ替えて隠す（外さないので中身と選んだ範囲が残る）
          hidden={phase === "recording"}
          className="field-sizing-content min-w-0 flex-1 resize-y field-edit"
          onKeyDown={handleKeyDown}
          onChange={(event) => {
            setEmpty(false);
            onBodyChange(event.target.value);
          }}
        />
        <VoiceWave voice={phase} levels={levels} />
      </div>
      <EditMessage voice={phase} elapsed={elapsed} message={message} voiceStatus={voiceStatus} voiceDetail={voiceDetail} />
      <div className="flex justify-end gap-1.5">
        {voice === undefined ? (
          actions
        ) : (
          <VoiceButtons doneRef={doneRef} voice={voice} voiceReason={voiceReason} submit={actions} onStart={onVoiceStart} onCancel={onVoiceCancel} onDone={() => onVoiceDone?.()} onBlocked={onVoiceBlocked} />
        )}
      </div>
    </form>
  );
};
