// 絞り込みのドロワー（部品設計『絞り込み.tsx』）。列ごとの文字の欄と、条件ごとに値を件数つきのチェックボックスで並べる
import { useEffect, useRef, useState } from "react";

import { Icon, StatusMark } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";
import type { Filters } from "@/shared/core/filters";
import { TagExprEditor } from "@/shared/components/tag-expr-editor";
import { simpleTagsOf, type PresetChoice, type PresetFilter } from "@/shared/core/presets";
import { cn } from "@/shared/lib/cn";

/** 条件の値 */
export type FilterValue = { value: string; count: number };

/** 条件 1 つ */
export type FilterGroup = { key: string; label: string; values: FilterValue[]; mark?: "status" | "kind" };

/** タグの組み合わせ方。`all` は選んだタグを全て持つ項目、`any` はどれかを持つ項目を残す */
export type TagMatch = "all" | "any";

const TAG_MATCH_BUTTON: Record<TagMatch, string> = { all: "すべて含む", any: "どれかを含む" };

/** 文字の欄を打ち終えるまで待つミリ秒 */
const TEXT_DELAY_MS = 250;

export type FilterDrawerProps = {
  groups: FilterGroup[];
  selected: Filters;
  total: number;
  shown: number;
  narrow?: boolean;
  texts?: { key: string; label: string; value: string }[];
  tagMatch?: TagMatch;
  onTagMatchChange?: (match: TagMatch) => void;
  /** 選べるプリセット。選ぶとプリセットのタグでタグの条件を置き換える */
  presets?: PresetChoice[];
  onApplyPreset?: (name: string) => void;
  /** 今のタグの条件の式。条件が無ければ null */
  tagExpr?: PresetFilter | null;
  /** タグの条件を式で置き換える。渡すとタグの条件を式で書ける */
  onTagExprChange?: (expr: PresetFilter | null) => void;
  onToggleValue: (key: string, value: string) => void;
  onClearGroup: (key: string) => void;
  onClearAll: () => void;
  onClose: () => void;
  onTextChange: (key: string, text: string) => void;
};

export const FilterDrawer = ({ groups, selected, total, shown, narrow = false, texts = [], tagMatch = "all", onTagMatchChange, presets = [], onApplyPreset, tagExpr = null, onTagExprChange, onToggleValue, onClearGroup, onClearAll, onClose, onTextChange }: FilterDrawerProps) => {
  const timer = useRef(0);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    root.current?.querySelector("input")?.focus();
    return () => {
      window.clearTimeout(timer.current);
    };
  }, []);
  // チェックで表せない式はタグの条件を式で書く表示にする
  const complex = tagExpr !== null && simpleTagsOf(tagExpr) === null;
  const [writing, setWriting] = useState(complex);
  const exprMode = complex || writing;
  const filtering = Object.values(selected).some((values) => values.length > 0) || complex;
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
        {presets.length > 0 && onApplyPreset !== undefined ? (
          <fieldset className="mb-2">
            <legend className="text-small font-medium">プリセット</legend>
            <ul className="mt-1 flex flex-wrap gap-1">
              {presets.map((preset) => (
                <li key={preset.name}>
                  <button
                    type="button"
                    aria-pressed={preset.applied}
                    title={preset.description}
                    className={cn(
                      "flex h-8 items-center gap-1.5 rounded-control border border-border bg-card px-2.5 text-small hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring",
                      preset.count === 0 && "border-dashed text-muted-foreground",
                      preset.applied && "border-mark-line bg-mark-weak font-medium hover:bg-mark-weak",
                    )}
                    onClick={() => {
                      onApplyPreset(preset.name);
                    }}
                  >
                    {preset.name}
                    <span className="text-xs text-muted-foreground">
                      <span className="font-mono">{preset.count}</span> 件
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </fieldset>
        ) : null}
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
              {group.key === "tags" && onTagMatchChange !== undefined && !exprMode ? (
                <fieldset className="mt-1 inline-flex rounded-control border border-border bg-card p-0.5">
                  <legend className="sr-only">タグの組み合わせ方</legend>
                  {(["all", "any"] as const).map((value) => (
                    <label
                      key={value}
                      className={cn("flex h-7 cursor-pointer items-center rounded-control px-2 text-small hover:bg-accent has-focus-visible:outline-2 has-focus-visible:outline-ring", tagMatch === value && "bg-mark-weak font-medium hover:bg-mark-weak")}
                    >
                      <input
                        type="radio"
                        name="tag-match"
                        value={value}
                        data-tag-match={value}
                        checked={tagMatch === value}
                        className="sr-only"
                        onChange={() => {
                          onTagMatchChange(value);
                        }}
                      />
                      {TAG_MATCH_BUTTON[value]}
                    </label>
                  ))}
                </fieldset>
              ) : null}
              {group.key === "tags" && onTagExprChange !== undefined ? (
                <fieldset className="mt-1 ml-1 inline-flex rounded-control border border-border bg-card p-0.5">
                  <legend className="sr-only">タグの条件の書き方</legend>
                  {([["check", "チェックで選ぶ"], ["expr", "式で書く"]] as const).map(([value, label]) => (
                    <label
                      key={value}
                      className={cn("flex h-7 cursor-pointer items-center rounded-control px-2 text-small hover:bg-accent has-focus-visible:outline-2 has-focus-visible:outline-ring", (value === "expr") === exprMode && "bg-mark-weak font-medium hover:bg-mark-weak", value === "check" && complex && "cursor-not-allowed text-muted-foreground")}
                    >
                      <input
                        type="radio"
                        name="tag-mode"
                        value={value}
                        checked={(value === "expr") === exprMode}
                        disabled={value === "check" && complex}
                        className="sr-only"
                        onChange={() => {
                          setWriting(value === "expr");
                        }}
                      />
                      {label}
                    </label>
                  ))}
                </fieldset>
              ) : null}
              {group.key === "tags" && onTagExprChange !== undefined && exprMode ? (
                <div className="mt-1">
                  <TagExprEditor expr={tagExpr ?? { and: [{ field: "tags", op: "eq", values: [] }] }} tags={group.values} onChange={onTagExprChange} />
                </div>
              ) : (
              <ul>
                {group.values.map(({ value, count }) => (
                  <li key={value}>
                    <label className={cn("flex items-center gap-1 py-0.5 text-small", count === 0 && "text-subtle-foreground")}>
                      <Checkbox value={value} data-key={group.key} checked={chosen.includes(value)} onChange={() => { onToggleValue(group.key, value); }} />
                      {group.mark === "status" ? <StatusMark status={value} /> : null}
                      <span className="min-w-0 flex-1 wrap-break-word">{value}</span>
                      <span aria-label={`${String(count)} 件`} className={cn("flex-none font-mono text-xs", count === 0 ? "text-subtle-foreground" : "text-muted-foreground")}>{count}</span>
                    </label>
                  </li>
                ))}
              </ul>
              )}
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
