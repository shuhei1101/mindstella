// Markdown の本文（部品設計『Markdownの本文.tsx』）。mdmark の `mount` を `useEffect` の中で呼び、描いた要素に見せ方を当てる
import { useEffect, useRef } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { MDMARK_FEATURES } from "@/shared/core/body-links";
import { decorateMarkdown, BODY_VIEW_DEFAULT, type BodyView } from "@/shared/core/markdown-decorate";

type Mdmark = { mount: (root: HTMLElement, options: { markdown: string; config: { features: Record<string, boolean> } }) => { destroy?: () => void } | undefined };

export type MarkdownBodyProps = { source: string; display?: BodyView; fold?: boolean; tables?: boolean };

export const MarkdownBody = ({ source, display = BODY_VIEW_DEFAULT, fold = true, tables = true }: MarkdownBodyProps) => {
  const { status, library } = useLibrary("mdmark");
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    const mounted = (library as Mdmark).mount(root, { markdown: source, config: { features: MDMARK_FEATURES } });
    decorateMarkdown({ root, display, fold, tables });
    return () => {
      mounted?.destroy?.();
      root.replaceChildren();
    };
  }, [status, library, source, display, fold, tables]);
  if (status === "failed") {
    return (
      <div>
        <p className="text-small text-muted-foreground">mdmark を読み込めないため、本文を原文のまま出しています。</p>
        <pre className="whitespace-pre-wrap">{source}</pre>
      </div>
    );
  }
  return <div ref={host} className="md" />;
};
