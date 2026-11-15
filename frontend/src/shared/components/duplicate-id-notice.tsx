// 重なった ID の通知（部品設計『重なった ID の通知.tsx』）。トップバーの下の帯に、同じ ID の項目が 2 件になったことと、その ID のリンク・閉じるボタンを出す。自動では閉じない
import { Fragment } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";

export type DuplicateIdNoticeProps = {
  /** 重なった ID と、その項目の種類の名前。空なら何も出さない */
  ids: { id: string; kind: string }[];
  onOpen?: (id: string) => void;
  onClose?: () => void;
};

export const DuplicateIdNotice = ({ ids, onOpen, onClose }: DuplicateIdNoticeProps) => {
  if (ids.length === 0) return null;
  return (
    <div role="alert" className="flex items-start gap-2.5 border-b border-border bg-card py-2.5 pr-1 pl-5 text-small text-foreground max-sm:pl-2.5">
      <Icon name="alert" className="mt-0.5 flex-none text-st-review" />
      <div className="min-w-0 flex-1 wrap-anywhere">
        <strong className="mb-0.5 block">同じ ID の項目が 2 件あります</strong>
        ほかのセッションの書き込みで、
        {ids.map(({ id, kind }, index) => (
          <Fragment key={id}>
            {index > 0 ? "、" : null}
            {kind}{" "}
            <a
              href={`#id=${encodeURIComponent(id)}`}
              className="font-mono whitespace-nowrap text-mark underline"
              onClick={(event) => {
                event.preventDefault();
                onOpen?.(id);
              }}
            >
              {id}
            </a>
          </Fragment>
        ))}
        {" "}が重なりました。片方の ID を変更してください。
      </div>
      <Button variant="ghost" size="icon" className="flex-none" aria-label="通知を閉じる" title="通知を閉じる" onClick={onClose}>
        <Icon name="x" />
      </Button>
    </div>
  );
};
