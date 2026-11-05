// 資料の画面（画面設計『資料.tsx』）。カード（既定）・ボード・表で見る。納品物を先頭に並べる
import { DeliverableBadge, DocCard, orderDocs } from "@/features/docs/docs/components/doc-cards";
import { AddedCard, addedCards, Board, boardColumns } from "@/shared/components/board";
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { commonColumns } from "@/shared/components/list-columns";
import { ListScreen } from "@/shared/components/list-screen";
import type { TableColumn } from "@/shared/components/table";
import { bodyFormatOf, DOC_STATUSES, type RecordIndex } from "@/shared/core/records";

const VIEWS = [
  { key: "cards", label: "カード" },
  { key: "board", label: "ボード" },
  { key: "table", label: "表" },
] as const;

const NO_VALUE_MARK = "—";

const docColumns = (index: RecordIndex): TableColumn[] => {
  const common = commonColumns(index.data.settings);
  const formatOf = (body: unknown) => bodyFormatOf(typeof body === "string" ? body : undefined);
  return [
    common.id,
    common.title(),
    { key: "deliverable", label: "納品物", filterable: true, order: ["納品物", "納品物以外"], get: (row) => (row["deliverable"] === true ? "納品物" : "納品物以外"), cell: (row) => (row["deliverable"] === true ? <DeliverableBadge /> : <span className="text-muted-foreground">{NO_VALUE_MARK}</span>) },
    common.status(DOC_STATUSES),
    common.text("kind", "種類", { filterable: true }),
    {
      key: "body_format",
      label: "形式",
      filterable: true,
      order: ["MD", "HTML"],
      get: (row) => {
        const format = formatOf(row["body"]);
        return format === null ? "" : format.toUpperCase();
      },
      cell: (row) => {
        const format = formatOf(row["body"]);
        return format === null ? <span className="text-muted-foreground">{NO_VALUE_MARK}</span> : <BodyFormatBadge format={format} />;
      },
    },
    common.target,
    common.category,
    common.phase,
    common.tags,
  ];
};

export type DocsScreenProps = { drawerOpen: boolean; onCloseDrawer: () => void };

export const DocsScreen = ({ drawerOpen, onCloseDrawer }: DocsScreenProps) => (
  <ListScreen
    kind="docs"
    views={[...VIEWS]}
    columnsOf={docColumns}
    drawerOpen={drawerOpen}
    onCloseDrawer={onCloseDrawer}
    content={({ view, shown, filters, marks, comments, edit, onOpen, onOpenAdded, selectedId }) => {
      if (view === "board") {
        return (
          <Board
            columns={boardColumns({ items: shown, statuses: DOC_STATUSES, statusFilter: filters["status"] ?? [] }).map((column) => ({ ...column, items: orderDocs(column.items) }))}
            emptyText="資料はありません。"
            added={addedCards(edit, DOC_STATUSES, onOpenAdded)}
            card={(item) => <DocCard key={item.id} doc={item} inBoard selected={item.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} />}
          />
        );
      }
      const adds = edit?.adds ?? [];
      return shown.length === 0 && adds.length === 0 ? (
        <p className="text-small text-muted-foreground">該当する資料はありません。別の条件を試してください。</p>
      ) : (
        <div className="grid grid-cols-3 gap-3 overflow-auto max-xl:grid-cols-2 max-md:grid-cols-1">
          {adds.map((item) => (
            <AddedCard key={item.id} item={item} mark={edit?.marks[item.id] ?? "pending"} onOpen={onOpenAdded} />
          ))}
          {orderDocs(shown).map((doc) => (
            <DocCard key={doc.id} doc={doc} inBoard={false} selected={doc.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} />
          ))}
        </div>
      );
    }}
  />
);
