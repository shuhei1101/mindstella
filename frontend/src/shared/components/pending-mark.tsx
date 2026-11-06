// 保存待ちの印（部品設計『保存待ちの印.tsx』）。差分の印・コメントの印と形で見分けられるよう、破線の枠（書き込めない編集は実線）にする
import { Icon, type IconName } from "@/shared/components/icon";
import type { PendingMarkKind } from "@/shared/core/edits";
import { cn } from "@/shared/lib/cn";

const PENDING_MARKS: Record<PendingMarkKind, { label: string; icon: IconName }> = {
  pending: { label: "保存待ち", icon: "layers" },
  remove: { label: "保存で削除", icon: "trash" },
  blocked: { label: "書き込めない", icon: "alert" },
};

/** 枠の線の種類と色（書き換え・追加は印の色の破線、削除は文字色の破線、書き込めない編集は失敗の赤の実線） */
const PENDING_TONE: Record<PendingMarkKind, string> = {
  pending: "border-dashed border-mark-line text-foreground",
  remove: "border-dashed border-foreground text-foreground",
  blocked: "border-destructive text-destructive",
};

export type PendingMarkProps = { kind: PendingMarkKind; compact?: boolean };

export const PendingMark = ({ kind, compact = false }: PendingMarkProps) => {
  const { label, icon } = PENDING_MARKS[kind];
  return (
    <span title={compact ? label : undefined} className={cn("inline-flex items-center gap-0.5 rounded-control border text-xs", compact ? "h-4.5 w-5 justify-center" : "px-1", PENDING_TONE[kind])}>
      <Icon name={icon} className="size-3" />
      {compact ? <span className="sr-only">{label}</span> : label}
    </span>
  );
};
