// 保存待ちの印（部品設計『保存待ちの印.tsx』）。差分の印・コメントの印と形で見分けられるよう、破線の枠（書き込めない編集は実線）にする
import { Icon, type IconName } from "@/shared/components/icon";
import type { PendingMarkKind } from "@/shared/core/edits";
import { cn } from "@/shared/lib/cn";

const PENDING_MARKS: Record<PendingMarkKind, { label: string; icon: IconName }> = {
  pending: { label: "保存待ち", icon: "layers" },
  remove: { label: "保存で削除", icon: "trash" },
  blocked: { label: "書き込めない", icon: "alert" },
};

export type PendingMarkProps = { kind: PendingMarkKind; compact?: boolean };

export const PendingMark = ({ kind, compact = false }: PendingMarkProps) => {
  const { label, icon } = PENDING_MARKS[kind];
  return (
    <span title={compact ? label : undefined} className={cn("inline-flex items-center gap-0.5 rounded-control border px-1 text-xs", kind === "blocked" ? "border-destructive text-destructive" : "border-dashed border-mark-line text-foreground")}>
      <Icon name={icon} className="size-3" />
      {compact ? <span className="sr-only">{label}</span> : label}
    </span>
  );
};
