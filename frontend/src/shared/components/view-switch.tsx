// 表示形式の切り替え（部品設計『表示形式の切り替え.tsx』）。形式ごとに同じ幅のボタンを 1 つの枠の中につなげて並べ、選んでいる形式を浮き出た見た目にする
import { Icon, type IconName } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

/** 表示形式 */
export type View = "board" | "cards" | "table";

const VIEW_ICON: Record<View, IconName> = { board: "board", cards: "cards", table: "table" };

export type ViewSwitchProps = {
  views: { key: View; label: string }[];
  current: View;
  onChange: (key: View) => void;
};

export const ViewSwitch = ({ views, current, onChange }: ViewSwitchProps) => (
  <div role="group" aria-label="表示形式" className="inline-flex rounded-control border border-border bg-muted p-0.5">
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
          "inline-flex h-6 w-24 cursor-pointer items-center justify-center gap-1 rounded-sm text-small text-muted-foreground hover:bg-card hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring",
          key === current && "bg-tab-selected font-medium text-foreground shadow-sm ring-1 ring-mark/50 hover:bg-tab-selected",
        )}
      >
        <Icon name={VIEW_ICON[key]} />
        {label}
      </button>
    ))}
  </div>
);
