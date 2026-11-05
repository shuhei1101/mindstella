// 関係する項目の節
import { StatusMark } from "@/shared/components/icon";
import { titleOf, type RecordIndex } from "@/shared/core/records";

export type RelatedListProps = { label: string; ids: readonly string[]; index: RecordIndex; onOpen: (id: string) => void };

export const RelatedList = ({ label, ids, index, onOpen }: RelatedListProps) =>
  ids.length === 0 ? null : (
    <section className="flex flex-col gap-1">
      <h3 className="text-small font-semibold">{label}</h3>
      <ul className="flex flex-col gap-1">
        {ids.map((id) => {
          const status = index.byId.get(id)?.item.status;
          return (
            <li key={id} className="flex items-center gap-2 text-small">
              <button type="button" data-id={id} className="cursor-pointer font-mono text-xs underline-offset-2 hover:underline" onClick={() => { onOpen(id); }}>
                {id}
              </button>
              <span className="min-w-0 flex-1 truncate">{titleOf(index, id)}</span>
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
