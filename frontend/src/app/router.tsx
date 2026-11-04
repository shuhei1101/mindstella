// 生成したルートのツリーで、SPA を配るパスの頭（インターフェース定義『SPAの配信』）を付けたルーターを作る
import type { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";

import { routeTree } from "@/route-tree.gen";

/** ルーターの頭 */
export const ROUTER_BASEPATH = "/spa";

export const createAppRouter = (queryClient: QueryClient) =>
  createRouter({ routeTree, basepath: ROUTER_BASEPATH, context: { queryClient } });

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
