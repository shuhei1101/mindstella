// 絞り込みの条件のチップ。× で 1 つ解除し、末尾の「すべて解除」で全ての条件を外す
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { TEXT_FILTER_PREFIX, withoutKey, type Filters } from "@/shared/core/filters";

export type FilterChipsProps = { filters: Filters; labels: Record<string, string>; onFilter: (filters: Filters) => void };

const Chip = ({ text, onClear }: { text: string; onClear: () => void }) => (
  <span className="inline-flex items-center gap-1 rounded-full bg-mark-weak px-2 text-xs">
    {text}
    <button type="button" aria-label={`${text} の条件を解除`} className="cursor-pointer" onClick={onClear}>
      <Icon name="x" className="size-3" />
    </button>
  </span>
);

export const FilterChips = ({ filters, labels, onFilter }: FilterChipsProps) => {
  const chips = Object.entries(filters).flatMap(([key, values]) => {
    if (key.startsWith(TEXT_FILTER_PREFIX)) {
      const name = labels[key.slice(TEXT_FILTER_PREFIX.length)] ?? key.slice(TEXT_FILTER_PREFIX.length);
      const joint = /[A-Za-z0-9]$/.test(name) ? " " : "";
      return values.map((value) => ({ id: `${key}:${value}`, text: `${name}${joint}に「${value}」を含む`, next: withoutKey(filters, key) }));
    }
    return values.map((value) => {
      const rest = values.filter((candidate) => candidate !== value);
      return { id: `${key}:${value}`, text: `${labels[key] ?? key}: ${value}`, next: rest.length === 0 ? withoutKey(filters, key) : { ...filters, [key]: rest } };
    });
  });
  return (
    <div className="flex flex-wrap items-center gap-1">
      {chips.map((chip) => (
        <Chip key={chip.id} text={chip.text} onClear={() => { onFilter(chip.next); }} />
      ))}
      {chips.length > 0 ? (
        <Button variant="ghost" onClick={() => { onFilter({}); }}>
          すべて解除
        </Button>
      ) : null}
    </div>
  );
};
