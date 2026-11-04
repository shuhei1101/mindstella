// 次に検討する項目のタイル（`derived.next` を並べる）。横に並べる幅では枠に収まるだけ、縦に積む幅では上位 3 件を出す
import { useEffect, useRef } from "react";

import type { Item, NextCandidate } from "@/shared/api/generated/model";
import { Icon } from "@/shared/components/icon";
import { TileHead } from "@/features/overview/overview/components/list-tile";

/** 縦に積む幅で出す件数 */
const NEXT_STACKED_COUNT = 3;

/** タイルを横に並べる幅 */
const WIDE_QUERY = "(min-width: 1101px)";

/** 影響度の目盛り（大・中・小）と「影響度 {値}」 */
const ImpactBadge = ({ weight }: { weight: string | null }) => {
  const levels = ["大", "中", "小"];
  if (weight === null || !levels.includes(weight)) return null;
  const filled = 3 - levels.indexOf(weight);
  return (
    <span title={`影響度 ${weight}`} className="inline-flex items-center gap-1.5 text-small whitespace-nowrap text-muted-foreground">
      <span aria-hidden="true" className="inline-flex gap-0.5">
        {[0, 1, 2].map((index) => (
          <i key={index} className={index < filled ? "inline-block h-2.5 w-1 rounded-xs bg-muted-foreground" : "inline-block h-2.5 w-1 rounded-xs bg-border"} />
        ))}
      </span>
      影響度 {weight}
    </span>
  );
};

export type NextTileProps = {
  candidates: NextCandidate[];
  /** ID → 項目（カテゴリーを引く） */
  itemOf: (id: string) => Item | undefined;
  onOpen: (id: string) => void;
  /** 「すべて表示」を押したとき。渡さないと出さない */
  onShowAll?: (() => void) | undefined;
};

export const NextTile = ({ candidates, itemOf, onOpen, onShowAll }: NextTileProps) => {
  const tileRef = useRef<HTMLElement>(null);
  const listRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    const tile = tileRef.current;
    const list = listRef.current;
    if (tile === null || list === null) return undefined;
    // 項目の数で高さが決まらないよう、描いた後の枠で隠す項目を決める
    const fit = (): void => {
      const rows = [...list.children] as HTMLElement[];
      for (const row of rows) row.hidden = false;
      if (window.matchMedia(WIDE_QUERY).matches) {
        const limit = tile.getBoundingClientRect().bottom - Number.parseFloat(getComputedStyle(tile).paddingBottom);
        for (const row of rows) row.hidden = row.getBoundingClientRect().bottom > limit;
      } else {
        rows.forEach((row, position) => {
          row.hidden = position >= NEXT_STACKED_COUNT;
        });
      }
    };
    const observer = new ResizeObserver(fit);
    observer.observe(tile);
    return () => {
      observer.disconnect();
    };
  }, [candidates]);
  return (
    <section
      ref={tileRef}
      id="tile-next"
      aria-labelledby="h-next"
      className="col-span-2 min-w-0 rounded-control bg-card px-6.5 py-6 max-xl:col-span-full max-md:col-auto max-md:p-5 xl:overflow-hidden xl:contain-size dark:border dark:border-border-soft"
    >
      <TileHead id="h-next" icon="next" title="次に検討する項目" count={candidates.length > 0 ? candidates.length : null} onShowAll={onShowAll} />
      {candidates.length === 0 ? (
        <p className="my-1.5 text-subtle-foreground">次に検討する項目はありません。</p>
      ) : (
        <ol ref={listRef} className="m-0 mt-3.5 list-none p-0">
          {candidates.map((candidate, position) => (
            <li key={candidate.id} className="border-t border-border-soft first:border-t-0">
              <button
                type="button"
                data-id={candidate.id}
                onClick={() => {
                  onOpen(candidate.id);
                }}
                className="group grid w-full cursor-pointer grid-cols-next gap-x-0 gap-y-0.5 border-0 bg-transparent py-3.5 text-left"
              >
                <span aria-hidden="true" className="mono row-span-2 text-rank leading-tight font-semibold text-mark">
                  {position + 1}
                </span>
                <span className="text-next leading-snug font-bold tracking-tight group-hover:text-mark max-md:text-next-narrow">
                  {candidate.title}
                </span>
                <span aria-hidden="true" className="col-start-3 row-span-2 row-start-1 self-center text-subtle-foreground group-hover:text-mark">
                  <Icon name="chev" />
                </span>
                <span className="col-start-2 flex flex-wrap items-center gap-x-3 text-small text-muted-foreground">
                  <span>{[itemOf(candidate.id)?.category, candidate.phase].filter(Boolean).join(" · ")}</span>
                  <ImpactBadge weight={candidate.weight} />
                  <span title="後続の件数" className="mono inline-flex items-center gap-1">
                    <Icon name="follow" className="size-3.5" />
                    {candidate.followers}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
};
