// Markdown の本文（部品設計『Markdownの本文.tsx』）。mdmark で描いた本文（表の入れ物・図の入れ物つき）を `useEffect` の中で置き、見せ方を当てる
import { useEffect, useRef } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { renderMarkdown } from "@/shared/core/body-links";
import { decorateMarkdown, BODY_VIEW_DEFAULT, type BodyView } from "@/shared/core/markdown-decorate";

export type MarkdownBodyProps = { source: string; display?: BodyView; fold?: boolean; tables?: boolean };

export const MarkdownBody = ({ source, display = BODY_VIEW_DEFAULT, fold = true, tables = true }: MarkdownBodyProps) => {
  const { status } = useLibrary("mdmark");
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    // 描いた本文（mdmark が根に付けた見た目の属性ごと）を部品の要素へ置き、見せ方を当てる
    const rendered = renderMarkdown(source);
    root.replaceChildren(rendered);
    decorateMarkdown({ root: rendered, display, fold, tables });
    return () => {
      root.replaceChildren();
    };
  }, [status, source, display, fold, tables]);
  if (status === "failed") {
    return (
      <div>
        <p className="text-small text-muted-foreground">mdmark を読み込めないため、本文を原文のまま出しています。</p>
        <pre className="whitespace-pre-wrap">{source}</pre>
      </div>
    );
  }
  return <div ref={host} />;
};
