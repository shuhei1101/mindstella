// HTML の本文の差分（部品設計『HTMLの本文の差分.tsx』）。描いた結果の印と原文の差分を切り替える
import { useCallback, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { useLibrary } from "@/shared/adapters/libraries";
import { DomHost } from "@/shared/components/dom-host";
import { htmlBodyDiff, type HtmlBodyDiffProps as DiffInput } from "@/shared/core/html-body-diff";

/** `layoutSwitch` は、見せ方の組と同じ切り替えの行の先頭に置く並べ方の切り替え */
export type HtmlBodyDiffProps = Omit<DiffInput, "layoutSwitch"> & { layoutSwitch?: ReactNode };

export const HtmlBodyDiff = ({ layoutSwitch, ...input }: HtmlBodyDiffProps) => {
  const { status } = useLibrary("jsdiff");
  // 選んだ時点の Markdown の本文は mdmark で描くので、読み終えてから組む
  const mdmark = useLibrary("mdmark").status;
  const ready = status === "ready" && (input.beforeFormat !== "md" || mdmark !== "loading");
  // 切り替えの行の中で、並べ方の切り替えを描く入れ物
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const hasSwitch = layoutSwitch !== undefined && layoutSwitch !== null;
  const key = JSON.stringify({ ...input, beforeView: undefined, afterView: undefined, hasSwitch });
  const create = useCallback(
    () => {
      if (!ready) return { node: null };
      const holder = hasSwitch ? document.createElement("div") : null;
      holder?.setAttribute("style", "display: contents");
      setSlot(holder);
      return { node: htmlBodyDiff({ ...input, layoutSwitch: holder }), destroy: () => { setSlot(null); } };
    },
    // 中身の値が変わったときだけ組み直す
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, ready],
  );
  return (
    <>
      <DomHost create={create} />
      {slot === null ? null : createPortal(layoutSwitch, slot)}
    </>
  );
};
