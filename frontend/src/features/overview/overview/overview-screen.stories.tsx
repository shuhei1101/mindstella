// 概要の画面のストーリー。記録・レビュー中のコメント・保存待ちの編集・スレッドは MSW が返す
import type { Meta, StoryObj } from "@storybook/react-vite";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";

import { OverviewScreen } from "@/features/overview/overview/overview-screen";
import { parsePreviewSearch } from "@/shared/core/preview-search";

/** 概要の画面が読む search を持つルーターの中で描く */
const InRouter = () => {
  const rootRoute = createRootRoute();
  const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", validateSearch: parsePreviewSearch, component: OverviewScreen });
  const router = createRouter({ routeTree: rootRoute.addChildren([indexRoute]), history: createMemoryHistory({ initialEntries: ["/"] }) });
  return <RouterProvider router={router} />;
};

const meta = {
  title: "Features/Overview/OverviewScreen",
  component: InRouter,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof InRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 記録で 6 つのタイルを描く */
export const Default: Story = {};
