// 狭い幅で使う、字下げした縦の一覧
import { buildMapGraph, type MapNode } from "@/features/decisions/decisions/map-layout";
import { CommentMark } from "@/shared/components/comment-mark";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { StatusMark } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import type { ScreenEdit } from "@/shared/core/edits";
import type { Item, Settings } from "@/shared/core/records";

export type DecisionOutlineProps = { items: readonly Item[]; settings: Settings; marks: DiffMarks | undefined; comments: Record<string, number>; edit: ScreenEdit | null; onOpen: (id: string) => void };

export const DecisionOutline = ({ items, settings, marks, comments, edit, onOpen }: DecisionOutlineProps) => {
  const tree = buildMapGraph(items, settings);
  const nodeOf = new Map(tree.nodes.map((node) => [node.id, node]));
  const childrenOf = new Map<string, MapNode[]>();
  for (const edge of tree.edges) {
    const [source, target] = [edge.sources[0] ?? "", edge.targets[0] ?? ""];
    const child = nodeOf.get(target);
    if (child !== undefined) childrenOf.set(source, [...(childrenOf.get(source) ?? []), child]);
  }
  const entry = (node: MapNode) => {
    const below = childrenOf.get(node.id) ?? [];
    const pending = edit?.marks[node.id];
    const mark = marks?.[node.id];
    const count = comments[node.id] ?? 0;
    return (
      <li key={node.id}>
        {node.kind === "item" ? (
          <button type="button" data-id={node.id} className="flex cursor-pointer items-center gap-1 py-1 text-left text-small" onClick={() => { onOpen(node.id); }}>
            <StatusMark status={node.item?.status} />
            <span>{node.label}</span>
            {mark === undefined ? null : <DiffMark kind={mark} />}
            {pending === undefined ? null : <PendingMark kind={pending} compact />}
            {count > 0 ? <CommentMark count={count} /> : null}
          </button>
        ) : (
          <div className="py-0.5 text-small font-medium">{node.label}</div>
        )}
        {below.length > 0 ? <ul className="pl-4">{below.map(entry)}</ul> : null}
      </li>
    );
  };
  const roots = tree.nodes.filter((node) => node.kind === "target");
  return (
    <nav aria-label="検討事項の一覧" className="overflow-auto lg:hidden">
      {roots.length > 0 ? <ul>{roots.map(entry)}</ul> : <p className="text-small text-muted-foreground">表示する検討事項はありません。</p>}
    </nav>
  );
};
