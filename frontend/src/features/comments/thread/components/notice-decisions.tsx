// AI の通知の書き込みが並べた検討事項を、選んで推奨の案でまとめて決める一覧
import { useState } from "react";

import { DecisionPickList, type DecisionPickRow } from "@/shared/components/decision-pick-list";
import { recommendedKeyOf, type RecordIndex } from "@/shared/core/records";
import { useBulkDecide } from "@/shared/hooks/use-bulk-decide";

/** 本文の中の検討事項の ID */
const DECISION_ID = /\bD-\d+\b/g;

/** 本文が並べた検討事項の ID を、出た順に重なりを除いて返却する */
export const decisionIdsOf = (body: string): string[] => [...new Set(body.match(DECISION_ID) ?? [])];

export type NoticeDecisionsProps = { index: RecordIndex; body: string };

export const NoticeDecisions = ({ index, body }: NoticeDecisionsProps) => {
  const [picked, setPicked] = useState<string[]>([]);
  const bulk = useBulkDecide();
  const rows: DecisionPickRow[] = decisionIdsOf(body).flatMap((id) => {
    const found = index.byId.get(id);
    if (found?.kind !== "decisions") return [];
    const { item } = found;
    return [{ id, title: item.title, status: item.status ?? "", recommended: recommendedKeyOf(item), decidedBy: item.decided_by ?? null }];
  });
  if (rows.length === 0) return null;
  return (
    <DecisionPickList
      rows={rows}
      picked={picked}
      pending={bulk.pending}
      failures={bulk.failures}
      onToggle={({ id, checked }) => {
        setPicked((current) => (checked ? [...current, id] : current.filter((one) => one !== id)));
      }}
      onDecide={() => {
        bulk.decide({ ids: picked, onDecided: () => { setPicked([]); } });
      }}
      onClear={() => { setPicked([]); }}
    />
  );
};
