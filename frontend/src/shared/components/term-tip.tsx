// 本文の印のツールチップ（部品設計『本文の印のツールチップ.tsx』）
import { useCallback } from "react";

import { DomHost } from "@/shared/components/dom-host";
import { termTip, type TermTipProps } from "@/shared/core/term-tips";

export const TermTip = ({ entries, anchor, pinned = false, on }: TermTipProps) => {
  const create = useCallback(() => {
    const tip = termTip({ entries, anchor, pinned, on });
    queueMicrotask(() => { tip.showPopover(); });
    return { node: tip };
  }, [entries, anchor, pinned, on]);
  return <DomHost create={create} />;
};
