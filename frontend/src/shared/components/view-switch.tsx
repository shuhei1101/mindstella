// 表示形式の切り替え（部品設計『表示形式の切り替え.tsx』）。形式ごとに同じ幅のボタンを並べ、選んでいる形式を押された見た目にする
import { Icon, type IconName } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

/** 表示形式 */
export type View = "map" | "board" | "cards" | "table";

const VIEW_ICON: Record<View, IconName> = { map: "map", board: "board", cards: "cards", table: "table" };

export type ViewSwitchProps = {
  views: { key: View; label: string }[];
  current: View;
  onChange: (key: View) => void;
};

export const ViewSwitch = ({ views, current, onChange }: ViewSwitchProps) => (
  <div role="group" aria-label="表示形式" className="inline-flex rounded-control border border-border bg-card p-0.5">
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
          "inline-flex h-7 w-24 cursor-pointer items-center justify-center gap-1 rounded-control text-small hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring",
          key === current && "bg-mark-weak font-medium text-foreground hover:bg-mark-weak",
        )}
      >
        <Icon name={VIEW_ICON[key]} />
        {label}
      </button>
    ))}
  </div>
);
