// スレッドの見出しのタイトル。書き込みの並びが一番上のときは全文、スクロールした後は 1 行にして末尾を「…」にする
import { cn } from "@/shared/lib/cn";

export type ThreadTitleProps = {
  title: string;
  /** 書き込みの並びをスクロールした後か（1 行に省略する） */
  collapsed: boolean;
};

export const ThreadTitle = ({ title, collapsed }: ThreadTitleProps) => (
  <span data-part="thread-title" data-collapsed={collapsed ? "" : undefined} title={collapsed ? title : undefined} className={cn("min-w-0 flex-1 wrap-anywhere", collapsed && "truncate")}>
    {title}
  </span>
);
