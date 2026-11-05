// QueryClientProvider と RouterProvider を組み、書き換えの知らせへつなぐ
import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { useEffect } from "react";

import type { createAppRouter } from "@/app/router";
import { connectEvents } from "@/shared/adapters/events-client";

export const App = ({ queryClient, router }: { queryClient: QueryClient; router: ReturnType<typeof createAppRouter> }) => {
  useEffect(() => connectEvents(queryClient), [queryClient]);
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
};
