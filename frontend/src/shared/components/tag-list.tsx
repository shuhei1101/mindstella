// タグの並び（部品設計『タグの並び.tsx』）。記録の順のまま並べ、主題のタグは枠と文字を 1 段濃くする
import { Icon } from "@/shared/components/icon";
import type { Tag } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

export type TagListProps = { values?: readonly (Tag | string)[] };

export const TagList = ({ values = [] }: TagListProps) => (
  <>
    {values.map((value) => {
      const name = typeof value === "string" ? value : value.name;
      const isMain = typeof value !== "string" && value.main === true;
      return (
        <span key={name} title={isMain ? "主題" : undefined} className={cn("inline-flex items-center gap-0.5 rounded-control border px-1 text-xs", isMain ? "border-foreground font-medium text-foreground" : "border-border-soft text-muted-foreground")}>
          {isMain ? <Icon name="main" className="size-3" /> : null}
          {isMain ? <span className="sr-only">主題</span> : null}
          {name}
        </span>
      );
    })}
  </>
);
