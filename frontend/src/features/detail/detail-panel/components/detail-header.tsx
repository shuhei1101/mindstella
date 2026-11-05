// 詳細の見出し（種類と ID・戻る・進む・編集・エクスポート・全画面・閉じる）
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { DocExportMenu } from "@/shared/components/doc-export-menu";
import { Icon } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { Button } from "@/shared/components/ui/button";
import type { PendingMarkKind } from "@/shared/core/edits";
import { bodyFormatOf, KIND_LABEL, type Item, type Kind, type RecordIndex } from "@/shared/core/records";

export type DetailHeaderProps = {
  item: Item;
  kind: Kind;
  index: RecordIndex;
  full: boolean;
  editable: boolean;
  editing: boolean;
  pending: PendingMarkKind | null;
  onToggleEdit: () => void;
  onToggleFull: () => void;
  onClose: () => void;
};

export const DetailHeader = ({ item, kind, index, full, editable, editing, pending, onToggleEdit, onToggleFull, onClose }: DetailHeaderProps) => {
  const format = bodyFormatOf(item.body);
  const source = kind === "docs" && format === "md" && !editing ? index.data.bodies[item.body ?? ""] : undefined;
  const editLabel = editing ? "編集を終える" : "編集する";
  const fullLabel = full ? "元の大きさに戻す" : "全画面表示";
  return (
    <div className="flex items-center gap-1 border-b border-border-soft p-2">
      <span className="text-xs text-muted-foreground">
        <span className="max-sm:hidden">{KIND_LABEL[kind]} </span>
        <span className="font-mono">{item.id}</span>
      </span>
      {kind === "docs" && format !== null ? <BodyFormatBadge format={format} /> : null}
      {pending === null ? null : <PendingMark kind={pending} compact />}
      <span aria-hidden="true" title={item.title} className="min-w-0 flex-1 truncate text-small">
        {item.title}
      </span>
      {editable ? (
        <Button variant="outline" aria-pressed={editing} title={editLabel} onClick={onToggleEdit}>
          <Icon name="edit" />
          <span>{editLabel}</span>
        </Button>
      ) : null}
      {source === undefined ? null : <DocExportMenu item={item} source={source} index={index} />}
      <Button variant="ghost" size="icon" aria-label="前の項目へ戻る" title="前の項目へ戻る" onClick={() => { window.history.back(); }}>
        ←
      </Button>
      <Button variant="ghost" size="icon" aria-label="次の項目へ進む" title="次の項目へ進む" onClick={() => { window.history.forward(); }}>
        →
      </Button>
      <Button variant="ghost" size="icon" aria-label={fullLabel} title={fullLabel} onClick={onToggleFull}>
        <Icon name={full ? "shrink" : "expand"} />
      </Button>
      {full ? null : (
        <Button variant="ghost" size="icon" aria-label="詳細を閉じる" onClick={onClose}>
          <Icon name="x" />
        </Button>
      )}
    </div>
  );
};
