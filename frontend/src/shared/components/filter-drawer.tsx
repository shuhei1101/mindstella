// 絞り込みのドロワー（部品設計『絞り込み.tsx』）。列ごとの文字の欄と、条件ごとに値を件数つきのチェックボックスで並べる
import { useEffect, useRef } from "react";

import { Icon, StatusMark } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";
import type { Filters } from "@/shared/core/filters";
import { cn } from "@/shared/lib/cn";

/** 条件の値 */
export type FilterValue = { value: string; count: number; hit?: number };

/** 条件 1 つ */
export type FilterGroup = { key: string; label: string; values: FilterValue[]; mark?: "status" | "kind" };

/** 文字の欄を打ち終えるまで待つミリ秒 */
const TEXT_DELAY_MS = 250;

export type FilterDrawerProps = {
  groups: FilterGroup[];
  selected: Filters;
  total: number;
  shown: number;
  narrow?: boolean;
  texts?: { key: string; label: string; value: string }[];
  onToggleValue: (key: string, value: string) => void;
  onClearGroup: (key: string) => void;
  onClearAll: () => void;
  onClose: () => void;
  onTextChange: (key: string, text: string) => void;
};

export const FilterDrawer = ({ groups, selected, total, shown, narrow = false, texts = [], onToggleValue, onClearGroup, onClearAll, onClose, onTextChange }: FilterDrawerProps) => {
  const timer = useRef(0);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    root.current?.querySelector("input")?.focus();
    return () => {
      window.clearTimeout(timer.current);
    };
  }, []);
  const filtering = Object.values(selected).some((values) => values.length > 0);
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- ドロワーが Esc を受ける
    <div
      ref={root}
      role="dialog"
      aria-labelledby="drawer-title"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          onClose();
        }
      }}
      className={cn("fixed inset-y-0 left-0 z-30 flex w-105 max-w-full flex-col border-r border-border bg-card", narrow && "w-full")}
    >
      <div className="flex items-center gap-2 border-b border-border-soft p-2">
        <p id="drawer-title" className="font-medium">
          絞り込み
        </p>
        <span aria-live="polite" className="text-small text-muted-foreground">
          {filtering ? `${String(total)} 件中 ${String(shown)} 件` : `${String(total)} 件`}
        </span>
        <Button variant="ghost" size="icon" aria-label="絞り込みを閉じる" className="ml-auto" onClick={onClose}>
          <Icon name="x" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-2">
        {texts.length > 0 ? (
          <fieldset className="mb-2">
            <legend className="text-small font-medium">文字を含む</legend>
            {texts.map((text) => (
              <label key={text.key} className="mt-1 flex items-center gap-2 text-small">
                <span className="w-24 flex-none">{text.label}</span>
                <Input
                  type="search"
                  defaultValue={text.value}
                  autoComplete="off"
                  data-text-key={text.key}
                  onChange={(event) => {
                    const { value } = event.target;
                    window.clearTimeout(timer.current);
                    timer.current = window.setTimeout(() => {
                      onTextChange(text.key, value);
                    }, TEXT_DELAY_MS);
                  }}
                />
              </label>
            ))}
          </fieldset>
        ) : null}
        {groups.map((group) => {
          const chosen = selected[group.key] ?? [];
          const checked = group.values.filter(({ value }) => chosen.includes(value)).length;
          return (
            <fieldset key={group.key} className="mb-2">
              <legend className="flex items-center gap-2 text-small font-medium">
                {group.label}
                {checked > 0 ? <span className="text-xs text-muted-foreground">{checked} 件を選択</span> : null}
              </legend>
              {checked > 0 ? (
                <Button variant="ghost" aria-label={`${group.label}の条件を解除`} onClick={() => { onClearGroup(group.key); }}>
                  解除
                </Button>
              ) : null}
              <ul>
                {group.values.map(({ value, count, hit }) => (
                  <li key={value}>
                    <label className={cn("flex items-center gap-1 py-0.5 text-small", count === 0 && "text-subtle-foreground")}>
                      <Checkbox value={value} data-key={group.key} checked={chosen.includes(value)} onChange={() => { onToggleValue(group.key, value); }} />
                      {group.mark === "status" ? <StatusMark status={value} /> : null}
                      <span className="min-w-0 flex-1 wrap-break-word">{value}</span>
                      {hit !== undefined && hit > 0 ? <span aria-label={`キーワードに一致した項目 ${String(hit)} 件`} className="flex-none font-mono text-xs text-mark">{hit}</span> : null}
                      <span aria-label={`${String(count)} 件`} className={cn("flex-none font-mono text-xs", count === 0 ? "text-subtle-foreground" : "text-muted-foreground")}>{count}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
          );
        })}
      </div>
      <div className="flex items-center gap-2 border-t border-border-soft p-2">
        {filtering ? <Button variant="ghost" onClick={onClearAll}>すべて解除</Button> : null}
        <Button className="ml-auto" onClick={onClose}>
          {shown} 件を表示
        </Button>
      </div>
    </div>
  );
};
