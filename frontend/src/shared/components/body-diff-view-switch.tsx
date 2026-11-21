// 本文の差分の見せ方の切り替え（部品設計『本文の差分の見せ方の切り替え.tsx』）
import { cn } from "@/shared/lib/cn";

/** 本文の差分の見せ方（`rendered` は描いた結果、`source` は原文の差分） */
export type BodyDiffView = "rendered" | "source";

const BODY_DIFF_VIEW_BUTTON = { rendered: "描いた結果", source: "原文の差分" } as const satisfies Record<BodyDiffView, string>;

export type BodyDiffViewSwitchProps = { view: BodyDiffView; onChange: (view: BodyDiffView) => void };

/** 押している方を押したときも知らせる（mdmark の「変更表示」で閉じた行の差分を開き直す） */
export const BodyDiffViewSwitch = ({ view, onChange }: BodyDiffViewSwitchProps) => (
  <div role="group" aria-label="本文の差分の見せ方" className="inline-flex self-start rounded-control border border-border bg-card p-0.5">
    {(["rendered", "source"] as const).map((value) => (
      <button
        key={value}
        type="button"
        data-view={value}
        aria-pressed={view === value}
        onClick={() => {
          onChange(value);
        }}
        className={cn("h-7 cursor-pointer rounded-control px-2 text-small hover:bg-accent", view === value && "bg-mark-weak font-medium hover:bg-mark-weak")}
      >
        {BODY_DIFF_VIEW_BUTTON[value]}
      </button>
    ))}
  </div>
);
