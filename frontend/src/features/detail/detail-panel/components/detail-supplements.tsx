// 詳細の本文と、参照・関連・経緯の欄（補足）の見分け方。モック作成で案を見比べるため、見分け方を引数で選ぶ
import { useState, type ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

/** 見分け方。`tabs` は本文と補足をタブで切り替え、`collapse` は補足を折りたたみ、`tint` は補足の欄の背景の色を変える */
export type SupplementLayout = "tabs" | "collapse" | "tint";

/** 補足の欄の見出し */
const SUPPLEMENT_LABEL = "参照・関連・経緯";

export type DetailSupplementsProps = {
  layout: SupplementLayout | undefined;
  /** 本文（状態・タイトルから本文まで） */
  main: ReactNode;
  /** 補足（参照・関連・経緯・リンク） */
  supplements: ReactNode;
};

export const DetailSupplements = ({ layout, main, supplements }: DetailSupplementsProps) => {
  const [tab, setTab] = useState<"main" | "supplements">("main");
  if (layout === undefined) {
    return (
      <>
        {main}
        {supplements}
      </>
    );
  }
  if (layout === "tabs") {
    const tabClass = (selected: boolean): string =>
      cn("h-8 cursor-pointer rounded-control px-3 text-small focus-visible:outline-2 focus-visible:outline-ring", selected ? "bg-mark text-on-mark" : "hover:bg-accent");
    return (
      <>
        <div role="tablist" aria-label="詳細の表示" className="flex gap-1 border-b border-border-soft pb-2">
          <button type="button" role="tab" aria-selected={tab === "main"} className={tabClass(tab === "main")} onClick={() => { setTab("main"); }}>
            本文
          </button>
          <button type="button" role="tab" aria-selected={tab === "supplements"} className={tabClass(tab === "supplements")} onClick={() => { setTab("supplements"); }}>
            {SUPPLEMENT_LABEL}
          </button>
        </div>
        <div role="tabpanel" className="flex flex-col gap-3">
          {tab === "main" ? main : supplements}
        </div>
      </>
    );
  }
  if (layout === "collapse") {
    return (
      <>
        {main}
        <details className="group rounded-card border border-border-soft">
          <summary className="cursor-pointer px-3 py-2 text-small font-medium text-muted-foreground hover:bg-row-hover">{SUPPLEMENT_LABEL}</summary>
          <div className="flex flex-col gap-3 border-t border-border-soft p-3">{supplements}</div>
        </details>
      </>
    );
  }
  return (
    <>
      {main}
      <aside aria-label={SUPPLEMENT_LABEL} className="flex flex-col gap-3 rounded-card bg-muted p-3">
        <p className="m-0 text-xs font-medium text-muted-foreground">{SUPPLEMENT_LABEL}</p>
        {supplements}
      </aside>
    </>
  );
};
