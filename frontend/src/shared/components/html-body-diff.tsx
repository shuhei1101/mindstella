// HTML の本文の差分（部品設計『HTMLの本文の差分.tsx』）。描いた結果の印と原文の差分を切り替える
import { useCallback, type ReactNode } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { DomHost } from "@/shared/components/dom-host";
import { htmlBodyDiff, type HtmlBodyDiffProps as DiffInput } from "@/shared/core/html-body-diff";

export type HtmlBodyDiffProps = Omit<DiffInput, "layoutSwitch"> & { layoutSwitch?: ReactNode };

export const HtmlBodyDiff = ({ layoutSwitch, ...input }: HtmlBodyDiffProps) => {
  const { status } = useLibrary("jsdiff");
  const key = JSON.stringify({ ...input, beforeView: undefined, afterView: undefined });
  const create = useCallback(
    () => ({ node: status === "ready" ? htmlBodyDiff(input) : null }),
    // 中身の値が変わったときだけ組み直す
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, status],
  );
  return (
    <div className="flex flex-col gap-1">
      {layoutSwitch}
      <DomHost create={create} />
    </div>
  );
};
