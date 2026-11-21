// HTML の本文の差分（部品設計『HTMLの本文の差分.tsx』）。描いた結果の印と原文の差分を切り替える
import { useCallback } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { DomHost } from "@/shared/components/dom-host";
import { htmlBodyDiff, type HtmlBodyDiffProps } from "@/shared/core/html-body-diff";

export type { HtmlBodyDiffProps };

export const HtmlBodyDiff = (input: HtmlBodyDiffProps) => {
  const ready = useLibrary("jsdiff").status === "ready";
  const key = JSON.stringify({ ...input, beforeView: undefined, afterView: undefined });
  const create = useCallback(
    () => (ready ? { node: htmlBodyDiff(input) } : { node: null }),
    // 中身の値が変わったときだけ組み直す
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, ready],
  );
  return <DomHost create={create} />;
};
