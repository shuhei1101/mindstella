// トップバー（部品設計『トップバー.tsx』）。題名・接続の状態・検索の入口・変更履歴・ライト / ダーク・表示の設定・絞り込み・保存待ち・コメントのボタンと、画面を移るタブの帯を出す
import type { MouseEvent } from "react";

import { Icon, type IconName } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/cn";
import type { Connection } from "@/shared/stores/connection-store";
import type { Theme } from "@/shared/stores/theme-store";

/** タブの帯の画面の識別子（URL の search params の `tab` と同じ値） */
export type TabKey = "overview" | "decisions" | "tasks" | "research" | "docs" | "terms" | "notes" | "logs";

/** 開いている画面（ネットワークを含む） */
export type TopbarCurrent = TabKey | "graph";

/** タブの帯に並べる 1 つの画面 */
export type TopbarTab = {
  key: TabKey;
  label: string;
  icon: IconName;
  /** その種類の項目の件数（概要は持たない） */
  count?: number;
  /** 差分の表示の間、その種類に新規・変更・消した項目があるか */
  marked?: boolean;
};

/** 変更履歴で選んだ時点 */
export type DiffPoint = { name: string; sub: string };

export type TopbarProps = {
  title: string;
  tabs: TopbarTab[];
  current: TopbarCurrent;
  theme: Theme;
  connection?: Connection;
  /** 描いている記録を読んだ日時（`built_at`） */
  readAt?: string | null;
  diffPoint?: DiffPoint | null;
  comments?: boolean;
  commentCount?: number;
  commentsOpen?: boolean;
  commentsUnread?: boolean;
  settingsOpen?: boolean;
  filter?: boolean;
  filterCount?: number;
  filterOpen?: boolean;
  pending?: boolean;
  pendingCount?: number;
  pendingOpen?: boolean;
  pendingBlocked?: boolean;
  onNavigate?: (key: TopbarCurrent) => void;
  onOpenSearch?: () => void;
  onThemeChange?: (theme: Theme) => void;
  /** 渡さないと「変更履歴」を出さない */
  onOpenHistory?: () => void;
  onClearDiff?: () => void;
  onToggleComments?: () => void;
  /** 渡さないと表示の設定のボタンを出さない */
  onToggleSettings?: () => void;
  onToggleFilter?: () => void;
  onTogglePending?: () => void;
};

/** 件数の表示を揺らさない上限 */
const COUNT_CAP = 99;

/** 絞り込みのバッジが 2 桁に広がる条件の数 */
const FILTER_BADGE_WIDE_FROM = 10;

/** 件数の札の文字（99 を超えたら `99+`） */
const capped = (count: number): string => (count > COUNT_CAP ? `${String(COUNT_CAP)}+` : String(count));

/** UTC の ISO 8601 を JST の `MM/DD HH:mm` にする */
const formatJst = (iso: string): string => {
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const part = (type: Intl.DateTimeFormatPartTypes): string => parts.find((entry) => entry.type === type)?.value ?? "";
  return `${part("month")}/${part("day")} ${part("hour")}:${part("minute")}`;
};

/** 検索のキーの案内（macOS は ⌘K） */
const searchKey = (): string => (/Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘K" : "Ctrl+K");

/** 幅で詰め方を切り替える条件（今の画面の style.css の `:has()` の条件と同じ） */
type Fit = {
  offline: boolean;
  diff: boolean;
  /** 件数の札が幅の広い中身（絞り込みのバッジ 2 桁・`99+`）を持つ */
  wide: boolean;
  pending: boolean;
};

/** 表示の設定・絞り込み・保存待ち・コメントのボタンに共通のクラス */
const panelButtonClass = (fit: Fit, open: boolean): string =>
  cn(
    "h-8 min-w-6 flex-none border border-topbar-line bg-transparent px-2.5 font-normal text-topbar-fg",
    "hover:bg-topbar-hover hover:text-topbar-fg focus-visible:outline-mark-line",
    "max-xl:px-2",
    fit.offline && "max-2xl:px-2",
    "max-sm:gap-1 max-sm:px-1.5",
    fit.wide && (fit.diff || fit.offline) && "max-sm:gap-0.5 max-sm:px-0.5",
    "max-xs:gap-0.5 max-xs:px-0.5",
    open && "border-topbar-fg-2 bg-topbar-hover",
  );

/** ボタンの文字（幅 1100px 以下と、つながらない間の 1440px 以下は隠す） */
const panelLabelClass = (fit: Fit): string => cn("max-xl:hidden", fit.offline && "max-2xl:hidden");

/** 印だけのボタン（検索・変更履歴・ライト / ダーク）の狭い幅の詰め方 */
const iconButtonFitClass = (fit: Fit): string =>
  cn(
    fit.wide && (fit.diff || fit.offline) && "max-sm:w-7 max-sm:flex-none",
    "max-xs:w-7 max-xs:flex-none",
    fit.offline && fit.diff && "max-xs:w-6.5",
  );

/** 画面を移るリンク。押したときは使う側が移る */
const TabLink = ({
  tab,
  current,
  onNavigate,
  special = false,
}: {
  tab: { key: TopbarCurrent; label: string; icon: IconName; count?: number | undefined; marked?: boolean | undefined };
  current: TopbarCurrent;
  onNavigate: ((key: TopbarCurrent) => void) | undefined;
  special?: boolean;
}) => {
  const selected = tab.key === current;
  const handleClick = (event: MouseEvent<HTMLAnchorElement>): void => {
    event.preventDefault();
    onNavigate?.(tab.key);
  };
  return (
    <a
      href={tab.key === "overview" ? "./" : `?tab=${tab.key}`}
      data-tab={tab.key}
      aria-current={selected ? "page" : undefined}
      onClick={handleClick}
      className={cn(
        "relative flex h-11 items-center gap-2 border-b-2 border-transparent px-2.5 whitespace-nowrap text-muted-foreground no-underline hover:text-foreground",
        selected && "border-mark font-semibold text-foreground",
        special && "my-1.5 h-8 gap-1.5 rounded-control border border-border px-3.5",
        special && selected && "border-mark bg-mark-weak",
      )}
    >
      <Icon name={tab.icon} className={cn(special && "text-mark")} />
      {tab.label}
      {tab.count === undefined ? null : <span className="mono text-tab-count font-normal text-subtle-foreground">{tab.count}</span>}
      {tab.marked === true ? (
        <span className="absolute top-2.75 left-5.5 size-2 rounded-full bg-diff-changed ring-2 ring-card">
          <span className="sr-only">新規・変更・消した項目があります</span>
        </span>
      ) : null}
    </a>
  );
};

/** サーバーにつながらないときの表示。広い幅は読んだ日時つき、狭い幅は短い文言（日時は `title`） */
const ConnectionNotice = ({ readAt }: { readAt: string | null }) => {
  const readAtText = readAt === null ? null : formatJst(readAt);
  return (
    <span
      role="status"
      title={readAtText === null ? "サーバーにつながりません" : `${readAtText} に読んだ記録を出しています`}
      className="inline-flex flex-none items-center gap-1.5 text-small whitespace-nowrap text-topbar-fg"
    >
      <Icon name="offline" className="text-topbar-danger max-2xs:size-4.5" />
      <span className="max-2xl:hidden">
        {readAtText === null ? "サーバーにつながりません" : `サーバーにつながりません（${readAtText} に読んだ記録）`}
      </span>
      <span className="hidden max-2xl:inline max-lg:sr-only">つながりません</span>
    </span>
  );
};

/** 選んだ時点の札と、差分の表示をやめる × */
const DiffChip = ({ point, fit, onClear }: { point: DiffPoint; fit: Fit; onClear: (() => void) | undefined }) => (
  <span
    className={cn(
      "chip-width inline-flex h-8 items-center gap-0.5 rounded-control bg-topbar-fg pr-0.5 pl-2.5 text-small font-semibold text-topbar-bg",
      "max-xl:chip-width-narrow",
      fit.offline && "max-2xl:chip-width-narrow",
    )}
  >
    <span className="truncate" title={`${point.name}（${point.sub}）`}>
      <span className="sr-only">差分の時点: </span>
      {point.name}
    </span>
    <button
      type="button"
      aria-label="差分の表示をやめる"
      title="差分の表示をやめる"
      onClick={onClear}
      className="grid size-7 flex-none cursor-pointer place-items-center rounded-control hover:bg-topbar-chip-hover"
    >
      <Icon name="x" />
    </button>
  </span>
);

export const Topbar = ({
  title,
  tabs,
  current,
  theme,
  connection = "online",
  readAt = null,
  diffPoint = null,
  comments = false,
  commentCount = 0,
  commentsOpen = false,
  commentsUnread = false,
  settingsOpen = false,
  filter = false,
  filterCount = 0,
  filterOpen = false,
  pending = false,
  pendingCount = 0,
  pendingOpen = false,
  pendingBlocked = false,
  onNavigate,
  onOpenSearch,
  onThemeChange,
  onOpenHistory,
  onClearDiff,
  onToggleComments,
  onToggleSettings,
  onToggleFilter,
  onTogglePending,
}: TopbarProps) => {
  const nextTheme: Theme = theme === "dark" ? "light" : "dark";
  const showPending = pending && pendingCount > 0;
  const fit: Fit = {
    offline: connection === "offline",
    diff: diffPoint !== null,
    wide:
      (filter && filterCount >= FILTER_BADGE_WIDE_FROM) ||
      (comments && commentCount > COUNT_CAP) ||
      (showPending && pendingCount > COUNT_CAP),
    pending: showPending,
  };
  // 差分の札を出している間（つながらない間は 1440px 以下、それ以外は 1100px 以下）は、ツール名の文字と空きを隠して札に幅を回す
  const diffSqueeze = cn(fit.diff && "max-xl:hidden", fit.offline && fit.diff && "max-2xl:hidden");
  return (
    <div>
      <header
        className={cn(
          "relative z-30 flex h-13 items-center gap-4 bg-topbar-bg px-5 text-topbar-fg",
          "sm:max-lg:gap-2",
          fit.diff && "max-xl:gap-2",
          fit.offline && fit.diff && "max-2xl:gap-2",
          fit.diff ? "max-sm:gap-2 max-sm:px-2.5" : "max-sm:gap-0.75 max-sm:px-2.5",
          fit.wide && (fit.diff || fit.offline) && "max-sm:gap-px max-sm:px-2",
          "max-xs:gap-px max-xs:px-2",
        )}
      >
        <span
          className={cn(
            "flex min-w-0 flex-none items-center gap-2.5",
            fit.offline && fit.diff && "max-sm:hidden",
            fit.wide && fit.diff && "max-sm:hidden",
            fit.diff && "max-xs:hidden",
          )}
        >
          <svg
            className="size-5.5 flex-none text-mark"
            viewBox="0 0 32 32"
            aria-hidden="true"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="8" cy="16" r="4" />
            <path d="M12 16h5M17 16V7h5M17 16v9h5" />
            <circle cx="25" cy="7" r="2.6" />
            <circle cx="25" cy="25" r="2.6" />
          </svg>
          <span
            className={cn(
              "font-bold tracking-tight",
              diffSqueeze,
              fit.wide && (fit.diff || fit.offline) && "max-sm:hidden",
              fit.pending && "max-sm:hidden",
              "max-xs:hidden",
            )}
          >
            mindstella
          </span>
        </span>
        <span title={title} className="min-w-0 shrink grow-0 basis-auto truncate text-small text-topbar-fg-2 max-lg:hidden">
          {title}
        </span>
        <span className={cn("flex-1", comments && "basis-0", diffSqueeze)} />
        {fit.offline ? <ConnectionNotice readAt={readAt} /> : null}
        <button
          type="button"
          aria-label="すべての項目を検索"
          aria-keyshortcuts="Control+K Meta+K"
          onClick={onOpenSearch}
          className={cn(
            "flex h-8 min-w-65 cursor-pointer items-center gap-2 rounded-control border border-topbar-line bg-transparent px-2.5 text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg",
            fit.diff && "max-xl:flex-none",
            fit.offline && "max-2xl:flex-none",
            "max-lg:w-8 max-lg:min-w-0 max-lg:justify-center max-lg:p-0",
            iconButtonFitClass(fit),
          )}
        >
          <Icon name="search" />
          <span className="max-lg:hidden">すべての項目を検索</span>
          <kbd className="ml-auto rounded-kbd border border-topbar-line px-1.25 font-mono text-count whitespace-nowrap max-lg:hidden">
            {searchKey()}
          </kbd>
        </button>
        {onOpenHistory === undefined ? null : (
          <button
            type="button"
            aria-haspopup="dialog"
            aria-label="変更履歴"
            onClick={onOpenHistory}
            className={cn(
              "inline-flex h-8 flex-none cursor-pointer items-center gap-1.5 rounded-control border border-topbar-line bg-transparent px-2.5 text-small whitespace-nowrap text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg",
              "max-xl:w-8 max-xl:justify-center max-xl:p-0",
              fit.offline && "max-2xl:w-8 max-2xl:justify-center max-2xl:p-0",
              iconButtonFitClass(fit),
            )}
          >
            <Icon name="history" />
            <span className={cn("max-xl:hidden", fit.offline && "max-2xl:hidden")}>変更履歴</span>
          </button>
        )}
        {diffPoint === null ? null : <DiffChip point={diffPoint} fit={fit} onClear={onClearDiff} />}
        {comments ? <span className={cn("flex-1 basis-0", diffSqueeze)} /> : null}
        {onToggleSettings === undefined ? null : (
          <Button
            variant="ghost"
            aria-label="表示の設定"
            aria-expanded={settingsOpen}
            onClick={onToggleSettings}
            className={cn(
              panelButtonClass(fit, settingsOpen),
              fit.diff && "max-xl:ml-auto max-xl:px-1",
              fit.offline && fit.diff && "max-2xl:ml-auto max-2xl:px-1",
              fit.diff && "max-sm:px-1",
              fit.wide && (fit.diff || fit.offline) && "max-sm:px-0.5",
              "max-xs:px-0.5",
            )}
          >
            <Icon name="sliders" />
            <span className={panelLabelClass(fit)}>表示の設定</span>
          </Button>
        )}
        {filter ? (
          <Button
            variant="ghost"
            aria-label={filterCount === 0 ? "絞り込み" : `絞り込み（${String(filterCount)} つの条件で絞り込み中）`}
            aria-expanded={filterOpen}
            onClick={onToggleFilter}
            className={panelButtonClass(fit, filterOpen)}
          >
            <Icon name="filter" />
            <span className={panelLabelClass(fit)}>絞り込み</span>
            {filterCount === 0 ? null : (
              <span
                aria-hidden="true"
                data-wide={filterCount >= FILTER_BADGE_WIDE_FROM ? "" : undefined}
                className="mono inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-mark px-1.25 text-count leading-none font-semibold text-on-mark"
              >
                {filterCount}
              </span>
            )}
          </Button>
        ) : null}
        {showPending ? (
          <Button
            variant="ghost"
            aria-label={`保存待ち（${String(pendingCount)} 件${pendingBlocked ? "・書き込めない編集あり" : ""}）`}
            aria-expanded={pendingOpen}
            onClick={onTogglePending}
            className={panelButtonClass(fit, pendingOpen)}
          >
            <span className={cn("inline-grid place-items-center", pendingBlocked && "text-topbar-danger")}>
              <Icon name={pendingBlocked ? "alert" : "layers"} />
            </span>
            <span className={panelLabelClass(fit)}>保存待ち</span>
            <span
              data-wide={pendingCount > COUNT_CAP ? "" : undefined}
              className={cn(
                "mono inline-grid h-4.5 min-w-4.5 place-items-center rounded-full px-1.25 text-count font-bold text-topbar-bg",
                pendingBlocked ? "bg-topbar-danger" : "bg-topbar-unread",
              )}
            >
              {capped(pendingCount)}
            </span>
          </Button>
        ) : null}
        {comments ? (
          <Button
            variant="ghost"
            aria-label={`コメント（${commentsUnread ? "未読あり・" : ""}レビュー中 ${String(commentCount)} 件）`}
            aria-expanded={commentsOpen}
            onClick={onToggleComments}
            className={cn("group", panelButtonClass(fit, commentsOpen))}
          >
            <span className="relative inline-grid place-items-center">
              <Icon name="comment" />
              {commentsUnread ? (
                <span
                  aria-hidden="true"
                  className={cn(
                    "absolute -top-0.75 -right-1 size-2.25 rounded-full bg-topbar-unread ring-2 ring-topbar-bg group-hover:ring-topbar-hover",
                    commentsOpen && "ring-topbar-hover",
                  )}
                />
              ) : null}
            </span>
            <span className={panelLabelClass(fit)}>コメント</span>
            <span
              data-wide={commentCount > COUNT_CAP ? "" : undefined}
              className={cn(
                "mono inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-topbar-fg px-1.25 text-count font-semibold text-topbar-bg",
                commentCount === 0 && "bg-transparent text-topbar-fg-2 ring-1 ring-topbar-line ring-inset",
              )}
            >
              {capped(commentCount)}
            </span>
          </Button>
        ) : null}
        <button
          type="button"
          data-theme={nextTheme}
          aria-label={theme === "dark" ? "ライトに切り替え" : "ダークに切り替え"}
          onClick={() => {
            onThemeChange?.(nextTheme);
          }}
          className={cn(
            "inline-grid size-8 cursor-pointer place-items-center rounded-control border-0 bg-transparent text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg",
            iconButtonFitClass(fit),
          )}
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} />
        </button>
      </header>
      <nav
        aria-label="項目の種類"
        className="no-scrollbar relative z-25 flex gap-1 overflow-x-auto border-b border-border bg-card px-5"
      >
        {tabs.map((tab) => (
          <TabLink key={tab.key} tab={tab} current={current} onNavigate={onNavigate} />
        ))}
        <span className="min-w-4 flex-1" />
        <TabLink tab={{ key: "graph", label: "ネットワーク", icon: "network" }} current={current} onNavigate={onNavigate} special />
      </nav>
    </div>
  );
};
