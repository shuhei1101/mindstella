// 変更履歴（画面設計『変更履歴.tsx』）。記録のまとまりから時点を並べ、選んだ時点を差分の表示にする
import { HistoryDialog as HistoryModal, type HistoryPoint } from "@/shared/components/history-dialog";
import { resolveDiffPoint, type DiffPoint, type OpenedPoint } from "@/shared/core/diff";
import { formatJst } from "@/shared/core/format";
import type { Changes } from "@/shared/core/records";

/** 並べる時点（差分を出さない・まだまとめていない変更・前回開いてから・まとまりの新しい順） */
export const historyPoints = (changes: Changes, since: OpenedPoint): HistoryPoint[] => {
  const countOf = (sel: string): number => {
    const point = resolveDiffPoint(changes, sel, since);
    return point === null ? 0 : point.added.size + point.changed.size + point.removed.size;
  };
  const hasPending = changes.pending.added.length + changes.pending.changed.length + (changes.pending.removed ?? []).length > 0;
  return [
    { sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" },
    ...(hasPending ? [{ sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: countOf("pending") }] : []),
    { sel: "since", name: "前回開いてから", sub: `${formatJst(since.at)} より後`, count: countOf("since") },
    ...changes.sets.map((set) => ({ sel: set.id, name: set.summary, sub: formatJst(set.at), count: countOf(set.id) })),
  ];
};

export type HistoryScreenProps = { changes: Changes; since: OpenedPoint; point: DiffPoint | null; onSelect: (sel: string) => void; onClose: () => void };

export const HistoryScreen = ({ changes, since, point, onSelect, onClose }: HistoryScreenProps) => <HistoryModal points={historyPoints(changes, since)} current={point?.sel ?? ""} onSelect={onSelect} onClose={onClose} />;
