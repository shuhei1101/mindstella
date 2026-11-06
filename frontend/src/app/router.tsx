// 生成したルートのツリーで、SPA を配るパスの頭（インターフェース定義『SPAの配信』）を付けたルーターを作る
import type { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";

import { routeTree } from "@/route-tree.gen";
import { parseSearchString, stringifySearchString } from "@/shared/core/preview-search";

/** ルーターの頭 */
export const ROUTER_BASEPATH = "/spa";

export const createAppRouter = (queryClient: QueryClient) =>
  createRouter({ routeTree, basepath: ROUTER_BASEPATH, context: { queryClient }, parseSearch: parseSearchString, stringifySearch: stringifySearchString });

declare module "@tanstack/react-router" {
  // 宣言のマージで TanStack Router の型を登録するには interface が要る
  // eslint-disable-next-line @typescript-eslint/consistent-type-definitions
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
