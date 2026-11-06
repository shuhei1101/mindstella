// 取り下げの札（部品設計『取り下げの札.tsx』）。× の印は読み上げに出さず、「取り下げ」の文字で伝える
import { Icon } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

export type WithdrawnBadgeProps = { large?: boolean };

export const WithdrawnBadge = ({ large = false }: WithdrawnBadgeProps) => (
  <span className={cn("inline-flex items-center gap-0.5 rounded-control border border-border px-1 text-muted-foreground", large ? "text-small" : "text-xs")}>
    <Icon name="x" className="size-3" />
    取り下げ
  </span>
);
