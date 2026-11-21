// 生成したルートのツリーで、配るワークスペースのパスの頭（配る書き出しはハッシュの履歴）を付けたルーターを作る
import type { QueryClient } from "@tanstack/react-query";
import { createHashHistory, createRouter } from "@tanstack/react-router";

import { routeTree } from "@/route-tree.gen";
import { isEmbedded } from "@/shared/core/embedded";
import { parseSearchString, stringifySearchString } from "@/shared/core/preview-search";
import { workspacePath } from "@/shared/core/workspace-path";

export const createAppRouter = (queryClient: QueryClient) =>
  createRouter({
    routeTree,
    ...(isEmbedded() ? { history: createHashHistory(), basepath: "/" } : { basepath: workspacePath() }),
    context: { queryClient },
    parseSearch: parseSearchString,
    stringifySearch: stringifySearchString,
    // ページ全体のスクロール位置を履歴の項目ごとに戻す
    scrollRestoration: true,
  });

declare module "@tanstack/react-router" {
  // 宣言のマージで TanStack Router の型を登録するには interface が要る
  // eslint-disable-next-line @typescript-eslint/consistent-type-definitions
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
