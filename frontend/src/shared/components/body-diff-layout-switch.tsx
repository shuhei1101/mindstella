// 本文の差分の並べ方の切り替え（部品設計『本文の差分の並べ方の切り替え.tsx』）
import { cn } from "@/shared/lib/cn";

/** 本文の差分の並べ方 */
export type BodyLayout = "inline" | "side";

const BODY_LAYOUT_BUTTON: Record<BodyLayout, string> = { inline: "インライン", side: "左右に並べる" };

export type BodyDiffLayoutSwitchProps = { layout: BodyLayout; onChange: (layout: BodyLayout) => void };

export const BodyDiffLayoutSwitch = ({ layout, onChange }: BodyDiffLayoutSwitchProps) => (
  <div role="group" aria-label="本文の差分の並べ方" className="inline-flex rounded-control border border-border bg-card p-0.5">
    {(["inline", "side"] as const).map((value) => (
      <button
        key={value}
        type="button"
        data-layout={value}
        aria-pressed={layout === value}
        onClick={() => {
          if (layout !== value) onChange(value);
        }}
        className={cn("h-7 cursor-pointer rounded-control px-2 text-small hover:bg-accent", layout === value && "bg-mark-weak font-medium hover:bg-mark-weak")}
      >
        {BODY_LAYOUT_BUTTON[value]}
      </button>
    ))}
  </div>
);
