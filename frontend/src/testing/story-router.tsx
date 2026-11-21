// 画面のストーリーを、URL の search を持つメモリの履歴のルーターの中で描く
import type { ReactElement } from "react";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";

import { parsePreviewSearch, parseSearchString, stringifySearchString } from "@/shared/core/preview-search";

export type InStoryRouterProps = {
  /** 開く URL（`/?tab=decisions` など） */
  path: string;
  /** ルートの中に描く画面 */
  screen: () => ReactElement;
};

export const InStoryRouter = ({ path, screen }: InStoryRouterProps) => {
  const rootRoute = createRootRoute();
  const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", validateSearch: parsePreviewSearch, component: screen });
  const router = createRouter({ routeTree: rootRoute.addChildren([indexRoute]), history: createMemoryHistory({ initialEntries: [path] }), parseSearch: parseSearchString, stringifySearch: stringifySearchString });
  return <RouterProvider router={router} />;
};
