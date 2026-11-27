// 詳細の中身を「本文」「関連」「コメント」のタブで切り替える（画面設計『詳細パネル』の要素「本文の切り替え」）
import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/shared/lib/cn";
import { SEGMENTED_GROUP_CLASS, SEGMENTED_ITEM_CLASS, SEGMENTED_SELECTED_CLASS } from "@/shared/lib/segmented";

/** 詳細のタブ */
export type DetailTab = "main" | "related" | "comments";

export type DetailSupplementsProps = {
  /** 選んでいるタブ */
  tab: DetailTab;
  onTabChange: (tab: DetailTab) => void;
  /** 本文（状態・タイトルから本文まで） */
  main: ReactNode;
  /** 関連（リンクと関係する項目） */
  supplements: ReactNode;
  /** レビュー中のコメント。null のときはタブを出さない */
  comments: ReactNode | null;
  /** その項目に向けたスレッドの件数。0 のときはバッジを描かない */
  commentCount?: number;
};

/** 件数のバッジの文字の上限（超えたら `99+`） */
const COUNT_CAP = 99;

export const DetailSupplements = ({ tab, onTabChange, main, supplements, comments, commentCount = 0 }: DetailSupplementsProps) => {
  const prefix = useId();
  const buttons = useRef(new Map<DetailTab, HTMLButtonElement>());
  const first = { key: "main" as const, label: "本文", content: main };
  const tabs: { key: DetailTab; label: string; content: ReactNode }[] = [
    first,
    { key: "related", label: "関連", content: supplements },
    ...(comments === null ? [] : [{ key: "comments" as const, label: "コメント", content: comments }]),
  ];
  const current = tabs.find((entry) => entry.key === tab) ?? first;
  const tabId = (key: DetailTab): string => `${prefix}-tab-${key}`;
  const panelId = `${prefix}-panel`;
  // 矢印・Home・End で選んだときは、選んだタブを描き直した後にフォーカスを移す
  const keyed = useRef(false);
  useEffect(() => {
    if (!keyed.current) return;
    keyed.current = false;
    buttons.current.get(current.key)?.focus();
  }, [current.key]);
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number): void => {
    const last = tabs.length - 1;
    const next = { ArrowRight: index === last ? 0 : index + 1, ArrowLeft: index === 0 ? last : index - 1, Home: 0, End: last }[event.key];
    const target = next === undefined ? undefined : tabs[next];
    if (target === undefined) return;
    event.preventDefault();
    keyed.current = true;
    onTabChange(target.key);
  };
  return (
    <>
      <div role="tablist" aria-label="詳細の表示" className={cn(SEGMENTED_GROUP_CLASS, "self-start")}>
        {tabs.map((entry, index) => {
          const selected = entry.key === current.key;
          const count = entry.key === "comments" ? commentCount : 0;
          return (
            <button
              key={entry.key}
              ref={(node) => {
                if (node === null) buttons.current.delete(entry.key);
                else buttons.current.set(entry.key, node);
              }}
              id={tabId(entry.key)}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={panelId}
              aria-label={count > 0 ? `${entry.label} ${String(count)} 件` : undefined}
              tabIndex={selected ? 0 : -1}
              className={cn(SEGMENTED_ITEM_CLASS, "h-6 min-w-20 px-3", selected && SEGMENTED_SELECTED_CLASS)}
              onClick={() => {
                onTabChange(entry.key);
              }}
              onKeyDown={(event) => {
                onKeyDown(event, index);
              }}
            >
              {entry.label}
              {count > 0 ? (
                <span aria-hidden="true" className="ml-1 inline-grid h-4 min-w-4 place-items-center rounded-full bg-mark px-1 font-mono text-count leading-none text-on-mark">
                  {count > COUNT_CAP ? `${String(COUNT_CAP)}+` : count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={panelId} aria-labelledby={tabId(current.key)} className="flex flex-col gap-3">
        {current.content}
      </div>
    </>
  );
};
