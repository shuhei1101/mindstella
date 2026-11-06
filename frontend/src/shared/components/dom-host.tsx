// React の外で組み立てた要素を置く入れ物。`create` が変わるたびに作り直し、片付ける
import { useEffect, useRef } from "react";

export type DomHostProps = { create: () => { node: Node | null; destroy?: () => void }; className?: string };

export const DomHost = ({ create, className }: DomHostProps) => {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null) return undefined;
    const { node, destroy } = create();
    root.replaceChildren(...(node === null ? [] : [node]));
    return () => {
      destroy?.();
      root.replaceChildren();
    };
  }, [create]);
  return <div ref={host} className={className} />;
};
