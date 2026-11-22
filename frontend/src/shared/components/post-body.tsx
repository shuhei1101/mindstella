// 書き込みの本文。段落の中の改行を強制改行にして Markdown として描き、表は幅に収まらないときにその中だけ横にスクロールさせ、項目の ID をその項目を開くボタン、記録にあるまとまりを指すリンクをまとまりのリンクにする。mdmark を読めないときは本文を文字のまま改行を保って出す
import { useEffect, useRef } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { renderDiagrams, renderMarkdown, withHardBreaks } from "@/shared/core/body-links";
import { drawHtmlBlocks, withoutLineMarks } from "@/shared/core/body-render";
import { decorateMarkdown } from "@/shared/core/markdown-decorate";
import { buttonizeItemIds, linkChangeSets, linkThreadIds, type LookupTitle } from "@/shared/core/post-links";
import type { RecordIndex } from "@/shared/core/records";
import { attachTermTips } from "@/shared/core/term-tips";
import type { LookupThread, OpenThread } from "@/shared/core/thread-ids";
import { cn } from "@/shared/lib/cn";

export type PostBodyProps = {
  body: string;
  titles?: LookupTitle;
  changeSets?: LookupTitle;
  /** 記録の索引。渡すと、項目の ID のボタンに乗せる・フォーカスしたときに項目のツールチップを出す */
  index?: RecordIndex | null;
  id?: string;
  className?: string;
  onOpenItem?: (id: string) => void;
  onOpenChangeSet?: (id: string) => void;
  /** 記録にあるスレッドの引き方。渡すと、本文のスレッドの ID と書き込みの ID をそのスレッドを開くボタンにする */
  threadTitles?: LookupThread | null;
  onOpenThread?: OpenThread;
};

const noTitle: LookupTitle = () => null;

export const PostBody = ({ body, titles = noTitle, changeSets = noTitle, index = null, id, className, onOpenItem, onOpenChangeSet, threadTitles = null, onOpenThread }: PostBodyProps) => {
  const { status } = useLibrary("mdmark");
  // 図は mermaid を読み終えてから描く（読み終えたら本文を描き直す）
  const diagrams = useLibrary("mermaid").status;
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    // 描いた本文を部品の要素へ置き、ボタンとリンクを付ける
    const rendered = withoutLineMarks(renderMarkdown(withHardBreaks(body), { table: false }));
    root.replaceChildren(rendered);
    // 図は描き終えるのを待たずに出し、`html` のコードブロックは枠に置き換える
    if (diagrams !== "loading") void renderDiagrams(rendered);
    drawHtmlBlocks(rendered);
    wrapTables(rendered);
    decorateMarkdown({ root: rendered, fold: false });
    linkChangeSets({ root: rendered, changeSets, onChangeSet: (set) => onOpenChangeSet?.(set) });
    buttonizeItemIds({ root: rendered, titles, onOpen: (item) => onOpenItem?.(item) });
    if (threadTitles !== null) linkThreadIds({ root: rendered, threads: threadTitles, onOpen: (thread, post) => onOpenThread?.(thread, post) });
    if (index !== null) attachTermTips({ root: rendered, index, onOpen: (item) => onOpenItem?.(item), threads: threadTitles });
    return () => {
      root.replaceChildren();
    };
  }, [status, diagrams, body, titles, changeSets, index, onOpenItem, onOpenChangeSet, threadTitles, onOpenThread]);
  // 読めない・読み込み中は文字のまま改行を保って出す
  if (status !== "ready") {
    return (
      <p id={id} data-part="body" className={cn("m-0 whitespace-pre-wrap", className)}>
        {body}
      </p>
    );
  }
  return <div id={id} ref={host} data-part="body" className={cn("min-w-0", className)} />;
};

/** 表を、幅に収まらないときにその中だけ横にスクロールする入れ物で包む */
const wrapTables = (root: HTMLElement): void => {
  for (const table of root.querySelectorAll("table")) {
    const scroller = document.createElement("div");
    scroller.className = "post-table-scroll max-w-full overflow-x-auto";
    table.replaceWith(scroller);
    scroller.append(table);
  }
};
