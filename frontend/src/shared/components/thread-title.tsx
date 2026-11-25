// スレッドの見出しのタイトル。書き込みの並びが一番上のときは全文、スクロールした後は 1 行にして末尾を「…」にする
import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { cn } from "@/shared/lib/cn";

export type ThreadTitleProps = {
  title: string;
  /** 書き込みの並びをスクロールした後か（1 行に省略する） */
  collapsed: boolean;
  /** タイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  /** タイトルの中の ID のリンクを押したとき */
  onOpen?: (id: string) => void;
};

export const ThreadTitle = ({ title, collapsed, lookup, onOpen }: ThreadTitleProps) => (
  <span data-part="thread-title" data-collapsed={collapsed ? "" : undefined} title={collapsed ? title : undefined} className={cn("min-w-0 flex-1 wrap-anywhere", collapsed && "truncate")}>
    <RecordText text={title} mode="link" lookup={lookup} {...(onOpen === undefined ? {} : { onOpen })} />
  </span>
);
