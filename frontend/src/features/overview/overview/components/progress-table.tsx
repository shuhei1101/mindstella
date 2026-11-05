// カテゴリー別の進捗のタイル（`derived.progress` の表。カテゴリーを行、フェーズを列にする）
import type { CategoryProgress, Settings } from "@/shared/api/generated/model";
import { Icon } from "@/shared/components/icon";
import { ProgressBar } from "@/features/overview/overview/components/goal-tile";

export type ProgressTableProps = {
  progress: CategoryProgress[];
  settings: Settings;
  /** セルと行の見出しを押したとき（フェーズは行の見出しなら null）。渡さないと押せなくする */
  onSelect?: ((category: string, phase: string | null) => void) | undefined;
};

/** 押せるセル・行の見出しの見た目 */
const LINK_CLASS = "-mx-1.5 -my-1 inline-flex cursor-pointer items-center gap-2 rounded-control border-0 bg-transparent px-1.5 py-1 text-left text-inherit hover:bg-accent";

export const ProgressTable = ({ progress, settings, onSelect }: ProgressTableProps) => {
  // 対象ごとに見出しの行を立て、その対象のカテゴリーを続ける
  const groups = settings.targets.flatMap((target) => {
    const entries = progress.filter(
      (entry) =>
        entry.total > 0 &&
        settings.categories.some((category) => category.name === entry.category && category.target === target.name),
    );
    return entries.length === 0 ? [] : [{ target: target.name, entries }];
  });
  return (
    <section id="tile-progress" aria-labelledby="h-cat" className="col-span-full min-w-0 rounded-control bg-card px-6.5 py-6 max-md:col-auto max-md:p-5 dark:border dark:border-border-soft">
      <h2 id="h-cat" className="m-0 flex items-center gap-2 text-h2 font-semibold text-muted-foreground">
        <Icon name="layers" />
        カテゴリー別の進捗
      </h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full border-collapse text-small">
          <thead>
            <tr>
              <th scope="col" className="border-b border-border-soft px-2.5 py-2.25 text-left text-xs font-semibold whitespace-nowrap text-muted-foreground">
                カテゴリー
              </th>
              {settings.phases.map((phase) => (
                <th key={phase} scope="col" className="border-b border-border-soft px-2.5 py-2.25 text-left text-xs font-semibold whitespace-nowrap text-muted-foreground">
                  {phase}
                </th>
              ))}
              <th scope="col" className="border-b border-border-soft px-2.5 py-2.25 text-right text-xs font-semibold whitespace-nowrap text-muted-foreground">
                決定済み
              </th>
            </tr>
          </thead>
          {groups.map((group) => (
            <tbody key={group.target}>
              <tr>
                <th
                  colSpan={settings.phases.length + 2}
                  scope="rowgroup"
                  className="border-b border-border px-2.5 pt-4 pb-2.25 text-left text-xs font-semibold whitespace-nowrap text-muted-foreground"
                >
                  {settings.target_label}: {group.target}
                </th>
              </tr>
              {group.entries.map((entry) => (
                <tr key={entry.category}>
                  <th scope="row" className="border-b border-border-soft px-2.5 py-2.25 text-left font-semibold whitespace-nowrap">
                    {onSelect === undefined ? (
                      <span>{entry.category}</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          onSelect(entry.category, null);
                        }}
                        className={LINK_CLASS}
                      >
                        {entry.category}
                      </button>
                    )}
                  </th>
                  {entry.cells.map((cell) => (
                    <td key={cell.phase} className="border-b border-border-soft px-2.5 py-2.25 whitespace-nowrap">
                      {cell.total === 0 ? (
                        <span className="text-subtle-foreground">—</span>
                      ) : onSelect === undefined ? (
                        <span className="inline-flex items-center gap-2" aria-label={`${entry.category} の ${cell.phase}: ${String(cell.settled)}/${String(cell.total)} 件決定済み`}>
                          <ProgressBar settled={cell.settled} total={cell.total} className="h-1.25 w-14" />
                          <span className="mono text-xs text-muted-foreground">
                            {cell.settled}/{cell.total}
                          </span>
                        </span>
                      ) : (
                        <button
                          type="button"
                          aria-label={`${entry.category} の ${cell.phase}: ${String(cell.settled)}/${String(cell.total)} 件決定済み`}
                          onClick={() => {
                            onSelect(entry.category, cell.phase);
                          }}
                          className={LINK_CLASS}
                        >
                          <ProgressBar settled={cell.settled} total={cell.total} className="h-1.25 w-14" />
                          <span className="mono text-xs text-muted-foreground">
                            {cell.settled}/{cell.total}
                          </span>
                        </button>
                      )}
                    </td>
                  ))}
                  <td className="border-b border-border-soft px-2.5 py-2.25 text-right mono whitespace-nowrap">
                    {entry.settled}/{entry.total}
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
    </section>
  );
};
