// スレッドの見出しのタイトル。書き込みの並びが一番上のときは 2 行で省略し、収まらないときだけ開閉のボタンで全文を開く。スクロールした後は 1 行にして末尾を「…」にする
import { useEffect, useId, useRef, useState, type RefObject } from "react";

import { Icon } from "@/shared/components/icon";
import { RecordText } from "@/shared/components/record-text";
import { Button } from "@/shared/components/ui/button";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { cn } from "@/shared/lib/cn";

/** 書き込みの並びが一番上のときに出す、折り返した後の見た目の行の数 */
export const THREAD_TITLE_LINES = 2;

/** 全文の高さが、行の高さ × 行数を超えたとみなす余裕（小数の丸め） */
const CLAMP_TOLERANCE_PX = 1;

export type ThreadTitleProps = {
  title: string;
  /** 書き込みの並びをスクロールした後か（1 行に省略する） */
  collapsed: boolean;
  /** タイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  /** タイトルの中の ID のリンクを押したとき */
  onOpen?: (id: string) => void;
};

/** 2 行を超えるかを、タイトルの高さが変わるたびに測る（ブラウザの ResizeObserver と同期する） */
const useExceedsLines = (box: RefObject<HTMLSpanElement | null>, title: string): boolean => {
  const [exceeds, setExceeds] = useState(false);
  useEffect(() => {
    const element = box.current;
    if (element === null) return undefined;
    const measure = (): void => {
      const lineHeight = Number.parseFloat(getComputedStyle(element).lineHeight);
      setExceeds(element.scrollHeight > lineHeight * THREAD_TITLE_LINES + CLAMP_TOLERANCE_PX);
    };
    const frame = requestAnimationFrame(measure);
    const observer = new ResizeObserver(() => requestAnimationFrame(measure));
    observer.observe(element);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [box, title]);
  return exceeds;
};

type TitleToggleProps = { open: boolean; controls: string; onToggle: () => void };

/** 2 行に省略したタイトルの全文を開く・閉じるボタン */
const TitleToggle = ({ open, controls, onToggle }: TitleToggleProps) => (
  <Button variant="ghost" aria-expanded={open} aria-controls={controls} data-part="more" aria-label={open ? "タイトルを折りたたむ" : "タイトルの続きを表示"} className="-ml-2 h-7 font-normal" onClick={onToggle}>
    <Icon name="chev" className={open ? "-rotate-90" : "rotate-90"} />
    <span>{open ? "折りたたむ" : "続きを表示"}</span>
  </Button>
);

export const ThreadTitle = ({ title, collapsed, lookup, onOpen }: ThreadTitleProps) => {
  const textId = useId();
  const box = useRef<HTMLSpanElement>(null);
  const exceeds = useExceedsLines(box, title);
  const [open, setOpen] = useState(false);
  const clamped = !collapsed && exceeds && !open;
  const expanded = !collapsed && open;
  return (
    <span data-part="thread-title" data-collapsed={collapsed ? "" : undefined} data-clamped={clamped ? "" : undefined} className="flex min-w-0 flex-1 flex-col items-start">
      <span ref={box} id={textId} title={collapsed ? title : undefined} className={cn("w-full min-w-0 wrap-anywhere", collapsed && "truncate", clamped && "line-clamp-2", expanded && "max-h-72 overflow-y-auto")}>
        <RecordText text={title} mode="link" lookup={lookup} {...(onOpen === undefined ? {} : { onOpen })} />
      </span>
      {!collapsed && exceeds ? <TitleToggle open={open} controls={textId} onToggle={() => { setOpen((value) => !value); }} /> : null}
    </span>
  );
};
