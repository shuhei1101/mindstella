// カードに並べる、項目の作成日時と更新日時（JST の MM/DD HH:mm）
import { formatJst } from "@/shared/core/format";

export type ItemDatesProps = { created: string; updated: string };

export const ItemDates = ({ created, updated }: ItemDatesProps) => (
  <span data-part="item-dates" className="flex flex-wrap items-center gap-x-2 text-xs whitespace-nowrap text-muted-foreground">
    <span>
      作成 <time dateTime={created}>{formatJst(created)}</time>
    </span>
    <span>
      更新 <time dateTime={updated}>{formatJst(updated)}</time>
    </span>
  </span>
);
