// 調査・用語集・メモ・会話ログの画面（画面設計『記録の表.tsx』）。種類ごとの列を持つ表だけを出す
import { commonColumns, IdLinks, rowTexts } from "@/shared/components/list-columns";
import { ListScreen } from "@/shared/components/list-screen";
import type { TableColumn } from "@/shared/components/table";
import { TagList } from "@/shared/components/tag-list";
import { titleOf, type RecordIndex } from "@/shared/core/records";

/** 表だけを持つ画面の種類 */
export type RecordKind = "research" | "terms" | "notes" | "logs";

const recordColumns = (kind: RecordKind) => (index: RecordIndex, onOpen: (id: string) => void): TableColumn[] => {
  const common = commonColumns(index.data.settings);
  const related = (label: string): TableColumn => ({ key: "related", label, get: (row) => rowTexts(row, "related"), cell: (row) => <IdLinks ids={rowTexts(row, "related")} titleOf={(id) => titleOf(index, id)} onOpen={onOpen} /> });
  const list = (key: string, label: string): TableColumn => ({ key, label, get: (row) => rowTexts(row, key), cell: (row) => <TagList values={rowTexts(row, key)} /> });
  const columnsOf: Record<RecordKind, TableColumn[]> = {
    research: [common.id, common.title(), common.text("question", "問い"), common.text("conclusion", "結論"), common.text("confidence", "確度", { filterable: true, order: ["高", "中", "低"] }), common.tags],
    terms: [common.id, common.title("用語"), common.text("meaning", "意味"), list("aliases", "別名"), list("avoid", "使わない表記"), common.tags],
    notes: [common.id, common.title(), common.text("content", "内容"), common.tags, related("関連")],
    logs: [common.id, common.text("date", "日付"), common.title(), common.tags, related("更新した項目")],
  };
  return columnsOf[kind];
};

export type RecordsScreenProps = { kind: RecordKind; drawerOpen: boolean; onCloseDrawer: () => void };

export const RecordsScreen = ({ kind, drawerOpen, onCloseDrawer }: RecordsScreenProps) => <ListScreen kind={kind} views={null} columnsOf={recordColumns(kind)} drawerOpen={drawerOpen} onCloseDrawer={onCloseDrawer} />;
