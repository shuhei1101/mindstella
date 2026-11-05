// 検討事項の案のカード（採用 / 不採用と理由、採用した案が無いときは推奨の印）。差分の表示の間は前の値と今の値を並べる
import type { ReactNode } from "react";

import { KeyDiff } from "@/features/detail/detail-panel/components/key-diff";
import { ValueText } from "@/features/detail/detail-panel/components/value-text";
import { Icon } from "@/shared/components/icon";
import type { Option } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

type Field = "pros" | "cons" | "note" | "reason";

const FIELDS: [string, Field][] = [
  ["メリット", "pros"],
  ["デメリット", "cons"],
  ["備考", "note"],
  ["理由", "reason"],
];

const optionText = (value: string | string[] | undefined): string | undefined => {
  if (Array.isArray(value)) return value.length === 0 ? undefined : value.join("、");
  return value;
};

const resultOf = (option: Option | undefined): string | null => {
  if (option === undefined) return null;
  if (option.adopted === true) return "採用";
  return option.adopted === false ? "不採用" : null;
};

export type OptionListProps = { options: readonly Option[]; previous: readonly Option[] | null; marks?: Record<string, ReactNode> };

export const OptionList = ({ options, previous, marks = {} }: OptionListProps) => {
  const compare = previous !== null;
  const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
  const decided = options.some((option) => option.adopted === true);
  return (
    <div className="flex flex-col gap-2">
      {options.map((option) => {
        const before = previous?.find((entry) => entry.key === option.key);
        const result = resultOf(option);
        const recommended = option.recommended === true && !decided;
        const rows = FIELDS.map(([label, field]) => ({ label, field, value: optionText(option[field]), was: optionText(before?.[field]) })).filter(({ value, was }) => (value !== undefined && value !== "") || (compare && was !== undefined));
        return (
          <div key={option.key} className={cn("rounded-control border border-border-soft p-2", option.adopted === true && "border-mark-line bg-mark-weak", option.adopted === false && "opacity-70")}>
            <div className="flex items-start gap-2">
              <span className="font-mono text-small font-semibold">{option.key}</span>
              <div data-key={`options[${option.key}].content`} className="min-w-0 flex-1">
                {compare && before?.content !== option.content ? <KeyDiff was={before?.content ?? null} now={option.content} /> : <ValueText value={option.content} />}
              </div>
              {recommended ? (
                <span className="inline-flex items-center gap-0.5 rounded-control border border-mark-line px-1 text-xs text-mark">
                  <Icon name="star" className="size-3" />
                  推奨
                </span>
              ) : null}
              {compare && resultOf(before) !== result ? <KeyDiff was={resultOf(before)} now={result} plain /> : result === null ? null : <span className="text-xs">{result}</span>}
              {marks[option.key]}
            </div>
            {rows.length > 0 ? (
              <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-2 text-small">
                {rows.map(({ label, field, value, was }) => (
                  <div key={field} className="contents">
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd data-key={`options[${option.key}].${field}`}>{compare && was !== value ? <KeyDiff was={was ?? null} now={value ?? null} /> : <ValueText value={value} />}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
        );
      })}
      {removed.map((option) => (
        <div key={option.key} className="flex gap-2 rounded-control border border-border-soft p-2">
          <span className="font-mono text-small font-semibold">{option.key}</span>
          <del className="df-was">
            <span className="sr-only">消した案: </span>
            {option.content}
          </del>
        </div>
      ))}
    </div>
  );
};
