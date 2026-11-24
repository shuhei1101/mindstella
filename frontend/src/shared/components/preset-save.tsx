// プリセットの保存（部品設計『プリセットの保存.tsx』）。今の絞り込みのタグの条件に名前を付けて、プリセットとして保存する
import { useId, useState } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";

/** 保存の結果。失敗したときは入力欄の下に出す文 */
export type PresetSaveResult = { error: string | null };

export type PresetSaveProps = {
  /** 今の絞り込みにタグの条件があるか。無ければ保存できない */
  hasTagCondition: boolean;
  /** タグの条件のほかに、状態・種類・列の文字の条件があるか。あれば、タグの条件だけを保存する旨を出す */
  hasOtherConditions: boolean;
  /** 名前を受けて保存する。失敗したら理由を返却する */
  onSave: (name: string) => Promise<PresetSaveResult>;
  /** 最初から入力欄を開いた状態で出す（ストーリー用） */
  defaultOpen?: boolean;
  /** 最初に出すエラー（ストーリー用） */
  defaultError?: string | null;
  /** 最初に入れておく名前（ストーリー用） */
  defaultName?: string;
};

export const PresetSave = ({ hasTagCondition, hasOtherConditions, onSave, defaultOpen = false, defaultError = null, defaultName = "" }: PresetSaveProps) => {
  const [open, setOpen] = useState(defaultOpen);
  const [name, setName] = useState(defaultName);
  const [error, setError] = useState<string | null>(defaultError);
  const [saving, setSaving] = useState(false);
  const inputId = useId();
  const errorId = useId();
  const reasonId = useId();
  if (!open) {
    return (
      <div className="flex flex-col gap-1">
        <Button
          variant="outline"
          aria-disabled={!hasTagCondition}
          aria-describedby={hasTagCondition ? undefined : reasonId}
          className="self-start aria-disabled:cursor-not-allowed aria-disabled:opacity-50"
          onClick={() => {
            if (hasTagCondition) setOpen(true);
          }}
        >
          <Icon name="plus" />
          <span>プリセットとして保存</span>
        </Button>
        {hasTagCondition ? null : (
          <p id={reasonId} className="text-xs text-muted-foreground">
            タグの条件を選ぶと、プリセットとして保存できます。
          </p>
        )}
      </div>
    );
  }
  const submit = async (): Promise<void> => {
    if (name.trim() === "") {
      setError("プリセットの名前を入れてください。");
      return;
    }
    setSaving(true);
    const result = await onSave(name.trim());
    setSaving(false);
    setError(result.error);
    if (result.error === null) {
      setOpen(false);
      setName("");
    }
  };
  return (
    <form
      className="flex flex-col gap-1.5 rounded-control border border-border p-2"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <label htmlFor={inputId} className="text-small font-medium">
        プリセットの名前
      </label>
      <Input
        id={inputId}
        value={name}
        autoComplete="off"
        aria-invalid={error !== null}
        aria-describedby={error === null ? undefined : errorId}
        onChange={(event) => {
          setName(event.target.value);
        }}
      />
      {error === null ? null : (
        <p id={errorId} className="text-xs text-destructive">
          {error}
        </p>
      )}
      {hasOtherConditions ? <p className="text-xs text-muted-foreground">タグの条件だけを保存します。状態・種類・文字の条件は保存しません。</p> : null}
      <div className="flex justify-end gap-1">
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setOpen(false);
            setError(null);
          }}
        >
          キャンセル
        </Button>
        <Button type="submit" aria-disabled={saving} className="aria-disabled:opacity-50">
          {saving ? "保存中…" : "保存"}
        </Button>
      </div>
    </form>
  );
};
