// カード・ボードの並べ替え。並べる項目を選ぶボタンの組で、同じ項目をもう一度押すと向きが逆になる
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";

export type CardSortKey = "default" | "created" | "updated";

export type CardSortDir = "asc" | "desc";

export type CardSortValue = { key: CardSortKey; dir: CardSortDir };

/** 画面を開いた直後の並べ替え。資料は更新日時の新しい順、ほかの種類は連番 */
export const INITIAL_CARD_SORT = {
  docs: { key: "updated", dir: "desc" },
  other: { key: "default", dir: "asc" },
} as const satisfies Record<string, CardSortValue>;

const OPTIONS = [
  { key: "default", label: "連番" },
  { key: "created", label: "作成日時" },
  { key: "updated", label: "更新日時" },
] as const satisfies readonly { key: CardSortKey; label: string }[];

/** 初めて選んだ日時の項目は新しい順、選んでいる項目をもう一度選ぶと向きを逆にする */
export const nextCardSort = (current: CardSortValue, key: CardSortKey): CardSortValue => {
  if (key === "default") return { key, dir: "asc" };
  if (current.key !== key) return { key, dir: "desc" };
  return { key, dir: current.dir === "desc" ? "asc" : "desc" };
};

export type CardSortProps = { value: CardSortValue; onChange: (value: CardSortValue) => void };

export const CardSort = ({ value, onChange }: CardSortProps) => (
  <div role="group" aria-label="並べ替え" className="flex flex-none items-center gap-1 text-small">
    <span className="text-xs text-muted-foreground">並べ替え</span>
    {OPTIONS.map((option) => {
      const selected = value.key === option.key;
      const dirLabel = value.dir === "desc" ? "新しい順" : "古い順";
      return (
        <Button key={option.key} variant={selected ? "secondary" : "ghost"} aria-pressed={selected} title={selected && option.key !== "default" ? `${option.label}（${dirLabel}）` : option.label} onClick={() => { onChange(nextCardSort(value, option.key)); }}>
          {option.label}
          {selected && option.key !== "default" ? <Icon name="arrow" className={value.dir === "desc" ? "rotate-90" : "-rotate-90"} /> : null}
        </Button>
      );
    })}
  </div>
);
