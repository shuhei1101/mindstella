// 全体の検索（画面設計『全体の検索.tsx』）。ID・タイトル・本文で、全種類の項目を探すモーダル
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { Icon, StatusMark } from "@/shared/components/icon";
import { Dialog, DialogContent, DialogTitle } from "@/shared/components/ui/dialog";
import { KIND_LABEL, searchItems, type Item, type RecordIndex, type SearchHit, type SearchTier } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

/** 段ごとの見出し */
const TIER_LABEL: Record<SearchTier, string> = { 1: "完全に一致", 2: "タイトルに一致", 3: "ほかの所に一致" };

/** 結果 1 件に添える、項目の要約 */
const summaryOf = (item: Item | undefined): string => item?.answer ?? item?.conclusion ?? item?.meaning ?? item?.content ?? item?.lead ?? "";

export type SearchDialogProps = {
  index: RecordIndex;
  query: string;
  onQueryChange: (query: string) => void;
  onOpen: (id: string) => void;
  onClose: () => void;
};

export const SearchDialog = ({ index, query, onQueryChange, onOpen, onClose }: SearchDialogProps) => {
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const returnTo = useRef<Element | null>(null);
  // 開く前にフォーカスがあった要素を覚え、閉じたら戻す
  useEffect(() => {
    returnTo.current = document.activeElement;
    return () => {
      if (returnTo.current instanceof HTMLElement && returnTo.current.isConnected) returnTo.current.focus();
    };
  }, []);
  const hits = searchItems({ query, index });
  const selected = hits[Math.min(active, hits.length - 1)];
  const optionId = (hit: SearchHit): string => `search-hit-${hit.id}`;
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>): void => {
    // 開いている間の Ctrl+K（macOS は Cmd+K）は、言葉を選び直す
    if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
      event.preventDefault();
      event.currentTarget.select();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setActive((position) => Math.max(0, Math.min(hits.length - 1, position + (event.key === "ArrowDown" ? 1 : -1))));
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
          {/* eslint-disable-next-line jsx-a11y/no-autofocus -- 画面設計『全体の検索.tsx』の autofocus */}
          <input
            ref={input}
            autoFocus
            type="text"
            aria-label="検索キーワード"
            placeholder="ID・タイトル・本文で検索"
            autoComplete="off"
            aria-controls="search-results"
            aria-activedescendant={selected === undefined ? undefined : optionId(selected)}
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
          {query.trim() !== "" && hits.length === 0 ? <p className="p-2 text-small text-muted-foreground">該当する項目はありません。別の条件を試してください。</p> : null}
          {tiers.map((group) => (
            <div key={group.tier} role="group" aria-label={TIER_LABEL[group.tier]}>
              <h2 className="px-2 pt-2 text-xs font-medium text-muted-foreground">{TIER_LABEL[group.tier]}</h2>
              {group.hits.map((hit) => {
                const item = index.byId.get(hit.id)?.item;
                return (
                  <div
                    key={hit.id}
                    id={optionId(hit)}
                    role="option"
                    aria-selected={hit === selected}
                    className={cn("flex cursor-pointer gap-3 rounded-control px-2 py-1.5", hit === selected ? "bg-row-selected" : "hover:bg-row-hover")}
                    onClick={() => {
                      onOpen(hit.id);
                    }}
                  >
                    <span className="flex-none font-mono text-small whitespace-nowrap">{hit.id}</span>
                    <span className="min-w-0 text-small">
                      <span className="inline-flex items-center gap-1">
                        <StatusMark status={item?.status} />
                        {hit.title}
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
