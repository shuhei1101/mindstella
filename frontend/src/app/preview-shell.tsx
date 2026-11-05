// SPA の外枠（インターフェース定義『SPAを開く』）。`tab` の画面を描き、`id`・`full`・`panel` の詳細と保存待ちのパネルを重ねる。features の画面を組むのはここだけ
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { DecisionsScreen } from "@/features/decisions/decisions/decisions-screen";
import { DetailFullscreen } from "@/features/detail/detail-fullscreen/detail-fullscreen";
import { DetailPanel } from "@/features/detail/detail-panel/detail-panel";
import { DocsScreen } from "@/features/docs/docs/docs-screen";
import { PendingEditsPanel } from "@/features/edits/pending-edits/pending-edits-panel";
import { HistoryScreen } from "@/features/history/history/history-dialog";
import { OverviewScreen } from "@/features/overview/overview/overview-screen";
import { RecordsScreen, type RecordKind } from "@/features/records/records/records-screen";
import { WorkspaceSettingsScreen } from "@/features/settings/workspace-settings/workspace-settings-screen";
import { TasksScreen } from "@/features/tasks/tasks/tasks-screen";
import type { Threads } from "@/shared/api/generated/model";
import type { IconName } from "@/shared/components/icon";
import { Topbar, type TabKey, type TopbarCurrent, type TopbarTab } from "@/shared/components/topbar";
import { AppError } from "@/shared/core/app-error";
import { SETTINGS_TARGET } from "@/shared/core/edits";
import { toLegacyUrl } from "@/shared/core/legacy-url";
import { normalizeSearch, toLegacyHash } from "@/shared/core/preview-search";
import { KIND_KEYS, KIND_LABEL } from "@/shared/core/records";
import { commentsQuery, recordsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { useDiffView } from "@/shared/hooks/use-diff-view";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { writePrefs } from "@/shared/stores/prefs-store";
import { useThemeStore } from "@/shared/stores/theme-store";

const TAB_ICON: Record<TabKey, IconName> = { overview: "home", decisions: "decision", tasks: "task", research: "research", docs: "doc", terms: "term", notes: "note", logs: "log" };

const RECORD_KINDS: readonly string[] = ["research", "terms", "notes", "logs"];

const hasUnread = (threads: Threads | undefined): boolean => threads?.threads.some((thread) => thread.status === "open" && thread.posts.some((post) => !post.seen)) ?? false;

const RecordsError = ({ error }: { error: Error }) => (
  <section role="alert" className="m-4 rounded-control bg-card px-6.5 py-6">
    <h1 className="m-0 text-h2 font-semibold">記録を読めませんでした</h1>
    <ul className="mt-2.5 mb-0 grid gap-1 pl-5 text-small text-muted-foreground">
      {error.message.split("\n").map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  </section>
);

export const PreviewShell = () => {
  const { search, setTab, openItem, setDiff, setPanel, replaceSearch } = usePreviewSearch();
  const records = useQuery(recordsQuery());
  const comments = useQuery(commentsQuery());
  const threads = useQuery(threadsQuery());
  const { index, rawIndex, edits } = useRecords();
  const { point, since } = useDiffView();
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);
  const connection = useConnectionStore((state) => state.connection);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const data = records.data?.status === 200 ? records.data.data : undefined;
  const visible = useVisibleKinds();
  const pendingCount = edits.length;
  const diffActive = point !== null;
  // 記録に合わない値を外す（並べ替えの列は一覧の画面が確かめる）
  useEffect(() => {
    if (index === null) return;
    const next = normalizeSearch(search, { index, pendingCount, visibleKinds: [...visible], diffActive, sortColumns: search.sort === undefined ? [] : [search.sort.replace(/^-/, "")] });
    if (JSON.stringify(next) !== JSON.stringify(search)) replaceSearch(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- search の中身が変わったときだけ確かめる
  }, [index, JSON.stringify(search), pendingCount, diffActive]);
  const tabs: TopbarTab[] = [
    { key: "overview", label: "概要", icon: TAB_ICON.overview },
    ...KIND_KEYS.filter((kind) => visible.has(kind)).map((kind) => ({ key: kind, label: KIND_LABEL[kind], icon: TAB_ICON[kind], ...(data === undefined ? {} : { count: data[kind].length }) })),
  ];
  const tab = search.tab ?? "overview";
  const listTab = tab !== "overview" && tab !== "settings";
  const reachable = !(records.error !== null && !(records.error instanceof AppError));
  const openLegacy = (hash: Record<string, string>): void => {
    window.location.assign(toLegacyUrl(hash));
  };
  // React に無い画面（検索・コメント・表示の設定・ネットワーク）は今の画面を開く
  const toLegacy = (): void => {
    openLegacy(toLegacyHash(search));
  };
  const closeDrawer = (): void => {
    setDrawerOpen(false);
  };
  const screen = () => {
    if (data === undefined) return null;
    if (tab === "overview") return <OverviewScreen />;
    if (tab === "settings") return <WorkspaceSettingsScreen />;
    const list = (() => {
      if (tab === "decisions") return <DecisionsScreen drawerOpen={drawerOpen} onCloseDrawer={closeDrawer} />;
      if (tab === "tasks") return <TasksScreen drawerOpen={drawerOpen} onCloseDrawer={closeDrawer} />;
      if (tab === "docs") return <DocsScreen drawerOpen={drawerOpen} onCloseDrawer={closeDrawer} />;
      return RECORD_KINDS.includes(tab) ? <RecordsScreen key={tab} kind={tab as RecordKind} drawerOpen={drawerOpen} onCloseDrawer={closeDrawer} /> : null;
    })();
    return (
      <main id="main" className="flex min-h-0 min-w-0 flex-1 flex-col">
        {list}
      </main>
    );
  };
  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <Topbar
        title={data?.settings.summary ?? ""}
        tabs={tabs}
        current={tab as TopbarCurrent}
        theme={theme}
        connection={connection === "offline" || !reachable ? "offline" : "online"}
        readAt={data?.built_at ?? null}
        diffPoint={point === null ? null : { name: point.name, sub: point.sub }}
        comments
        commentCount={comments.data?.status === 200 ? comments.data.data.items.length : 0}
        commentsUnread={hasUnread(threads.data?.status === 200 ? threads.data.data : undefined)}
        filter={listTab}
        filterCount={Object.keys(search.f).length}
        filterOpen={drawerOpen}
        pending={!diffActive}
        pendingCount={pendingCount}
        pendingOpen={search.panel === "pending"}
        onNavigate={(key) => {
          if (key === "graph" || key === "settings") openLegacy({ tab: key });
          else setTab(key);
        }}
        onOpenSearch={toLegacy}
        onThemeChange={setTheme}
        onOpenHistory={() => { setHistoryOpen(true); }}
        onClearDiff={() => {
          writePrefs({ diffSel: null });
          setDiff(undefined);
        }}
        onToggleComments={toLegacy}
        onToggleSettings={toLegacy}
        onToggleFilter={() => { setDrawerOpen(!drawerOpen); }}
        onTogglePending={() => { setPanel(search.panel === "pending" ? undefined : "pending"); }}
      />
      <div className="flex min-h-0 flex-1">
        {data === undefined && records.error instanceof AppError ? <RecordsError error={records.error} /> : null}
        {screen()}
        {index !== null && search.id !== undefined && search.full === undefined ? <DetailPanel id={search.id} index={index} /> : null}
      </div>
      {index !== null && search.id !== undefined && search.full !== undefined ? <DetailFullscreen id={search.id} index={index} /> : null}
      {rawIndex !== null && search.panel === "pending" ? (
        <PendingEditsPanel
          edits={edits}
          index={rawIndex}
          onClose={() => { setPanel(undefined); }}
          onOpen={(target) => {
            if (target === SETTINGS_TARGET) setTab("settings");
            else openItem(target);
          }}
        />
      ) : null}
      {historyOpen && rawIndex !== null ? (
        <HistoryScreen
          changes={rawIndex.data.changes}
          since={since ?? { at: rawIndex.data.built_at, seq: rawIndex.data.changes.sets[0]?.until_seq ?? 0 }}
          point={point}
          onSelect={(sel) => {
            writePrefs({ diffSel: sel === "" ? null : sel });
            setDiff(sel === "" ? undefined : sel);
            setHistoryOpen(false);
          }}
          onClose={() => { setHistoryOpen(false); }}
        />
      ) : null}
    </div>
  );
};
