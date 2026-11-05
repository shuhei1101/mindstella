// Provider とルーターつきで画面を描く
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";
import { render, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { createAppRouter } from "@/app/router";
import { parsePreviewSearch } from "@/shared/core/preview-search";
import { FakeEventSource } from "@/testing/fake-event-source";

/** URL のパスでルートを開き、その画面を描く */
export const renderRoute = (path: string) => {
  vi.stubGlobal("EventSource", FakeEventSource);
  window.history.replaceState(null, "", path);
  const queryClient = createQueryClient();
  const router = createAppRouter(queryClient);
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
};

/** メモリの履歴のルーターの中で hook を呼び、最新の戻り値と履歴を返す */
export const renderPreviewHook = async <T,>(path: string, useHook: () => T) => {
  const result: { current: T | undefined } = { current: undefined };
  const Host = () => {
    result.current = useHook();
    return null;
  };
  const rootRoute = createRootRoute();
  const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", validateSearch: parsePreviewSearch, component: Host });
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createRouter({ routeTree: rootRoute.addChildren([indexRoute]), history });
  const queryClient = createQueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  await waitFor(() => {
    if (result.current === undefined) throw new Error("hook がまだ呼ばれていない");
  });
  return { result: result as { current: T }, history, router, queryClient };
};
