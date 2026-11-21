// 概要の画面（画面設計『概要.tsx』）。トップバーと、未読の AI の書き込み・未決定・要見直し・確認中の資料のタイルを描き、記録が読めないときは detail の行を出す
import { useQuery } from "@tanstack/react-query";

import { ListTile, type ListTileRow } from "@/features/overview/overview/components/list-tile";
import type { Item, Kind, Records, Thread } from "@/shared/api/generated/model";
import { formatJst } from "@/shared/core/format";
import { compareIds } from "@/shared/core/records";
import type { PreviewSearch } from "@/shared/core/preview-search";
import { recordsQuery, threadsQuery } from "@/shared/hooks/preview-queries";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";

/** 状態がその値の項目を、連番の順に行にする */
const rowsOf = (items: readonly Item[], status: string): ListTileRow[] =>
  items
    .filter((item) => item.status === status)
    .sort((a, b) => compareIds(a.id, b.id))
    .map((item) => ({ id: item.id, label: item.title, status: item.status }));

/** 未読の AI の書き込みを持つオープンのスレッドを、最後の未読の書き込みの新しい順に行にする */
const unreadRows = (threads: readonly Thread[]): ListTileRow[] =>
  threads
    .filter((thread) => thread.status === "open")
    .flatMap((thread) => {
      const unseen = thread.posts.filter((post) => post["author"] === "ai" && !post.seen);
      const last = unseen.at(-1)?.["created"];
      if (typeof last !== "string") return [];
      const summary = typeof thread["summary"] === "string" ? thread["summary"] : "";
      return [{ row: { id: thread.id, label: `${thread.id} ${summary}`.trim(), note: formatJst(last) }, last }];
    })
    .sort((a, b) => (a.last < b.last ? 1 : a.last > b.last ? -1 : 0))
    .map(({ row }) => row);

const Tiles = ({ records, threads, visible }: { records: Records; threads: readonly Thread[]; visible: ReadonlySet<Kind> }) => {
  const { openList, openThread } = usePreviewSearch();
  const openItem = (kind: Kind) => (id: string) => {
    openList(kind, { id });
  };
  const listLink = (shown: boolean, tab: Kind, view: PreviewSearch["view"], f: Record<string, string>) =>
    shown
      ? () => {
          openList(tab, { view, f });
        }
      : undefined;
  const unread = unreadRows(threads);
  const decisionsShown = visible.has("decisions");
  return (
    <>
      <header className="pt-3 pb-7">
        {records.settings.description === undefined ? null : (
          <p id="overview-description" className="m-0 mb-2 readable-width text-h2/relaxed text-muted-foreground">
            {records.settings.description}
          </p>
        )}
        <h1 className="m-0 mt-1.5 text-hero/tight font-bold tracking-tight @max-3xl:text-hero-narrow">{records.settings.summary}</h1>
      </header>
      <div className="grid grid-cols-2 gap-4 @max-3xl:grid-cols-1">
        <ListTile
          tileId="tile-unread"
          headingId="h-unread"
          icon="comment"
          title="未読の AI の書き込み"
          rows={unread}
          emptyText="未読の AI の書き込みはありません。"
          onOpen={openThread}
          onShowAll={() => {
            openThread(null);
          }}
        />
        <ListTile
          tileId="tile-open"
          headingId="h-open"
          icon="decision"
          title="未決定の検討事項"
          rows={rowsOf(records.decisions, "未決定")}
          emptyText="未決定の検討事項はありません。"
          onOpen={openItem("decisions")}
          onShowAll={listLink(decisionsShown, "decisions", "table", { status: "未決定" })}
        />
        <ListTile
          tileId="tile-review"
          headingId="h-review"
          icon="alert"
          title="要見直し"
          rows={rowsOf(records.decisions, "要見直し")}
          emptyText="要見直しの検討事項はありません。"
          onOpen={openItem("decisions")}
          onShowAll={listLink(decisionsShown, "decisions", "table", { status: "要見直し" })}
        />
        <ListTile
          tileId="tile-docs"
          headingId="h-docs"
          icon="doc"
          title="確認中の資料"
          rows={rowsOf(records.docs, "確認中")}
          emptyText="確認中の資料はありません。"
          onOpen={openItem("docs")}
          onShowAll={listLink(visible.has("docs"), "docs", "cards", { status: "確認中" })}
        />
      </div>
    </>
  );
};

export const OverviewScreen = () => {
  const records = useQuery(recordsQuery());
  const threads = useQuery(threadsQuery());
  const visible = useVisibleKinds();
  const data = records.data?.status === 200 ? records.data.data : undefined;
  const threadList = threads.data?.status === 200 ? threads.data.data.threads : [];
  return (
    // タイルの並び・文字の大きさ・余白は、詳細パネルで狭くなる領域の幅で切り替える
    <main id="main" className="@container min-h-0 flex-1 overflow-y-auto overscroll-contain pt-7 pb-16">
      <div className="mx-auto w-full max-w-content px-8 @max-3xl:px-4">{data === undefined ? null : <Tiles records={data} threads={threadList} visible={visible} />}</div>
    </main>
  );
};
