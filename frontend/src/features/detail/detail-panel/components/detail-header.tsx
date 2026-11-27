// 詳細の見出し（種類と ID・確認済み・戻る・進む・編集・エクスポート・コメントの一覧・全画面・閉じる）と、確認済みを書き換えられなかった旨
import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { BodyFormatBadge } from "@/shared/components/body-format-badge";
import { BodyToc } from "@/shared/components/body-toc";
import { DocExportControl } from "@/shared/components/doc-export-menu";
import { Icon } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { SiblingNav, type SiblingNavProps } from "@/shared/components/sibling-nav";
import { Button } from "@/shared/components/ui/button";
import type { PendingMarkKind } from "@/shared/core/edits";
import type { TocEntry } from "@/shared/core/body-toc";
import { cn } from "@/shared/lib/cn";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useShortcut } from "@/shared/hooks/use-shortcut";
import { bodyFormatOf, KIND_LABEL, type Item, type Kind, type RecordIndex } from "@/shared/core/records";

export type DetailHeaderProps = {
  item: Item;
  kind: Kind;
  index: RecordIndex;
  full: boolean;
  editable: boolean;
  editing: boolean;
  /** コメントの一覧のボタンを出すか（サーバーの配信で、全画面でない詳細パネルのとき） */
  comments: boolean;
  /** コメントの一覧のボタンに出す件数。0 のときはバッジを描かない */
  commentCount?: number;
  pending: PendingMarkKind | null;
  /** 本文の先頭のタイトルがスクロール領域の上へ外れているか（外れている間だけ見出しにタイトルを出す） */
  showTitle: boolean;
  /** 見出しのタイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  /** 見出しのタイトルの中の ID のリンクを押したとき */
  onOpenRecord: (id: string) => void;
  onToggleEdit: () => void;
  onToggleFull: () => void;
  onClose: () => void;
  /** 本文の見出し。空のときは目次のボタンを描かない */
  toc?: readonly TocEntry[];
  /** 目次で押した見出し */
  onHeading?: (slug: string) => void;
  /** 元の画面の今の並び。null・渡さないとき（一覧から開いていないとき）は前後の項目へ移るボタンを描かず、キーも受けない */
  sibling?: SiblingNavProps | null;
};

/** 件数のバッジの文字の上限（超えたら `99+`） */
const COUNT_CAP = 99;

/** 項目のコメントの一覧を開くボタン。件数が 1 以上のとき、アイコンの右上に件数のバッジを重ねる */
const CommentListButton = ({ id, count, onOpen }: { id: string; count: number; onOpen: (id: string) => void }) => (
  <Button variant="ghost" size="icon" className="relative" aria-label={`${id} のコメントの一覧を開く${count > 0 ? `（${String(count)} 件）` : ""}`} title="この項目のコメントの一覧" onClick={() => { onOpen(id); }}>
    <Icon name="comment" />
    {count > 0 ? (
      <span aria-hidden="true" className="pointer-events-none absolute -top-1 -right-1 inline-grid h-4 min-w-4 place-items-center rounded-full bg-mark px-1 font-mono text-count leading-none text-on-mark">
        {count > COUNT_CAP ? `${String(COUNT_CAP)}+` : count}
      </span>
    ) : null}
  </Button>
);

/** 一覧の並びの前後へ移る `k`・`j` を受け、受けている間だけボタンに添えるキーを返す */
const useSiblingKeys = (sibling: SiblingNavProps | null): SiblingNavProps["keys"] => {
  const prevKey = useShortcut("item.prev", () => sibling?.onPrev(), sibling !== null && sibling.position > 1);
  const nextKey = useShortcut("item.next", () => sibling?.onNext(), sibling !== null && sibling.position < sibling.total);
  return prevKey.active || nextKey.active ? { prev: prevKey.keys, next: nextKey.keys } : null;
};

export const DetailHeader = ({ item, kind, index, full, editable, editing, comments, commentCount = 0, pending, showTitle, lookup, onOpenRecord, onToggleEdit, onToggleFull, onClose, toc = [], onHeading, sibling = null }: DetailHeaderProps) => {
  const { canBack, canForward, openItemComments, backItem, forwardItem } = usePreviewSearch();
  const siblingKeys = useSiblingKeys(sibling);
  const format = bodyFormatOf(item.body);
  const source = kind === "docs" && format === "md" && !editing ? index.data.bodies[item.body ?? ""] : undefined;
  const editLabel = editing ? "編集を終える" : "編集する";
  const fullLabel = full ? "元の大きさに戻す" : "全画面表示";
  return (
    <div className="border-b border-border-soft">
      <div className="flex items-center gap-1 p-2">
        <span className="shrink-0 text-xs whitespace-nowrap text-muted-foreground">
          <span className="max-sm:hidden">{KIND_LABEL[kind]} </span>
          <span className="font-mono">{item.id}</span>
        </span>
        {kind === "docs" && format !== null ? <BodyFormatBadge format={format} /> : null}
        {pending === null ? null : <PendingMark kind={pending} compact />}
        {/* 隠している間も場所は取ったままにし、種類と ID を動かさない */}
        <span inert={!showTitle} title={item.title} className={cn("min-w-0 flex-1 truncate text-small transition-opacity duration-150 motion-reduce:transition-none", !showTitle && "opacity-0")}>
          <RecordText text={item.title} mode="link" lookup={lookup} onOpen={onOpenRecord} />
        </span>
        {editable ? (
          <Button variant="outline" aria-pressed={editing} title={editLabel} onClick={onToggleEdit}>
            <Icon name="edit" />
            <span>{editLabel}</span>
          </Button>
        ) : null}
        {toc.length === 0 || onHeading === undefined ? null : <BodyToc entries={toc} onHeading={onHeading} />}
        {source === undefined ? null : <DocExportControl item={item} source={source} index={index} />}
        {full || !comments ? null : (
          <CommentListButton id={item.id} count={commentCount} onOpen={openItemComments} />
        )}
        {sibling === null ? null : <SiblingNav {...sibling} keys={siblingKeys} />}
        <Button variant="ghost" size="icon" aria-label="前の項目へ戻る" title="前の項目へ戻る" disabled={!canBack} onClick={backItem}>
          ←
        </Button>
        <Button variant="ghost" size="icon" aria-label="次の項目へ進む" title="次の項目へ進む" disabled={!canForward} onClick={forwardItem}>
          →
        </Button>
        <Button variant="ghost" size="icon" aria-label={fullLabel} title={fullLabel} className="max-md:hidden" onClick={onToggleFull}>
          <Icon name={full ? "shrink" : "expand"} />
        </Button>
        {full ? null : (
          <Button variant="ghost" size="icon" aria-label="詳細を閉じる" onClick={onClose}>
            <Icon name="x" />
          </Button>
        )}
      </div>
    </div>
  );
};
