// チップの入力（部品設計『チップの入力.tsx』）。値のチップと、値を足す入力欄。項目のタグは主題のトグルを持つ
import { useRef, useState } from "react";

import { Icon } from "@/shared/components/icon";
import { Input } from "@/shared/components/ui/input";
import type { Tag } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

export type ChipsInputProps = {
  controlId: string;
  name: string;
  hint?: string;
  values: readonly (Tag | string)[];
  suggestions?: readonly string[] | null;
  monospace?: boolean;
  mainToggle?: boolean;
  disabled?: boolean;
  /** 追加する前に入れた値を確かめる。`value` を返したらその値を追加し、`error` を返したら追加せず入力欄の直下に誤りを出す */
  validate?: (value: string) => { error: string } | { value: string };
  onChange: (values: (Tag | string)[], removed: string | null) => void;
};

const toTag = (value: Tag | string): Tag => {
  if (typeof value === "string") return { name: value };
  return value.main === true ? { name: value.name, main: true } : { name: value.name };
};

export const ChipsInput = ({ controlId, name, hint = "", values, suggestions = null, monospace = false, mainToggle = false, disabled = false, validate, onChange }: ChipsInputProps) => {
  const field = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const current = values.map(toTag);
  const output = (tags: Tag[]): (Tag | string)[] => (mainToggle ? tags : tags.map((tag) => tag.name));
  const addValue = (): void => {
    const input = field.current;
    if (input === null) return;
    const entered = input.value.trim();
    if (entered === "") return;
    const checked = validate === undefined ? { value: entered } : validate(entered);
    // 誤り: 追加せず、入れた値を入力欄に残して直下に誤りを出す
    if ("error" in checked) {
      setError(checked.error);
      return;
    }
    setError(null);
    input.value = "";
    if (current.some((tag) => tag.name === checked.value)) return;
    onChange(output([...current, { name: checked.value }]), null);
  };
  const listId = `${controlId}-list`;
  const errorId = `${controlId}-error`;
  return (
    <div role="group" aria-label={name} className={cn("flex flex-wrap items-center gap-1", error !== null && "rounded-md ring-1 ring-destructive")}>
      {current.map((entry, index) => (
        <span key={entry.name} className={cn("inline-flex items-center gap-1 rounded-full bg-muted px-2 text-xs", monospace && "font-mono", entry.main === true && "bg-mark-weak")}>
          {mainToggle ? (
            <button
              type="button"
              disabled={disabled}
              aria-label={`${entry.name} を主題`}
              aria-pressed={entry.main === true}
              title={entry.main === true ? "主題を外す" : "主題にする"}
              className="-my-1 -ml-1 inline-flex size-6 flex-none cursor-pointer items-center justify-center"
              onClick={() => {
                onChange(output(current.map((tag, position) => (position !== index ? tag : tag.main === true ? { name: tag.name } : { name: tag.name, main: true }))), null);
              }}
            >
              <Icon name={entry.main === true ? "main" : "mainOff"} className="size-3" />
              <span className="sr-only">主題</span>
            </button>
          ) : null}
          {entry.name}
          <button
            type="button"
            disabled={disabled}
            aria-label={`${entry.name} を外す`}
            className="cursor-pointer"
            onClick={() => {
              onChange(output(current.filter((_, position) => position !== index)), entry.name);
            }}
          >
            <Icon name="x" className="size-3" />
          </button>
        </span>
      ))}
      <Input
        ref={field}
        id={controlId}
        type="text"
        role="combobox"
        list={suggestions === null ? undefined : listId}
        placeholder={hint}
        aria-label={`${name}を追加`}
        aria-expanded={false}
        aria-controls={listId}
        aria-invalid={error === null ? undefined : true}
        aria-describedby={error === null ? undefined : errorId}
        autoComplete="off"
        disabled={disabled}
        className="w-40 flex-1"
        onChange={() => {
          setError(null);
        }}
        onKeyDown={(event) => {
          if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
          event.preventDefault();
          addValue();
        }}
        onBlur={addValue}
      />
      {error === null ? null : (
        <p id={errorId} className="m-0 basis-full text-small">
          入力の誤り: {error}
        </p>
      )}
      {suggestions === null ? null : (
        <datalist id={listId}>
          {suggestions.map((tag) => (
            <option key={tag} value={tag} />
          ))}
        </datalist>
      )}
    </div>
  );
};
