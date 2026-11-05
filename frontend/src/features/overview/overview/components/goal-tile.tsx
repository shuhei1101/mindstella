// ゴールまでの進捗のタイル（`derived.goal` の数・棒・納品物）。ゴールが無いときはフェーズ別の進捗
import type { Goal, Settings } from "@/shared/api/generated/model";
import { Icon } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

/** 納品物のチェックリストに出す件数（これを超えたら「すべて表示」） */
const DELIVERABLE_LIMIT = 5;

/** 決定済みの数の棒（0〜100%） */
export const ProgressBar = ({ settled, total, className }: { settled: number; total: number; className?: string }) => {
  const ratio = total === 0 ? 0 : settled / total;
  return (
    <i className={cn("block h-1.5 overflow-hidden rounded-full bg-muted", className)}>
      <b className="block h-full rounded-full bg-mark" style={{ width: `${String(ratio * 100)}%` }} />
    </i>
  );
};

export type GoalTileProps = {
  goal: Goal;
  settings: Settings;
  /** 資料の ID があるか（納品物を押せるか） */
  hasItem: (id: string) => boolean;
  onOpen: (id: string) => void;
  /** 納品物の「すべて表示」を押したとき。渡さないと出さない */
  onShowAllDeliverables?: (() => void) | undefined;
};

export const GoalTile = ({ goal, settings, hasItem, onOpen, onShowAllDeliverables }: GoalTileProps) => {
  const settled = goal.phase_progress.reduce((sum, cell) => sum + cell.settled, 0);
  const total = goal.phase_progress.reduce((sum, cell) => sum + cell.total, 0);
  const deliverables = settings.goal?.deliverables ?? [];
  const remaining = new Set(goal.remaining_deliverables.map((entry) => entry.title));
  const doneCount = deliverables.filter((entry) => !remaining.has(entry.title)).length;
  return (
    <section id="tile-goal" aria-labelledby="h-goal" className="min-w-0 rounded-control bg-card px-6.5 py-6 max-md:p-5 dark:border dark:border-border-soft">
      <h2 id="h-goal" className="m-0 flex items-center gap-2 text-h2 font-semibold text-muted-foreground">
        <Icon name="flag" />
        {goal.has_goal ? "ゴールまでの進捗" : "フェーズ別の進捗"}
      </h2>
      {goal.has_goal ? null : <p className="mt-2.5 mb-0 text-muted-foreground">ゴールは決まっていません</p>}
      <p className="mt-3.5 mb-0 mono text-goal leading-none font-bold tracking-tighter">
        {settled}
        <small className="text-goal-sub font-medium tracking-normal text-subtle-foreground"> / {total}</small>
      </p>
      <p className="mt-1.5 mb-5.5 text-muted-foreground">決定済み</p>
      <ul className="m-0 grid list-none gap-2.5 p-0">
        {goal.phase_progress.map((cell) => (
          <li key={cell.phase} className="grid grid-cols-stage items-center gap-2.5 text-small">
            <span>{cell.phase}</span>
            <ProgressBar settled={cell.settled} total={cell.total} />
            <span className="text-right mono text-muted-foreground">
              {cell.settled}/{cell.total}
            </span>
          </li>
        ))}
      </ul>
      {goal.has_goal ? (
        <div className="mt-5.5 text-small">
          <div className="flex items-center gap-2 font-semibold text-muted-foreground">
            <Icon name="box" className="text-mark" />
            納品物
            <span className="mono font-normal text-subtle-foreground">
              {doneCount}/{deliverables.length}
            </span>
            {deliverables.length > DELIVERABLE_LIMIT && onShowAllDeliverables !== undefined ? (
              <button
                type="button"
                onClick={onShowAllDeliverables}
                className="ml-auto cursor-pointer border-0 bg-transparent p-0 text-small font-semibold text-mark hover:underline hover:underline-offset-3"
              >
                すべて表示（{deliverables.length} 件）
              </button>
            ) : null}
          </div>
          <ul className="m-0 mt-2.5 grid list-none gap-1.5 p-0">
            {deliverables.slice(0, DELIVERABLE_LIMIT).map((entry) => {
              const done = !remaining.has(entry.title);
              const doc = entry.doc;
              return (
                <li key={entry.title} className="flex items-center gap-2">
                  <Icon name={done ? "checked" : "unchecked"} className={done ? "text-mark" : "text-subtle-foreground"} />
                  {doc !== undefined && hasItem(doc) ? (
                    <button
                      type="button"
                      onClick={() => {
                        onOpen(doc);
                      }}
                      className={cn(
                        "cursor-pointer border-0 bg-transparent p-0 text-left text-foreground hover:text-mark",
                        done && "text-muted-foreground line-through decoration-subtle-foreground",
                      )}
                    >
                      {entry.title}
                    </button>
                  ) : (
                    <span className={cn(done && "text-muted-foreground line-through decoration-subtle-foreground")}>{entry.title}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </section>
  );
};
