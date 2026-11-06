// 差分の印（部品設計『差分の印.tsx』）。色だけでなく形（+ と ● と −）でも新規と変更と消したを分け、名前は読み上げに残す
import { Icon, type IconName } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

/** 差分の印の種類 */
export type DiffKind = "new" | "changed" | "removed";

/** 項目の ID → 差分の印（消した項目は中身が残らないので、印は新規と変更だけ） */
export type DiffMarks = Record<string, Exclude<DiffKind, "removed">>;

const DIFF_LABEL: Record<DiffKind, string> = { new: "新規", changed: "変更", removed: "消した" };
const DIFF_GLYPH: Record<DiffKind, IconName> = { new: "plus", changed: "changed", removed: "minus" };
const DIFF_TONE: Record<DiffKind, string> = { new: "text-st-done", changed: "text-diff-changed", removed: "text-destructive" };

export type DiffMarkProps = { kind: DiffKind; labeled?: boolean };

export const DiffMark = ({ kind, labeled = false }: DiffMarkProps) =>
  labeled ? (
    <span className={cn("inline-flex items-center gap-0.5 rounded-control border border-current px-1 text-xs", DIFF_TONE[kind])}>
      <Icon name={DIFF_GLYPH[kind]} className="size-3" />
      {DIFF_LABEL[kind]}
    </span>
  ) : (
    <span title={DIFF_LABEL[kind]} className={cn("inline-flex", DIFF_TONE[kind])}>
      <Icon name={DIFF_GLYPH[kind]} className="size-3" />
      <span className="sr-only">{DIFF_LABEL[kind]}</span>
    </span>
  );
