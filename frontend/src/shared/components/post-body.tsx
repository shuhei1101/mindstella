// 書き込みの本文。段落の中の改行を強制改行にして Markdown として描き、項目の ID をその項目を開くボタン、記録にあるまとまりを指すリンクをまとまりのリンクにする。mdmark を読めないときは本文を文字のまま改行を保って出す
import { useEffect, useRef } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { renderMarkdown, withHardBreaks } from "@/shared/core/body-links";
import { withoutLineMarks } from "@/shared/core/body-render";
import { decorateMarkdown } from "@/shared/core/markdown-decorate";
import { buttonizeItemIds, linkChangeSets, type LookupTitle } from "@/shared/core/post-links";
import { cn } from "@/shared/lib/cn";

export type PostBodyProps = {
  body: string;
  titles?: LookupTitle;
  changeSets?: LookupTitle;
  id?: string;
  className?: string;
  onOpenItem?: (id: string) => void;
  onOpenChangeSet?: (id: string) => void;
};

const noTitle: LookupTitle = () => null;

export const PostBody = ({ body, titles = noTitle, changeSets = noTitle, id, className, onOpenItem, onOpenChangeSet }: PostBodyProps) => {
  const { status } = useLibrary("mdmark");
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    // 描いた本文を部品の要素へ置き、ボタンとリンクを付ける
    const rendered = withoutLineMarks(renderMarkdown(withHardBreaks(body)));
    root.replaceChildren(rendered);
    decorateMarkdown({ root: rendered, fold: false, tables: false });
    linkChangeSets({ root: rendered, changeSets, onChangeSet: (set) => onOpenChangeSet?.(set) });
    buttonizeItemIds({ root: rendered, titles, onOpen: (item) => onOpenItem?.(item) });
    return () => {
      root.replaceChildren();
    };
  }, [status, body, titles, changeSets, onOpenItem, onOpenChangeSet]);
  // 読めない・読み込み中は文字のまま改行を保って出す
  if (status !== "ready") {
    return (
      <p id={id} className={cn("m-0 whitespace-pre-wrap", className)}>
        {body}
      </p>
    );
  }
  return <div id={id} ref={host} className={className} />;
};
