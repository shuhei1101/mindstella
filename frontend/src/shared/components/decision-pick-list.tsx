// AI の通知のスレッドに並んだ検討事項の一覧。未決定で推奨の案を持つ検討事項を選び、推奨の案でまとめて決定する
import { BulkDecideBar, type BulkDecideFailure } from "@/shared/components/bulk-decide-bar";
import { StatusMark } from "@/shared/components/icon";
import { Checkbox } from "@/shared/components/ui/checkbox";

/** 誰が決めたか */
export type DecidedBy = "user" | "ai";

/** 一覧の 1 行 */
export type DecisionPickRow = { id: string; title: string; status: string; recommended: string | null; decidedBy: DecidedBy | null };

/** 選んだ・解除したときに呼ぶ関数 */
export type TogglePick = (input: { id: string; checked: boolean }) => void;

export type DecisionPickListProps = {
  rows: DecisionPickRow[];
  /** 選んでいる検討事項の ID */
  picked: string[];
  pending?: boolean;
  failures?: BulkDecideFailure[];
  onToggle: TogglePick;
  onDecide: () => void;
  onClear: () => void;
};

const DECIDED_BY_LABEL = { user: "利用者が決定", ai: "AI が決定" } as const satisfies Record<DecidedBy, string>;

/** 未決定で推奨の案を持つ行だけを選べる */
export const isPickable = (row: DecisionPickRow): boolean => row.status === "未決定" && row.recommended !== null;

export const DecisionPickList = ({ rows, picked, pending = false, failures = [], onToggle, onDecide, onClear }: DecisionPickListProps) => (
  <div className="flex flex-col gap-2">
    <ul aria-label="通知した検討事項" className="flex flex-col divide-y divide-border-soft rounded-card border border-border-soft bg-card">
      {rows.map((row) => {
        const pickable = isPickable(row);
        return (
          <li key={row.id} className="flex items-start gap-2 px-2 py-1.5 text-small">
            <Checkbox
              aria-label={pickable ? `${row.id} を選ぶ` : `${row.id} は選べません`}
              checked={picked.includes(row.id)}
              disabled={!pickable || pending}
              className="mt-0.5 cursor-pointer disabled:cursor-default"
              onChange={(event) => {
                onToggle({ id: row.id, checked: event.target.checked });
              }}
            />
            <div className="min-w-0 flex-1">
              <span className="flex flex-wrap items-center gap-1">
                <span className="font-mono text-xs">{row.id}</span>
                {row.title}
              </span>
              <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <StatusMark status={row.status} />
                  {row.status}
                </span>
                <span>{row.recommended === null ? "推奨の案なし" : `推奨 ${row.recommended}`}</span>
                {row.decidedBy === null ? null : <span>{DECIDED_BY_LABEL[row.decidedBy]}</span>}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
    <BulkDecideBar count={picked.length} pending={pending} failures={failures} onDecide={onDecide} onClear={onClear} />
  </div>
);
