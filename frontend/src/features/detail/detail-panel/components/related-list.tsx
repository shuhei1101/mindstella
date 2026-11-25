// 関係する項目の節
import { StatusMark } from "@/shared/components/icon";
import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { titleOf, type RecordIndex } from "@/shared/core/records";

export type RelatedListProps = {
  label: string;
  ids: readonly string[];
  index: RecordIndex;
  /** 関係する項目のタイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  /** ID のボタンと、タイトルの中の ID のリンクを押したとき */
  onOpen: (id: string) => void;
};

export const RelatedList = ({ label, ids, index, lookup, onOpen }: RelatedListProps) =>
  ids.length === 0 ? null : (
    <section className="flex flex-col gap-1">
      <h3 className="m-0 text-h2 font-semibold">{label}</h3>
      <ul className="flex flex-col gap-1">
        {ids.map((id) => {
          const status = index.byId.get(id)?.item.status;
          return (
            <li key={id} className="flex items-center gap-2 text-small">
              <button type="button" data-id={id} className="cursor-pointer font-mono text-xs underline-offset-2 hover:underline" onClick={() => { onOpen(id); }}>
                {id}
              </button>
              <span className="min-w-0 flex-1 truncate">
                <RecordText text={titleOf(index, id)} mode="link" lookup={lookup} onOpen={onOpen} />
              </span>
              {status === undefined ? null : (
                <span className="inline-flex items-center gap-1 text-xs whitespace-nowrap">
                  <StatusMark status={status} />
                  {status}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
