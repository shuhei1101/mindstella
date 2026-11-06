// 概要の画面（画面設計『概要.tsx』）。トップバーとタイルを描き、記録が読めないときは detail の行を出す
import { useQuery } from "@tanstack/react-query";

import { GoalTile } from "@/features/overview/overview/components/goal-tile";
import { ListTile } from "@/features/overview/overview/components/list-tile";
import { NextTile } from "@/features/overview/overview/components/next-tile";
import { ProgressTable } from "@/features/overview/overview/components/progress-table";
import type { Item, Kind, Records } from "@/shared/api/generated/model";
import type { PreviewSearch } from "@/shared/core/preview-search";
import { recordsQuery } from "@/shared/hooks/preview-queries";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useVisibleKinds } from "@/shared/hooks/use-visible-kinds";

/** 記録からタイルを並べる */
const KINDS: readonly Kind[] = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"];

const Tiles = ({ records, visible }: { records: Records; visible: ReadonlySet<Kind> }) => {
  const { openList } = usePreviewSearch();
  const openItem = (kind: Kind) => (id: string) => {
    openList(kind, { id });
  };
  const listLink = (shown: boolean, tab: Kind, view: PreviewSearch["view"], f: Record<string, string>) =>
    shown
      ? () => {
          openList(tab, { view, f });
        }
      : undefined;
  const openCategory = (category: string, phase: string | null): void => {
    openList("decisions", { view: "table", f: { category, ...(phase === null ? {} : { phase }) } });
  };
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
          <p id="overview-description" className="m-0 mb-2 readable-width text-h2/relaxed text-muted-foreground">
            {records.settings.description}
          </p>
        )}
        <h1 className="m-0 mt-1.5 text-hero/tight font-bold tracking-tight max-md:text-hero-narrow">{records.settings.summary}</h1>
      </header>
      <div className="grid grid-cols-3 gap-4 max-xl:grid-cols-2 max-md:grid-cols-1">
        <NextTile
          candidates={records.derived.next}
          itemOf={(id) => byId.get(id)}
          onOpen={openItem("decisions")}
          onShowAll={listLink(decisionsShown, "decisions", "table", { status: "未決定", ready: "着手可能" })}
        />
        <GoalTile
          goal={records.derived.goal}
          settings={records.settings}
          hasItem={(id) => byId.has(id)}
          onOpen={openItem("docs")}
          onShowAllDeliverables={listLink(visible.has("docs"), "docs", "cards", { deliverable: "納品物" })}
        />
        <ListTile
          tileId="tile-review"
          headingId="h-review"
          icon="alert"
          title="要見直し"
          items={review}
          emptyText="要見直しの検討事項はありません。"
          onOpen={openItem("decisions")}
          onShowAll={listLink(decisionsShown, "decisions", "table", { status: "要見直し" })}
        />
        <ListTile
          tileId="tile-hold"
          headingId="h-hold"
          icon="pause"
          title="保留"
          items={hold}
          emptyText="保留の検討事項はありません。"
          onOpen={openItem("decisions")}
          onShowAll={listLink(decisionsShown, "decisions", "table", { status: "保留" })}
        />
        <ListTile
          tileId="tile-running"
          headingId="h-run"
          icon="play"
          title="進行中のタスク"
          items={running}
          emptyText="進行中のタスクはありません。"
          onOpen={openItem("tasks")}
          onShowAll={listLink(tasksShown, "tasks", "table", { status: "進行中" })}
        />
        <ProgressTable
          progress={records.derived.progress}
          settings={records.settings}
          onSelect={decisionsShown ? openCategory : undefined}
        />
      </div>
    </>
  );
};

export const OverviewScreen = () => {
  const records = useQuery(recordsQuery());
  const visible = useVisibleKinds();
  const data = records.data?.status === 200 ? records.data.data : undefined;
  return (
    <main id="main" className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-8 pt-7 pb-16 max-md:px-4">
      <div className="mx-auto w-full max-w-content">{data === undefined ? null : <Tiles records={data} visible={visible} />}</div>
    </main>
  );
};
