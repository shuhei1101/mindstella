// 左右に並べた本文の差分（部品設計『左右に並べた本文の差分.tsx』）
import { useCallback } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { DomHost } from "@/shared/components/dom-host";
import { renderDiagrams } from "@/shared/core/body-links";
import { LINE_DIFF_TIMEOUT_MS } from "@/shared/core/diff";
import { sideBySideBodyDiff } from "@/shared/core/side-by-side";

export type SideBySideBodyDiffProps = { before: string; after: string; lined?: boolean };

export const SideBySideBodyDiff = ({ before, after, lined = true }: SideBySideBodyDiffProps) => {
  const mdmark = useLibrary("mdmark").status;
  const marked = useLibrary("marked").status;
  const jsdiff = useLibrary("jsdiff").status;
  const create = useCallback(() => {
    if (mdmark !== "ready" || marked !== "ready" || jsdiff !== "ready") return { node: null };
    const view = sideBySideBodyDiff({ before, after, lined, deadline: performance.now() + LINE_DIFF_TIMEOUT_MS });
    if (view === null) return { node: null };
    view.markWords();
    void renderDiagrams(view.root).then(() => { view.decorate(); });
    return { node: view.root };
  }, [before, after, lined, mdmark, marked, jsdiff]);
  return <DomHost create={create} />;
};
