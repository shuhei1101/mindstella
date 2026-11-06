// SPA の外枠（インターフェース定義『SPAを開く』）。`tab` の画面を描き、`id`・`full`・`panel` の詳細と保存待ちのパネルを重ねる。features の画面を組むのはここだけ
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { DecisionsScreen } from "@/features/decisions/decisions/decisions-screen";
import { DetailFullscreen } from "@/features/detail/detail-fullscreen/detail-fullscreen";
import { DetailPanel } from "@/features/detail/detail-panel/detail-panel";
import { DocsScreen } from "@/features/docs/docs/docs-screen";
import { PendingEditsPanel } from "@/features/edits/pending-edits/pending-edits-panel";
import { HistoryScreen } from "@/features/history/history/history-dialog";
import { ItemAddPanel } from "@/features/detail/detail-panel/components/item-add-panel";
import { OverviewScreen } from "@/features/overview/overview/overview-screen";
import { RecordsScreen, type RecordKind } from "@/features/records/records/records-screen";
import { WorkspaceSettingsScreen } from "@/features/settings/workspace-settings/workspace-settings-screen";
import { TasksScreen } from "@/features/tasks/tasks/tasks-screen";
import type { Threads } from "@/shared/api/generated/model";
import { Icon, type IconName } from "@/shared/components/icon";
import { Topbar, type TabKey, type TopbarTab } from "@/shared/components/topbar";
import { AppError } from "@/shared/core/app-error";
import { SETTINGS_TARGET } from "@/shared/core/edits";
import { toLegacyUrl } from "@/shared/core/legacy-url";
import { normalizeSearch, toLegacyHash } from "@/shared/core/preview-search";
import { KIND_KEYS, KIND_LABEL, type Kind } from "@/shared/core/records";
import { commentsQuery, recordsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { useDiffView } from "@/shared/hooks/use-diff-view";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";
import { useEditSessionStore } from "@/shared/stores/edit-session-store";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { writePrefs } from "@/shared/stores/prefs-store";
import { useThemeStore } from "@/shared/stores/theme-store";

const TAB_ICON: Record<TabKey, IconName> = { overview: "home", decisions: "decision", tasks: "task", research: "research", docs: "doc", terms: "term", notes: "note", logs: "log" };

const isListKind = (tab: string): tab is Kind => (KIND_KEYS as readonly string[]).includes(tab);

const isRecordKind = (tab: string): tab is RecordKind => ["research", "terms", "notes", "logs"].includes(tab);

/** 保存の通知を出しておくミリ秒 */
const SAVED_NOTICE_MS = 4000;

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

// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
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
  const adding = useEditSessionStore((state) => state.adding);
  const openAdded = useEditSessionStore((state) => state.openAdded);
  const closeAdd = useEditSessionStore((state) => state.closeAdd);
  const blocked = useEditSessionStore((state) => state.blocked);
  const saved = useEditSessionStore((state) => state.saved);
  const setSaved = useEditSessionStore((state) => state.setSaved);
  // 保存の通知は少し経ったら消す
  useEffect(() => {
    if (saved === null) return undefined;
    const timer = window.setTimeout(() => { setSaved(null); }, SAVED_NOTICE_MS);
    return () => { window.clearTimeout(timer); };
  }, [saved, setSaved]);
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
    openLegacy(toLegacyHash(search, tab));
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
      return isRecordKind(tab) ? <RecordsScreen key={tab} kind={tab} drawerOpen={drawerOpen} onCloseDrawer={closeDrawer} /> : null;
    })();
    return (
      <main id="main" className="flex min-h-0 min-w-0 flex-1 flex-col">
        <h1 className="sr-only text-next">{isListKind(tab) ? KIND_LABEL[tab] : ""}</h1>
        {list}
      </main>
    );
  };
  return (
    <div className="flex h-dvh flex-col">
      <Topbar
        title={data?.settings.summary ?? ""}
        tabs={tabs}
        current={tab}
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
        pendingBlocked={blocked.length > 0}
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
        {data === undefined && records.error instanceof AppError ? (
          <main id="main" className="min-h-0 flex-1 overflow-y-auto">
            <div>
              <RecordsError error={records.error} />
            </div>
          </main>
        ) : null}
        {screen()}
        {index !== null && search.id !== undefined && search.full === undefined ? <DetailPanel id={search.id} index={index} /> : null}
        {index !== null && adding !== null && search.id === undefined ? <ItemAddPanel key={adding.target ?? adding.kind} kind={adding.kind} target={adding.target} index={index} edits={edits} /> : null}
      </div>
      {index !== null && search.id !== undefined && search.full !== undefined ? <DetailFullscreen id={search.id} index={index} /> : null}
      {rawIndex !== null && search.panel === "pending" ? (
        <PendingEditsPanel
          edits={edits}
          index={rawIndex}
          onClose={() => { setPanel(undefined); }}
          onOpen={(target) => {
            const added = edits.find((edit) => edit.op === "item-add" && edit.target === target);
            if (target === SETTINGS_TARGET) setTab("settings");
            else if (added === undefined) {
              closeAdd();
              openItem(target);
            } else openAdded(added.key as Kind, target);
          }}
        />
      ) : null}
      {saved === null ? null : (
        <p role="status" className="fixed bottom-4 left-1/2 z-40 m-0 flex -translate-x-1/2 items-center gap-1 rounded-control bg-primary px-3 py-2 text-small text-primary-foreground">
          <Icon name="check" className="size-4" />
          {`${String(saved)} 件を保存しました。`}
        </p>
      )}
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
