// スレッドの状態の札・レビュー中の印・未読の札（スレッドの行・スレッド・レビュー中の書き込みの画面が使う）
import { Icon, type IconName } from "@/shared/components/icon";
import type { Thread } from "@/shared/core/comments";
import { cn } from "@/shared/lib/cn";

/** 書き手の呼び名 */
export const AUTHOR_LABELS = { user: "あなた", ai: "AI" } as const;

/** 状態の札の種類（レビュー中は、まだ送っていない新しいスレッド） */
export type ThreadStateKind = Thread["status"] | "pending";

/** 状態の札の印と文言 */
export const STATE_LABELS = {
  open: { icon: "changed", label: "オープン" },
  closed: { icon: "check", label: "クローズ" },
  pending: { icon: "edit", label: "レビュー中" },
} as const satisfies Record<ThreadStateKind, { icon: IconName; label: string }>;

/** 状態の札（色に加えて印と文字で区別する） */
export const ThreadState = ({ status }: { status: ThreadStateKind }) => (
  <span data-state={status} className={cn("inline-flex items-center gap-1 rounded-control border px-1.5 text-small", status === "pending" ? "border-dashed border-border" : "border-border")}>
    <Icon name={STATE_LABELS[status].icon} />
    {STATE_LABELS[status].label}
  </span>
);

/** レビュー中の印 */
export const PendingMark = () => (
  <span className="inline-flex items-center gap-1 rounded-control border border-dashed border-border px-1.5 text-small">
    <Icon name="edit" />
    レビュー中
  </span>
);

/** 未読の札 */
export const UnseenMark = () => (
  <span className="inline-flex items-center gap-1 rounded-control bg-primary px-1.5 text-small text-primary-foreground">
    <span aria-hidden="true" className="size-1.5 rounded-full bg-primary-foreground" />
    未読
  </span>
);
