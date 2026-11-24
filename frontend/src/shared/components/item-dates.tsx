// カードに並べる、項目の作成日時と更新日時（JST。今年は MM/DD HH:mm、今年でない日時は YYYY/MM/DD HH:mm）
import { formatItemDateTime } from "@/shared/core/format";

export type ItemDatesProps = { created: string; updated: string };

export const ItemDates = ({ created, updated }: ItemDatesProps) =>
  formatItemDateTime(created) === "" && formatItemDateTime(updated) === "" ? null : (
  <span data-part="item-dates" className="flex flex-wrap items-center gap-x-2 text-xs whitespace-nowrap text-muted-foreground">
    <span>
      作成 <time dateTime={created}>{formatItemDateTime(created)}</time>
    </span>
    <span>
      更新 <time dateTime={updated}>{formatItemDateTime(updated)}</time>
    </span>
  </span>
);
