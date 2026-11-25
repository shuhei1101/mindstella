// 全体の検索（画面設計『全体の検索.tsx』）。ID・タイトル・本文で、全種類の項目を探すモーダル
import { RecordText } from "@/shared/components/record-text";
import type { LookupRecordId } from "@/shared/core/record-ids";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { Icon, StatusMark } from "@/shared/components/icon";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import { KIND_LABEL, searchItems, type Item, type RecordIndex, type SearchHit, type SearchTier } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** 段ごとの見出し */
const TIER_LABEL: Record<SearchTier, string> = { 1: "完全に一致", 2: "タイトルに一致", 3: "ほかの所に一致" };

/** 結果 1 件に添える、項目の要約 */
const summaryOf = (item: Item | undefined): string => item?.answer ?? item?.conclusion ?? item?.meaning ?? item?.content ?? item?.lead ?? "";

/** 開いている画面の絞り込みの条件の値 1 つ。検索の文字で始まる値を、結果の先頭に絞り込みの候補として出す */
export type FilterCandidate = { key: string; label: string; value: string; count: number };

/** 検索の文字と値の名前を、NFKC と大文字小文字をそろえて比べる文字列にする */
const normalize = (text: string): string => text.normalize("NFKC").toLowerCase().trim();

/** 値の名前が検索の文字で始まる候補だけを残す */
export const matchFilterCandidates = ({ query, candidates }: { query: string; candidates: readonly FilterCandidate[] }): FilterCandidate[] => {
  const word = normalize(query);
  if (word === "") return [];
  return candidates.filter((candidate) => normalize(candidate.value).startsWith(word));
};

export type SearchDialogProps = {
  index: RecordIndex;
  /** 結果のタイトルの中の ID から記録の項目・スレッドを検索する */
  lookup: LookupRecordId;
  query: string;
  onQueryChange: (query: string) => void;
  onOpen: (id: string) => void;
  onClose: () => void;
  /** 開いている画面の絞り込みの条件の値。絞り込みのドロワーを持たない画面では指定しない */
  filterCandidates?: readonly FilterCandidate[];
  /** 絞り込みの候補を押したときに、その条件の値をオンにする */
  onApplyFilter?: (key: string, value: string) => void;
};

export const SearchDialog = ({ index, lookup, query, onQueryChange, onOpen, onClose, filterCandidates = [], onApplyFilter }: SearchDialogProps) => {
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  // 開く前にフォーカスがあった要素を覚え、閉じたら戻す
  const [returnTo] = useState(() => document.activeElement);
  useEffect(
    () => () => {
      if (returnTo instanceof HTMLElement && returnTo.isConnected) returnTo.focus();
    },
    [returnTo],
  );
  // 検索の言葉は、ポータルの中に付いた時点でフォーカスを置く（画面設計の autofocus）
  const attachInput = (node: HTMLInputElement | null): void => {
    input.current = node;
    node?.focus();
  };
  const hits = searchItems({ query, index });
  const filters = onApplyFilter === undefined ? [] : matchFilterCandidates({ query, candidates: filterCandidates });
  const total = filters.length + hits.length;
  const position = Math.min(active, total - 1);
  const selectedFilter = position < filters.length ? filters[position] : undefined;
  const selected = position >= filters.length ? hits[position - filters.length] : undefined;
  const optionId = (hit: SearchHit): string => `search-hit-${hit.id}`;
  const filterOptionId = (candidate: FilterCandidate): string => `search-filter-${candidate.key}-${candidate.value}`;
  const applyFilter = (candidate: FilterCandidate): void => {
    onApplyFilter?.(candidate.key, candidate.value);
    onClose();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>): void => {
    // 開いている間の Ctrl+K（macOS は Cmd+K）は、言葉を選び直す
    if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
      event.preventDefault();
      event.currentTarget.select();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => Math.max(0, Math.min(total - 1, current + (event.key === "ArrowDown" ? 1 : -1))));
    } else if (event.key === "Enter" && selectedFilter !== undefined) {
      event.preventDefault();
      applyFilter(selectedFilter);
    } else if (event.key === "Enter" && selected !== undefined) {
      event.preventDefault();
      onOpen(selected.id);
    }
  };
  const tiers = ([1, 2, 3] as const).map((tier) => ({ tier, hits: hits.filter((hit) => hit.tier === tier) })).filter((group) => group.hits.length > 0);
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent initialFocus={input} className="top-16 flex translate-y-0 flex-col gap-3 p-3">
        <DialogTitle className="sr-only">すべての項目を検索</DialogTitle>
        <div className="flex items-center gap-2">
          <Icon name="search" className="text-muted-foreground" />
          <input
            ref={attachInput}
            type="text"
            aria-label="検索キーワード"
            placeholder="ID・タイトル・本文で検索"
            autoComplete="off"
            aria-controls="search-results"
            aria-activedescendant={selectedFilter !== undefined ? filterOptionId(selectedFilter) : selected === undefined ? undefined : optionId(selected)}
            className="h-8 min-w-0 flex-1 rounded-control border border-input bg-card px-2 text-small"
            value={query}
            onChange={(event) => {
              setActive(0);
              onQueryChange(event.target.value);
            }}
            onKeyDown={onKeyDown}
          />
          <button type="button" aria-label="検索を閉じる" className="flex-none cursor-pointer rounded-control p-1 hover:bg-muted" onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>
        <div id="search-results" role="listbox" aria-label="検索の結果" className="min-h-0 overflow-y-auto">
          {query.trim() === "" ? <p className="p-2 text-small text-muted-foreground">ID・タイトル・本文で、すべての項目を検索します。</p> : null}
          {filters.length === 0 ? null : (
            <div role="group" aria-label="絞り込みをオンにする">
              <div role="presentation" aria-hidden="true" className="px-2 pt-2 text-xs font-medium text-muted-foreground">
                絞り込みをオンにする
              </div>
              {filters.map((candidate) => (
                <div
                  key={`${candidate.key}:${candidate.value}`}
                  id={filterOptionId(candidate)}
                  role="option"
                  tabIndex={-1}
                  aria-selected={candidate === selectedFilter}
                  className={cn("flex cursor-pointer items-center gap-2 rounded-control px-2 py-1.5 text-small", candidate === selectedFilter ? "bg-row-selected" : "hover:bg-row-hover")}
                  onClick={() => {
                    applyFilter(candidate);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") applyFilter(candidate);
                  }}
                >
                  <Icon name="filter" className="flex-none text-mark" />
                  <span className="min-w-0 flex-1">
                    {candidate.label} = <span className="font-medium">{candidate.value}</span>
                  </span>
                  <span className="flex-none text-xs text-muted-foreground">
                    <span className="font-mono">{candidate.count}</span> 件
                  </span>
                </div>
              ))}
            </div>
          )}
          {query.trim() !== "" && total === 0 ? <p className="p-2 text-small text-muted-foreground">該当する項目はありません。別の条件を試してください。</p> : null}
          {tiers.map((group) => (
            <div key={group.tier} role="group" aria-label={TIER_LABEL[group.tier]}>
              <div role="presentation" aria-hidden="true" className="px-2 pt-2 text-xs font-medium text-muted-foreground">
                {TIER_LABEL[group.tier]}
              </div>
              {group.hits.map((hit) => {
                const item = index.byId.get(hit.id)?.item;
                return (
                  <div
                    key={hit.id}
                    id={optionId(hit)}
                    role="option"
                    tabIndex={-1}
                    aria-selected={hit === selected}
                    aria-describedby={`${optionId(hit)}-ids`}
                    className={cn("flex cursor-pointer gap-3 rounded-control px-2 py-1.5", hit === selected ? "bg-row-selected" : "hover:bg-row-hover")}
                    onClick={() => {
                      onOpen(hit.id);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") onOpen(hit.id);
                    }}
                  >
                    <span className="flex-none font-mono text-small whitespace-nowrap">{hit.id}</span>
                    <span className="min-w-0 text-small">
                      <span className="inline-flex items-center gap-1">
                        <StatusMark status={item?.status} />
                        <RecordText text={hit.title} mode="marker" lookup={lookup} descriptionId={`${optionId(hit)}-ids`} />
                        <span className="rounded-full bg-muted px-1.5 text-xs text-muted-foreground">{KIND_LABEL[hit.kind]}</span>
                      </span>
                      <br />
                      <span className="text-xs text-muted-foreground">{summaryOf(item)}</span>
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};
