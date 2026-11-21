// QueryClientProvider と RouterProvider を組み、サーバーの配信では書き換えの知らせへつなぐ
import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { useEffect } from "react";

import type { createAppRouter } from "@/app/router";
import { connectEvents } from "@/shared/adapters/events-client";
import { isEmbedded } from "@/shared/core/embedded";

export const App = ({ queryClient, router }: { queryClient: QueryClient; router: ReturnType<typeof createAppRouter> }) => {
  // 配る書き出しは書き換えの知らせを持たない
  useEffect(() => (isEmbedded() ? undefined : connectEvents(queryClient)), [queryClient]);
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
};
