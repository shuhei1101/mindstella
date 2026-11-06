// 消した項目の帯（部品設計『消した項目の帯.tsx』）。消した項目は中身が残らないため、押せる要素にしない
import { DiffMark } from "@/shared/components/diff-mark";

export type RemovedBandProps = { items: { id: string; title: string }[] };

export const RemovedBand = ({ items }: RemovedBandProps) =>
  items.length === 0 ? null : (
    <section aria-label="この時点で消した項目" className="rounded-control border border-border-soft bg-muted p-2">
      <h2 className="flex items-center gap-1 text-h2 font-medium">
        消した項目
        <span className="font-mono text-xs text-muted-foreground">{items.length}</span>
      </h2>
      <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
        {items.map((item) => (
          <li key={item.id} data-removed-id={item.id} className="flex items-center gap-1 text-small">
            <DiffMark kind="removed" />
            <span className="font-mono text-xs">{item.id}</span>
            <span className="line-through">{item.title}</span>
          </li>
        ))}
      </ul>
    </section>
  );
