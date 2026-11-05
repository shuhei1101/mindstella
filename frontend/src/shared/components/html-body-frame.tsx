// HTML の本文の枠（部品設計『HTMLの本文の枠.tsx』）。スクリプトを動かさない枠に描き、高さを中身に合わせる
import { useCallback } from "react";

import { DomHost } from "@/shared/components/dom-host";
import { htmlFrameElement, type HtmlBodyFrameProps } from "@/shared/core/html-frame";

export const HtmlBodyFrame = ({ source, selectable = false, label, marks, on }: HtmlBodyFrameProps) => {
  const create = useCallback(
    () => ({ node: htmlFrameElement({ source, selectable, ...(label === undefined ? {} : { label }), ...(marks === undefined ? {} : { marks }), ...(on === undefined ? {} : { on }) }) }),
    [source, selectable, label, marks, on],
  );
  return <DomHost create={create} />;
};
