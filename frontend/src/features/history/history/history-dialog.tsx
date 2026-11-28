// 変更履歴（画面設計『変更履歴.tsx』）。記録のまとまりから時点を並べ、選んだ時点を差分の表示にする
import { HistoryDialog as HistoryModal, type HistoryPoint } from "@/shared/components/history-dialog";
import { resolveDiffPoint, type DiffPoint } from "@/shared/core/diff";
import { formatJst } from "@/shared/core/format";
import type { Changes } from "@/shared/core/records";

/** 並べる時点（最新・今回の差分・まだまとめていない変更・まとまりの新しい順）。`unread` を渡したときだけ、まとまりの行に未読を付ける */
export const historyPoints = (changes: Changes, unread?: readonly string[]): HistoryPoint[] => {
  const countOf = (sel: string): number => {
    const point = resolveDiffPoint(changes, sel);
    return point === null ? 0 : point.added.size + point.changed.size + point.removed.size;
  };
  const hasPending = changes.pending.added.length + changes.pending.changed.length + (changes.pending.removed ?? []).length > 0;
  const unreadSet = unread === undefined ? null : new Set(unread);
  const turn = resolveDiffPoint(changes, "turn");
  return [
    { sel: "", name: "最新", sub: "マーカーと差分を出さずに今の内容だけを読む" },
    // 今回の差分は常に出す（送信の後に書き換えが無くても選べる）
    ...(turn === null ? [] : [{ sel: "turn", name: turn.name, sub: turn.sub, count: countOf("turn") }]),
    ...(hasPending ? [{ sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: countOf("pending") }] : []),
    ...changes.sets.map((set) => ({ sel: set.id, name: set.summary, sub: formatJst(set.at), count: countOf(set.id), external: set.by === "external", ...(unreadSet === null ? {} : { unread: unreadSet.has(set.id) }) })),
  ];
};

export type HistoryScreenProps = {
  changes: Changes;
  point: DiffPoint | null;
  /** 未読のまとまりの ID（配る書き出しでは渡さない） */
  unreadSetIds?: readonly string[];
  onSelect: (sel: string) => void;
  onClose: () => void;
  /** 「すべて既読にする」を押したとき（配る書き出しでは渡さない） */
  onMarkAllRead?: () => void;
};

export const HistoryScreen = ({ changes, point, unreadSetIds, onSelect, onClose, onMarkAllRead }: HistoryScreenProps) => (
  <HistoryModal points={historyPoints(changes, unreadSetIds)} current={point?.sel ?? ""} onSelect={onSelect} onClose={onClose} {...(onMarkAllRead === undefined ? {} : { onMarkAllRead })} />
);
