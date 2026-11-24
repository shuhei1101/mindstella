// 表示形式の切り替え（部品設計『表示形式の切り替え.tsx』）。形式ごとに同じ幅のボタンを 1 つの枠の中につなげて並べ、選んでいる形式を浮き出た見た目にする
import { Icon, type IconName } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";
import { SEGMENTED_GROUP_CLASS, SEGMENTED_ITEM_CLASS, SEGMENTED_SELECTED_CLASS } from "@/shared/lib/segmented";

/** 表示形式 */
export type View = "board" | "cards" | "table";

const VIEW_ICON: Record<View, IconName> = { board: "board", cards: "cards", table: "table" };

export type ViewSwitchProps = {
  views: { key: View; label: string }[];
  current: View;
  onChange: (key: View) => void;
};

export const ViewSwitch = ({ views, current, onChange }: ViewSwitchProps) => (
  <div role="group" aria-label="表示形式" className={SEGMENTED_GROUP_CLASS}>
    {views.map(({ key, label }) => (
      <button
        key={key}
        type="button"
        data-view={key}
        aria-pressed={key === current}
        onClick={() => {
          if (key !== current) onChange(key);
        }}
        className={cn(
          SEGMENTED_ITEM_CLASS,
          "inline-flex h-6 w-24 items-center justify-center gap-1",
          key === current && SEGMENTED_SELECTED_CLASS,
        )}
      >
        <Icon name={VIEW_ICON[key]} />
        {label}
      </button>
    ))}
  </div>
);
