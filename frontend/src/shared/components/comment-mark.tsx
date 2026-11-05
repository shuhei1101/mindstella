// コメントの印（部品設計『コメントの印.tsx』）。数字は画面にだけ見せ、読み上げは実数の「コメント {件数} 件」を持つ
import { Icon } from "@/shared/components/icon";

const COMMENT_MARK_SHOWN_MAX = 99;

export type CommentMarkProps = { count: number };

export const CommentMark = ({ count }: CommentMarkProps) => {
  const spoken = `コメント ${String(count)} 件`;
  return (
    <span title={spoken} className="inline-flex items-center gap-0.5 rounded-full bg-mark-weak px-1 text-xs">
      <Icon name="bubble" className="size-3" />
      <span aria-hidden="true">{count > COMMENT_MARK_SHOWN_MAX ? `${String(COMMENT_MARK_SHOWN_MAX)}+` : String(count)}</span>
      <span className="sr-only">{spoken}</span>
    </span>
  );
};
