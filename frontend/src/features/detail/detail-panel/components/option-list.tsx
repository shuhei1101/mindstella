// 検討事項の案のカード（左上の記号のアイコン、採用 / 不採用と推奨のバッジ。採用した案が無いときは推奨の案の理由を「推奨理由」の欄に出す）。差分の表示の間は前の値と今の値を並べる
import { useState, type ReactNode } from "react";

import { KeyDiff } from "@/features/detail/detail-panel/components/key-diff";
import { ValueText } from "@/features/detail/detail-panel/components/value-text";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
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

/** 案の記号の丸いアイコン */
const KEY_ICON_CLASS = "grid size-6 flex-none place-items-center rounded-full bg-muted font-mono text-small font-semibold text-foreground";

/** 推奨・採用・不採用のバッジ */
const BADGE_CLASS = "mt-0.5 inline-flex h-5 flex-none items-center gap-0.5 rounded-control border px-1.5 text-xs";

/** 利用者が選んだ案（送信前のレビュー中。AI の採用とは別） */
export type OptionChoice = { key: string; note?: string };

export type OptionListProps = {
  options: readonly Option[];
  previous: readonly Option[] | null;
  marks?: Record<string, ReactNode>;
  /** 利用者が選んだ案。`onChoose` を渡したときだけ使う */
  choice?: OptionChoice | null;
  /** 案を選んで確定したとき。渡したときだけ、未決定の検討事項の案のカードに選ぶ操作を出す */
  onChoose?: (choice: OptionChoice) => void;
  /** 選んだ案を取り消したとき */
  onCancelChoice?: () => void;
};

/** 案を選ぶ操作の帯。押すと一言の入力と確定を出す */
const ChooseBar = ({ optionKey, chosen, note, onChoose, onCancel }: { optionKey: string; chosen: boolean; note: string | undefined; onChoose: (choice: OptionChoice) => void; onCancel: (() => void) | undefined }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(note ?? "");
  if (editing) {
    return (
      <div className="mt-2 flex flex-col gap-1.5 border-t border-border-soft pt-2">
        <label className="text-xs text-muted-foreground" htmlFor={`choice-note-${optionKey}`}>
          一言（任意）
        </label>
        <Textarea id={`choice-note-${optionKey}`} rows={2} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="選んだ理由など" />
        <div className="flex justify-end gap-1.5">
          <Button variant="ghost" onClick={() => setEditing(false)}>
            キャンセル
          </Button>
          <Button
           
            onClick={() => {
              onChoose(draft.trim() === "" ? { key: optionKey } : { key: optionKey, note: draft.trim() });
              setEditing(false);
            }}
          >
            この案を選ぶ
          </Button>
        </div>
      </div>
    );
  }
  if (chosen) {
    return (
      <div className="mt-2 flex flex-wrap items-center justify-between gap-1.5 border-t border-border-soft pt-2">
        <span className="min-w-0 text-small wrap-break-word text-muted-foreground">{note === undefined ? "一言なし" : `一言: ${note}`}</span>
        <span className="flex gap-1.5">
          <Button variant="ghost" onClick={() => setEditing(true)}>
            一言を編集
          </Button>
          <Button variant="outline" onClick={onCancel}>
            選択を取り消す
          </Button>
        </span>
      </div>
    );
  }
  return (
    <div className="mt-2 flex justify-end border-t border-border-soft pt-2">
      <Button variant="outline" onClick={() => setEditing(true)}>
        <Icon name="check" className="size-3.5" />
        この案を選ぶ
      </Button>
    </div>
  );
};

/** 案のカードに渡す、選ぶ操作の状態 */
type ChooseState = { chosen: boolean; note: string | undefined; onChoose: (choice: OptionChoice) => void; onCancel: (() => void) | undefined };

/** 案のカード 1 枚 */
const OptionCard = ({ option, before, compare, decided, mark, choose }: { option: Option; before: Option | undefined; compare: boolean; decided: boolean; mark: ReactNode; choose?: ChooseState }) => {
  const recommended = option.recommended === true && !decided;
  const rows = FIELDS.map(([label, field]) => ({ label: recommended && field === "reason" ? "推奨理由" : label, field, value: optionText(option[field]), was: optionText(before?.[field]) }))
    .filter(({ value, was }) => (value !== undefined && value !== "") || (compare && was !== undefined));
  const chosen = choose?.chosen === true;
  return (
    <div data-chosen={chosen ? "" : undefined} className={cn("rounded-control border border-border-soft p-2", option.adopted === true && "border-mark-line bg-mark-weak", chosen && "border-dashed border-primary")}>
      <div className="flex items-start gap-2">
        <span className={KEY_ICON_CLASS}>
          <span className="sr-only">案 </span>
          {option.key}
        </span>
        <div data-key={`options[${option.key}].content`} className="flex min-h-6 min-w-0 flex-1 items-center">
          {compare && before?.content !== option.content ? <KeyDiff was={before?.content ?? null} now={option.content} /> : <ValueText value={option.content} />}
        </div>
        {recommended ? (
          <span className={cn(BADGE_CLASS, "border-mark-line text-mark")}>
            <Icon name="star" className="size-3" />
            推奨
          </span>
        ) : null}
        <ResultBadge before={before} option={option} compare={compare} />
        {chosen ? (
          <span className={cn(BADGE_CLASS, "border-dashed border-primary text-primary")}>
            <Icon name="check" className="size-3" />
            選択済み（未送信）
          </span>
        ) : null}
        {mark}
      </div>
      {rows.length > 0 ? (
        <dl className="mt-1 grid grid-cols-meta items-baseline gap-x-2 text-small">
          {rows.map(({ label, field, value, was }) => (
            <div key={field} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd data-key={`options[${option.key}].${field}`}>{compare && was !== value ? <KeyDiff was={was ?? null} now={value ?? null} /> : <ValueText value={value} />}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {choose === undefined ? null : <ChooseBar optionKey={option.key} chosen={chosen} note={choose.note} onChoose={choose.onChoose} onCancel={choose.onCancel} />}
    </div>
  );
};

/** 採用・不採用のバッジ（差分の表示の間は前の値と今の値） */
const ResultBadge = ({ before, option, compare }: { before: Option | undefined; option: Option; compare: boolean }) => {
  const result = resultOf(option);
  if (compare && resultOf(before) !== result) return <KeyDiff was={resultOf(before)} now={result} plain />;
  if (result === null) return null;
  return <span className={cn(BADGE_CLASS, option.adopted === true ? "border-mark-line bg-mark-weak text-mark" : "border-border text-muted-foreground")}>{result}</span>;
};

export const OptionList = ({ options, previous, marks = {}, choice = null, onChoose, onCancelChoice }: OptionListProps) => {
  const compare = previous !== null;
  const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
  const decided = options.some((option) => option.adopted === true);
  const choosable = onChoose !== undefined && !decided && !compare;
  return (
    <div className="flex flex-col gap-2">
      {options.map((option) => (
        <OptionCard
          key={option.key}
          option={option}
          before={previous?.find((entry) => entry.key === option.key)}
          compare={compare}
          decided={decided}
          mark={marks[option.key]}
          {...(choosable ? { choose: { chosen: choice?.key === option.key, note: choice?.key === option.key ? choice.note : undefined, onChoose, onCancel: onCancelChoice } } : {})}
        />
      ))}
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
