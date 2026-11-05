// 検討事項の画面（画面設計『検討事項.tsx』）。ボード（既定）・マップ・表で見る
import { DecisionMap } from "@/features/decisions/decisions/components/decision-map";
import { addedCards, Board, boardColumns, ItemCard } from "@/shared/components/board";
import { commonColumns, IdLinks, rowTexts } from "@/shared/components/list-columns";
import { ListScreen } from "@/shared/components/list-screen";
import type { TableColumn } from "@/shared/components/table";
import { DECISION_STATUSES, titleOf, type RecordIndex } from "@/shared/core/records";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";

const VIEWS = [
  { key: "board", label: "ボード" },
  { key: "map", label: "マップ" },
  { key: "table", label: "表" },
] as const;

const decisionColumns = (index: RecordIndex, onOpen: (id: string) => void): TableColumn[] => {
  const common = commonColumns(index.data.settings);
  return [
    common.id,
    common.title(),
    common.status(DECISION_STATUSES),
    common.target,
    common.category,
    common.phase,
    common.text("weight", "影響度", { filterable: true, order: ["大", "中", "小"] }),
    { key: "ready", label: "着手可否", filterable: true, order: ["着手可能", "前提待ち", "なし"], get: (row) => (row["status"] !== "未決定" ? "なし" : index.readyIds.has(row.id) ? "着手可能" : "前提待ち") },
    { key: "depends_on", label: "前提", get: (row) => rowTexts(row, "depends_on"), cell: (row) => <IdLinks ids={rowTexts(row, "depends_on")} titleOf={(id) => titleOf(index, id)} onOpen={onOpen} /> },
    common.tags,
  ];
};

export type DecisionsScreenProps = { drawerOpen: boolean; onCloseDrawer: () => void };

export const DecisionsScreen = ({ drawerOpen, onCloseDrawer }: DecisionsScreenProps) => {
  const { closeItem } = usePreviewSearch();
  return (
    <ListScreen
      kind="decisions"
      views={[...VIEWS]}
      columnsOf={decisionColumns}
      drawerOpen={drawerOpen}
      onCloseDrawer={onCloseDrawer}
      content={({ index, view, shown, filters, marks, comments, edit, onOpen, onOpenAdded, selectedId }) =>
        view === "map" ? (
          <DecisionMap items={shown} settings={index.data.settings} selectedId={selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} onClear={closeItem} />
        ) : (
          <Board
            columns={boardColumns({ items: shown, statuses: DECISION_STATUSES, statusFilter: filters["status"] ?? [] })}
            emptyText="検討事項はありません。"
            added={addedCards(edit, DECISION_STATUSES, onOpenAdded)}
            card={(item) => <ItemCard key={item.id} index={index} item={item} meta={[item.category, item.phase]} links={item.depends_on ?? []} selected={item.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} />}
          />
        )
      }
    />
  );
};
