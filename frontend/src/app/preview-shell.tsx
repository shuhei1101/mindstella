// SPA の外枠（インターフェース定義『SPAを開く』）。`tab` の画面を描き、`id`・`full`・`panel` の詳細と保存待ちのパネル、`search` の全体の検索を重ねる。features の画面を組むのはここだけ
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { CommentsPanel } from "@/features/comments/comments-panel/comments-panel";
import { DecisionsScreen } from "@/features/decisions/decisions/decisions-screen";
import { DetailFullscreen } from "@/features/detail/detail-fullscreen/detail-fullscreen";
import { DetailPanel } from "@/features/detail/detail-panel/detail-panel";
import { DocsScreen } from "@/features/docs/docs/docs-screen";
import { GraphScreen } from "@/features/graph/graph/graph-screen";
import { PendingEditsPanel } from "@/features/edits/pending-edits/pending-edits-panel";
import { HistoryScreen } from "@/features/history/history/history-dialog";
import { ItemAddPanel } from "@/features/detail/detail-panel/components/item-add-panel";
import { OverviewScreen } from "@/features/overview/overview/overview-screen";
import { RecordsScreen, type RecordKind } from "@/features/records/records/records-screen";
import { SearchDialog } from "@/features/search/search/search-dialog";
import { useSearchShortcut } from "@/features/search/search/use-search-shortcut";
import { DisplaySettingsPanel } from "@/features/settings/display-settings/display-settings-panel";
import { WorkspaceSettingsScreen } from "@/features/settings/workspace-settings/workspace-settings-screen";
import { TasksScreen } from "@/features/tasks/tasks/tasks-screen";
import { Icon, type IconName } from "@/shared/components/icon";
import { Topbar, type TabKey, type TopbarTab } from "@/shared/components/topbar";
import { AppError } from "@/shared/core/app-error";
import { anyOpenUnseen, type ReviewItem, type Thread } from "@/shared/core/comments";
import { SETTINGS_TARGET } from "@/shared/core/edits";
import { normalizeSearch } from "@/shared/core/preview-search";
import { KIND_KEYS, KIND_LABEL, type Kind } from "@/shared/core/records";
import { commentsQuery, recordsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { useDiffView } from "@/shared/hooks/use-diff-view";
import { usePreviewSearch, type VoiceTarget } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";
import { useEditSessionStore } from "@/shared/stores/edit-session-store";
import { useConnectionStore } from "@/shared/stores/connection-store";
import { clearDisplayNotice, displayChanged, sameDisplay, useDisplayNoticeAt } from "@/shared/stores/display-notice-store";
import { writePrefs } from "@/shared/stores/prefs-store";
import { useThemeStore } from "@/shared/stores/theme-store";
import { discardVoice, dismissVoiceNotice, useVoiceNotice, useVoiceSession, voiceTargetOf, type VoiceDestination } from "@/shared/stores/voice-store";

const TAB_ICON: Record<TabKey, IconName> = { overview: "home", decisions: "decision", tasks: "task", research: "research", docs: "doc", terms: "term", notes: "note", logs: "log" };

const isListKind = (tab: string): tab is Kind => (KIND_KEYS as readonly string[]).includes(tab);

const isRecordKind = (tab: string): tab is RecordKind => ["research", "terms", "notes", "logs"].includes(tab);

/** 保存の通知を出しておくミリ秒 */
const SAVED_NOTICE_MS = 5000;

/** 「ワークスペースの既定が変わりました。」を出しておくミリ秒（今の画面の `NOTICE_MS` と同じ） */
const DISPLAY_NOTICE_MS = 6000;

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

/** 入力欄の向けた先と開く画面から、開く画面を決める */
const voiceTargetFor = (key: string): VoiceTarget | null => {
  const target = voiceTargetOf(key);
  if (target === null) return null;
  const { destination, view } = target;
  if ("thread" in destination) return { thread: destination.thread };
  if (view === "comments" || destination.target === null) return { thread: null };
  return { item: destination.target, full: view === "full" };
};

/** 録音中なら ✓ の「文字起こし」、文字起こし中は入力欄へフォーカスを移す（画面を開いた後の描画を待つ） */
const focusVoiceInput = (): void => {
  window.setTimeout(() => {
    const done = document.querySelector<HTMLButtonElement>('button[aria-label="文字起こし"]');
    if (done !== null) {
      done.focus();
      return;
    }
    document.querySelector('button[aria-label="文字起こし中"]')?.closest("form")?.querySelector("textarea")?.focus();
  }, 0);
};

/** トップバーの音声入力中の表示と知らせの帯。記録・スレッドを読み直したら、向けた先が無くなった録音を捨てる */
const useVoiceTopbar = ({ exists, openVoiceInput }: { exists: ((destination: VoiceDestination) => boolean) | null; openVoiceInput: (target: VoiceTarget) => void }) => {
  const session = useVoiceSession();
  const notice = useVoiceNotice();
  useEffect(() => {
    if (exists !== null) discardVoice(exists);
  }, [exists]);
  const onOpenVoice = (): void => {
    const key = session?.key ?? notice?.key ?? null;
    if (key === null) return;
    if (session === null) dismissVoiceNotice();
    const target = voiceTargetFor(key);
    if (target !== null) openVoiceInput(target);
    // 詳細のコメントの入力を閉じていれば開く
    if (target !== null && "item" in target) writePrefs({ commentFormClosed: null });
    focusVoiceInput();
  };
  return {
    voice: session === null ? null : { state: session.phase, label: session.label, elapsed: session.elapsed },
    voiceNotice: notice === null ? null : { kind: notice.kind, text: notice.text },
    onOpenVoice,
    onDismissVoiceNotice: dismissVoiceNotice,
  };
};

// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
export const PreviewShell = () => {
  const { search, setTab, openItem, openList, setDiff, setPanel, replaceSearch, setSearch, openFromSearch, openVoiceInput } = usePreviewSearch();
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
  const data = records.data?.status === 200 ? records.data.data : undefined;
  // 読み直した記録の表示の既定が前と違えば知らせる（最初に読んだ記録では知らせない）
  const display = data?.settings.display;
  const lastDisplay = useRef<{ value: typeof display } | null>(null);
  useEffect(() => {
    if (data === undefined) return;
    if (lastDisplay.current !== null && !sameDisplay(lastDisplay.current.value, display)) displayChanged({ next: display, at: new Date().toISOString() });
    lastDisplay.current = { value: display };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 既定の中身が変わったときだけ比べる
  }, [data === undefined, JSON.stringify(display ?? null)]);
  const noticeAt = useDisplayNoticeAt();
  useEffect(() => {
    if (noticeAt === null) return undefined;
    const timer = window.setTimeout(clearDisplayNotice, DISPLAY_NOTICE_MS);
    return () => { window.clearTimeout(timer); };
  }, [noticeAt]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const visible = useVisibleKinds();
  const pendingCount = edits.length;
  const diffActive = point !== null;
  // 開いたときに確かめ終えたか（開いている間に取り消して保存待ちが 0 件になっても、保存待ちのパネルは開いたまま空の状態を出す）
  const opened = useRef(false);
  const threadList = threads.data?.status === 200 ? (threads.data.data.threads as unknown as Thread[]) : null;
  const reviewItems = comments.data?.status === 200 ? ((comments.data.data.items as unknown as ReviewItem[] | undefined) ?? []) : null;
  const voiceExists = useMemo(
    () =>
      index === null || threadList === null || reviewItems === null
        ? null
        : (destination: VoiceDestination): boolean =>
            "thread" in destination ? threadList.some((thread) => thread.id === destination.thread) || reviewItems.some((item) => item.id === destination.thread) : destination.target === null || index.byId.has(destination.target),
    [index, threadList, reviewItems],
  );
  const voiceTopbar = useVoiceTopbar({ exists: voiceExists, openVoiceInput });
  // スレッドとレビュー中の書き込みを読む前は、`thread`・`ttag` を外さない
  const threadContext = threadList === null || reviewItems === null ? {} : { threadIds: [...threadList.map((thread) => thread.id), ...reviewItems.filter((item) => item.thread === null).map((item) => item.id)], threadTags: [...new Set(threadList.flatMap((thread) => thread.tags))] };
  // 記録に合わない値を外す（並べ替えの列は一覧の画面が確かめる）
  useEffect(() => {
    if (index === null) return;
    const next = normalizeSearch(search, { index, pendingCount: opened.current ? Math.max(pendingCount, 1) : pendingCount, visibleKinds: [...visible], diffActive, sortColumns: search.sort === undefined ? [] : [search.sort.replace(/^-/, "")], ...threadContext });
    opened.current = true;
    if (JSON.stringify(next) !== JSON.stringify(search)) replaceSearch(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- search の中身が変わったときだけ確かめる
  }, [index, JSON.stringify(search), pendingCount, diffActive, JSON.stringify(threadContext), [...visible].join(",")]);
  const tabs: TopbarTab[] = [
    { key: "overview", label: "概要", icon: TAB_ICON.overview },
    ...KIND_KEYS.filter((kind) => visible.has(kind)).map((kind) => ({ key: kind, label: KIND_LABEL[kind], icon: TAB_ICON[kind], ...(data === undefined ? {} : { count: data[kind].length }) })),
  ];
  const tab = search.tab ?? "overview";
  const listTab = tab !== "overview" && tab !== "settings";
  useSearchShortcut({ open: search.search !== undefined, onOpen: () => { setSearch({ search: "1" }); } });
  const reachable = !(records.error !== null && !(records.error instanceof AppError));
  const closeDrawer = (): void => {
    setDrawerOpen(false);
  };
  const screen = () => {
    if (data === undefined) return null;
    if (tab === "overview") return <OverviewScreen />;
    if (tab === "settings") return <WorkspaceSettingsScreen />;
    if (tab === "graph") {
      return (
        <main id="main" className="flex min-h-0 min-w-0 flex-1 flex-col">
          <h1 className="sr-only">ネットワーク</h1>
          <GraphScreen drawerOpen={drawerOpen} onCloseDrawer={closeDrawer} />
        </main>
      );
    }
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
        commentsOpen={search.panel === "comments"}
        commentsUnread={threadList !== null && anyOpenUnseen(threadList)}
        settingsOpen={search.panel === "display"}
        filter={listTab}
        filterCount={Object.keys(search.f).length}
        filterOpen={drawerOpen}
        pending={!diffActive}
        pendingCount={pendingCount}
        pendingOpen={search.panel === "pending"}
        pendingBlocked={blocked.length > 0}
        {...voiceTopbar}
        onNavigate={setTab}
        onOpenSearch={() => { setSearch({ search: "1" }); }}
        onThemeChange={setTheme}
        onOpenHistory={() => { setHistoryOpen(true); }}
        onClearDiff={() => {
          writePrefs({ diffSel: null });
          setDiff(undefined);
        }}
        onToggleComments={() => { setPanel(search.panel === "comments" ? undefined : "comments"); }}
        onToggleSettings={() => { setPanel(search.panel === "display" ? undefined : "display"); }}
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
            // 設定の画面は本文の区画を置き換えるので、保存待ちのパネルを閉じて開く（溜めた編集は残る）
            if (target === SETTINGS_TARGET) openList("settings", {});
            else if (added === undefined) {
              closeAdd();
              openItem(target);
            } else openAdded(added.key as Kind, target);
          }}
        />
      ) : null}
      {search.panel === "comments" ? <CommentsPanel onOpenItem={openItem} onOpenChangeSet={setDiff} /> : null}
      {search.panel === "display" ? <DisplaySettingsPanel /> : null}
      {index !== null && search.search !== undefined ? (
        <SearchDialog
          index={index}
          query={search.q ?? ""}
          onQueryChange={(q) => { setSearch({ q: q === "" ? undefined : q }); }}
          onOpen={(id) => {
            const kind = index.byId.get(id)?.kind;
            if (kind === undefined) return;
            openFromSearch(visible.has(kind) ? kind : undefined, id);
          }}
          onClose={() => { setSearch({ search: undefined, q: undefined }); }}
        />
      ) : null}
      {saved === null ? null : (
        <p role="status" className="fixed bottom-4 left-1/2 z-40 m-0 flex -translate-x-1/2 items-center gap-1 rounded-control bg-primary px-3 py-2 text-small text-primary-foreground">
          <Icon name="check" className="size-4" />
          {`${String(saved)} 件を保存しました。`}
        </p>
      )}
      {noticeAt === null ? null : (
        <p role="status" className="fixed bottom-4 left-1/2 z-40 m-0 flex -translate-x-1/2 items-center gap-1 rounded-control bg-primary px-3 py-2 text-small text-primary-foreground">
          <Icon name="sliders" className="size-4" />
          ワークスペースの既定が変わりました。
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
