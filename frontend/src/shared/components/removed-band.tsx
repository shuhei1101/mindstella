// 削除した項目の帯（部品設計『削除した項目の帯.tsx』）。削除した項目は中身が残らないため、押せる要素にしない
import { DiffMark } from "@/shared/components/diff-mark";
import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId } from "@/shared/core/record-ids";

export type RemovedBandProps = {
  items: { id: string; title: string }[];
  /** 削除したときのタイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  /** タイトルの中の ID のリンクを押したとき */
  onOpen?: (id: string) => void;
};

export const RemovedBand = ({ items, lookup, onOpen }: RemovedBandProps) =>
  items.length === 0 ? null : (
    <section aria-label="この時点で削除した項目" className="rounded-control border border-border-soft bg-muted p-2">
      <h2 className="flex items-center gap-1 text-h2 font-medium">
        削除した項目
        <span className="font-mono text-xs text-muted-foreground">{items.length}</span>
      </h2>
      <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
        {items.map((item) => (
          <li key={item.id} data-removed-id={item.id} className="flex items-center gap-1 text-small">
            <DiffMark kind="removed" />
            <span className="font-mono text-xs">{item.id}</span>
            <span className="line-through">
              <RecordText text={item.title} mode="link" lookup={lookup} {...(onOpen === undefined ? {} : { onOpen })} />
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
