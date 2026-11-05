// 項目の追加の入力。溜めると `item-add` の編集にする
import { useState } from "react";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import type { Kind } from "@/shared/core/records";
import { useAddEdit } from "@/shared/hooks/use-edits";

export type ItemAddFormProps = { kind: Kind; onClose: () => void };

export const ItemAddForm = ({ kind, onClose }: ItemAddFormProps) => {
  const add = useAddEdit();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        const value = title.trim();
        if (value === "") {
          setError("タイトルを入力してください。");
          return;
        }
        setError(null);
        add.mutate({ op: "item-add", key: kind, value: { title: value } }, { onSuccess: onClose, onError: (failure) => { setError(failure.message); } });
      }}
    >
      <label className="flex flex-col gap-1 text-small">
        タイトル
        <Input value={title} autoComplete="off" aria-invalid={error !== null} onChange={(event) => { setTitle(event.target.value); }} />
      </label>
      {error === null ? null : (
        <p role="alert" className="text-small text-destructive">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          キャンセル
        </Button>
        <Button type="submit" disabled={add.isPending}>
          追加
        </Button>
      </div>
    </form>
  );
};
