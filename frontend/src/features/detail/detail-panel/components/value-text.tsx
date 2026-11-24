// Markdown で描く値。描いた後に本文と同じく、本文のマーカー・項目の ID・スレッドの ID のリンクを付ける
import { createContext, useContext, useEffect, useRef } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { MarkdownBody } from "@/shared/components/markdown-body";
import { linkBody, renderMarkdown, withHardBreaks } from "@/shared/core/body-links";
import { decorateMarkdown } from "@/shared/core/markdown-decorate";
import type { RecordIndex } from "@/shared/core/records";
import type { LookupThread, OpenThread } from "@/shared/core/thread-ids";

/** 値の欄のリンクに使う、本文を描く要素と同じ値 */
export type ValueLinks = {
  index: RecordIndex;
  selfId: string;
  onOpen: (id: string) => void;
  /** 配る書き出しでは null（スレッドの ID は文字のまま） */
  threads: LookupThread | null;
  onOpenThread?: OpenThread;
};

/** 詳細パネルが値の欄のリンクの値を渡す */
export const ValueLinksContext = createContext<ValueLinks | null>(null);

export type ValueTextProps = { value: string | undefined } & Partial<ValueLinks>;

const LinkedValue = ({ source, links }: { source: string; links: ValueLinks }) => {
  const { status } = useLibrary("mdmark");
  const host = useRef<HTMLDivElement>(null);
  const { index, selfId, onOpen, threads, onOpenThread } = links;
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    const rendered = renderMarkdown(source, { table: true });
    root.replaceChildren(rendered);
    decorateMarkdown({ root: rendered, fold: false });
    linkBody({ root: rendered, index, selfId, onOpen, source, threads, ...(onOpenThread === undefined ? {} : { onOpenThread }) });
    return () => {
      root.replaceChildren();
    };
  }, [status, source, index, selfId, onOpen, threads, onOpenThread]);
  if (status === "failed") return <MarkdownBody source={source} fold={false} />;
  return <div ref={host} />;
};

export const ValueText = ({ value, index, selfId, onOpen, threads, onOpenThread }: ValueTextProps) => {
  const context = useContext(ValueLinksContext);
  if (value === undefined || value === "") return null;
  const source = withHardBreaks(value);
  const links: ValueLinks | null = index !== undefined && selfId !== undefined && onOpen !== undefined ? { index, selfId, onOpen, threads: threads ?? null, ...(onOpenThread === undefined ? {} : { onOpenThread }) } : context;
  return links === null ? <MarkdownBody source={source} fold={false} /> : <LinkedValue source={source} links={links} />;
};
