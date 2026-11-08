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

/** 状態の札の色（オープンは状態の色、クローズは薄い文字、レビュー中は本文の色の破線） */
const STATE_TONE = { open: "text-st-open", closed: "text-muted-foreground", pending: "border-dashed text-foreground" } as const satisfies Record<ThreadStateKind, string>;

/** 状態の札（色に加えて印と文字で区別する） */
export const ThreadState = ({ status }: { status: ThreadStateKind }) => (
  <span data-state={status} className={cn("inline-flex h-5 shrink-0 items-center gap-1 rounded-kbd border border-current px-1.5 text-xs leading-none font-medium whitespace-nowrap", STATE_TONE[status])}>
    <Icon name={STATE_LABELS[status].icon} className="size-2.75" />
    {STATE_LABELS[status].label}
  </span>
);

/** レビュー中の印 */
export const PendingMark = () => (
  <span data-part="pending" className="inline-flex shrink-0 items-center gap-0.75 rounded-kbd border border-dashed border-muted-foreground px-1.5 text-xs font-medium whitespace-nowrap text-foreground">
    <Icon name="edit" className="size-2.75" />
    レビュー中
  </span>
);

/** 未読の札 */
export const UnseenMark = () => (
  <span data-part="unread" className="inline-flex h-4.5 shrink-0 items-center gap-1 rounded-kbd bg-primary px-1.5 text-xs leading-none font-semibold whitespace-nowrap text-primary-foreground">
    <span aria-hidden="true" data-part="dot" className="size-1.5 rounded-full bg-current" />
    未読
  </span>
);
