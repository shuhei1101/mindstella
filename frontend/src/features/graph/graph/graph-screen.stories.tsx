// ネットワークの画面のストーリー。記録・レビュー中のコメントは MSW が返す
import type { Meta, StoryObj } from "@storybook/react-vite";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";

import { GraphScreen } from "@/features/graph/graph/graph-screen";
import { parsePreviewSearch, parseSearchString, stringifySearchString } from "@/shared/core/preview-search";

/** ネットワークの画面が読む search を持つルーターの中で描く */
const InRouter = ({ path, drawerOpen }: { path: string; drawerOpen: boolean }) => {
  const rootRoute = createRootRoute();
  const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", validateSearch: parsePreviewSearch, component: () => <GraphScreen drawerOpen={drawerOpen} onCloseDrawer={() => undefined} /> });
  const router = createRouter({ routeTree: rootRoute.addChildren([indexRoute]), history: createMemoryHistory({ initialEntries: [path] }), parseSearch: parseSearchString, stringifySearch: stringifySearchString });
  return (
    <div className="flex h-dvh flex-col">
      <RouterProvider router={router} />
    </div>
  );
};

const meta = {
  title: "Features/Graph/GraphScreen",
  component: InRouter,
  parameters: { layout: "fullscreen" },
  args: { path: "/?tab=graph", drawerOpen: false },
} satisfies Meta<typeof InRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 全ての項目を描く */
export const Default: Story = {};

/** 項目を選んだ（その玉へ寄り、つながる玉を強調する） */
export const Selected: Story = { args: { path: "/?tab=graph&id=D-1" } };

/** 絞り込みのドロワーを開き、条件のチップを出す */
export const Filtered: Story = { args: { path: "/?tab=graph&f.type=%E6%A4%9C%E8%A8%8E%E4%BA%8B%E9%A0%85", drawerOpen: true } };

/** 条件に合う項目が無い */
export const Empty: Story = { args: { path: "/?tab=graph&f.tags=%E7%84%A1%E3%81%84%E3%82%BF%E3%82%B0" } };
