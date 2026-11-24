// 本文の折りたたみ（部品設計『本文の折りたたみ.tsx』）。折り返した後の見た目の行で一定の行数までに本文を畳み、超えるときだけ開閉のボタンを出す。本文と開閉のボタンを子の関数へ別々に渡す
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Icon } from "@/shared/components/icon";
import { PostBody } from "@/shared/components/post-body";
import { Button } from "@/shared/components/ui/button";
import type { LookupTitle } from "@/shared/core/post-links";
import type { RecordIndex } from "@/shared/core/records";
import type { LookupThread, OpenThread } from "@/shared/core/thread-ids";

/** 畳んだときに出す、折り返した後の見た目の行の数 */
export const REVIEW_FOLD_LINES = 5;

/** 全文の高さが、行の高さ × 行数を超えたとみなす余裕（小数の丸め） */
const FOLD_TOLERANCE_PX = 1;

export type ReviewBodyFoldProps = {
  id: string;
  label: string;
  body: string;
  changeSets?: LookupTitle;
  open: boolean;
  lines?: number;
  titles?: LookupTitle;
  /** 記録の索引（本文の項目の ID のツールチップ） */
  index?: RecordIndex | null;
  focus?: string;
  onToggle: (id: string, open: boolean) => void;
  onOpenChangeSet?: (id: string) => void;
  onOpenItem?: (id: string) => void;
  /** 本文のスレッドの ID と書き込みの ID のボタン（送信した書き込みを畳むとき） */
  threadTitles?: LookupThread | null;
  onOpenThread?: OpenThread;
  children: (body: ReactNode, toggle: ReactNode | null) => ReactNode;
};

export const ReviewBodyFold = ({ id, label, body, changeSets, open, lines = REVIEW_FOLD_LINES, titles, index = null, focus = "", onToggle, onOpenChangeSet, onOpenItem, threadTitles, onOpenThread, children }: ReviewBodyFoldProps) => {
  const bodyId = `review-body-${id}`;
  const box = useRef<HTMLDivElement>(null);
  const [exceeds, setExceeds] = useState(false);
  // 本文の高さが変わったら測り直す（ブラウザの ResizeObserver と同期する）
  useEffect(() => {
    const element = box.current;
    if (element === null) return undefined;
    const measure = (): void => {
      const lineHeight = Number.parseFloat(getComputedStyle(element).lineHeight);
      setExceeds(element.scrollHeight > lineHeight * lines + FOLD_TOLERANCE_PX);
    };
    const frame = requestAnimationFrame(measure);
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(() => requestAnimationFrame(measure)) : null;
    observer?.observe(element);
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [body, lines]);
  const folded = exceeds && !open;
  const content = (
    <div ref={box} id={bodyId} data-folded={folded ? "" : undefined} className="overflow-hidden" style={folded ? { maxHeight: `calc(${String(lines)} * 1lh)` } : undefined}>
      <PostBody body={body} titles={titles} index={index} changeSets={changeSets} onOpenItem={onOpenItem} onOpenChangeSet={onOpenChangeSet} threadTitles={threadTitles} onOpenThread={onOpenThread} />
    </div>
  );
  const toggle = exceeds ? (
    <Button variant="ghost" aria-expanded={open} aria-controls={bodyId} data-part="more" aria-label={open ? `${label}の本文を折りたたむ` : `${label}の続きを表示`} data-focus={`${focus}more:${id}`} onClick={() => onToggle(id, !open)}>
      <Icon name="chev" className={open ? "-rotate-90" : "rotate-90"} />
      <span>{open ? "折りたたむ" : "続きを表示"}</span>
    </Button>
  ) : null;
  return <>{children(content, toggle)}</>;
};
