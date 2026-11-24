// 本文の目次（部品設計『本文の目次.tsx』）。詳細のヘッダーのボタンで開き、本文の見出しを階層つきで並べて、押すとその見出しへ移る
import { useState } from "react";

import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Popover, PopoverContent, PopoverTitle, PopoverTrigger } from "@/shared/components/ui/popover";
import type { TocEntry } from "@/shared/core/body-toc";
import { cn } from "@/shared/lib/cn";

/** 階層ごとの字下げ。一番上の階層の見出しを字下げしない */
const INDENT: Record<number, string> = { 0: "pl-2", 1: "pl-5", 2: "pl-8", 3: "pl-11", 4: "pl-14", 5: "pl-17" };

export type BodyTocProps = {
  entries: readonly TocEntry[];
  /** 押した見出しを指す名前を通知する */
  onHeading: (slug: string) => void;
  /** 最初から開いた状態で出す（ストーリー用） */
  defaultOpen?: boolean;
};

export const BodyToc = ({ entries, onHeading, defaultOpen = false }: BodyTocProps) => {
  const [open, setOpen] = useState(defaultOpen);
  const top = Math.min(...entries.map((entry) => entry.level));
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant="ghost" size="icon" aria-label="本文の目次" title="本文の目次" />}>
        <Icon name="toc" />
      </PopoverTrigger>
      <PopoverContent className="max-h-96 w-72 overflow-y-auto">
        <PopoverTitle className="px-2 pb-1 text-xs font-medium text-muted-foreground">目次</PopoverTitle>
        <nav aria-label="本文の目次">
          <ul className="flex flex-col">
            {entries.map((entry) => (
              <li key={entry.slug}>
                <button
                  type="button"
                  className={cn("w-full cursor-pointer truncate rounded-control py-1 pr-2 text-left text-small hover:bg-row-hover focus-visible:outline-2 focus-visible:outline-ring", INDENT[entry.level - top])}
                  title={entry.text}
                  onClick={() => {
                    setOpen(false);
                    onHeading(entry.slug);
                  }}
                >
                  {entry.text}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </PopoverContent>
    </Popover>
  );
};
