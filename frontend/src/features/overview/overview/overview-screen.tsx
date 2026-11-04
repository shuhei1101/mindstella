// 概要の画面（画面設計『概要.tsx』）。トップバーとタイルを描き、記録が読めないときは detail の行を出す
import { useQuery } from "@tanstack/react-query";

import { GoalTile } from "@/features/overview/overview/components/goal-tile";
import { ListTile } from "@/features/overview/overview/components/list-tile";
import { NextTile } from "@/features/overview/overview/components/next-tile";
import { ProgressTable } from "@/features/overview/overview/components/progress-table";
import { overviewQueries } from "@/features/overview/overview/queries";
import type { Item, Kind, Records, Threads } from "@/shared/api/generated/model";
import type { IconName } from "@/shared/components/icon";
import { type TabKey, Topbar, type TopbarCurrent, type TopbarTab } from "@/shared/components/topbar";
import { AppError } from "@/shared/core/app-error";
import { toLegacyUrl } from "@/shared/core/legacy-url";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { PREFS_KEY, useThemeStore } from "@/shared/stores/theme-store";

/** 種類の並び（タブの帯の順） */
const KINDS: readonly Kind[] = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"];

/** 種類 → 画面に出す名前 */
const KIND_LABEL: Record<Kind, string> = {
  decisions: "検討事項",
  tasks: "タスク",
  research: "調査",
  docs: "資料",
  terms: "用語集",
  notes: "メモ",
  logs: "会話ログ",
};

/** タブ → アイコン */
const TAB_ICON: Record<TabKey, IconName> = {
  overview: "home",
  decisions: "decision",
  tasks: "task",
  research: "research",
  docs: "doc",
  terms: "term",
  notes: "note",
  logs: "log",
};

/** 表示する種類（端末の上書き、無ければワークスペースの既定、それも無ければ全ての種類） */
const visibleKindsOf = (records: Records): Set<Kind> => {
  try {
    const prefs: unknown = JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}");
    const kinds = (prefs as { kinds?: unknown }).kinds;
    if (Array.isArray(kinds)) return new Set(KINDS.filter((kind) => kinds.includes(kind)));
  } catch {
    // 読めない上書きは無いものとして扱う
  }
  return new Set(records.settings.display?.visible_kinds ?? KINDS);
};

/** オープンのスレッドに利用者の未読の書き込みがあるか */
const hasUnread = (threads: Threads | undefined): boolean =>
  threads?.threads.some((thread) => thread.status === "open" && thread.posts.some((post) => !post.seen)) ?? false;

/** 今の画面を同じタブで開く */
const openLegacy = (hash: Record<string, string>): void => {
  window.location.assign(toLegacyUrl(hash));
};

/** 今の画面の詳細パネル */
const openItem = (kind: Kind) => (id: string) => {
  openLegacy({ tab: kind, id });
};

/** 記録を読めなかったときの表示（detail の行） */
const RecordsError = ({ error }: { error: Error }) => (
  <section role="alert" className="rounded-control bg-card px-6.5 py-6">
    <h1 className="m-0 text-h2 font-semibold">記録を読めませんでした</h1>
    <ul className="mt-2.5 mb-0 grid gap-1 pl-5 text-small text-muted-foreground">
      {error.message.split("\n").map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  </section>
);

/** 記録からタイルを並べる */
const Tiles = ({ records }: { records: Records }) => {
  const visible = visibleKindsOf(records);
  const byId = new Map<string, Item>(KINDS.flatMap((kind) => records[kind].map((item) => [item.id, item] as const)));
  const review = records.decisions.filter((item) => item.status === "要見直し");
  const hold = records.decisions.filter((item) => item.status === "保留");
  const running = records.tasks.filter((item) => item.status === "進行中");
  const decisionsShown = visible.has("decisions");
  const tasksShown = visible.has("tasks");
  return (
    <>
      <header className="pt-3 pb-7">
        {records.settings.description === undefined ? null : (
          <p id="overview-description" className="readable-width m-0 mb-2 text-h2 leading-relaxed text-muted-foreground">
            {records.settings.description}
          </p>
        )}
        <h1 className="m-0 mt-1.5 text-hero leading-tight font-bold tracking-tight max-md:text-hero-narrow">{records.settings.summary}</h1>
      </header>
      <div className="grid grid-cols-3 gap-4 max-xl:grid-cols-2 max-md:grid-cols-1">
        <NextTile
          candidates={records.derived.next}
          itemOf={(id) => byId.get(id)}
          onOpen={openItem("decisions")}
          onShowAll={decisionsShown ? () => openLegacy({ tab: "decisions", view: "table", "f.status": "未決定", "f.ready": "着手可能" }) : undefined}
        />
        <GoalTile
          goal={records.derived.goal}
          settings={records.settings}
          hasItem={(id) => byId.has(id)}
          onOpen={openItem("docs")}
          onShowAllDeliverables={visible.has("docs") ? () => openLegacy({ tab: "docs", view: "cards", "f.deliverable": "納品物" }) : undefined}
        />
        <ListTile
          tileId="tile-review"
          headingId="h-review"
          icon="alert"
          title="要見直し"
          items={review}
          emptyText="要見直しの検討事項はありません。"
          onOpen={openItem("decisions")}
          onShowAll={decisionsShown ? () => openLegacy({ tab: "decisions", view: "table", "f.status": "要見直し" }) : undefined}
        />
        <ListTile
          tileId="tile-hold"
          headingId="h-hold"
          icon="pause"
          title="保留"
          items={hold}
          emptyText="保留の検討事項はありません。"
          onOpen={openItem("decisions")}
          onShowAll={decisionsShown ? () => openLegacy({ tab: "decisions", view: "table", "f.status": "保留" }) : undefined}
        />
        <ListTile
          tileId="tile-running"
          headingId="h-run"
          icon="play"
          title="進行中のタスク"
          items={running}
          emptyText="進行中のタスクはありません。"
          onOpen={openItem("tasks")}
          onShowAll={tasksShown ? () => openLegacy({ tab: "tasks", view: "table", "f.status": "進行中" }) : undefined}
        />
        <ProgressTable
          progress={records.derived.progress}
          settings={records.settings}
          onSelect={
            decisionsShown
              ? (category, phase) => {
                  openLegacy({ tab: "decisions", view: "table", "f.category": category, ...(phase === null ? {} : { "f.phase": phase }) });
                }
              : undefined
          }
        />
      </div>
    </>
  );
};

export const OverviewScreen = () => {
  const [recordsQuery, commentsQuery, editsQuery, threadsQuery] = overviewQueries();
  const records = useQuery(recordsQuery);
  const comments = useQuery(commentsQuery);
  const edits = useQuery(editsQuery);
  const threads = useQuery(threadsQuery);
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);
  const connection = useConnectionStore((state) => state.connection);
  // 成功の応答だけを本文にする（失敗は apiClient が AppError にして投げる）
  const data = records.data?.status === 200 ? records.data.data : undefined;
  const visible = data === undefined ? new Set<Kind>(KINDS) : visibleKindsOf(data);
  const tabs: TopbarTab[] = [
    { key: "overview", label: "概要", icon: TAB_ICON.overview },
    ...KINDS.filter((kind) => visible.has(kind)).map((kind) => ({
      key: kind,
      label: KIND_LABEL[kind],
      icon: TAB_ICON[kind],
      ...(data === undefined ? {} : { count: data[kind].length }),
    })),
  ];
  const commentCount = comments.data?.status === 200 ? comments.data.data.items.length : 0;
  const pendingCount = edits.data?.status === 200 ? edits.data.data.items.length : 0;
  const unread = hasUnread(threads.data?.status === 200 ? threads.data.data : undefined);
  // 記録に届かないときも接続が切れた表示にする
  const reachable = !(records.error !== null && !(records.error instanceof AppError));
  const navigate = (key: TopbarCurrent): void => {
    if (key !== "overview") openLegacy({ tab: key });
  };
  const openLegacyOverview = (): void => {
    openLegacy({ tab: "overview" });
  };
  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <Topbar
        title={data?.settings.summary ?? ""}
        tabs={tabs}
        current="overview"
        theme={theme}
        connection={connection === "offline" || !reachable ? "offline" : "online"}
        readAt={data?.built_at ?? null}
        comments
        commentCount={commentCount}
        commentsUnread={unread}
        pending
        pendingCount={pendingCount}
        onNavigate={navigate}
        onOpenSearch={openLegacyOverview}
        onThemeChange={setTheme}
        onOpenHistory={openLegacyOverview}
        onToggleComments={openLegacyOverview}
        onToggleSettings={openLegacyOverview}
        onTogglePending={openLegacyOverview}
      />
      <main id="main" className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-8 pt-7 pb-16 max-md:px-4">
        <div className="mx-auto w-full max-w-content">
          {data === undefined && records.error instanceof AppError ? <RecordsError error={records.error} /> : null}
          {data === undefined ? null : <Tiles records={data} />}
        </div>
      </main>
    </div>
  );
};
