// 本文の形式の札（部品設計『本文の形式の札.tsx』）。色だけに頼らず、`MD` / `HTML` の文字で伝える
import { cn } from "@/shared/lib/cn";

const FORMAT_LABEL = { md: "MD", html: "HTML" } as const;
const FORMAT_TITLE = { md: "本文は Markdown", html: "本文は HTML" } as const;

export type BodyFormatBadgeProps = { format: "md" | "html" };

export const BodyFormatBadge = ({ format }: BodyFormatBadgeProps) => (
  <span title={FORMAT_TITLE[format]} className={cn("rounded-control border border-border px-1 font-mono text-xs text-muted-foreground", format === "html" && "border-muted-foreground bg-muted text-foreground")}>
    {FORMAT_LABEL[format]}
  </span>
);
