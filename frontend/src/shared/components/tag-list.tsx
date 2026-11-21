// タグの並び（部品設計『タグの並び.tsx』）。記録の順のまま並べ、主題のタグは枠と文字を 1 段濃くする
import { Icon } from "@/shared/components/icon";
import type { Tag } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

export type TagListProps = { values?: readonly (Tag | string)[]; onSelect?: (name: string) => void };

export const TagList = ({ values = [], onSelect }: TagListProps) => (
  <>
    {values.map((value) => {
      const name = typeof value === "string" ? value : value.name;
      const isMain = typeof value !== "string" && value.main === true;
      const className = cn("inline-flex items-center gap-0.5 rounded-control border px-1 text-xs", isMain ? "border-foreground font-medium text-foreground" : "border-border-soft text-muted-foreground");
      const body = (
        <>
          {isMain ? <Icon name="main" className="size-3" /> : null}
          {isMain ? <span className="sr-only">主題</span> : null}
          {name}
        </>
      );
      if (onSelect === undefined) {
        return (
          <span key={name} title={isMain ? "主題" : undefined} className={className}>
            {body}
          </span>
        );
      }
      return (
        <button
          key={name}
          type="button"
          data-tag={name}
          title={`タグ「${name}」で絞り込む`}
          aria-label={`タグ「${name}」で絞り込む${isMain ? "（主題）" : ""}`}
          className={cn(className, "cursor-pointer hover:border-foreground hover:text-foreground")}
          onClick={(event) => {
            event.stopPropagation();
            onSelect(name);
          }}
        >
          {body}
        </button>
      );
    })}
  </>
);
