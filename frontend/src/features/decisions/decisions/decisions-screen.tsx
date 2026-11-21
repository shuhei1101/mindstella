// 検討事項の画面（画面設計『検討事項.tsx』）。ボード（既定）・表で見る
import { useState } from "react";

import { addedCards, Board, boardColumns, ItemCard } from "@/shared/components/board";
import { BulkDecideBar } from "@/shared/components/bulk-decide-bar";
import { commonColumns, IdLinks } from "@/shared/components/list-columns";
import { ListScreen, type PresetPlacement } from "@/shared/components/list-screen";
import type { TableColumn } from "@/shared/components/table";
import { DECIDED_BY_LABEL, DECISION_STATUSES, type Item, type RecordIndex, recommendedKeyOf, refsOf, titleOf } from "@/shared/core/records";
import { useBulkDecide } from "@/shared/hooks/use-bulk-decide";

const VIEWS = [
  { key: "board", label: "ボード" },
  { key: "table", label: "表" },
] as const;

const decisionColumns = (index: RecordIndex, onOpen: (id: string) => void): TableColumn[] => {
  const common = commonColumns();
  return [
    common.id,
    common.title(),
    common.status(DECISION_STATUSES),
    common.text("weight", "影響度", { filterable: true, order: ["大", "中", "小"] }),
    { key: "ready", label: "着手可否", filterable: true, order: ["着手可能", "前提待ち", "なし"], get: (row) => (row["status"] !== "未決定" ? "なし" : index.readyIds.has(row.id) ? "着手可能" : "前提待ち") },
    { key: "depends_on", label: "前提", get: (row) => refsOf(row as unknown as Item, "depends_on"), cell: (row) => <IdLinks ids={refsOf(row as unknown as Item, "depends_on")} titleOf={(id) => titleOf(index, id)} onOpen={onOpen} /> },
    { key: "decided_by", label: "誰が決めたか", filterable: true, order: [DECIDED_BY_LABEL.user, DECIDED_BY_LABEL.ai], get: (row) => decidedByLabelOf(row as unknown as Item) },
    common.tags,
  ];
};

/** 誰が決めたかの表示の文言。持たなければ空 */
const decidedByLabelOf = (item: Item): string => (item.decided_by === undefined ? "" : DECIDED_BY_LABEL[item.decided_by]);

/** 推奨の案でまとめて決められる検討事項か */
const isDecidable = (item: Item): boolean => item.status === "未決定" && recommendedKeyOf(item) !== null;

export type DecisionsScreenProps = { drawerOpen: boolean; onCloseDrawer: () => void; presetPlacement?: PresetPlacement };

export const DecisionsScreen = ({ drawerOpen, onCloseDrawer, presetPlacement }: DecisionsScreenProps) => {
  const [picked, setPicked] = useState<string[]>([]);
  const bulk = useBulkDecide();
  const toggle = (id: string, checked: boolean): void => {
    setPicked((current) => (checked ? [...current, id] : current.filter((one) => one !== id)));
  };
  return (
    <ListScreen
      presetPlacement={presetPlacement}
      kind="decisions"
      views={[...VIEWS]}
      columnsOf={decisionColumns}
      drawerOpen={drawerOpen}
      onCloseDrawer={onCloseDrawer}
      content={({ index, shown, filters, marks, comments, edit, onOpen, onOpenAdded, selectedId, onSelectTag, scrollRef }) => (
        <>
          <BulkDecideBar
            count={picked.length}
            pending={bulk.pending}
            failures={bulk.failures}
            onDecide={() => {
              bulk.decide({ ids: picked, onDecided: () => { setPicked([]); } });
            }}
            onClear={() => { setPicked([]); }}
          />
          <Board
            scrollRef={scrollRef}
            columns={boardColumns({ items: shown, statuses: DECISION_STATUSES, statusFilter: filters["status"] ?? [] })}
            emptyText="検討事項はありません。"
            added={addedCards(edit, DECISION_STATUSES, onOpenAdded)}
            card={(item) => (
              <ItemCard
                key={item.id}
                index={index}
                item={item}
                meta={[decidedByLabelOf(item)]}
                links={refsOf(item, "depends_on")}
                selected={item.id === selectedId}
                marks={marks}
                comments={comments}
                edit={edit}
                onOpen={onOpen}
                onSelectTag={onSelectTag}
                pick={
                  item.status === "未決定" || picked.includes(item.id)
                    ? {
                        checked: picked.includes(item.id),
                        disabled: bulk.pending || (!isDecidable(item) && !picked.includes(item.id)),
                        label: isDecidable(item) ? `${item.id} を選ぶ` : `${item.id} は推奨の案が無いため選べません`,
                        onChange: (checked) => { toggle(item.id, checked); },
                      }
                    : undefined
                }
              />
            )}
          />
        </>
      )}
    />
  );
};
