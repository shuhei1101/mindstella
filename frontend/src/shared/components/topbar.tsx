// トップバー（部品設計『トップバー.tsx』）。題名・接続の状態・更新のボタン・検索の入口・変更履歴・ライト / ダーク・表示の設定・絞り込み・保存待ち・音声入力中の表示・コメントのボタンと、音声入力の知らせの帯・画面を移るタブの帯・重なった ID の通知を出す
import { type MouseEvent, useEffect, useState } from "react";

import { DuplicateIdNotice } from "@/shared/components/duplicate-id-notice";
import { Icon, type IconName } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { formatElapsed } from "@/shared/core/voice";
import { cn } from "@/shared/lib/cn";
import type { Connection } from "@/shared/stores/connection-store";
import type { Theme } from "@/shared/stores/theme-store";

/** タブの帯の画面の識別子（URL の search params の `tab` と同じ値） */
export type TabKey = "overview" | "decisions" | "tasks" | "research" | "docs" | "terms" | "notes" | "logs";

/** 開いている画面（ワークスペースの設定を含む） */
export type TopbarCurrent = TabKey | "settings";

/** タブの帯に並べる 1 つの画面 */
export type TopbarTab = {
  key: TabKey;
  label: string;
  icon: IconName;
  /** その種類の項目の件数（概要は持たない） */
  count?: number;
  /** 差分の表示の間、その種類に新規・変更・削除した項目があるか */
  marked?: boolean;
};

/** 音声入力中の入力欄 */
export type TopbarVoice = { state: "recording" | "transcribing"; label: string; elapsed: number };

/** トップバーの下の音声入力の知らせ */
export type TopbarVoiceNotice = { kind: "discarded" | "failed"; text: string };

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
  /** 書き換えの通知の反映を保留しているか（更新のボタンに点を出す） */
  stale?: boolean;
  /** 接続し直して読み込み直している間 */
  refreshing?: boolean;
  /** 渡さないと更新のボタンを出さない */
  onRefresh?: () => void;
  /** 渡さないと音声入力中の表示を出さない */
  voice?: TopbarVoice | null;
  /** 渡さないと知らせの帯を出さない */
  voiceNotice?: TopbarVoiceNotice | null;
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
  /** 音声入力中の表示と帯の「入力欄を開く」を押したとき */
  onOpenVoice?: () => void;
  onDismissVoiceNotice?: () => void;
  /** 重なった ID と種類の名前。空でなければ、タブの帯の下に重なった ID の通知を出す */
  duplicateIds?: { id: string; kind: string }[];
  onOpenDuplicate?: (id: string) => void;
  onCloseDuplicate?: () => void;
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

/**
 * ホバーと :focus-visible で出すツールチップ。読み上げは親の aria-label が持つ。
 * トップバーの左側の要素は `start`（左端に揃えて右へ伸ばす）、右側の要素は `end` にして画面の外へ出さない。
 * 上の余白（`pt-1.5`）でボタンとつなぎ、ポインタをツールチップへ動かしても消えない。Esc でトップバーの `data-tipsoff` が付くと隠す
 */
const Tip = ({ text, align = "end" }: { text: string; align?: "start" | "end" }) => (
  <span
    aria-hidden="true"
    className={cn(
      "absolute top-full z-40 hidden pt-1.5 group-hover/tip:block group-focus-visible/tip:block in-data-tipsoff:hidden!",
      align === "start" ? "left-0" : "right-0",
    )}
  >
    <span className="block w-max max-w-64 rounded-control bg-foreground px-2 py-1 text-small font-normal text-background">{text}</span>
  </span>
);

/** 幅で詰め方を切り替える条件 */
type Fit = {
  offline: boolean;
  diff: boolean;
  /** 件数の札が幅の広い中身（絞り込みのバッジ 2 桁・`99+`）を持つ */
  wide: boolean;
  pending: boolean;
  /** 更新のボタン・接続の状態・更新があります・音声入力中・差分の表示のどれかを出していて、狭い幅で詰める */
  crowded: boolean;
};

/** 表示の設定・絞り込み・保存待ち・コメントのボタンに共通のクラス */
const panelButtonClass = (fit: Fit, open: boolean): string =>
  cn(
    "group/tip relative h-8 min-w-6 flex-none border border-topbar-line bg-transparent px-2.5 font-normal text-topbar-fg",
    "hover:bg-topbar-hover hover:text-topbar-fg focus-visible:outline-mark-line",
    "max-xl:px-2",
    fit.offline && "max-2xl:px-2",
    "max-sm:gap-1 max-sm:px-1.5",
    fit.wide && (fit.diff || fit.offline) && "max-sm:gap-0.5 max-sm:px-0.5",
    "max-xs:gap-0.5 max-xs:px-0.5",
    fit.crowded && "max-sm:w-7 max-sm:justify-center max-sm:gap-0 max-sm:px-0 max-xs:w-6",
    open && "border-topbar-fg-2 bg-topbar-hover",
  );

/** 詰める幅（481px 未満）で、件数の札をアイコンの右上に重ねる */
const badgeFitClass = (fit: Fit): string =>
  cn(fit.crowded && "max-sm:absolute max-sm:-top-1.5 max-sm:-right-1.5 max-sm:h-4 max-sm:min-w-4 max-sm:px-0.5 max-sm:ring-2 max-sm:ring-topbar-bg");

/** 印だけのボタン（検索・変更履歴・ライト / ダーク）の狭い幅の詰め方 */
const iconButtonFitClass = (fit: Fit): string =>
  cn(
    fit.wide && (fit.diff || fit.offline) && "max-sm:w-7 max-sm:flex-none",
    "max-xs:w-7 max-xs:flex-none",
    fit.offline && fit.diff && "max-xs:w-6.5",
    fit.crowded && "max-sm:w-7 max-sm:flex-none max-xs:w-6",
  );

/** 画面を移るリンク。押したときは使う側が移る */
const TabLink = ({
  tab,
  current,
  onNavigate,
}: {
  tab: { key: TopbarCurrent; label: string; icon: IconName; count?: number | undefined; marked?: boolean | undefined };
  current: TopbarCurrent;
  onNavigate: ((key: TopbarCurrent) => void) | undefined;
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
      )}
    >
      <Icon name={tab.icon} />
      {tab.label}
      {tab.count === undefined ? null : <span className="mono text-tab-count font-normal text-subtle-foreground">{tab.count}</span>}
      {tab.marked === true ? (
        <span className="absolute top-2.75 left-5.5 size-2 rounded-full bg-diff-changed ring-2 ring-card">
          <span className="sr-only">新規・変更・削除した項目があります</span>
        </span>
      ) : null}
    </a>
  );
};

/** サーバーにつながらないときの表示。どの幅でも印だけを出し、状態と読んだ日時は読み上げとツールチップに持つ */
const ConnectionNotice = ({ fit, readAt }: { fit: Fit; readAt: string | null }) => {
  const readAtText = readAt === null ? null : formatJst(readAt);
  const text = readAtText === null ? "サーバーにつながりません" : `サーバーにつながりません（${readAtText} に読んだ記録）`;
  return (
    <span
      role="status"
      // 押せない表示だが、キーボードでもツールチップの状態と読んだ日時を確かめられるようにフォーカスを受ける
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- 状態の表示をツールチップで読むため
      tabIndex={0}
      className={cn("group/tip relative inline-grid size-8 flex-none place-items-center rounded-control text-topbar-fg focus-visible:outline-2 focus-visible:outline-mark-line", iconButtonFitClass(fit))}
    >
      <Icon name="offline" className="text-topbar-danger max-2xs:size-4.5" />
      <span className="sr-only">{text}</span>
      <Tip text={text} align="start" />
    </span>
  );
};

/** 更新のボタン。押すと書き換えの通知へ接続し直して記録を読み込み直す。反映を保留している間は点を出す */
const RefreshButton = ({ fit, stale, refreshing, onClick }: { fit: Fit; stale: boolean; refreshing: boolean; onClick: () => void }) => {
  const text = stale ? "更新があります。最新の記録を読み込む" : "最新の記録を読み込む";
  return (
    <button
      type="button"
      aria-label={text}
      aria-busy={refreshing}
      disabled={refreshing}
      onClick={onClick}
      className={cn(
        "group/tip relative inline-grid size-8 flex-none cursor-pointer place-items-center rounded-control border-0 bg-transparent text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg disabled:cursor-default",
        iconButtonFitClass(fit),
      )}
    >
      <Icon name={refreshing ? "spin" : "refresh"} className={cn(refreshing && "animate-spin")} />
      {stale ? <span aria-hidden="true" className="absolute top-1 right-1 size-2 rounded-full bg-topbar-unread ring-2 ring-topbar-bg" /> : null}
      <Tip text={text} align="start" />
    </button>
  );
};

/** トップバーの帯のクラス（幅ごとの要素の間隔と左右の余白） */
const headerClass = (fit: Fit): string =>
  cn(
    "relative z-30 flex h-13 items-center gap-4 bg-topbar-bg px-5 text-topbar-fg",
    "sm:max-lg:gap-2",
    fit.diff && "max-xl:gap-2",
    fit.offline && fit.diff && "max-2xl:gap-2",
    fit.diff ? "max-sm:gap-2 max-sm:px-2.5" : "max-sm:gap-0.75 max-sm:px-2.5",
    fit.wide && (fit.diff || fit.offline) && "max-sm:gap-px max-sm:px-2",
    "max-xs:gap-px max-xs:px-2",
    fit.crowded && "max-sm:gap-px max-sm:px-1.5",
  );

/** 差分の札を出している間（つながらない間は 1440px 以下、それ以外は 1100px 以下）に、札へ幅を回すため隠す */
const diffSqueezeClass = (fit: Fit): string => cn(fit.diff && "max-xl:hidden", fit.offline && fit.diff && "max-2xl:hidden");

/** ツール名の印と文字（押せない飾り） */
const Brand = ({ fit }: { fit: Fit }) => (
  <span
    className={cn(
      "flex min-w-0 flex-none items-center gap-2.5",
      fit.offline && fit.diff && "max-sm:hidden",
      fit.wide && fit.diff && "max-sm:hidden",
      fit.diff && "max-xs:hidden",
      fit.crowded && "max-sm:hidden",
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
        diffSqueezeClass(fit),
        fit.wide && (fit.diff || fit.offline) && "max-sm:hidden",
        fit.pending && "max-sm:hidden",
        "max-xs:hidden",
      )}
    >
      mindstella
    </span>
  </span>
);

/** 全体の検索の入口。虫眼鏡と、幅 901px 以上はキーの案内を出す */
const SearchButton = ({ fit, onClick }: { fit: Fit; onClick: (() => void) | undefined }) => (
  <button
    type="button"
    aria-label="すべての項目を検索"
    aria-keyshortcuts="Control+K Meta+K"
    onClick={onClick}
    className={cn(
      "group/tip relative flex h-8 flex-none cursor-pointer items-center gap-1.5 rounded-control border border-topbar-line bg-transparent pr-1.5 pl-2 text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg",
      "max-lg:w-8 max-lg:justify-center max-lg:p-0",
      iconButtonFitClass(fit),
    )}
  >
    <Icon name="search" />
    <kbd className="rounded-kbd border border-topbar-line px-1.25 font-mono text-count whitespace-nowrap max-lg:hidden">{searchKey()}</kbd>
    <Tip text="すべての項目を検索" align="start" />
  </button>
);

/** 「変更履歴」のボタン */
const HistoryButton = ({ fit, active, onClick }: { fit: Fit; active: boolean; onClick: () => void }) => (
  <button
    type="button"
    aria-haspopup="dialog"
    aria-label={active ? "変更履歴（過去の差分を表示中）" : "変更履歴"}
    onClick={onClick}
    className={cn(
      "group/tip relative inline-grid size-8 flex-none cursor-pointer place-items-center rounded-control border border-topbar-line bg-transparent text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg",
      active && "text-topbar-fg",
      iconButtonFitClass(fit),
    )}
  >
    <Icon name="history" />
    <Tip text={active ? "変更履歴（過去の差分を表示中）" : "変更履歴"} align="start" />
    {active ? <span aria-hidden="true" className="absolute -top-1 -right-1 size-2.5 rounded-full bg-diff-changed ring-2 ring-topbar-bg" /> : null}
  </button>
);

/** 差分の表示をやめる × */
const ClearDiffButton = ({ fit, onClick }: { fit: Fit; onClick: (() => void) | undefined }) => (
  <button
    type="button"
    aria-label="差分の表示をやめる"
    onClick={onClick}
    className={cn("group/tip relative grid size-8 flex-none cursor-pointer place-items-center rounded-control text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg", iconButtonFitClass(fit))}
  >
    <Icon name="x" />
    <Tip text="差分の表示をやめる" align="start" />
  </button>
);

/** 表示の設定のボタン */
const SettingsButton = ({ fit, open, onClick }: { fit: Fit; open: boolean; onClick: () => void }) => (
  <Button
    variant="ghost"
    aria-label="表示の設定"
    aria-expanded={open}
    onClick={onClick}
    className={cn(
      panelButtonClass(fit, open),
      fit.diff && "max-xl:ml-auto max-xl:px-1",
      fit.offline && fit.diff && "max-2xl:ml-auto max-2xl:px-1",
      fit.diff && "max-sm:px-1",
      fit.wide && (fit.diff || fit.offline) && "max-sm:px-0.5",
      "max-xs:px-0.5",
    )}
  >
    <Icon name="sliders" />
    <Tip text="表示の設定" />
  </Button>
);

/** 絞り込みのボタンと、値を選んでいる条件の数のバッジ */
const FilterButton = ({ fit, count, open, onClick }: { fit: Fit; count: number; open: boolean; onClick: (() => void) | undefined }) => (
  <Button
    variant="ghost"
    aria-label={count === 0 ? "絞り込み" : `絞り込み（${String(count)} つの条件で絞り込み中）`}
    aria-expanded={open}
    onClick={onClick}
    className={panelButtonClass(fit, open)}
  >
    <Icon name="filter" />
    <Tip text={count === 0 ? "絞り込み" : `絞り込み（${String(count)} つの条件）`} />
    {count === 0 ? null : (
      <span
        aria-hidden="true"
        data-wide={count >= FILTER_BADGE_WIDE_FROM ? "" : undefined}
        className={cn("inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-mark px-1.25 mono text-count leading-none font-semibold text-on-mark", badgeFitClass(fit))}
      >
        {count}
      </span>
    )}
  </Button>
);

/** 保存待ちのボタン（重ねた紙の印・「保存待ち」・件数） */
const PendingButton = ({
  fit,
  count,
  open,
  blocked,
  onClick,
}: {
  fit: Fit;
  count: number;
  open: boolean;
  blocked: boolean;
  onClick: (() => void) | undefined;
}) => (
  <Button
    variant="ghost"
    aria-label={`保存待ち（${String(count)} 件${blocked ? "・書き込めない編集あり" : ""}）`}
    aria-expanded={open}
    onClick={onClick}
    className={panelButtonClass(fit, open)}
  >
    <span className={cn("inline-grid place-items-center", blocked && "text-topbar-danger")}>
      <Icon name={blocked ? "alert" : "layers"} />
    </span>
    <Tip text={blocked ? "保存待ち（書き込めない編集あり）" : "保存待ち"} />
    <span
      data-wide={count > COUNT_CAP ? "" : undefined}
      className={cn(
        "inline-grid h-4.5 min-w-4.5 place-items-center rounded-full px-1.25 mono text-count font-bold text-topbar-bg",
        blocked ? "bg-topbar-danger" : "bg-topbar-unread",
        badgeFitClass(fit),
      )}
    >
      {capped(count)}
    </span>
  </Button>
);

/** コメントのボタン（吹き出しの印と未読の点・「コメント」・件数） */
const CommentsButton = ({
  fit,
  count,
  open,
  unread,
  onClick,
}: {
  fit: Fit;
  count: number;
  open: boolean;
  unread: boolean;
  onClick: (() => void) | undefined;
}) => (
  <Button
    variant="ghost"
    aria-label={`コメント（${unread ? "未読あり・" : ""}レビュー中 ${String(count)} 件）`}
    aria-expanded={open}
    onClick={onClick}
    className={cn("group", panelButtonClass(fit, open))}
  >
    <span className="relative inline-grid place-items-center">
      <Icon name="comment" />
      {unread ? (
        <span
          aria-hidden="true"
          className={cn(
            "absolute -top-0.75 -right-1 size-2.25 rounded-full bg-topbar-unread ring-2 ring-topbar-bg group-hover:ring-topbar-hover",
            open && "ring-topbar-hover",
          )}
        />
      ) : null}
    </span>
    <Tip text={unread ? "コメント（未読あり）" : "コメント"} />
    <span
      data-wide={count > COUNT_CAP ? "" : undefined}
      className={cn(
        "inline-grid h-4.5 min-w-4.5 place-items-center rounded-full bg-topbar-fg px-1.25 mono text-count font-semibold text-topbar-bg",
        count === 0 && "bg-transparent text-topbar-fg-2 ring-1 ring-topbar-line ring-inset",
        badgeFitClass(fit),
      )}
    >
      {capped(count)}
    </span>
  </Button>
);

/** 音声入力中の表示（コメントのボタンの左隣）。押すと録音中の入力欄へ移る */
const VoiceButton = ({ voice, onClick }: { voice: TopbarVoice; onClick: (() => void) | undefined }) => {
  const recording = voice.state === "recording";
  return (
    <button
      type="button"
      aria-label={recording ? `音声入力中（${voice.label}）。録音中の入力欄へ移動` : `文字起こし中（${voice.label}）。入力欄へ移動`}
      onClick={onClick}
      className={cn(
        "group/tip relative inline-flex h-8 min-w-8 flex-none cursor-pointer items-center justify-center gap-1.5 rounded-control border bg-transparent px-2.5 text-small whitespace-nowrap text-topbar-fg hover:bg-topbar-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mark-line",
        recording ? "border-topbar-danger" : "border-topbar-line",
        "max-xl:px-2 max-sm:gap-0 max-sm:px-0.5",
      )}
    >
      {recording ? <Icon name="mic" className="text-topbar-danger" /> : <Icon name="spin" className="size-3 animate-spin" />}
      {recording ? (
        <span aria-hidden="true" className="font-mono text-count text-topbar-fg-2 tabular-nums max-sm:hidden">
          {formatElapsed(voice.elapsed)}
        </span>
      ) : null}
      <Tip text={recording ? `音声入力中（${voice.label}）` : `文字起こし中（${voice.label}）`} />
    </button>
  );
};

/** トップバーの下の音声入力の知らせの帯。× か「入力欄を開く」を押すまで残す */
const VoiceNoticeBand = ({ notice, onOpen, onDismiss }: { notice: TopbarVoiceNotice; onOpen: (() => void) | undefined; onDismiss: (() => void) | undefined }) => (
  <div className="flex items-center gap-2 border-b border-border bg-muted py-1 pr-1 pl-5 text-small text-foreground max-sm:pl-2.5">
    <Icon name="alert" className="flex-none text-st-review" />
    <span role="status" className="min-w-0 flex-1 wrap-anywhere">
      {notice.text}
    </span>
    {notice.kind === "failed" ? (
      <Button variant="outline" className="flex-none" onClick={onOpen}>
        入力欄を開く
      </Button>
    ) : null}
    <Button variant="ghost" size="icon" className="flex-none" aria-label="閉じる" title="閉じる" onClick={onDismiss}>
      <Icon name="x" />
    </Button>
  </div>
);

/** ライト / ダークの切り替え */
const ThemeButton = ({ fit, theme, onChange }: { fit: Fit; theme: Theme; onChange: ((theme: Theme) => void) | undefined }) => {
  const nextTheme: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      data-theme={nextTheme}
      aria-label={theme === "dark" ? "ライトに切り替え" : "ダークに切り替え"}
      onClick={() => {
        onChange?.(nextTheme);
      }}
      className={cn(
        "group/tip relative inline-grid size-8 flex-none cursor-pointer place-items-center rounded-control border-0 bg-transparent text-topbar-fg-2 hover:bg-topbar-hover hover:text-topbar-fg",
        iconButtonFitClass(fit),
      )}
    >
      <Icon name={theme === "dark" ? "sun" : "moon"} />
      <Tip text={theme === "dark" ? "ライトに切り替え" : "ダークに切り替え"} />
    </button>
  );
};

/** 画面を移るタブの帯 */
const TabBar = ({ tabs, current, onNavigate }: { tabs: TopbarTab[]; current: TopbarCurrent; onNavigate: ((key: TopbarCurrent) => void) | undefined }) => (
  <nav aria-label="項目の種類" className="relative z-25 no-scrollbar flex gap-1 overflow-x-auto border-b border-border bg-card px-5">
    {tabs.map((tab) => (
      <TabLink key={tab.key} tab={tab} current={current} onNavigate={onNavigate} />
    ))}
  </nav>
);

/** 幅で詰め方を切り替える条件を引数から求める */
const fitOf = (props: TopbarProps): Fit => {
  const { connection = "online", diffPoint = null, comments = false, commentCount = 0, filter = false, filterCount = 0, pending = false, pendingCount = 0 } = props;
  const showPending = pending && pendingCount > 0;
  return {
    offline: connection === "offline",
    diff: diffPoint !== null,
    wide: (filter && filterCount >= FILTER_BADGE_WIDE_FROM) || (comments && commentCount > COUNT_CAP) || (showPending && pendingCount > COUNT_CAP),
    pending: showPending,
    crowded: props.onRefresh !== undefined || connection === "offline" || diffPoint !== null || (props.voice ?? null) !== null || props.stale === true,
  };
};

export const Topbar = (props: TopbarProps) => {
  const {
    title,
    tabs,
    current,
    theme,
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
    pendingCount = 0,
    pendingOpen = false,
    pendingBlocked = false,
    voice = null,
    voiceNotice = null,
    stale = false,
    refreshing = false,
    onRefresh,
    duplicateIds = [],
    onOpenHistory,
    onToggleSettings,
  } = props;
  const fit = fitOf(props);
  // Esc でツールチップを隠し、ポインタが別の要素へ移るかフォーカスが動いたら戻す（WCAG 1.4.13 の Dismissible）
  const [tipsOff, setTipsOff] = useState(false);
  useEffect(() => {
    const hide = (event: globalThis.KeyboardEvent): void => {
      if (event.key === "Escape") setTipsOff(true);
    };
    const show = (): void => {
      setTipsOff(false);
    };
    document.addEventListener("keydown", hide);
    document.addEventListener("pointerover", show);
    document.addEventListener("focusin", show);
    return () => {
      document.removeEventListener("keydown", hide);
      document.removeEventListener("pointerover", show);
      document.removeEventListener("focusin", show);
    };
  }, []);
  return (
    <div>
      <header className={headerClass(fit)} data-tipsoff={tipsOff ? "" : undefined}>
        <Brand fit={fit} />
        <span title={title} className="min-w-0 shrink grow-0 basis-auto truncate text-small text-topbar-fg-2 max-lg:hidden">
          {title}
        </span>
        <span className={cn("flex-1", comments && "basis-0", diffSqueezeClass(fit))} />
        {fit.offline ? <ConnectionNotice fit={fit} readAt={readAt} /> : null}
        {onRefresh === undefined ? null : <RefreshButton fit={fit} stale={stale} refreshing={refreshing} onClick={onRefresh} />}
        <SearchButton fit={fit} onClick={props.onOpenSearch} />
        {onOpenHistory === undefined ? null : <HistoryButton fit={fit} active={diffPoint !== null} onClick={onOpenHistory} />}
        {diffPoint === null ? null : <ClearDiffButton fit={fit} onClick={props.onClearDiff} />}
        {comments ? <span className={cn("flex-1 basis-0", diffSqueezeClass(fit))} /> : null}
        {onToggleSettings === undefined ? null : <SettingsButton fit={fit} open={settingsOpen} onClick={onToggleSettings} />}
        {filter ? <FilterButton fit={fit} count={filterCount} open={filterOpen} onClick={props.onToggleFilter} /> : null}
        {fit.pending ? (
          <PendingButton fit={fit} count={pendingCount} open={pendingOpen} blocked={pendingBlocked} onClick={props.onTogglePending} />
        ) : null}
        {voice === null ? null : <VoiceButton voice={voice} onClick={props.onOpenVoice} />}
        {comments ? (
          <CommentsButton fit={fit} count={commentCount} open={commentsOpen} unread={commentsUnread} onClick={props.onToggleComments} />
        ) : null}
        <ThemeButton fit={fit} theme={theme} onChange={props.onThemeChange} />
      </header>
      {voiceNotice === null ? null : <VoiceNoticeBand notice={voiceNotice} onOpen={props.onOpenVoice} onDismiss={props.onDismissVoiceNotice} />}
      <TabBar tabs={tabs} current={current} onNavigate={props.onNavigate} />
      <DuplicateIdNotice ids={duplicateIds} onOpen={props.onOpenDuplicate} onClose={props.onCloseDuplicate} />
    </div>
  );
};
