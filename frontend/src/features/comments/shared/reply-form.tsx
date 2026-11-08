// 返信の入力（部品設計『返信の入力.tsx』）。スレッドの下端に留める、返信をレビュー中に溜める入力欄と「レビューに追加」のボタン
import { useId, type SyntheticEvent, type KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { cn } from "@/shared/lib/cn";

/** 返信を溜める状態。idle は結果を出さない */
export type ReplyStatus = "idle" | "saving" | "saved" | "failed";

/** 本文の最大の文字数（『レビュー中のコメントの追加』の body） */
const COMMENT_BODY_MAX_LENGTH = 10000;

export type ReplyFormProps = {
  thread: string;
  body: string;
  status: ReplyStatus;
  count?: number | null;
  detail?: string | null;
  onSubmit: (thread: string, body: string) => void;
  onInput: (body: string) => void;
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

export const ReplyForm = ({ thread, body, status, count = null, detail = null, onSubmit, onInput }: ReplyFormProps) => {
  const fieldId = useId();
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
    <form noValidate data-part="reply" className="@container grid gap-1.5 border-t border-border p-3" onSubmit={handleSubmit}>
      <label htmlFor={fieldId} className="text-small text-muted-foreground">
        返信
      </label>
      <Textarea id={fieldId} name="body" rows={1} maxLength={COMMENT_BODY_MAX_LENGTH} value={body} readOnly={saving} aria-keyshortcuts="Control+Enter" aria-describedby={messageId} className="field-sizing-content resize-y field-send" onChange={(event) => onInput(event.target.value)} onKeyDown={handleKeyDown} />
      <div className="flex items-start gap-2 @max-send-narrow:flex-wrap @max-send-narrow:justify-end">
        <p id={messageId} role="status" className={cn("m-0 flex flex-1 items-start gap-1 text-small text-muted-foreground @max-send-narrow:order-2 @max-send-narrow:basis-full @max-send-narrow:empty:hidden", status === "failed" && "text-foreground")}>
          <ReplyResult status={status} count={count} detail={detail} />
        </p>
        <Button type="submit" title="レビューに追加（Ctrl+Enter）" data-focus="reply-send" disabled={saving || body.trim() === ""}>
          <Icon name="comment" />
          レビューに追加
        </Button>
      </div>
    </form>
  );
};
