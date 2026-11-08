// レビュー中の書き込みの本文をその場で書き換える入力欄と「キャンセル」「修正」（スレッドの書き込みとレビュー中の書き込みの画面と詳細のコメントが使う）
import { useState, type KeyboardEvent } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";

export type ReviewEditFormProps = {
  id: string;
  label: string;
  body: string;
  error?: string | null;
  saving?: boolean;
  onSubmit: (id: string, body: string) => void;
  onCancel: (id: string) => void;
};

export const ReviewEditForm = ({ id, label, body, error = null, saving = false, onSubmit, onCancel }: ReviewEditFormProps) => {
  const [value, setValue] = useState(body);
  const [empty, setEmpty] = useState(false);
  const trySave = (): void => {
    if (saving) return;
    if (value.trim() === "") {
      setEmpty(true);
      return;
    }
    onSubmit(id, value);
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
  const message = empty ? "コメントを入れてから直してください。" : error;
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
      <Textarea aria-label={`${label}の本文`} aria-keyshortcuts="Control+Enter" value={value} readOnly={saving} className="field-sizing-content resize-y field-edit" onKeyDown={handleKeyDown} onChange={(event) => {
        setEmpty(false);
        setValue(event.target.value);
      }} />
      {message === null ? null : (
        <p role="alert" data-part="message" className="m-0 flex items-start gap-1 text-small">
          <Icon name="alert" className="text-st-review" />
          <span>{message}</span>
        </p>
      )}
      <div className="flex justify-end gap-1.5">
        <Button variant="ghost" disabled={saving} onClick={() => onCancel(id)}>
          キャンセル
        </Button>
        <Button type="submit" title="修正（Ctrl+Enter）" disabled={saving}>
          修正
        </Button>
      </div>
    </form>
  );
};
