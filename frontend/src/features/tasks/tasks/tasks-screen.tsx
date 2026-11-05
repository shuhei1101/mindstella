// タスクの画面（画面設計『タスク.tsx』）。ボード（既定）と表で見る
import { Board, boardColumns, ItemCard } from "@/shared/components/board";
import { commonColumns, IdLinks, rowTexts } from "@/shared/components/list-columns";
import { ListScreen } from "@/shared/components/list-screen";
import type { TableColumn } from "@/shared/components/table";
import { TASK_STATUSES, titleOf, type RecordIndex } from "@/shared/core/records";

const VIEWS = [
  { key: "board", label: "ボード" },
  { key: "table", label: "表" },
] as const;

const taskColumns = (index: RecordIndex, onOpen: (id: string) => void): TableColumn[] => {
  const common = commonColumns(index.data.settings);
  return [
    common.id,
    common.title(),
    common.status(TASK_STATUSES),
    common.text("kind", "種類", { filterable: true }),
    { key: "for", label: "進める検討事項", get: (row) => rowTexts(row, "for"), cell: (row) => <IdLinks ids={rowTexts(row, "for")} titleOf={(id) => titleOf(index, id)} onOpen={onOpen} /> },
    common.target,
    common.category,
    common.phase,
    common.tags,
  ];
};

export type TasksScreenProps = { drawerOpen: boolean; onCloseDrawer: () => void };

export const TasksScreen = ({ drawerOpen, onCloseDrawer }: TasksScreenProps) => (
  <ListScreen
    kind="tasks"
    views={[...VIEWS]}
    columnsOf={taskColumns}
    drawerOpen={drawerOpen}
    onCloseDrawer={onCloseDrawer}
    content={({ index, shown, filters, marks, comments, edit, onOpen, selectedId }) => (
      <Board
        columns={boardColumns({ items: shown, statuses: TASK_STATUSES, statusFilter: filters["status"] ?? [] })}
        emptyText="タスクはありません。"
        card={(item) => <ItemCard key={item.id} index={index} item={item} meta={[item.kind, item.category]} links={item.for ?? []} selected={item.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} />}
      />
    )}
  />
);
