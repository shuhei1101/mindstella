// 資料の画面（画面設計『資料.tsx』）。カード（既定）・ボード・表で見る。連番の順に並べる
import { DocCard, orderDocs } from "@/features/docs/docs/components/doc-cards";
import { AddedCard, addedCards, Board, boardColumns } from "@/shared/components/board";
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { commonColumns } from "@/shared/components/list-columns";
import { ListScreen } from "@/shared/components/list-screen";
import type { TableColumn } from "@/shared/components/table";
import { bodyFormatOf, DOC_STATUSES } from "@/shared/core/records";

const VIEWS = [
  { key: "cards", label: "カード" },
  { key: "board", label: "ボード" },
  { key: "table", label: "表" },
] as const;

const NO_VALUE_MARK = "—";

const docColumns = (): TableColumn[] => {
  const common = commonColumns();
  const formatOf = (body: unknown) => bodyFormatOf(typeof body === "string" ? body : undefined);
  return [
    common.id,
    common.title(),
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
    content={({ view, shown, filters, marks, comments, edit, onOpen, onOpenAdded, selectedId, onSelectTag, scrollRef }) => {
      if (view === "board") {
        return (
          <Board
            scrollRef={scrollRef}
            columns={boardColumns({ items: shown, statuses: DOC_STATUSES, statusFilter: filters["status"] ?? [] }).map((column) => ({ ...column, items: orderDocs(column.items) }))}
            emptyText="資料はありません。"
            added={addedCards(edit, DOC_STATUSES, onOpenAdded)}
            card={(item) => <DocCard key={item.id} doc={item} inBoard selected={item.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} onSelectTag={onSelectTag} />}
          />
        );
      }
      const adds = edit?.adds ?? [];
      return shown.length === 0 && adds.length === 0 ? (
        <p className="text-small text-muted-foreground">該当する資料はありません。別の条件を試してください。</p>
      ) : (
        // カードの列の数は、詳細パネルで狭くなる領域の幅で切り替える
        <div className="@container flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="grid grid-cols-3 gap-3 overflow-auto @max-7xl:grid-cols-2 @max-3xl:grid-cols-1">
          {adds.map((item) => (
            <AddedCard key={item.id} item={item} mark={edit?.marks[item.id] ?? "pending"} onOpen={onOpenAdded} />
          ))}
          {orderDocs(shown).map((doc) => (
            <DocCard key={doc.id} doc={doc} inBoard={false} selected={doc.id === selectedId} marks={marks} comments={comments} edit={edit} onOpen={onOpen} onSelectTag={onSelectTag} />
          ))}
        </div>
        </div>
      );
    }}
  />
);
