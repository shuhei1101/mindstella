// 要見直し・保留・進行中のタスクに共通の、件数と名前と「すべて表示」のタイル
import { Icon, type IconName, StatusMark } from "@/shared/components/icon";
import type { Item } from "@/shared/api/generated/model";

/** タイルに出す件数 */
const LIST_LIMIT = 3;

export type ListTileProps = {
  /** タイルの項目 ID（画面設計） */
  tileId: string;
  /** 見出しの要素の id */
  headingId: string;
  icon: IconName;
  title: string;
  items: Item[];
  /** 0 件のときに出す文 */
  emptyText: string;
  /** 「すべて表示」を押したとき。渡さないと出さない（その種類の画面を表示しないとき） */
  onShowAll?: (() => void) | undefined;
  onOpen: (id: string) => void;
};

export const ListTile = ({ tileId, headingId, icon, title, items, emptyText, onShowAll, onOpen }: ListTileProps) => (
  <section id={tileId} aria-labelledby={headingId} className="min-w-0 rounded-control bg-card px-6.5 py-6 max-md:p-5 dark:border dark:border-border-soft">
    <TileHead id={headingId} icon={icon} title={title} count={items.length > 0 ? items.length : null} onShowAll={onShowAll} />
    <p className="mono mt-1.5 mb-2.5 text-num leading-tight font-bold tracking-tight">{items.length}</p>
    {items.length === 0 ? (
      <p className="my-1.5 text-subtle-foreground">{emptyText}</p>
    ) : (
      <ul className="m-0 grid list-none gap-1.5 p-0">
        {items.slice(0, LIST_LIMIT).map((item) => (
          <li key={item.id} className="grid gap-0.5">
            <button
              type="button"
              data-id={item.id}
              onClick={() => {
                onOpen(item.id);
              }}
              className="group flex cursor-pointer items-center gap-2 border-0 bg-transparent p-0 text-left font-semibold hover:text-mark"
            >
              <StatusMark status={item.status} />
              <span>{item.title}</span>
              <span aria-hidden="true" className="text-subtle-foreground">
                <Icon name="chev" />
              </span>
            </button>
          </li>
        ))}
      </ul>
    )}
  </section>
);

/** タイルの見出し（アイコンと名前）と、右端の「すべて表示（N 件）」 */
export const TileHead = ({
  id,
  icon,
  title,
  count,
  onShowAll,
}: {
  id: string;
  icon: IconName;
  title: string;
  /** 「すべて表示」に添える件数。null なら「すべて表示」を出さない */
  count: number | null;
  onShowAll?: (() => void) | undefined;
}) => (
  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
    <h2 id={id} className="m-0 flex items-center gap-2 text-h2 font-semibold whitespace-nowrap text-muted-foreground">
      <Icon name={icon} />
      {title}
    </h2>
    {count === null || onShowAll === undefined ? null : (
      <button
        type="button"
        onClick={onShowAll}
        className="cursor-pointer border-0 bg-transparent p-0 text-small font-semibold whitespace-nowrap text-mark hover:underline hover:underline-offset-3"
      >
        すべて表示（{count} 件）
      </button>
    )}
  </div>
);
