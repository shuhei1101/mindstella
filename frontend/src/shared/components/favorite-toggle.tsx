// お気に入りの星のボタン（部品設計『お気に入りの星.tsx』）。押すと項目をお気に入りに登録・解除する。カードの右上と表の星の列に配置する
import { Icon } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

export type FavoriteToggleProps = {
  /** 押した項目のタイトル（読み上げの名前に入れる） */
  title: string;
  /** お気に入りに登録しているか */
  on: boolean;
  onToggle: () => void;
  className?: string;
};

export const FavoriteToggle = ({ title, on, onToggle, className }: FavoriteToggleProps) => (
  <button
    type="button"
    data-favorite={on ? "on" : "off"}
    aria-pressed={on}
    aria-label={`${title}をお気に入りに登録`}
    title={on ? "お気に入りを解除" : "お気に入りに登録"}
    className={cn("relative z-10 inline-flex size-6 flex-none cursor-pointer items-center justify-center rounded-control hover:bg-row-hover focus-visible:outline-2 focus-visible:outline-ring", on ? "text-mark" : "text-subtle-foreground hover:text-foreground", className)}
    onClick={(event) => {
      // カード・行を開く操作へ伝えない
      event.stopPropagation();
      onToggle();
    }}
  >
    <Icon name="star" className={cn("size-4", on && "fill-current")} />
  </button>
);
