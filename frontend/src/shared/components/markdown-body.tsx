// Markdown の本文（部品設計『Markdownの本文.tsx』）。mdmark で描いた本文（`tables` なら mdmark の表の機能で描く表・図の入れ物つき）を `useEffect` の中で置き、見せ方を当てる。`base` を指定すると、選んだ時点の本文と比べた mdmark の差分で描く
import { useEffect, useRef } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { renderMarkdown } from "@/shared/core/body-links";
import type { BodyDiffView } from "@/shared/components/body-diff-view-switch";
import { decorateMarkdown, BODY_VIEW_DEFAULT, type BodyView } from "@/shared/core/markdown-decorate";

/** 原文の差分の取り出し元に渡す文書の ID */
const DIFF_DOC_ID = "body";

export type MarkdownBodyProps = { source: string; display?: BodyView; fold?: boolean; tables?: boolean; base?: string; diffView?: BodyDiffView };

export const MarkdownBody = ({ source, display = BODY_VIEW_DEFAULT, fold = true, tables = true, base, diffView = "rendered" }: MarkdownBodyProps) => {
  const { status } = useLibrary("mdmark");
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    // 描いた本文（mdmark が根に付けた見た目の属性ごと）を部品の要素へ置き、見せ方を当てる
    // 選んだ時点と同じ本文は色を付けずに描く
    const diff = base === undefined || base === source ? {} : diffView === "source" ? { diffSource: { docId: DIFF_DOC_ID, before: base, after: source } } : { base };
    const rendered = renderMarkdown(source, { table: tables, ...diff });
    root.replaceChildren(rendered);
    decorateMarkdown({ root: rendered, display, fold });
    return () => {
      root.replaceChildren();
    };
  }, [status, source, display, fold, tables, base, diffView]);
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
